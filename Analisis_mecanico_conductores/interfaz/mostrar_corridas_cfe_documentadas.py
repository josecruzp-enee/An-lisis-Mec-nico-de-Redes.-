"""Streamlit: ejecución CFE con hipótesis documentadas sobre vanos reales."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee, seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    ejecutar_corridas_cfe_por_vano,CFE_FUENTE,
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
            "Viento reducido (km/h) — condición del caso",value="0",
            help="No se inventa ni se deduce automáticamente del viento máximo.",
        )
        hielo=st.text_input(
            "Espesor de hielo radial (mm) — condición del caso",value="0",
            help="No se sustituye una hipótesis con hielo por hielo cero.",
        )
        rho=st.number_input(
            "Densidad de aire para cálculo aerodinámico (kg/m³)",
            min_value=.1,value=1.225,format="%.3f",
            help="Entrada física visible: 1.225 kg/m³ es el valor nominal usado por el motor, no un valor atribuido a una tabla ENEE.",
        )
        st.caption(
            "Coeficiente de arrastre CFE para cables: Cd = 1.0. "
            "Se conserva el cálculo de viento del motor; se debe verificar "
            "su equivalencia con las expresiones de presión de CFE."
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
        resumen,tabla=ejecutar_corridas_cfe_por_vano(
            puntos_calculo,ini,fin,
            viento_max_kmh=viento_max,
            viento_reducido_kmh=float(viento_reducido),
            hielo_mm=float(hielo),
            temperaturas_C=temperaturas,
            Cd=1.,rho_kg_m3=float(rho),
            incluir_ensayo_viento_16C=True,
        )
        st.subheader("Referencias final e inicial acopladas (modelo experimental)")
        if float(viento_reducido)==0. and float(hielo)==0.:
            st.warning(
                "Viento reducido e hielo ingresados como cero: estas condiciones "
                "NO reproducen el clima extremo que sirvió para publicar las "
                "tablas CFE 07 FT. La comparación con P tabulado no valida el diseño."
            )
        st.dataframe(resumen,hide_index=True,use_container_width=True)
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
        from salidas.PDF.generar_pdf_corrida_cfe import generar_pdf_corrida_cfe
        from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
        xyz_pdf, _ = _geometria(puntos_calculo)
        memoria_pdf = generar_pdf_corrida_cfe(
            resumen=resumen, tabla=tabla,
            conductor=f"{conductor[0]} {conductor[1]}",
            fuente_material=fuente_material,
            proyecto=proyecto_pdf,
            propiedades_inicial=ini,
            propiedades_final=fin,
            geometria_xyz=xyz_pdf,
            libramientos=tabla_libramientos,
            perfil_terreno=perfiles_terreno,
            clima={
                "viento_max_kmh": viento_max,
                "viento_reducido_kmh": float(viento_reducido),
                "hielo_mm": float(hielo),
                "rho_kg_m3": float(rho),
                "Cd": 1.0,
            },
        )
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
            "ESTADO DEL MÉTODO: la referencia FINAL se dimensiona con restricciones "
            "y la INICIAL se vincula a la tensión extrema final (-10°C). "
            "No se ha validado un modelo constitutivo de creep ni su equivalencia "
            "con SAGSEC. Las comprobaciones de estructuras CFE NO sustituyen ENEE."
        )
    except (ValueError,KeyError,TypeError,OverflowError,ArithmeticError) as exc:
        st.error(f"No se pudo resolver el caso: {exc}")
