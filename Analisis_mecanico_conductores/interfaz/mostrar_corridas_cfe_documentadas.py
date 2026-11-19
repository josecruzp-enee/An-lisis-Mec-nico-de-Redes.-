"""Streamlit: ejecución CFE con hipótesis documentadas sobre vanos reales."""
from __future__ import annotations

import streamlit as st
from motor_general import ejecutar_modulo

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee, seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    # El cálculo se coordina desde motor_general.
    DENSIDAD_HIELO_ENSAYO_KG_M3,
    seleccionar_propiedades_cfe_07_ft_01,
)


def mostrar_corridas_cfe(puntos):
    st.subheader("CFE — tensiones y flechas por vano real")
    st.caption(
        "Norma de referencia: CFE DCCIAMBT (2014), 05 00 02/03 y 07 FT 01. "
        "Conserva las ecuaciones de catenaria 3D y compatibilidad del motor. "
        "No introduce P, claro de diseño ni flecha ENEE como entradas."
    )
    st.info(
        "CLAROS: vano real = distancia entre apoyos; claro regla = equivalente "
        "convencional de una sección de tendido; claro de diseño = referencia "
        "del procedimiento normativo. El claro regla se mostrará solo como "
        "dato orientativo: este motor calcula amarres fijos por vano."
    )
    st.caption(
        "Remates: columna opcional Remate del Excel (SI/NO). "
        "P1 y último apoyo son remates por defecto; marcá SI en P3 "
        "si divide la línea. Cada sección se tiende independientemente."
    )
    opciones=[(f["calibre"],f["nombre"]) for f in leer_catalogo_enee()
             if f["nombre"] in ("RAVEN","PIGEON","PARTRIDGE","LINNET","HAWK")]
    if not opciones:
        st.error("No hay catálogo físico ENEE disponible")
        return
    with st.expander("Datos de identificación para la memoria PDF", expanded=False):
        proyecto_pdf = {
            "nombre": st.text_input("Nombre del proyecto", value="", key="m1_nombre"),
            "lugar": st.text_input("Municipio / ubicación", value="", key="m1_lugar"),
            "responsable": st.text_input("Responsable del cálculo", value="", key="m1_responsable"),
            "fecha": str(st.date_input("Fecha de la memoria", key="m1_fecha")),
        }
    from Analisis_mecanico_conductores.topografia.modelo_terreno import (
        leer_apoyos_kml, ElevacionesGeoTIFF, ElevacionesTerrarium,
        extraer_terreno_apoyos, calcular_libramientos_muestreados,
    )
    with st.expander("Topografía y libramientos (preliminares)", expanded=False):
        st.caption("Importá los apoyos KML y/o un DEM; no se inventan cotas ni alturas de amarre.")
        epsg_xy=st.number_input("EPSG del proyecto (X/Y UTM)",value=32616,min_value=2000,
                                 max_value=999999,key="m1_epsg")
        archivo_kml=st.file_uploader("KML de los apoyos",type="kml",key="m1_kml")
        puntos_topo=puntos
        if archivo_kml is not None:
            try:
                p_kml=leer_apoyos_kml(archivo_kml.getvalue(),epsg_xy=int(epsg_xy))
                st.info("Completá Altura_Amarre_m; las Altitud del KML se dejan vacías.")
                puntos_topo=st.data_editor(
                    p_kml,hide_index=True,num_rows="fixed",
                    disabled=["Punto","X","Y"],key="m1_cotas_kml",
                )
            except ValueError as exc:
                st.error(str(exc))
                puntos_topo=None
        fuente_topo=st.selectbox(
            "Fuente topográfica",
            ["Ninguna","GeoTIFF subido","Mapzen/AWS gratuito"],
            key="m1_dem_origen",
        )
        dem_archivo=(st.file_uploader("DEM GeoTIFF",type=["tif","tiff"],key="m1_dem")
                     if fuente_topo=="GeoTIFF subido" else None)
        sustituir_cotas=st.checkbox(
            "Sustituir expresamente las altitudes de los apoyos por el DEM",
            value=False,key="m1_dem_apoyos",
        )
        paso_topo=st.number_input("Paso de muestreo (m)",min_value=1.,
                                 max_value=20.,value=3.,key="m1_paso_dem")
        st.warning("Modelo preliminar: DEM no certifica distancias reglamentarias; "
                   "Mapzen/AWS requiere Internet.")
    with st.form("cfe_climas_documentados"):
        indice=next((i for i,x in enumerate(opciones) if x==("1/0","RAVEN")),0)
        conductor=st.selectbox(
            "Conductor del catálogo físico ENEE",opciones,index=indice,
            format_func=lambda x:f"{x[0]} — {x[1]}",
        )
        fuente_material=st.radio(
            "Propiedades mecánicas",
            ["CFE 07 FT 01 — fuente normativa", "ENEE Tabla 16 — comparación"],
            help="La reproducción CFE exige sus propiedades específicas; ENEE se conserva como alternativa comparativa.",
        )
        st.markdown("**Condiciones climáticas del proyecto**")
        viento_max=st.number_input(
            "Viento regional máximo (km/h)",min_value=1.,value=120.,
            help="Verificar la zona de viento prevista en CFE para el proyecto.",
        )
        viento_reducido=st.text_input(
            "Viento reducido (km/h) — condición del caso",value="109",
            help="No se inventa ni se deduce automáticamente del viento máximo.",
        )
        hielo=st.text_input(
            "Espesor de hielo radial (mm) — condición del caso",value="6",
            help="No se sustituye una hipótesis con hielo por hielo cero.",
        )
        rho=st.number_input(
            "Densidad de aire para cálculo aerodinámico (kg/m³)",
            min_value=.1,value=1.225,format="%.3f",
            help="Entrada física visible: 1.225 kg/m³ es el valor nominal usado por el motor, no un valor atribuido a una tabla ENEE.",
        )
        st.caption(
            "Coeficiente de arrastre CFE para cables: Cd = 1.0. "
            "Modo CFE: presión por claro de 05 00 03 (VR=120 km/h), "
            "sin volver a multiplicar por Cd ni por presión dinámica."
        )
        a,b,c=st.columns(3)
        with a:tmin=st.number_input("Temperatura mínima (°C)",value=-10.)
        with b:tmax=st.number_input("Temperatura máxima (°C)",value=50.)
        with c:paso=st.number_input("Paso (°C)",value=5.,min_value=1.)
        enviar=st.form_submit_button("Ejecutar cálculo mecánico CFE por vano")
    if not enviar:return
    try:
        if tmax<tmin:
            raise ValueError("Temperatura máxima inferior a mínima")
        if not viento_reducido.strip() or not hielo.strip():
            raise ValueError(
                "Faltan viento reducido y/o espesor de hielo documentados. "
                "Introducí valores numéricos, incluido 0 cuando corresponda."
            )
        if fuente_material.startswith("CFE"):
            ini,fin=seleccionar_propiedades_cfe_07_ft_01(conductor[1])
        else:
            ini=seleccionar_conductor_enee(*conductor,"Inicial")
            fin=seleccionar_conductor_enee(*conductor,"Final")
        temperaturas=[]
        actual=float(tmin)
        while actual<=tmax+1e-9:
            temperaturas.append(actual)
            actual+=float(paso)
            if len(temperaturas)>200:
                raise ValueError("Rango de temperaturas demasiado amplio")
        # Las cinco hipótesis se verifican también cuando no coinciden con
        # el paso de la tabla térmica (por ejemplo, 16 °C).
        if tmin <= 0 <= tmax and not any(abs(t) < 1e-9 for t in temperaturas):
            temperaturas.append(0.)
        if tmin <= 16 <= tmax and not any(abs(t-16.) < 1e-9 for t in temperaturas):
            temperaturas.append(16.)
        temperaturas.sort()
        if puntos_topo is None:
            raise ValueError("Revisar la importación del KML")
        puntos_calculo=puntos_topo.copy(deep=True)
        elevaciones=None
        if fuente_topo=="GeoTIFF subido":
            if dem_archivo is None:
                raise ValueError("Adjuntá el DEM GeoTIFF")
            elevaciones=ElevacionesGeoTIFF(dem_archivo.getvalue())
        elif fuente_topo=="Mapzen/AWS gratuito":
            elevaciones=ElevacionesTerrarium()
        if sustituir_cotas:
            if elevaciones is None:
                raise ValueError("Seleccioná un DEM para sustituir las cotas")
            puntos_calculo=extraer_terreno_apoyos(
                puntos_calculo,elevaciones,epsg_xy=int(epsg_xy),
            )
        if archivo_kml is not None or elevaciones is not None:
            if ("Altitud" not in puntos_calculo or
                puntos_calculo["Altitud"].isna().any()):
                raise ValueError(
                    "Faltan cotas: completalas o activá DEM para apoyos"
                )
            if ("Altura_Amarre_m" not in puntos_calculo or
                puntos_calculo["Altura_Amarre_m"].isna().any()):
                raise ValueError("Falta altura de amarre en uno o más apoyos")
        resumen,tabla=ejecutar_modulo("cfe",
            puntos_calculo,ini,fin,
            viento_max_kmh=viento_max,
            viento_reducido_kmh=float(viento_reducido),
            hielo_mm=float(hielo),
            temperaturas_C=temperaturas,
            Cd=1.,rho_kg_m3=float(rho),
            incluir_ensayo_viento_16C=True,
            densidad_hielo_kg_m3=DENSIDAD_HIELO_ENSAYO_KG_M3,
            modelo_presion_cfe=True,
        )
        st.caption(f"Hielo: densidad fijada = {DENSIDAD_HIELO_ENSAYO_KG_M3:g} kg/m³. Viento: presiones CFE 05 00 03 por claro, VR 120 km/h.")
        st.subheader("Referencias CFE — secciones independientes entre remates")
        st.dataframe(
            resumen[["Sección","Remate inicial","Remate final"]].drop_duplicates(),
            hide_index=True, use_container_width=True,
        )
        if float(viento_reducido)==0. and float(hielo)==0.:
            st.warning(
                "Viento reducido e hielo ingresados como cero: estas condiciones "
                "NO reproducen el clima extremo que sirvió para publicar las "
                "tablas CFE 07 FT. La comparación con P tabulado no valida el diseño."
            )
        st.dataframe(resumen,hide_index=True,use_container_width=True)
        st.info(
            "Condiciones inicial/final con una misma longitud natural por vano "
            "a 50 °C y creep adicional = 0. Se conservan E y α originales "
            "de CFE. Las tensiones extremas pueden diferir: su igualdad "
            "no se impone artificialmente."
        )
        st.subheader("Tendido independiente por sección y fijación por vano")
        st.caption(
            "Etapa 1: cada sección entre remates se tiende a 50 °C " 
            "con deslizamiento ideal solo en apoyos de paso. "
            "Etapa 2: longitud natural individual fijada; cambios de estado "
            "independientes sin deslizamiento posterior."
        )
        columnas=["Sección","Condición","Vano","Luz (m)","Longitud natural fijada (m)"]
        longitudes=tabla[columnas].drop_duplicates(["Sección","Condición","Vano"])
        st.dataframe(longitudes,hide_index=True,use_container_width=True)
        st.caption(
            "H a 50 °C mostrado en el resumen es el parámetro de entrada "
            "para generar las longitudes de referencia. Las componentes H "
            "por vano y las tensiones reales del tendido se presentan en las tablas."
        )
        st.caption(
            "El claro regla de la tabla resumen NO interviene en las ecuaciones "
            "de estas corridas. Para vanos desnivelados su interpretación "
            "convencional requiere un modelo de regulación apropiado."
        )
        st.subheader("Resultados por vano, temperatura y condición")
        st.caption(
            "La tensión H es la componente transversal a la carga del cable, "
            "no necesariamente horizontal global cuando actúa el viento. "
            "Las flechas corresponden a la geometría exacta."
        )
        max_residual = float(tabla["Residual (m)"].abs().max())
        minimo_h = float(tabla["H (kN)"].min())
        max_tension = float(tabla["T máx. (kN)"].max())
        k1, k2, k3 = st.columns(3)
        k1.metric("Tensión H mínima", f"{minimo_h:.3f} kN")
        k2.metric("Tensión máxima del cable", f"{max_tension:.3f} kN")
        k3.metric("Máximo residual de compatibilidad", f"{max_residual:.2e} m")
        if max_residual > 1e-7:
            st.warning(
                "El máximo residual excede 1e-7 m; comprobar convergencia "
                "antes de usar los resultados."
            )

        st.dataframe(tabla,hide_index=True,use_container_width=True)
        from Analisis_mecanico_conductores.interfaz.mostrar_verificaciones_cfe_integradas import (
            mostrar_verificacion_integrada,
        )
        mostrar_verificacion_integrada(
            tabla,puntos_calculo,conductor[1],hielo_mm=float(hielo),
        )
        if resumen["Sección"].nunique() == 1:
            with st.expander("Comparación multivano — guías deslizantes ideales", expanded=False):
                st.caption(
                    "Solucionador BVP de sección continua con remates extremos y "
                    "guías sin fricción intermedias. No equivale a espiga fija, "
                    "no optimiza nuevamente H50 y no acredita capacidad ENEE."
                )
                if st.button("Resolver sección continua ideal (50, 16 y 0 °C)",
                             key="ejecutar_multivano_cfe_ideal"):
                    try:
                        from Analisis_mecanico_conductores.tension_tendido.comparar_multivano_deslizante_cfe import (
                            calcular_comparacion_multivano_final,
                        )
                        fila_final=resumen.loc[resumen["Condición"].astype(str).str.startswith("Final")]
                        h50=float(fila_final["H_50_kN"].iloc[0])
                        with st.spinner("Resolviendo continuidad de cinco vanos por BVP..."):
                            comparacion=calcular_comparacion_multivano_final(
                                puntos_calculo,fin,h50,
                                temperaturas_C=(50.,16.,0.),
                                Cd=1.,rho_kg_m3=float(rho),
                            )
                        st.dataframe(comparacion,hide_index=True,use_container_width=True)
                        st.download_button(
                            "Descargar comparación multivano ideal",
                            comparacion.to_csv(index=False).encode("utf-8-sig"),
                            "comparacion_multivano_ideal.csv","text/csv",
                            key="descarga_multivano_ideal_cfe",
                        )
                    except (ValueError,TypeError,KeyError,ArithmeticError) as exc:
                        st.error("La sección ideal no se pudo resolver: "+str(exc))
        tabla_libramientos=None
        perfiles_terreno=None
        if elevaciones is not None:
            tabla_libramientos,perfiles_terreno=calcular_libramientos_muestreados(
                tabla,puntos_calculo,{"Inicial":ini,"Final":fin},
                elevaciones,epsg_xy=int(epsg_xy),paso_m=float(paso_topo),
                clima={"rho_kg_m3":float(rho),"Cd":1.0},
            )
            st.subheader("Libramientos preliminares: no certificados")
            st.caption(f"Fuente: {elevaciones.fuente}. Mínimos muestreados.")
            st.dataframe(tabla_libramientos,hide_index=True,use_container_width=True)
            st.download_button(
                "Descargar perfil terreno/conductor (CSV)",
                perfiles_terreno.to_csv(index=False).encode("utf-8-sig"),
                "perfil_terreno_y_conductor.csv","text/csv",key="m1_csv_perfil",
            )
            st.download_button(
                "Descargar libramientos (CSV)",
                tabla_libramientos.to_csv(index=False).encode("utf-8-sig"),
                "libramientos_preliminares.csv","text/csv",key="m1_csv_libr",
            )
        st.download_button(
            "Descargar corridas CFE (CSV)",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            "cfe_corridas_por_vano.csv","text/csv",
        )
        from io import BytesIO
        from pypdf import PdfWriter
        from Analisis_mecanico_conductores.salidas.PDF.generar_pdf_corrida_cfe import generar_pdf_corrida_cfe
        from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
        from Analisis_mecanico_conductores.motor_conductores import dividir_secciones_por_remates

        clima_pdf = {
            "viento_max_kmh": viento_max,
            "viento_reducido_kmh": float(viento_reducido),
            "hielo_mm": float(hielo),
            "densidad_hielo_kg_m3": DENSIDAD_HIELO_ENSAYO_KG_M3,
            "modelo_presion_cfe": True,
            "rho_kg_m3": float(rho),
            "Cd": 1.0,
        }
        secciones_pdf = dividir_secciones_por_remates(puntos_calculo)
        pdfs = []
        for codigo, puntos_seccion in secciones_pdf:
            resumen_seccion = resumen[resumen["Sección"] == codigo].copy()
            tabla_seccion = tabla[tabla["Sección"] == codigo].copy()
            xyz_pdf, _ = _geometria(puntos_seccion)
            vanos_seccion = set(tabla_seccion["Vano"].unique())
            def _filtrar_perfil(datos):
                if datos is None or "Vano" not in datos.columns:
                    return None
                return datos[datos["Vano"].isin(vanos_seccion)].copy()
            datos_proyecto = dict(proyecto_pdf)
            if len(secciones_pdf) > 1:
                datos_proyecto["nombre"] = (
                    f"{proyecto_pdf.get('nombre', 'Línea')} — {codigo} "
                    f"({puntos_seccion.iloc[0]['Punto']} a "
                    f"{puntos_seccion.iloc[-1]['Punto']})"
                )
            pdfs.append(generar_pdf_corrida_cfe(
                resumen=resumen_seccion, tabla=tabla_seccion,
                conductor=f"{conductor[0]} {conductor[1]}",
                fuente_material=fuente_material,
                proyecto=datos_proyecto,
                propiedades_inicial=ini,
                propiedades_final=fin,
                geometria_xyz=xyz_pdf,
                libramientos=_filtrar_perfil(tabla_libramientos),
                perfil_terreno=_filtrar_perfil(perfiles_terreno),
                clima=clima_pdf,
            ))
        if len(pdfs) == 1:
            memoria_pdf = pdfs[0]
        else:
            writer = PdfWriter()
            for documento in pdfs:
                writer.append(BytesIO(documento))
            destino = BytesIO()
            writer.write(destino)
            memoria_pdf = destino.getvalue()
        st.download_button(
            "Descargar memoria independiente — Módulo 1 (PDF)",
            data=memoria_pdf,
            file_name="modulo_01_analisis_mecanico_conductores.pdf",
            mime="application/pdf",
            key="descarga_pdf_modulo1_cfe",
        )
        if elevaciones is not None:
            elevaciones.cerrar()
        st.warning(
            "ESTADO DEL MÉTODO: longitud natural de referencia común por vano "
            "a 50 °C, sin creep adicional. Las cinco restricciones CFE se verifican "
            "con E y α propios de cada condición. No constituye predicción "
            "de deformación permanente ni equivalencia SAGSEC. "
            "Las comprobaciones estructurales CFE NO sustituyen ENEE."
        )
    except (ValueError,KeyError,TypeError,OverflowError,ArithmeticError) as exc:
        st.error(f"No se pudo resolver el caso: {exc}")
