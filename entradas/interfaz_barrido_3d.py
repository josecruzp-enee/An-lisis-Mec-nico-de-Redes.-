"""Interfaz Streamlit del barrido termo-mecánico 3D (versión experimental).

Los datos de material faltantes se solicitan; nunca se inventan.
Los resultados son solicitaciones, NO verificaciones estructurales.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from entradas.io_excel import leer_puntos_excel
from entradas.catalogo_viakon_acsr import CONDUCTORES_VIAKON_ACSR
from entradas.tabla_catalogo_acsr import tabla_catalogo_acsr
from entradas.referencias_mecanicas_acsr import referencia_mecanica_nexans
from calculos.diagnostico_tension_acsr import diagnosticar_tensiones, resumen_tensiones
from calculos.barrido_no_lineal_3d import ejecutar_barrido_no_lineal_3d
from calculos.auditoria_cargas import auditar_reacciones_por_vano
from calculos.solicitaciones_poste import combinar_solicitaciones_postes
from calculos.verificacion_poste import calcular_secciones_poste, secciones_gobernantes
from calculos.resistencia_postes import (
    cribar_resistencia_postes, resumen_resistencia_postes, COLUMNAS_CAPACIDADES,
)
from calculos.analisis_retenidas_red import (
    leer_configuraciones_retenidas, evaluar_retenidas_en_barrido,
)
from calculos.envolventes_3d import (
    envolventes_apoyos, envolventes_vanos, mayores_por_apoyo,
)


def _numeros(texto, campo, positivos=False):
    """Convierte una lista de valores sin completar silenciosamente faltantes."""
    valores = []
    for parte in texto.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        valor = float(parte)
        if not math.isfinite(valor) or (positivos and valor <= 0):
            raise ValueError(f"{campo}: valores no válidos")
        valores.append(valor)
    if not valores:
        raise ValueError(f"{campo}: introduzca al menos un valor")
    return valores


def _vanos_desde_excel(df):
    """Los amarres se expresan como desplazamientos XYZ relativos al terreno."""
    requeridas = ("Punto", "X", "Y", "Altitud", "Altura_Amarre_m")
    faltan = [c for c in requeridas if c not in df.columns]
    if faltan:
        raise ValueError("Faltan columnas para análisis 3D: " + ", ".join(faltan))
    if df[list(requeridas)].isna().any().any():
        raise ValueError("Hay cotas o alturas de amarre vacías")
    h = df["Altura_Amarre_m"].astype(float)
    if (h <= 0).any() or not h.map(math.isfinite).all():
        raise ValueError("Altura_Amarre_m debe ser positiva y finita")
    resultado = []
    for i in range(len(df)-1):
        a, b = df.iloc[i], df.iloc[i+1]
        resultado.append({
            "nombre": f"{a['Punto']} → {b['Punto']}",
            "inicio": str(a["Punto"]), "fin": str(b["Punto"]),
            "base_inicio_m": [float(a["X"]), float(a["Y"]), float(a["Altitud"])],
            "base_fin_m": [float(b["X"]), float(b["Y"]), float(b["Altitud"])],
            "amarre_inicio_m": [0, 0, float(a["Altura_Amarre_m"])],
            "amarre_fin_m": [0, 0, float(b["Altura_Amarre_m"])],
        })
    return resultado


def mostrar_barrido_3d():
    """Pantalla sencilla: 4 parámetros de uso y opciones técnicas desplegables."""
    st.subheader("Análisis termomecánico 3D")
    st.caption(
        "Módulo 01 — Conductores. El motor no lineal calcula tensiones, "
        "flechas y fuerzas en cada extremo, con viento local y variación "
        "térmica. Esta vista presupone amarres fijos: no debe utilizarse "
        "como cálculo de continuidad de suspensiones o de red completa."
    )
    archivo = st.file_uploader(
        "Excel de postes y coordenadas", type=["xlsx"],
        key="archivo_barrido_3d",
    )
    calibres = list(CONDUCTORES_VIAKON_ACSR)
    with st.expander("Consultar catálogo de conductores ACSR", expanded=False):
        tabla_acsr = tabla_catalogo_acsr()
        st.caption(
            "Datos nominales: Viakon. Columnas de E/EA/alpha: "
            "referencias comparativas Nexans por construcción; "
            "NO propiedades certificadas de Viakon."
        )
        st.dataframe(tabla_acsr, use_container_width=True, hide_index=True)
        st.download_button(
            "Exportar catálogo ACSR CSV",
            tabla_acsr.to_csv(index=False).encode("utf-8-sig"),
            file_name="catalogo_acsr_viakon_referencias.csv",
            mime="text/csv",
        )
    with st.form("config_barrido_3d"):
        a, b, c = st.columns(3)
        with a:
            calibre = st.selectbox(
                "Conductor", calibres,
                index=calibres.index("2/0 ACSR — QUAIL") if "2/0 ACSR — QUAIL" in calibres else 0,
            )
        with b:
            h0 = st.number_input(
                "Tensión inicial por conductor (kN)",
                min_value=0.1, value=6.0, step=0.5,
                help="Condición de tendido del estudio. El valor 6 kN es solo "
                     "el dato de nuestro ensayo, no una recomendación.",
            )
        with c:
            vmax = st.number_input(
                "Velocidad máxima de viento (m/s)",
                min_value=0, max_value=80, value=20, step=1,
            )
        with st.expander("Configuración avanzada — opcional", expanded=False):
            st.caption(
                "El barrido estándar usa viento de 0 a la velocidad máxima "
                "en pasos de 1 m/s. Direcciones: 0°, 90°, 180°, 270°."
            )
            col1, col2 = st.columns(2)
            with col1:
                cantidad = st.number_input(
                    "Conductores idénticos por vano", min_value=1,
                    max_value=12, value=3, step=1,
                )
                t0 = st.number_input(
                    "Temperatura de tendido (°C)", value=20.0, step=1.0,
                )
                temperaturas = st.text_input(
                    "Temperaturas del estudio (°C)", value="20,40",
                )
                tensiones = st.text_input(
                    "Tensiones adicionales (kN), separadas por coma",
                    value="",
                    help="Además de la tensión principal introducida arriba.",
                )
                rumbos = st.text_input(
                    "Azimuts de viento hacia (°)", value="0,90,180,270",
                )
            with col2:
                cd = st.number_input("Coeficiente aerodinámico Cd",
                                     min_value=0.01, value=1.2, step=0.05)
                rho = st.number_input("Densidad del aire (kg/m³)",
                                      min_value=0.1, value=1.225, step=0.01)
                st.markdown("**Propiedades termoelásticas del conductor**")
                propiedades = st.radio(
                    "Origen de EA y dilatación térmica",
                    ["Demostración con parámetros sintéticos",
                     "Referencia Nexans por construcción (solo comparativa)",
                     "Ficha técnica verificada"],
                    index=1,
                    help="La demostración NO genera resultados aptos para diseño.",
                )
                ea_texto = st.text_input("Rigidez EA (kN)", value="")
                alfa_texto = st.text_input("Dilatación térmica α (1/°C)", value="")
                fuente = st.text_input("Fabricante / documento / revisión",
                                       value="")
        enviar = st.form_submit_button("Calcular", type="primary")

    if not enviar:
        return
    if archivo is None:
        st.error("Primero cargá el Excel.")
        return
    try:
        t_lista = _numeros(temperaturas, "temperaturas")
        h_lista = [float(h0)] + (_numeros(tensiones, "tensiones adicionales", True)
                                  if tensiones.strip() else [])
        h_lista = list(dict.fromkeys(h_lista))
        r_lista = _numeros(rumbos, "direcciones")
        # Carga limitada para que el cálculo interactivo sea razonable.
        n_casos = (vmax + 1) * len(t_lista) * len(h_lista) * len(r_lista)
        if n_casos > 500:
            raise ValueError(
                f"Hay {n_casos} combinaciones. El límite interactivo es 500; "
                "reducí las direcciones o temperaturas en configuración avanzada."
            )
        df = leer_puntos_excel(archivo)
        vanos = _vanos_desde_excel(df)
        ficha = CONDUCTORES_VIAKON_ACSR[calibre]
        # Un estado inicial que ya iguala la rotura nominal no debe
        # ingresar al BVP lineal como si el cable permaneciera íntegro.
        limite_rotura=float(ficha["carga_rotura_kN"])
        for tension_inicial in h_lista:
            if tension_inicial >= limite_rotura:
                raise ValueError(
                    "La tensión inicial por conductor "
                    f"{tension_inicial:g} kN alcanza o supera la "
                    f"ruptura nominal Viakon de {limite_rotura:.3f} kN. "
                    "No se calcula un cable ficticiamente intacto."
                )
        if propiedades == "Ficha técnica verificada":
            if not ea_texto.strip() or not alfa_texto.strip() or not fuente.strip():
                raise ValueError(
                    "Para cálculo con propiedades documentadas, ingresá EA, α "
                    "y su fuente en configuración avanzada."
                )
            ea = float(ea_texto)
            alfa = float(alfa_texto)
            fuente_modelo = ficha["documento"] + " (peso/diámetro); EA/α: " + fuente
            demostracion = False
            referencia_no_certificada = False
        elif propiedades == "Referencia Nexans por construcción (solo comparativa)":
            ref = referencia_mecanica_nexans(calibre)
            ea = ref["EA_final_referencia_kN"]
            alfa = ref["alpha_final_referencia_por_C"]
            fuente_modelo = (
                ficha["documento"] + " (masa y diámetro); "
                + "Nexans E FINAL y alpha FINAL por construcción "
                + ref["configuracion"] + " (solo comparación): " + ref["fuente"]
            )
            demostracion = False
            referencia_no_certificada = True
        else:
            # PARÁMETROS SINTÉTICOS DEL ENSAYO, nunca propiedades ACSR 2/0.
            ea, alfa = 16000.0, 1.8e-5
            fuente_modelo = (
                "DEMOSTRACIÓN SINTÉTICA: EA=16000 kN, α=1.8e-5 1/°C; "
                "NO representan ficha del conductor seleccionado; masa y diámetro Viakon"
            )
            demostracion = True
            referencia_no_certificada = False
        resultado = ejecutar_barrido_no_lineal_3d(
            vanos,
            peso_kN_m=ficha["peso_kg_m"] * 9.80665 / 1000,
            diametro_m=ficha["diametro_m"],
            EA_kN=ea, alpha_por_C=alfa,
            temperatura_tendido_C=t0,
            temperaturas_C=t_lista, tensiones_iniciales_kN=h_lista,
            viento_min_ms=0, viento_max_ms=float(vmax),
            incremento_viento_ms=1,
            direcciones_viento_deg=r_lista,
            Cd=cd, rho_kg_m3=rho,
            cantidad_conductores=int(cantidad),
            fuente_conductor=fuente_modelo,
        )
        diagnostico_tension = diagnosticar_tensiones(resultado["vanos"], calibre)
        resumen_tension = resumen_tensiones(diagnostico_tension)
        # Se comprueba ANTES de mostrar resultados que la carga de todos
        # los extremos de vano coincide con las seis componentes por poste.
        auditoria = auditar_reacciones_por_vano(
            resultado["extremos"], resultado["nodos"]
        )
        st.caption(
            "Conductor: " + ficha["nombre_mostrado"]
            + " · construcción " + str(ficha["hilos_aluminio"])
            + "/" + str(ficha["hilos_acero"])
            + " (Al/acero) · diámetro " + str(ficha["diametro_mm"])
            + " mm · peso " + str(ficha["peso_kg_km"])
            + " kg/km · ruptura nominal " + str(ficha["TR_kgf"])
            + " kgf. Fuente: " + ficha["documento"]
            + ". La carga de ruptura NO es tensión admisible."
        )
        if demostracion:
            st.error(
                "RESULTADOS DE DEMOSTRACIÓN: se utilizaron EA y α SINTÉTICOS. "
                "No son las propiedades del ACSR seleccionado y NO sirven "
                "para dimensionamiento. Introducí la ficha técnica verificada "
                "en Configuración avanzada para un análisis del material real."
            )
        elif referencia_no_certificada:
            st.warning(
                "ESTUDIO COMPARATIVO: módulo elástico FINAL y dilatación "
                "FINAL de Nexans para una construcción equivalente, "
                "NO datos certificados de Viakon ni del estado inicial "
                "de tendido. No apto para dimensionamiento. "
                "Se mantienen las limitaciones de amarres fijos y "
                "elasticidad lineal. "
                f"E_final={ref['E_final_GPa']:.2f} GPa; "
                f"EA={ea:.1f} kN; alpha={alfa:.3e} 1/°C."
            )
        else:
            st.warning(
                "Solicitaciones calculadas con las propiedades ingresadas. "
                "El conductor se resuelve con BVP no lineal y viento "
                "normal a la tangente local. Los vanos siguen modelados "
                "con amarres fijos; NO hay continuidad automática ni "
                "verificación de postes, anclajes o cimentaciones."
            )
        st.success(
            f"{n_casos} estados × {len(vanos)} vanos; "
            f"{len(resultado['nodos'])} filas de acciones acumuladas. "
            "Motor: problema de contorno 3D no lineal (BVP)."
        )
        st.caption(
            "Cada vano: amarres fijos, conductor flexible con elasticidad "
            "axial lineal y coeficiente de arrastre constante. "
            "Las flechas usan la curva BVP; el despeje respecto al terreno "
            "lineal NO reemplaza un levantamiento topográfico."
        )
        st.markdown("### Control de tensión del conductor")
        st.dataframe(resumen_tension, use_container_width=True, hide_index=True)
        st.caption(
            "La carga nominal de ruptura de Viakon no es la tensión "
            "admisible de diseño. Una relación inferior a 1 no representa "
            "cumplimiento de tensión EDS/EDA ni de la norma aplicable."
        )
        if (diagnostico_tension["Relación T máxima / ruptura"] >= 1).any():
            st.error(
                "Se han calculado casos que alcanzan o superan la "
                "carga nominal de ruptura del conductor. El cálculo "
                "no acredita que esos estados puedan existir sin falla."
            )
            st.stop()
        st.caption(
            "Auditoría de cargas por extremos: "
            f"{auditoria['Filas extremos']} registros y residual máximo "
            f"{auditoria['Residual máximo carga o momento']:.2e}. "
            "Desglose disponible en Fuerzas y momentos por poste."
        )
        # Sumar el viento sobre el fuste al nivel del terreno.
        # No confundir las fuerzas SOLO de cables con acciones TOTALES.
        acciones_combinadas = combinar_solicitaciones_postes(
            resultado["nodos"], df, rho_kg_m3=rho, Cd_poste=cd,
        )
        completas = acciones_combinadas.loc[
            acciones_combinadas["Estado viento poste"].str.startswith("INCLUIDO")
        ].copy()
        pendientes = acciones_combinadas.loc[
            ~acciones_combinadas["Estado viento poste"].str.startswith("INCLUIDO"),
            "Punto",
        ].drop_duplicates().tolist()
        if pendientes:
            st.warning(
                "Sin geometría de poste para: " + ", ".join(pendientes)
                + ". Esos apoyos no figuran en los máximos combinados."
            )
        st.caption(
            "Acciones al terreno = conductores + viento sobre fuste cónico. "
            "El empotramiento se toma del Excel si existe; en caso contrario "
            "se estima con 10% de la longitud + 2 pies y NO se valida. "
            "No incluye viento sobre aisladores ni herrajes, peso propio, "
            "capacidad estructural o interacción suelo-poste."
        )
        if completas.empty:
            st.error("No hay geometrías de postes suficientes para sumar el viento.")
            return
        # Presentación de casos gobernantes. NO implica cumplimiento estructural.
        resumen = mayores_por_apoyo(completas)
        estados_postes = envolventes_apoyos(completas)
        estados_vanos = envolventes_vanos(resultado["vanos"])

        # La hoja opcional Retenidas contiene puntos XYZ REALES relativos
        # a la base de cada poste. Si no existe, no se asume geometría.
        retenidas_estado = None
        retenidas_detalles = None
        from io import BytesIO
        if "Retenidas" in pd.ExcelFile(BytesIO(archivo.getvalue())).sheet_names:
            tabla_retenidas = pd.read_excel(
                BytesIO(archivo.getvalue()), sheet_name="Retenidas"
            )
            geometria_retenidas = leer_configuraciones_retenidas(
                tabla_retenidas
            )
            retenidas_estado, retenidas_detalles = evaluar_retenidas_en_barrido(
                completas, geometria_retenidas
            )
        st.markdown("### Demandas máximas por poste")
        st.dataframe(resumen, use_container_width=True, hide_index=True)
        secciones = calcular_secciones_poste(
            resultado["nodos"], df, cantidad_secciones=21,
            rho_kg_m3=rho, Cd_poste=cd,
        )
        criticas = secciones_gobernantes(secciones)
        st.markdown("### Secciones críticas del fuste")
        st.dataframe(criticas, use_container_width=True, hide_index=True)
        # Las resistencias se leen de una ficha de diseño por sección.
        # La ausencia de ficha NUNCA se suple con carga de ruptura nominal.
        capacidades_tabla = None
        capacidades_cribado = None
        resumen_cribado = None
        if "Capacidades" in pd.ExcelFile(BytesIO(archivo.getvalue())).sheet_names:
            capacidades_tabla = pd.read_excel(
                BytesIO(archivo.getvalue()), sheet_name="Capacidades"
            )
            capacidades_cribado = cribar_resistencia_postes(
                secciones, capacidades_tabla
            )
            resumen_cribado = resumen_resistencia_postes(capacidades_cribado)
        if resumen_cribado is not None:
            st.markdown("### Cribado de capacidad resistente documentada")
            st.dataframe(resumen_cribado,
                         use_container_width=True, hide_index=True)
            st.warning(
                "Una demanda que exceda su límite individual queda "
                "identificada. Estar por debajo NO equivale a CUMPLE: "
                "faltan las interacciones mecánicas, estabilidad, "
                "estado real del poste y verificación de cimentación."
            )
        st.caption(
            "Acciones por secciones desde el terreno hasta la punta. "
            "El diámetro mostrado es EXTERIOR: no se calcula tensión del "
            "material sin espesor, refuerzo y propiedades resistentes. "
            "No incluye peso propio ni accesorios. Se emplea un amarre "
            "agrupado por punto; fases con alturas distintas requieren "
            "un modelo de amarres individuales."
        )
        st.caption(
            "H y M pueden ser gobernadas por estados diferentes. "
            "NO combine sus máximos como un único vector de cargas."
        )
        t1, t2, t3, t4, t5, t6, t7 = st.tabs([
            "Casos gobernantes", "Curvas de viento", "Tensiones por vano",
            "Fuerzas y momentos por poste", "Esfuerzos por sección",
            "Retenidas XYZ", "Resistencia de postes",
        ])
        with t1:
            st.markdown("**Envolvente por componente de cada poste**")
            st.dataframe(estados_postes, use_container_width=True, hide_index=True)
            st.markdown("**Envolvente de tensiones por vano**")
            st.dataframe(estados_vanos, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar envolventes de apoyos CSV",
                estados_postes.to_csv(index=False).encode("utf-8-sig"),
                "envolventes_apoyos_3d.csv", mime="text/csv",
            )
        with t2:
            tabla = completas
            poste = st.selectbox(
                "Poste", tabla["Punto"].drop_duplicates().tolist(),
                key="poste_grafica_3d",
            )
            h_graf = st.selectbox(
                "Tensión inicial (kN)", sorted(tabla["H inicial (kN)"].unique()),
                key="h_grafica_3d",
            )
            t_graf = st.selectbox(
                "Temperatura (°C)", sorted(tabla["Temperatura (°C)"].unique()),
                key="t_grafica_3d",
            )
            graf = tabla.loc[
                (tabla["Punto"] == poste)
                & (tabla["H inicial (kN)"] == h_graf)
                & (tabla["Temperatura (°C)"] == t_graf)
            ].copy()
            graf["M resultante (kN·m)"] = (
                graf["Mx (kN·m)"]**2 + graf["My (kN·m)"]**2
            )**0.5
            pivot_h = graf.pivot_table(
                index="Viento (m/s)", columns="Azimut viento (°)",
                values="H resultante (kN)",
            )
            st.markdown("**Fuerza horizontal resultante vs. viento**")
            st.line_chart(pivot_h, x_label="Velocidad viento (m/s)",
                          y_label="H (kN)")
            pivot_m = graf.pivot_table(
                index="Viento (m/s)", columns="Azimut viento (°)",
                values="M resultante (kN·m)",
            )
            st.markdown("**Momento flector resultante vs. viento**")
            st.line_chart(pivot_m, x_label="Velocidad viento (m/s)",
                          y_label="M (kN·m)")
        with t3:
            st.dataframe(resultado["vanos"], use_container_width=True)
            st.download_button(
                "Descargar tensiones CSV",
                resultado["vanos"].to_csv(index=False).encode("utf-8-sig"),
                "tensiones_barrido_3d.csv", mime="text/csv",
            )
        with t4:
            st.dataframe(acciones_combinadas, use_container_width=True)
            with st.expander("Ver aporte de cada vano y extremo", expanded=False):
                st.caption(
                    "Cargas de conductores antes de sumar viento sobre el poste. "
                    "Cada fila identifica el caso climático, vano y apoyo; "
                    "la suma de las seis componentes se audita automáticamente."
                )
                st.dataframe(
                    resultado["extremos"], use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Exportar aportes por extremo CSV",
                    resultado["extremos"].to_csv(index=False).encode("utf-8-sig"),
                    "cargas_por_vano_y_extremo.csv", mime="text/csv",
                )
            st.download_button(
                "Descargar fuerzas y momentos CSV",
                acciones_combinadas.to_csv(index=False).encode("utf-8-sig"),
                "acciones_barrido_3d.csv", mime="text/csv",
            )
        with t5:
            poste_seccion = st.selectbox(
                "Poste para diagrama de solicitaciones",
                secciones["Punto"].drop_duplicates().tolist(),
                key="poste_seccion_3d",
            )
            corte = secciones.loc[
                (secciones["Punto"] == poste_seccion)
                & (secciones["Estado sección"] ==
                   "SOLICITACIÓN, RESISTENCIA NO VERIFICABLE")
            ].copy()
            if corte.empty:
                st.info("Sin geometría suficiente para obtener secciones.")
            else:
                caso_seccion = st.selectbox(
                    "Caso de carga",
                    corte["Caso"].drop_duplicates().tolist(),
                    key="caso_seccion_3d",
                )
                diagrama = corte.loc[corte["Caso"] == caso_seccion]
                st.markdown("**Momento flector a lo largo del fuste**")
                st.line_chart(
                    diagrama.set_index("Altura corte (m)")["M flector (kN·m)"],
                    x_label="Altura sobre terreno (m)",
                    y_label="Momento (kN·m)",
                )
                st.markdown("**Cortante transversal a lo largo del fuste**")
                st.line_chart(
                    diagrama.set_index("Altura corte (m)")["V transversal (kN)"],
                    x_label="Altura sobre terreno (m)",
                    y_label="Cortante (kN)",
                )
                st.dataframe(diagrama, use_container_width=True, hide_index=True)
            st.download_button(
                "Exportar solicitaciones por sección CSV",
                secciones.to_csv(index=False).encode("utf-8-sig"),
                "secciones_postes_3d.csv", mime="text/csv",
            )
        with t6:
            st.caption(
                "Para evaluar retenidas, agregá al mismo libro Excel una hoja "
                "'Retenidas' con columnas: Punto, Retenida, Amarre_X_m, "
                "Amarre_Y_m, Amarre_Z_m, Anclaje_X_m, Anclaje_Y_m, "
                "Anclaje_Z_m. Las coordenadas son locales respecto a la "
                "base del poste en metros. Opcionales: T_limite_kN y "
                "Fuente_limite. No se presupone ninguna orientación."
            )
            if retenidas_estado is None:
                st.info(
                    "No hay hoja 'Retenidas' en el Excel. "
                    "El análisis de postes se mantiene sin retenidas."
                )
            else:
                st.warning(
                    "Estudio de FACTIBILIDAD ESTÁTICA, no diseño: "
                    "se determina si las direcciones XYZ podrían equilibrar "
                    "momentos con cables que solo trabajan a tracción. "
                    "No se han modelado pretensiones, elongación, "
                    "deformación del poste ni interacción de anclajes y suelo."
                )
                st.dataframe(retenidas_estado, use_container_width=True)
                st.dataframe(retenidas_detalles, use_container_width=True)
                st.download_button(
                    "Descargar demanda de retenidas CSV",
                    retenidas_detalles.to_csv(index=False).encode("utf-8-sig"),
                    "demanda_retenidas_xyz.csv", mime="text/csv",
                )
        with t7:
            st.caption(
                "Para comprobar límites resistentes, agregá al Excel una "
                "hoja 'Capacidades' con resistencias de DISEÑO por poste "
                "y altura de corte, con fuente y criterio aplicable. "
                "No se utiliza la carga de ruptura nominal como admisible."
            )
            # Exportación de las cotas analizadas, SIN INVENTAR resistencias.
            cotas = secciones.loc[
                secciones["Estado sección"] ==
                "SOLICITACIÓN, RESISTENCIA NO VERIFICABLE",
                ["Punto", "Altura corte (m)"]
            ].drop_duplicates().copy()
            cotas.rename(
                columns={"Altura corte (m)": "Altura_corte_m"},
                inplace=True,
            )
            plantilla = pd.DataFrame(
                {k: cotas[k].tolist() if k in cotas
                 else [None] * len(cotas) for k in COLUMNAS_CAPACIDADES}
            )
            archivo_capacidad = BytesIO()
            with pd.ExcelWriter(archivo_capacidad, engine="openpyxl") as writer:
                plantilla.to_excel(
                    writer, sheet_name="Capacidades", index=False
                )
            st.download_button(
                "Descargar plantilla de capacidades por sección",
                archivo_capacidad.getvalue(),
                file_name="plantilla_capacidades_postes.xlsx",
                mime=("application/vnd.openxmlformats-officedocument."
                      "spreadsheetml.sheet"),
            )
            st.caption(
                "Completar todas las resistencias: Mx_Rd_kNm, My_Rd_kNm, "
                "V_Rd_kN, N_comp_Rd_kN, N_trac_Rd_kN, Mz_Rd_kNm. "
                "Cada valor requiere Fuente y Criterio_diseno. "
                "Los datos deben provenir de una verificación mecánica "
                "documentada, no de los diámetros exteriores."
            )
            if capacidades_cribado is None:
                st.info(
                    "No existe hoja Capacidades. Los postes siguen "
                    "con resistencia NO VERIFICABLE."
                )
            else:
                st.dataframe(
                    capacidades_cribado, use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Exportar cribado resistente CSV",
                    capacidades_cribado.to_csv(index=False).encode("utf-8-sig"),
                    "cribado_resistencia_postes.csv",
                    mime="text/csv",
                )
    except (ValueError, TypeError, OverflowError, KeyError, ZeroDivisionError) as exc:
        st.error(f"No se pudo calcular: {exc}")
