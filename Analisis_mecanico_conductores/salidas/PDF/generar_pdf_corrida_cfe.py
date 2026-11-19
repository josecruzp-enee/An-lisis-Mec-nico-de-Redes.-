"""Memoria profesional independiente del módulo 1: sin recalcular ingeniería.

Las tablas y gráficas se alimentan EXCLUSIVAMENTE de los resultados del motor.
Apto para combinar posteriormente con las memorias de los otros módulos.
"""
from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak,
    Image, KeepTogether, Table,
)

COLUMNAS = (
    "Condición", "Hipótesis", "Temperatura (°C)", "Viento (km/h)",
    "Hielo (mm)", "Vano", "Luz (m)", "P a 50 °C (m)", "H (kN)",
    "T máx. (kN)", "Flecha (m)", "Lateral (m)", "Residual (m)",
)


def _fmt(v, dec=3):
    if v is None or (not isinstance(v, (dict, list, tuple)) and pd.isna(v)):
        return "No informado"
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v):
            raise ValueError("El PDF no admite valores no finitos")
        if v != 0 and abs(v) < 0.0001:
            return f"{v:.2e}"
        return f"{v:,.{dec}f}"
    return str(v)


def _estilos():
    e = getSampleStyleSheet()
    e.add(ParagraphStyle(
        name="TituloM1", parent=e["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=colors.black, spaceAfter=5*mm,
    ))
    e.add(ParagraphStyle(
        name="SubM1", parent=e["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.black,
        spaceBefore=4*mm, spaceAfter=2*mm, keepWithNext=1,
    ))
    e.add(ParagraphStyle(
        name="NormalM1", parent=e["Normal"], fontSize=8.5, leading=12,
        textColor=colors.black, spaceAfter=2*mm,
    ))
    e.add(ParagraphStyle(
        name="NotaM1", parent=e["Normal"], fontSize=7.5, leading=10,
        textColor=colors.black, spaceAfter=2*mm,
    ))
    e.add(ParagraphStyle(
        name="CeldaM1", parent=e["Normal"], fontSize=7, leading=9,
        textColor=colors.black,
    ))
    e.add(ParagraphStyle(
        name="CabM1", parent=e["CeldaM1"], fontName="Helvetica-Bold",
    ))
    return e


def _p(texto, estilo):
    return Paragraph(escape(str(texto)).replace("\n", "<br/>"), estilo)


def _tabla(filas, anchos, estilos, *, encabezado=True, compacta=False):
    if not filas:
        return Spacer(1, 1)
    c, h = estilos["CeldaM1"], estilos["CabM1"]
    matriz = [[_p(v, h if i == 0 and encabezado else c) for v in row]
              for i, row in enumerate(filas)]
    tabla = LongTable(matriz, colWidths=anchos,
                      repeatRows=1 if encabezado else 0,
                      hAlign="LEFT", splitByRow=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#E5E5E5") if encabezado else colors.white),
        ("GRID", (0, 0), (-1, -1), .28, colors.HexColor("#AAAAAA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 if compacta else 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 if compacta else 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _grafico(tabla, campo, titulo, ylabel):
    datos = tabla[
        (tabla["Hipótesis"] == "Tabla térmica") &
        (tabla["Viento (km/h)"] == 0) &
        (tabla["Hielo (mm)"] == 0)
    ]
    if datos.empty:
        return None, None
    primer_vano = str(datos["Vano"].iloc[0])
    datos = datos[datos["Vano"].astype(str) == primer_vano]
    fig, ax = plt.subplots(figsize=(9.1, 2.55))
    for estado, estilo in (("Inicial", "-"), ("Final", "--")):
        serie = datos[datos["Condición"] == estado].sort_values("Temperatura (°C)")
        if len(serie) >= 2:
            ax.plot(serie["Temperatura (°C)"], serie[campo],
                    linestyle=estilo, linewidth=1.5, marker="o",
                    markersize=2.5, label=estado)
    ax.set_title(titulo + " — " + primer_vano, fontsize=10)
    ax.set_xlabel("Temperatura del conductor (°C)", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.grid(True, alpha=.25)
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=7)
    fig.tight_layout(pad=1.2)
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=155, facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer, primer_vano


def _cabecera_pie(canvas, doc):
    canvas.saveState()
    page_w, page_h = landscape(A4)
    canvas.setStrokeColor(colors.HexColor("#888888"))
    canvas.line(14*mm, page_h - 12*mm, page_w - 14*mm, page_h - 12*mm)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(14*mm, page_h - 10*mm, "MEMORIA DE CÁLCULO | MÓDULO 01")
    canvas.line(14*mm, 12*mm, page_w - 14*mm, 12*mm)
    canvas.drawString(14*mm, 8*mm, "Análisis mecánico de conductores")
    canvas.drawRightString(page_w - 14*mm, 8*mm, f"Página {doc.page}")
    canvas.restoreState()


def generar_pdf_corrida_cfe(*, resumen: pd.DataFrame, tabla: pd.DataFrame,
                            conductor: str, fuente_material: str,
                            clima: dict | None = None,
                            proyecto: dict | None = None,
                            propiedades_inicial: dict | None = None,
                            propiedades_final: dict | None = None,
                            geometria_xyz=None, puntos_apoyos=None,
                            libramientos=None, perfil_terreno=None) -> bytes:
    """Genera la memoria PDF desde DataFrames ya calculados, sin modificar valores."""
    if not isinstance(resumen, pd.DataFrame) or len(resumen) < 2 or len(resumen) % 2:
        raise ValueError("Se requieren referencias inicial/final para cada sección")
    if "Sección" in resumen and "Sección" not in tabla:
        raise ValueError("Falta el identificador de sección en la tabla")
    por_secciones = "Sección" in resumen and resumen["Sección"].nunique() > 1
    if por_secciones and not (resumen.groupby("Sección").size() == 2).all():
        raise ValueError("Cada sección debe tener referencias inicial y final")
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        raise ValueError("No hay resultados que documentar")
    falta = set(COLUMNAS) - set(tabla.columns)
    if falta:
        raise ValueError("Columnas requeridas ausentes: " + ", ".join(sorted(falta)))
    for c in ("H (kN)", "T máx. (kN)", "Flecha (m)",
              "Lateral (m)", "Residual (m)"):
        v = pd.to_numeric(tabla[c], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(v).all():
            raise ValueError(f"Valores inválidos en {c}")
    if (tabla["H (kN)"] <= 0).any() or (tabla["T máx. (kN)"] <= 0).any():
        raise ValueError("Las tensiones físicas deben ser positivas")

    proyecto, clima = proyecto or {}, clima or {}
    fuente = str(fuente_material)
    # Se usan únicamente magnitudes YA calculadas. Se comprueban las
    # hipótesis CFE por sección una sola vez y se reutilizan más adelante.
    control = None
    if propiedades_final and clima.get("viento_max_kmh") is not None:
        from Analisis_mecanico_conductores.salidas.PDF.verificacion_hipotesis_cfe import verificar_cinco_hipotesis
        clave = str(conductor).split()[-1].upper()
        controles = []
        for nombre, tabla_grupo in (tabla.groupby("Sección", sort=False)
                                    if por_secciones else [("S1", tabla)]):
            cc = verificar_cinco_hipotesis(
                tabla_grupo, ruptura_kN=float(propiedades_final["ruptura_kN"]),
                nombre_conductor=clave,
                viento_max_kmh=float(clima["viento_max_kmh"]),
                viento_reducido_kmh=float(clima.get("viento_reducido_kmh", 0.)),
                hielo_mm=float(clima.get("hielo_mm", 0.)),
            )
            cc.insert(0, "Sección", nombre)
            controles.append(cc)
        control = pd.concat(controles, ignore_index=True)
    if control is None:
        estado_ejecutivo = "CFE: sin evaluación documentada"
    elif (control["Estado"] == "SIN EVALUAR").any():
        estado_ejecutivo = "CFE: verificación incompleta"
    elif (control["Estado"] == "NO CUMPLE").any():
        estado_ejecutivo = "CFE: NO CUMPLE"
    else:
        caso_critico = control.loc[control["Utilización"].idxmax()]
        estado_ejecutivo = (
            f"CFE: CUMPLE H1-H5 en {control['Sección'].nunique()} sección(es); "
            f"gobierna {caso_critico['Sección']} / {caso_critico['Código']} "
            f"({_fmt(float(caso_critico['Utilización'])*100,1)} %)"
        )
    estilos = _estilos()
    pagina = landscape(A4)
    margen = 15*mm
    ancho = pagina[0] - 2*margen
    memoria = BytesIO()
    doc = SimpleDocTemplate(
        memoria, pagesize=pagina, leftMargin=margen, rightMargin=margen,
        topMargin=16*mm, bottomMargin=16*mm,
        title=f"Memoria de cálculo - Módulo 1 - {conductor}",
        author=str(proyecto.get("responsable") or "Proyecto eléctrico"),
    )
    historia = []
    normal, nota, sub = estilos["NormalM1"], estilos["NotaM1"], estilos["SubM1"]

    def linea(t, tipo=normal):
        historia.append(_p(t, tipo))
    def titulo(t):
        historia.append(_p(t, sub))
    def datos_tabla(filas, proporciones, compacto=False):
        colwidths = [ancho*x/sum(proporciones) for x in proporciones]
        historia.append(_tabla(filas, colwidths, estilos, compacta=compacto))
        historia.append(Spacer(1, 3*mm))

    # Página 1: informe ejecutivo, contexto, trazabilidad y diagnóstico.
    historia.append(Spacer(1, 8*mm))
    historia.append(_p("MÓDULO 01 - ANÁLISIS MECÁNICO DE CONDUCTORES",
                      estilos["TituloM1"]))
    linea("RESUMEN EJECUTIVO · UNA SOLA LÍNEA / SECCIONES INDEPENDIENTES")
    titulo("Resultado general de la línea")
    linea(estado_ejecutivo)
    datos_tabla([
        ["Tensión máxima del conductor","Flecha máxima vertical",
         "Vanos / secciones","Residual máximo"],
        [_fmt(tension,3)+" kN",_fmt(flecha,3)+" m",
         f"{numero_vanos} / {resumen['Sección'].nunique() if por_secciones else 1}",
         _fmt(residuo)+" m"],
    ],[1,1,1,1],compacto=True)
    datos_tabla([
        ["Resultado crítico","Vano","Condición / hipótesis","Temperatura"],
        ["Tensión total máxima",str(fila_tmax["Vano"]),
         str(fila_tmax["Condición"])+": "+str(fila_tmax["Hipótesis"]),
         _fmt(fila_tmax["Temperatura (°C)"],0)+" °C"],
        ["Flecha máxima",str(fila_fmax["Vano"]),
         str(fila_fmax["Condición"])+": "+str(fila_fmax["Hipótesis"]),
         _fmt(fila_fmax["Temperatura (°C)"],0)+" °C"],
    ],[1.1,1,2.2,.7],compacto=True)
    linea(
        "ALCANCE: los límites de tensión CFE se verifican en este módulo. "
        "No están verificadas las resistencias de postes, retenidas ni "
        "libramientos; las fuerzas de apoyos corresponden solo a conductores.",
        nota,
    )
    titulo("Datos generales")
    datos_tabla([
        ["Dato", "Información"],
        ["Proyecto", proyecto.get("nombre") or "No informado"],
        ["Conductor", conductor],
        ["Fecha", proyecto.get("fecha") or date.today().isoformat()],
        ["Responsable", proyecto.get("responsable") or "No informado"],
        ["Ubicación", proyecto.get("lugar") or "No informado"],
        ["Fuente de propiedades", fuente],
    ], [1.2, 4.2])

    titulo("Condiciones climáticas de la corrida")
    datos_tabla([
        ["Viento máximo (km/h)", "Viento reducido (km/h)",
         "Hielo radial (mm)", "Densidad de aire (kg/m³)"],
        [_fmt(clima.get("viento_max_kmh"), 1),
         _fmt(clima.get("viento_reducido_kmh"), 1),
         _fmt(clima.get("hielo_mm"), 1),
         _fmt(clima.get("rho_kg_m3"), 3)],
    ], [1, 1, 1, 1])

    if por_secciones:
        titulo("Secciones de tendido de la línea")
        f_secciones = [["Sección", "Remate inicial", "Remate final", "Vanos", "Longitud (m)"]]
        for nombre, grupo in tabla.groupby("Sección", sort=False):
            datos_vanos = grupo.drop_duplicates("Vano")
            r0 = resumen[resumen["Sección"] == nombre].iloc[0]
            f_secciones.append([
                nombre, str(r0["Remate inicial"]), str(r0["Remate final"]),
                str(len(datos_vanos)), _fmt(float(datos_vanos["Luz (m)"].sum()), 2),
            ])
        datos_tabla(f_secciones, [1,1.2,1.2,.8,1.3], compacto=True)
        linea("Las secciones se tienden entre remates de forma independiente. "
              "Una sola memoria reúne el cálculo y su envolvente global; "
              "no se transfiere material entre secciones.", nota)

    # Primera lectura gráfica: plano completo y esfuerzos por apoyo.
    # Red completa: sumas de fuerzas en cada apoyo, con referencia a los
    # dos extremos del cable y las secciones de tendido del mismo modelo.
    if puntos_apoyos is not None:
        if not (propiedades_inicial and propiedades_final):
            raise ValueError("Faltan propiedades para obtener fuerzas de apoyos")
        from Analisis_mecanico_conductores.salidas.PDF.fuerzas_apoyos_cfe import (
            calcular_fuerzas_por_apoyo, grafico_red_y_fuerzas,
        )
        detalles, fuerzas, envolventes = calcular_fuerzas_por_apoyo(
            tabla,puntos_apoyos,{"Inicial":propiedades_inicial,
                                "Final":propiedades_final},clima,
        )
        historia.append(PageBreak())
        titulo("Plano general de red y esfuerzos del conductor")
        linea(
            "Las flechas muestran componentes horizontales de las fuerzas "
            "calculadas que ejercen los cables SOBRE cada apoyo en H4. "
            "Cada vano conserva su propia tensión de tendido según su sección. "
            "Las flechas están amplificadas para visualizar su dirección; "
            "no representan desplazamientos de los postes.",nota,
        )
        figura_red=grafico_red_y_fuerzas(puntos_apoyos,detalles,fuerzas,
                                         hipotesis="H4")
        historia.append(Image(figura_red,width=245*mm,height=95*mm))
        linea(
            "ATENCIÓN: el viento CFE se evalúa transversalmente en cada vano "
            "como envolvente local; las resultantes H4/H5 NO corresponden "
            "necesariamente a un viento de azimut único sobre toda la red. "
            "No incluyen peso ni viento del poste, cruceta o retenida.",nota,
        )
        titulo("Fuerzas críticas por apoyo (envolvente H1–H5)")
        filas_env=[["Apoyo","Hipótesis","Fx (kN)","Fy (kN)","Fz (kN)",
                    "|F| (kN)"]]
        for _,r in envolventes.iterrows():
            filas_env.append([
                r["Apoyo"],r["Hipótesis"],
                _fmt(r["Fx (kN)"],3),_fmt(r["Fy (kN)"],3),
                _fmt(r["Fz (kN)"],3),_fmt(r["F resultante (kN)"],3),
            ])
        datos_tabla(filas_env,[1,1,1,1,1,1.1],compacto=True)
    historia.append(PageBreak())
    titulo("Resultados por sección y comprobación CFE")
    titulo("Referencias de tendido y criterio gobernante")
    rfilas = [[
        "Sección", "Condición", "H referencia 50 °C (kN)", "P referencia (m)",
        "Hipótesis gobernante", "Utilización",
    ]]
    for _, r in resumen.iterrows():
        rfilas.append([
            str(r.get("Sección", "S1")),
            "Inicial" if "Inicial" in str(r.get("Condición", "")) else "Final",
            _fmt(r.get("H_50_kN"), 4),
            _fmt(r.get("parametro_P_m"), 3),
            r.get("hipotesis_gobernante", "No informado"),
            _fmt(r.get("relacion_critica"), 4),
        ])
    datos_tabla(rfilas, [.8,1,1.2,1.2,3.1,1.0],compacto=True)
    linea(
        "H referencia es el parámetro de entrada para distribuir longitud "
        "durante el tendido continuo. No equivale a una componente H común "
        "en todos los vanos ni a la tensión de tracción de los apoyos.", nota,
    )
    modo_sin_creep = (
        "Creep adicional" in resumen.columns
        and float(resumen.iloc[0]["Creep adicional"]) == 0.
    )
    linea(
        ("Se mantiene la misma longitud natural por vano a 50 C en ambas "
         "condiciones: creep adicional = 0. Se conservan E y alfa CFE por "
         "condición; no se fuerza igualdad de tensión extrema."
         if modo_sin_creep else
         "Condiciones inicial/final ajustadas por tensión extrema. "
         "No se dispone de ley constitutiva de creep."), nota,
    )

    # El diagnóstico toma la diferencia real de los estados publicados,
    # utilizando el alpha correspondiente a cada condición.
    if "Diferencia real de acoplamiento H4 (kN)" in resumen:
        for nombre, grupo in (resumen.groupby("Sección", sort=False)
                              if por_secciones else [("S1", resumen)]):
            diagnostico=grupo.iloc[0]
            diferencia=float(diagnostico["Diferencia real de acoplamiento H4 (kN)"])
            porcentaje=float(diagnostico["Diferencia real de acoplamiento H4 (%)"])
            linea(
                f"{nombre}: diferencia de tensión extrema inicial/final H4 "
                f"= {diferencia:.5f} kN ({porcentaje:.2f} %). "
                "No se impone igualdad de tensión; con creep adicional cero "
                "la longitud natural de cada vano es común.", nota,
            )

    residuo = float(tabla["Residual (m)"].abs().max())
    tension = float(tabla["T máx. (kN)"].max())
    flecha = float(tabla["Flecha (m)"].max())
    fila_tmax = tabla.loc[tabla["T máx. (kN)"].idxmax()]
    fila_fmax = tabla.loc[tabla["Flecha (m)"].idxmax()]
    numero_vanos = int(tabla["Vano"].nunique())
    # Estas magnitudes son envolventes de TODAS las filas, no solamente H1-H5.
    # La hipótesis gobernante por utilización es un indicador distinto.
    titulo("Valores críticos identificados")
    datos_tabla([
        ["Magnitud", "Valor", "Vano", "Estado", "Escenario / temperatura"],
        ["Mayor tensión total", _fmt(tension, 4) + " kN",
         str(fila_tmax["Vano"]), str(fila_tmax["Condición"]),
         str(fila_tmax["Hipótesis"]) + " / " +
         _fmt(fila_tmax["Temperatura (°C)"], 0) + " °C"],
        ["Mayor flecha vertical", _fmt(flecha, 4) + " m",
         str(fila_fmax["Vano"]), str(fila_fmax["Condición"]),
         str(fila_fmax["Hipótesis"]) + " / " +
         _fmt(fila_fmax["Temperatura (°C)"], 0) + " °C"],
    ], [1.3, 1.0, 1.0, 0.8, 2.7], compacto=True)
    linea("La condición que produce la mayor tensión absoluta no tiene "
          "por qué coincidir con la hipótesis de mayor utilización: los "
          "límites admisibles son distintos.", nota)
    historia.append(PageBreak())

    # Página 2: supuestos, ecuaciones y curvas sin estimaciones inventadas.
    titulo("Datos mecánicos y metodología")
    if propiedades_inicial and propiedades_final:
        mecanica = [["Propiedad", "Condición inicial", "Condición final", "Unidad"]]
        for etiqueta, key, unidad, escala in [
            ("Peso propio", "peso_kN_m", "N/m", 1000),
            ("Diámetro", "diametro_m", "mm", 1000),
            ("Rigidez axial EA", "EA_kN", "kN", 1),
            ("Dilatación térmica", "alpha_por_C", "1/°C", 1),
            ("Carga de ruptura", "ruptura_kN", "kN", 1),
        ]:
            def v(prop):
                dato = prop.get(key)
                if dato is None:
                    return "No informado"
                if key == "alpha_por_C":
                    return f"{float(dato):.5e}"
                return _fmt(float(dato)*escala, 6)
            mecanica.append([etiqueta, v(propiedades_inicial), v(propiedades_final), unidad])
        datos_tabla(mecanica, [2, 1.5, 1.5, 1])
    else:
        linea("No se suministraron al generador las propiedades mecánicas "
              "empleadas; la fuente seleccionada figura en la identificación.", nota)

    linea("Modelo adoptado: conductor flexible, catenaria hiperbólica bajo carga "
          "constante por unidad de longitud real; elasticidad axial lineal y "
          "temperatura uniforme. Cambios de estado resueltos por compatibilidad "
          "integral y búsqueda no lineal.", nota)
    linea("Relaciones básicas (vano nivelado sin viento):", nota)
    linea("P = H / q     |     f = P [cosh(L / 2P) - 1]     |     "
          "S = 2P sinh(L / 2P)", nota)
    linea("Compatibilidad: S0 = integral [ds / (1 + T(s)/EA)]. "
          "La longitud térmica de referencia varía según alfa y temperatura. "
          "Para geometría desnivelada se utiliza la solución de catenaria "
          "en el plano de la carga resultante.", nota)
    linea("Los resultados de referencia inicial/final se obtienen mediante "
          "las hipótesis del motor. No se atribuye una ley de creep no modelada "
          "ni se presentan límites de postes o retenidas como verificados.", nota)

    # Las dos curvas se colocan juntas, evitando páginas casi vacías.
    # La fuente de datos sigue siendo la misma tabla calculada por el motor.
    graficos = []
    for campo, titulo_g, unidad in [
        ("H (kN)", "Tensión horizontal vs. temperatura", "H (kN)"),
        ("Flecha (m)", "Flecha vs. temperatura", "Flecha (m)"),
    ]:
        png, vano = _grafico(tabla, campo, titulo_g, unidad)
        if png is not None:
            graficos.append((png, campo))
    if graficos:
        imagenes = [Image(png, width=115*mm, height=38*mm)
                    for png, _ in graficos]
        if len(imagenes) == 2:
            composicion = Table([[imagenes[0], imagenes[1]]],
                                colWidths=[ancho/2, ancho/2],
                                hAlign="LEFT")
            composicion.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING", (0,0), (-1,-1), 1),
                ("RIGHTPADDING", (0,0), (-1,-1), 1),
                ("TOPPADDING", (0,0), (-1,-1), 1),
                ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ]))
            historia.append(KeepTogether([
                _p("Curvas de comportamiento térmico", sub),
                composicion,
            ]))
        else:
            titulo("Curvas de comportamiento térmico")
            historia.extend(imagenes)
        linea("Las curvas representan el primer vano de la corrida y "
              "solamente las hipótesis térmicas sin viento ni hielo. "
              "Todos los vanos y escenarios se incluyen en los anexos.", nota)
    else:
        titulo("Curvas de comportamiento térmico")
        linea("No hay suficientes puntos de temperatura para dibujar curvas.", nota)

    # Control explícito de las CINCO hipótesis documentadas CFE.
    # Si no existe una fila calculada, se informa SIN EVALUAR.
    if control is not None:
        historia.append(PageBreak())
        titulo("Control de las cinco hipótesis mecánicas CFE")
        linea("Se verifican dos magnitudes distintas: T total frente al "
              "porcentaje RTS y H frente al límite horizontal TH1/TH2 "
              "cuando corresponda. Uso % es el mayor de ambos cocientes; "
              "SIN EVALUAR indica estados no calculados.", nota)
        filas_control = [[
            "Sección", "Caso", "Estado", "Temp. °C", "Viento km/h", "Hielo mm",
            "T máx. kN", "Límite T kN", "H máx. kN", "Límite H kN",
            "Uso %", "Resultado",
        ]]
        for _, r in control.iterrows():
            uso = r["Utilización"]
            filas_control.append([
                r["Sección"],r["Código"], r["Condición"],
                _fmt(r["Temperatura (°C)"], 0),
                _fmt(r["Viento (km/h)"], 0),
                _fmt(r["Hielo (mm)"], 1),
                _fmt(r["T máxima (kN)"], 3) if pd.notna(r["T máxima (kN)"]) else "—",
                _fmt(r["Límite (kN)"], 3),
                _fmt(r["H máxima (kN)"], 3) if pd.notna(r["H máxima (kN)"]) else "—",
                _fmt(r["Límite H (kN)"], 3) if pd.notna(r["Límite H (kN)"]) else "—",
                _fmt(uso*100, 2) if pd.notna(uso) else "—",
                r["Estado"],
            ])
        datos_tabla(filas_control, [0.6,0.6,0.8,0.75,0.9,0.75,1.0,1.0,0.95,1.0,0.8,1.05],compacto=True)
        for _, r in control.iterrows():
            linea(f"{r['Sección']} — {r['Código']}: {r['Hipótesis']}", nota)
        if (control["Estado"] == "SIN EVALUAR").any():
            linea("No se puede declarar que se satisficieron las cinco "
                  "hipótesis: existen estados sin evaluar.", nota)
        elif (control["Estado"] == "NO CUMPLE").any():
            linea("NO CUMPLE: una o más hipótesis superan su límite de tensión.", nota)
        else:
            linea("Las cinco hipótesis satisfacen los límites de tensión "
                  "definidos por el procedimiento implementado. Esto NO "
                  "equivale a certificar despejes ni apoyos.", nota)

    # Topografía opcional: representa valores muestreados de la fuente DEM.
    # No afirma un mínimo exacto continuo ni una distancia reglamentaria.
    if libramientos is not None and perfil_terreno is not None:
        if libramientos.empty or perfil_terreno.empty:
            raise ValueError("La topografía no contiene resultados")
        historia.append(PageBreak())
        titulo("Perfil topográfico y libramientos — PRELIMINAR")
        linea(
            "Las cotas del terreno proceden del DEM seleccionado, no de "
            "un levantamiento de precisión. Las distancias son verticales, "
            "estimadas en puntos discretos del conductor con desplazamiento "
            "lateral incluido. NO se certifica cumplimiento reglamentario.",
            nota,
        )
        minimo_total=libramientos.sort_values(
            "Libramiento mínimo muestreado (m)",ascending=True
        )
        fila_global=minimo_total.iloc[0]
        linea(
            f"Menor separación muestreada: "
            f"{_fmt(float(fila_global['Libramiento mínimo muestreado (m)']),3)} m, "
            f"vano {fila_global['Vano']}, condición "
            f"{fila_global['Condición']} "
            f"({fila_global['Hipótesis']}).",nota,
        )
        filas_topo=[["Vano", "Condición", "Hipótesis", "Temp. °C",
                      "Separación min. (m)", "Distancia desde apoyo (m)"]]
        for _,r in minimo_total.iterrows():
            filas_topo.append([
                r["Vano"],r["Condición"],r["Hipótesis"],
                _fmt(float(r["Temperatura (°C)"]),0),
                _fmt(float(r["Libramiento mínimo muestreado (m)"]),3),
                _fmt(float(r["Distancia crítica desde apoyo (m)"]),2),
            ])
        datos_tabla(filas_topo,[1,1,2,1,1.3,1.5],compacto=True)
        for vano,grupo in minimo_total.groupby("Vano",sort=False):
            critico=grupo.iloc[0]
            subperfil=perfil_terreno[
                (perfil_terreno["Vano"]==vano)
                & (perfil_terreno["Condición"]==critico["Condición"])
                & (perfil_terreno["Hipótesis"]==critico["Hipótesis"])
                & (perfil_terreno["Temperatura (°C)"]==critico["Temperatura (°C)"])
            ].sort_values("Distancia desde apoyo (m)")
            if subperfil.empty:
                raise ValueError("No existe perfil para la hipótesis crítica")
            figura,eje=plt.subplots(figsize=(9.3,3.1))
            x=subperfil["Distancia desde apoyo (m)"].to_numpy(float)
            terreno=subperfil["Elevación terreno (m)"].to_numpy(float)
            cable=subperfil["Elevación conductor (m)"].to_numpy(float)
            eje.plot(x,terreno,color="#7a654a",lw=2,label="Superficie DEM")
            eje.plot(x,cable,color="#2355a4",lw=1.6,label="Conductor calculado")
            eje.fill_between(x,terreno,cable,alpha=.12,color="#64748b")
            eje.set_title(f"{vano} — condición de menor separación muestreada",fontsize=10)
            eje.set_xlabel("Distancia horizontal desde el apoyo (m)",fontsize=8)
            eje.set_ylabel("Elevación (m)",fontsize=8)
            eje.grid(alpha=.2)
            eje.legend(fontsize=8)
            figura.tight_layout()
            imagen=BytesIO()
            figura.savefig(imagen,format="png",dpi=155)
            plt.close(figura)
            imagen.seek(0)
            historia.append(PageBreak())
            titulo(f"Superposición DEM-catenaria — {vano}")
            historia.append(Image(imagen,width=224*mm,height=77*mm))
            linea(
                "Condición visualizada: "+str(critico["Condición"])+", "+
                str(critico["Hipótesis"])+", "+
                _fmt(float(critico["Temperatura (°C)"]),0)+" °C. "+
                "Cotas y mínimos de naturaleza preliminar.", nota,
            )

    # Láminas de catenaria EXACTA por vano: H ya calculada, misma carga
    # del motor. Contrasta flecha/desplazamiento con la tabla antes de dibujar.
    if geometria_xyz is not None:
        if not (propiedades_inicial and propiedades_final):
            raise ValueError("Se necesitan las propiedades reales para el perfil")
        from Analisis_mecanico_conductores.salidas.PDF.graficos_catenarias_cfe import graficar_perfiles_cfe
        perfiles = graficar_perfiles_cfe(
            tabla, geometria_xyz,
            {"Inicial": propiedades_inicial, "Final": propiedades_final},
            clima,
        )
        for nombre_vano, archivo_figura in perfiles:
            historia.append(PageBreak())
            titulo(f"Perfil de catenarias y desviación por viento — {nombre_vano}")
            linea(
                "Curvas obtenidas de la catenaria hiperbólica del motor con "
                "la tensión calculada para cada estado. Se muestran las "
                "hipótesis disponibles en la tabla y la condición térmica "
                "final de 50 °C cuando está calculada. La vista inferior "
                "representa la desviación lateral por viento.", nota,
            )
            historia.append(Image(archivo_figura, width=245*mm, height=128*mm))
            linea(
                "La línea punteada representa la cuerda entre amarres. "
                "No se ha supuesto perfil de terreno: no se certifica "
                "distancia mínima de seguridad ni libramiento.", nota,
            )

    # El dictamen se presenta ANTES de los anexos, para una lectura autónoma.
    historia.append(PageBreak())
    titulo("Conclusiones técnicas de la corrida")
    linea(
        f"Se analizaron {numero_vanos} vanos "
        + (f"distribuidos en {resumen['Sección'].nunique()} secciones mecánicas "
           if por_secciones else "")
        + f"y {len(tabla)} registros de "
        "estado inicial/final con las propiedades y cargas declaradas. "
        f"La máxima tensión total calculada es {_fmt(tension, 4)} kN "
        f"({fila_tmax['Vano']}, {fila_tmax['Condición']}, "
        f"{fila_tmax['Hipótesis']}, "
        f"{_fmt(fila_tmax['Temperatura (°C)'], 0)} °C); "
        f"la mayor flecha vertical es {_fmt(flecha, 4)} m "
        f"({fila_fmax['Vano']}, {fila_fmax['Condición']}, "
        f"{fila_fmax['Hipótesis']}, "
        f"{_fmt(fila_fmax['Temperatura (°C)'], 0)} °C)."
    )
    linea(
        "Las longitudes naturales por vano se determinan para el tendido "
        "continuo ideal y quedan fijadas por separado tras el amarre. "
        "Los cambios de temperatura y carga se resuelven posteriormente "
        "sin transferencia de material entre vanos. "
        "Los residuos de compatibilidad indican convergencia de las "
        "ecuaciones implementadas, no una validación física independiente."
    )
    linea(
        f"El mayor residuo de compatibilidad registrado es "
        f"{residuo:.3e} m. "
        + ("Inicial/final conservan la longitud natural por vano a 50 C "
           "con creep adicional nulo; no se predice su evolución material."
           if modo_sin_creep else
           "La vinculación de referencias no demuestra una ley de creep.")
    )
    if propiedades_final and clima.get("viento_max_kmh") is not None:
        estado_control = list(control["Estado"])
        if "SIN EVALUAR" in estado_control:
            dictamen = ("Verificación incompleta: hay hipótesis CFE sin "
                        "evaluar y no puede declararse cumplimiento de las cinco.")
        elif "NO CUMPLE" in estado_control:
            dictamen = ("La corrida NO CUMPLE al menos una de las cinco "
                        "hipótesis mecánicas CFE implementadas.")
        else:
            critico = control.loc[control["Utilización"].idxmax()]
            dictamen = (
                "Las cinco hipótesis CFE implementadas cumplen sus límites. "
                f"Gobierna {critico['Código']} "
                f"({_fmt(float(critico['Utilización'])*100, 2)} % de utilización)."
            )
        linea(dictamen)
    else:
        linea("No se dispone de un cuadro completo de verificación CFE "
              "en este reporte; no se declara cumplimiento de las cinco hipótesis.")
    linea(
        "Alcance: resultados mecánicos del conductor bajo las hipótesis "
        "indicadas. No se verifican capacidades de postes, crucetas, "
        "herrajes, retenidas, cimentaciones ni distancias de seguridad. "
        "Tampoco se representa creep predictivo o suspensión móvil real."
    )
    titulo("Criterio de aceptación del informe")
    linea(
        "Este informe permite revisar las magnitudes calculadas y el "
        "cumplimiento de las restricciones implementadas. No equivale "
        "a certificación de diseño ni a validación general del motor "
        "contra resultados experimentales o casos multivano independientes.",
        nota,
    )
    historia.append(PageBreak())

    # Anexos de trazabilidad: primero esfuerzos por caso y material fijado.
    if puntos_apoyos is not None:
        historia.append(PageBreak())
        titulo("Anexo C — Resultantes vectoriales por apoyo y caso")
        filas_f=[["Apoyo","Caso","Fx (kN)","Fy (kN)","Fz (kN)","|F| (kN)"]]
        for _,r in fuerzas.iterrows():
            filas_f.append([r["Apoyo"],r["Hipótesis"],
                            _fmt(r["Fx (kN)"],3),_fmt(r["Fy (kN)"],3),
                            _fmt(r["Fz (kN)"],3),_fmt(r["F resultante (kN)"],3)])
        datos_tabla(filas_f,[1,1,1,1,1,1.1],compacto=True)
        linea("Convención: ejes globales X/Y del Excel, Z positivo hacia arriba. "
              "Las sumas vectoriales se realizan por apoyo y por caso; "
              "no se suman máximos independientes de diferentes casos.",nota)

    titulo("Anexo D — Referencias longitudinales por vano")
    if "Longitud natural fijada (m)" in tabla:
        titulo("Longitudes naturales de referencia fijadas por vano")
        campos=["Sección","Condición","Vano","Luz (m)","Longitud natural fijada (m)"] if por_secciones else ["Condición","Vano","Luz (m)","Longitud natural fijada (m)"]
        datos=tabla[campos].drop_duplicates(["Condición","Vano"])
        filas=[(["Sección"] if por_secciones else []) + ["Condición","Vano","Luz (m)","L0 fijada (m)"]]
        for _,fila in datos.iterrows():
            filas.append(([fila["Sección"]] if por_secciones else []) + [
                fila["Condición"],fila["Vano"],
                _fmt(fila["Luz (m)"],2),
                _fmt(fila["Longitud natural fijada (m)"],6),
            ])
        datos_tabla(filas,([.6] if por_secciones else [])+[1,1.7,1,1.3],compacto=True)
    titulo("Anexo E — Comparación térmica por vano")
    # Se extraen exclusivamente resultados ya existentes, sin recalcular.
    termicos = tabla[
        (tabla["Hipótesis"] == "Tabla térmica") &
        (tabla["Viento (km/h)"] == 0) &
        (tabla["Hielo (mm)"] == 0) &
        (tabla["Temperatura (°C)"].isin([20., 50.]))
    ]
    if not termicos.empty:
        titulo("Comparación de tensiones y flechas por vano")
        filas_termicas = [["Vano", "Estado", "Temp. °C",
                           "T máxima (kN)", "H (kN)", "Flecha (m)"]]
        for _, r in termicos.sort_values(
                ["Vano", "Condición", "Temperatura (°C)"]).iterrows():
            filas_termicas.append([
                r["Vano"], r["Condición"],
                _fmt(r["Temperatura (°C)"], 0),
                _fmt(r["T máx. (kN)"], 4),
                _fmt(r["H (kN)"], 4),
                _fmt(r["Flecha (m)"], 4),
            ])
        datos_tabla(filas_termicas, [1.3, .9, .9, 1.2, 1.0, 1.1], compacto=True)
        linea("Se incluyen las temperaturas disponibles de 20 y 50 °C. "
              "Las restantes condiciones figuran en los anexos.", nota)
    historia.append(PageBreak())

    # Anexos separados por estado, para evitar una página final de una sola fila.
    for indice, estado in enumerate(("Inicial", "Final")):
        if indice:
            historia.append(PageBreak())
        titulo("Anexo " + ("F" if indice == 0 else "G") +
               " - Resultados completos, condición " + estado.lower())
        subtabla = tabla[tabla["Condición"] == estado]
        if subtabla.empty:
            linea("Sin resultados para este estado.")
            continue
        linea(f"{len(subtabla)} registros. T = tensión máxima del conductor; "
              "H = componente de tracción perpendicular a la carga; "
              "f = flecha vertical. Residual de compatibilidad en metros.", nota)
        encabezado = (["Sección"] if por_secciones else []) + [
            "Vano", "Escenario", "Temp. °C", "Viento km/h", "Hielo mm",
            "H kN", "T máx. kN", "Flecha m", "Lateral m", "Residual m"]
        filas = [encabezado]
        for _, r in subtabla.iterrows():
            escenario = ("Térmico" if str(r["Hipótesis"]) == "Tabla térmica"
                         else str(r["Hipótesis"]).replace("CFE ", ""))
            filas.append(
                ([r["Sección"]] if por_secciones else []) + [
                r["Vano"], escenario, _fmt(r["Temperatura (°C)"], 0),
                _fmt(r["Viento (km/h)"], 0), _fmt(r["Hielo (mm)"], 1),
                _fmt(r["H (kN)"], 4), _fmt(r["T máx. (kN)"], 4),
                _fmt(r["Flecha (m)"], 4), _fmt(r["Lateral (m)"], 4),
                _fmt(r["Residual (m)"]),
            ])
        datos_tabla(filas, ([.65] if por_secciones else []) + [1.1, 1.7, .8, .8, .7, .95, 1.05, 1, 1, 1.3], compacto=True)

    historia.append(Spacer(1, 5*mm))
    titulo("Observaciones y alcance")
    linea("Los valores corresponden a la geometría, propiedades y condiciones "
          "seleccionadas. Las ecuaciones de catenaria no incorporan "
          "rigidez flexional, plasticidad o creep predictivo. "
          "El tratamiento actual por vano amarrado no equivale "
          "automáticamente a una sección de suspensión móvil.", nota)
    linea("Los esfuerzos y verificaciones de postes, crucetas, herrajes, "
          "retenidas y cimentaciones corresponden a módulos posteriores.", nota)
    doc.build(historia, onFirstPage=_cabecera_pie, onLaterPages=_cabecera_pie)
    salida = memoria.getvalue()
    if not salida.startswith(b"%PDF"):
        raise ValueError("No se pudo construir la memoria")
    return salida
