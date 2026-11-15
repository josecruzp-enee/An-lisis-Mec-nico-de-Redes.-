"""Interfaz de corridas por vano con el método Checa existente.

No solicita P ni flechas de referencia. Es una interfaz de contraste,
NO la reproducción certificada de condición final ENEE (sin creep).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee,seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.tension_tendido.corridas_por_vano_checa import (
    ejecutar_corridas_por_vano_checa,
)


def mostrar_corridas_por_vano_checa(puntos):
    st.subheader("Corridas por vano real — Checa")
    st.caption(
        "Catenaria 3D y cambio de estado por vano fijo. Se calculan "
        "las tensiones de tendido con las hipótesis TCD/THF que ya utiliza "
        "la Etapa 1. No se solicita P, claro de diseño ni flecha impuesta."
    )
    opciones=[(fila["calibre"],fila["nombre"]) for fila in leer_catalogo_enee()]
    if not opciones:
        st.error("No se encontró el catálogo de propiedades ENEE.")
        return
    with st.form("corridas_ener_c_b_por_vano"):
        seleccionado=st.selectbox(
            "Conductor (catálogo de propiedades ENEE)",
            opciones,format_func=lambda x:f"{x[0]} — {x[1]}",
        )
        t0=st.number_input("Temperatura de tendido (°C)",value=20.)
        c1,c2,c3=st.columns(3)
        with c1:
            minimo=st.number_input("Temperatura mínima (°C)",value=-10.)
        with c2:
            maximo=st.number_input("Temperatura máxima (°C)",value=50.)
        with c3:
            paso=st.number_input("Paso de temperatura (°C)",min_value=1.,value=5.)
        enviar=st.form_submit_button("Calcular tensiones y flechas por vano")
    if not enviar:
        return
    try:
        if maximo<minimo:
            raise ValueError("La temperatura máxima debe ser superior o igual a la mínima")
        temperaturas=[]
        actual=float(minimo)
        while actual<=maximo+1e-9:
            temperaturas.append(actual)
            actual+=float(paso)
            if len(temperaturas)>500:
                raise ValueError("Demasiadas temperaturas de ensayo")
        # No mezclar fichas: peso, diámetro y ruptura salen de la
        # misma construcción ENEE; solo cambia E inicial/final.
        inicial=seleccionar_conductor_enee(*seleccionado,"Inicial")
        final=seleccionar_conductor_enee(*seleccionado,"Final")
        # Conserva los parámetros aerodinámicos del módulo Checa ya
        # implementado; las tablas térmicas no aplican viento.
        resultado,tabla=ejecutar_corridas_por_vano_checa(
            puntos,inicial,final,temperaturas,
            temperatura_tendido_C=float(t0),
        )
        st.success(
            f"H de tendido calculada mediante Checa: "
            f"{resultado.H_tendido_kN:.4f} kN. "
            f"Hipótesis gobernante: {resultado.caso_gobernante}."
        )
        st.warning(
            "La serie 'Elasticidad final SIN creep' es un ensayo físico "
            "con longitud natural conservada, no la predicción de la "
            "condición final ENEE. Un ajuste a las tablas oficiales "
            "requerirá un modelo constitutivo documentado de "
            "deformación permanente. Las tablas ENEE nunca se usan como entrada."
        )
        st.subheader("Hipótesis y límites de Checa")
        st.dataframe(resultado.hipotesis,hide_index=True,use_container_width=True)
        st.subheader("Resultados por vano y temperatura")
        st.dataframe(tabla,hide_index=True,use_container_width=True)
        st.download_button(
            "Exportar comparación por vano (CSV)",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            file_name="corridas_por_vano_checa.csv",mime="text/csv",
        )
        st.caption(
            "El parámetro P aparece únicamente como resultado H/peso. "
            "En vano desnivelado H es la componente de la catenaria "
            "en la dirección perpendicular a la carga."
        )
    except (ValueError,KeyError,TypeError,ArithmeticError,OverflowError) as exc:
        st.error(f"No se pudo calcular el caso: {exc}")
