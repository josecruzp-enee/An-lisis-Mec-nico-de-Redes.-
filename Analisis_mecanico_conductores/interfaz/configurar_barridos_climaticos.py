"""Controles Streamlit para barridos exploratorios de la Etapa 1."""
from __future__ import annotations

import streamlit as st

from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import (
    ConfiguracionBarrido,
)


def mostrar_configuracion_barrido():
    """Construye y devuelve la configuración de temperatura, viento y hielo.

    No define tensiones admisibles ni genera normas implícitas. El barrido
    explora la H determinada previamente con hipótesis documentadas.
    """
    st.subheader("Barridos climáticos de sensibilidad")
    st.caption(
        "Rangos exploratorios; no sustituyen hipótesis normativas. "
        "Las temperaturas son del CONDUCTOR, no del aire."
    )
    with st.expander("Ajustar temperatura, viento y hielo",expanded=False):
        c1,c2,c3=st.columns(3)
        with c1:
            tmin=st.number_input("Temperatura mínima (°C)",value=0.,step=1.,key="barrido_tmin")
        with c2:
            tmax=st.number_input("Temperatura máxima (°C)",value=50.,step=1.,key="barrido_tmax")
        with c3:
            tpaso=st.number_input("Paso de temperatura (°C)",value=1.,min_value=.1,step=1.,key="barrido_tpaso")
        c4,c5=st.columns(2)
        with c4:
            vmax=st.number_input("Viento máximo (km/h)",value=130.,min_value=0.,step=5.,key="barrido_vmax")
        with c5:
            vpaso=st.number_input("Paso de viento (km/h)",value=5.,min_value=.1,step=5.,key="barrido_vpaso")
        matriz=st.checkbox(
            "Cruzar todas las temperaturas con todos los vientos (más lento)",
            value=False,key="barrido_matriz",
        )
        hielo=st.checkbox("Incluir manguito de hielo",value=False,key="barrido_hielo")
        espesor=20.
        paso_hielo=5.
        densidad=900.
        t_hielo=0.
        combinar=False
        if hielo:
            st.warning(
                "El hielo requiere justificación climática para el lugar; "
                "estos casos son exploratorios, no combinaciones normativas."
            )
            a,b=st.columns(2)
            with a:
                espesor=st.number_input(
                    "Espesor radial máximo del hielo (mm)",
                    value=20.,min_value=1.,step=5.,key="barrido_hielo_espesor"
                )
                densidad=st.number_input(
                    "Densidad asumida del hielo (kg/m³)",
                    value=900.,min_value=1.,step=25.,key="barrido_hielo_densidad"
                )
            with b:
                paso_hielo=st.number_input(
                    "Paso radial del hielo (mm)",value=5.,min_value=.1,
                    step=1.,key="barrido_hielo_paso"
                )
                t_hielo=st.number_input(
                    "Temperatura para caso con hielo (°C)",value=0.,
                    step=1.,key="barrido_hielo_t"
                )
            combinar=st.checkbox(
                "Evaluar hielo + viento máximo (solo exploración)",
                value=False,key="barrido_hielo_viento",
            )
    config=ConfiguracionBarrido(
        temperatura_min_C=tmin,temperatura_max_C=tmax,
        temperatura_paso_C=tpaso,viento_max_kmh=vmax,
        viento_paso_kmh=vpaso,modo_matriz_completa=matriz,
        incluir_hielo=hielo,hielo_max_mm=espesor,
        hielo_paso_mm=paso_hielo,densidad_hielo_kg_m3=densidad,
        temperatura_hielo_C=t_hielo,combinar_hielo_viento=combinar,
    )
    cantidad_t=round((tmax-tmin)/tpaso)+1 if tmax>=tmin else 0
    cantidad_v=round(vmax/vpaso)+1
    cantidad=cantidad_t*cantidad_v if matriz else cantidad_t+cantidad_v
    st.caption(
        f"Corridas previstas: aprox. {cantidad} estados sin hielo "
        f"({ 'matriz completa' if matriz else 'barridos independientes' }). "
        "Se muestran máximos por vano, sin verificar seguridad de obra."
    )
    return config


def mostrar_resultados_barrido(barrido):
    """Presenta gobernantes y permite descargar resultados por estado y vano."""
    if barrido is None:
        return
    st.subheader("Barrido de sensibilidad — casos gobernantes")
    st.caption(
        f"{barrido['total_estados']} estados evaluados. "
        "Máximos EXPLORATORIOS; no equivalen a límites admisibles ni "
        "certifican simultaneidad meteorológica."
    )
    st.dataframe(barrido["gobernantes"],use_container_width=True,hide_index=True)
    st.download_button(
        "Exportar gobernantes CSV",
        barrido["gobernantes"].to_csv(index=False).encode("utf-8-sig"),
        file_name="conductores_casos_gobernantes.csv",
        mime="text/csv",key="descarga_barrido_gobernantes",
    )
    with st.expander("Ver todas las corridas por vano"):
        st.dataframe(barrido["detalle"],use_container_width=True,hide_index=True)
        st.download_button(
            "Exportar corridas completas CSV",
            barrido["detalle"].to_csv(index=False).encode("utf-8-sig"),
            file_name="conductores_barrido_climatico.csv",
            mime="text/csv",key="descarga_barrido_completo",
        )
