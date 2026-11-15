"""Interfaz experimental CFE: corridas por vano en condición inicial y final.

Las tablas ENEE no se emplean para el cálculo. Usuario aporta propiedades
constitutivas documentadas y límites de las hipótesis; P50 se obtiene por
optimización explícita. El modelo final es aproximación elástica SIN creep.
No se presenta como reproducción certificada de SAGSEC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, EstadoReferenciaCFE, HipotesisDisenoCFE,
    calcular_parametro_cfe_desde_limites, calcular_tablas_inicial_final,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee, seleccionar_conductor_enee,
)


def mostrar_calculo_cfe(puntos):
    st.subheader("Ensayo CFE — condición inicial y final por vano")
    st.warning(
        "Módulo experimental: dimensiona P50 usando límites explícitos. "
        "Condición final: aproximación termoelástica sin predicción de creep. "
        "NO equivale aún a SAGSEC ni a verificación normativa ENEE. "
        "Las tablas ENEE NO son entradas del cálculo."
    )
    catalogo = leer_catalogo_enee()
    opciones = [(f["calibre"], f["nombre"]) for f in catalogo]
    if not opciones:
        st.error("No se encontró el catálogo ENEE de conductores.")
        return
    with st.form("cfe_inicial_final"):
        seleccion = st.selectbox(
            "Conductor ENEE (propiedades del catálogo)",
            opciones, format_func=lambda x: f"{x[0]} — {x[1]}",
        )
        st.caption("Se leen propiedades inicial/final de la misma construcción.")
        c1, c2 = st.columns(2)
        with c1:
            tmin = st.number_input("Temperatura mínima de tabla (°C)", value=-10., step=5.)
            tmax = st.number_input("Temperatura máxima de tabla (°C)", value=50., step=5.)
            paso = st.number_input("Paso (°C)", value=5., min_value=1., step=1.)
        with c2:
            temperatura_viento = st.number_input("Temperatura de viento máximo (°C)", value=0.)
            viento_max = st.number_input("Viento máximo (km/h)", value=0., min_value=0.)
            viento_reducido = st.number_input("Viento reducido (km/h)", value=0., min_value=0.)
            hielo_mm = st.number_input("Hielo radial (mm)", value=0., min_value=0.)
        st.markdown("**Límites de tracción (fracción de rotura) — se aplican a las hipótesis indicadas**")
        st.caption(
            "Valores de ensayo editables: verificá en CFE la edición, "
            "tipo de conductor y condición antes de utilizarlos en diseño."
        )
        porcentaje_fria = st.number_input(
            "Máx. −10 °C, viento reducido e hielo (% rotura)", value=45.,
            min_value=0.1, max_value=100., step=1.,
        )
        porcentaje_viento = st.number_input(
            "Máx. 0 °C, viento máximo (% rotura)", value=45.,
            min_value=0.1, max_value=100., step=1.,
        )
        porcentaje_templada = st.number_input(
            "Máx. 16 °C, sin viento, final (% rotura)", value=20.,
            min_value=0.1, max_value=100., step=1.,
        )
        porcentaje_cero = st.number_input(
            "Máx. 0 °C, sin viento, final (% rotura)", value=25.,
            min_value=0.1, max_value=100., step=1.,
        )
        incluir_extras = st.checkbox(
            "Incluir viento máximo y viento reducido con hielo en la salida",
            value=True,
        )
        ejecutar = st.form_submit_button("Calcular condiciones inicial y final")
    if not ejecutar:
        return
    try:
        if tmax < tmin:
            raise ValueError("Temperatura máxima inferior a la mínima")
        inicial = seleccionar_conductor_enee(*seleccion, "Inicial")
        final = seleccionar_conductor_enee(*seleccion, "Final")
        propiedades = PropiedadesConductorCFE(
            peso_kN_m=float(inicial["peso_kN_m"]),
            diametro_m=float(inicial["diametro_m"]),
            EA_inicial_kN=float(inicial["EA_kN"]),
            EA_final_kN=float(final["EA_kN"]),
            alpha_inicial_por_C=float(inicial["alpha_por_C"]),
            alpha_final_por_C=float(final["alpha_por_C"]),
            ruptura_kN=float(inicial["ruptura_kN"]),
            fuente=f"{inicial['fuente']} | {final['fuente']}",
        )
        xyz, _ = _geometria(puntos)
        fuente_limite = "Límites de ensayo seleccionados en la interfaz; referencia CFE DCCIAMBT 05 00 02"
        estados = (
            HipotesisDisenoCFE(
                "TH1 — frío, viento reducido e hielo", -10.,
                float(viento_reducido), float(hielo_mm),
                propiedades.ruptura_kN * porcentaje_fria / 100., fuente_limite,
            ),
            HipotesisDisenoCFE(
                "TH2 — viento máximo", float(temperatura_viento),
                float(viento_max), 0.,
                propiedades.ruptura_kN * porcentaje_viento / 100., fuente_limite,
            ),
            HipotesisDisenoCFE(
                "Tensión 16 °C sin viento (final)", 16., 0., 0.,
                propiedades.ruptura_kN * porcentaje_templada / 100., fuente_limite,
            ),
            HipotesisDisenoCFE(
                "Tensión 0 °C sin viento (final)", 0., 0., 0.,
                propiedades.ruptura_kN * porcentaje_cero / 100., fuente_limite,
            ),
        )
        # El dimensionamiento inicial y final se calcula por separado.
        # Esta aproximación NO predice la evolución permanente entre ambos.
        solo_cargas = estados[:2]
        p_inicial = calcular_parametro_cfe_desde_limites(
            xyz, propiedades, solo_cargas,
            condicion="Inicial",
        )
        p_final = calcular_parametro_cfe_desde_limites(
            xyz, propiedades, estados,
            condicion="Final",
        )
        temperaturas = np.arange(float(tmin), float(tmax)+paso*.5, float(paso))
        extras = (
            [("TH1", -10., float(viento_reducido), float(hielo_mm)),
             ("TH2", float(temperatura_viento), float(viento_max), 0.)]
            if incluir_extras else []
        )
        tabla = calcular_tablas_inicial_final(
            puntos, propiedades,
            EstadoReferenciaCFE(p_inicial["parametro_P_m"], p_inicial["metodo"]),
            EstadoReferenciaCFE(p_final["parametro_P_m"], p_final["metodo"]),
            temperaturas, estados_climaticos=extras,
        )
        st.success("Corridas calculadas por vano: condición inicial y condición final.")
        resumen = pd.DataFrame([p_inicial, p_final])
        st.subheader("Parámetros calculados desde hipótesis")
        st.dataframe(resumen, use_container_width=True, hide_index=True)
        st.subheader("Flechas y tensiones por vano y condición")
        st.dataframe(tabla, use_container_width=True, hide_index=True)
        st.download_button(
            "Exportar corridas CSV",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            "cfe_condiciones_inicial_final_por_vano.csv", "text/csv",
        )
        st.caption(
            "Resultados de investigación, no aprobación de diseño. "
            "La comparación con ENEE se hace fuera del algoritmo, "
            "usando un caso con las mismas hipótesis y propiedades."
        )
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        st.error(f"No se pudo resolver el caso: {exc}")
