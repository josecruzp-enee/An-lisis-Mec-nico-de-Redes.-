"""Streamlit: ejecución CFE con hipótesis documentadas sobre vanos reales."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee, seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    ejecutar_corridas_cfe_por_vano,CFE_FUENTE,
)


def mostrar_corridas_cfe(puntos):
    st.subheader("CFE — tensiones y flechas por vano real")
    st.caption(
        "Norma de referencia: CFE DCCIAMBT (2014), 05 00 02/03 y 07 FT 01. "
        "Conserva las ecuaciones de catenaria 3D y compatibilidad del motor. "
        "No introduce P, claro de diseño ni flecha ENEE como entradas."
    )
    opciones=[(f["calibre"],f["nombre"]) for f in leer_catalogo_enee()]
    if not opciones:
        st.error("No hay catálogo físico ENEE disponible")
        return
    with st.form("cfe_climas_documentados"):
        indice=next((i for i,x in enumerate(opciones) if x==("1/0","RAVEN")),0)
        conductor=st.selectbox(
            "Conductor del catálogo físico ENEE",opciones,index=indice,
            format_func=lambda x:f"{x[0]} — {x[1]}",
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
        ini=seleccionar_conductor_enee(*conductor,"Inicial")
        fin=seleccionar_conductor_enee(*conductor,"Final")
        temperaturas=[]
        actual=float(tmin)
        while actual<=tmax+1e-9:
            temperaturas.append(actual)
            actual+=float(paso)
            if len(temperaturas)>200:
                raise ValueError("Rango de temperaturas demasiado amplio")
        resumen,tabla=ejecutar_corridas_cfe_por_vano(
            puntos,ini,fin,
            viento_max_kmh=viento_max,
            viento_reducido_kmh=float(viento_reducido),
            hielo_mm=float(hielo),
            temperaturas_C=temperaturas,
            Cd=1.,rho_kg_m3=float(rho),
        )
        st.subheader("Tensiones de referencia calculadas")
        st.dataframe(resumen,hide_index=True,use_container_width=True)
        st.subheader("Resultados por vano, temperatura y condición")
        st.dataframe(tabla,hide_index=True,use_container_width=True)
        st.download_button(
            "Descargar corridas CFE (CSV)",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            "cfe_corridas_por_vano.csv","text/csv",
        )
        st.warning(
            "ESTADO DEL MÉTODO: las referencias inicial y final se obtienen "
            "por sus respectivas restricciones CFE; todavía no existe "
            "un modelo constitutivo de creep que las vincule. "
            "No presentar esta salida como reproducción validada de SAGSEC "
            "ni como condición final histórica ENEE."
        )
    except (ValueError,KeyError,TypeError,OverflowError,ArithmeticError) as exc:
        st.error(f"No se pudo resolver el caso: {exc}")
