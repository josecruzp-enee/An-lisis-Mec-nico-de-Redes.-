"""Formulario para una sección de regulación con Excel SOLO de puntos.

El archivo de coordenadas sigue siendo el mismo. No se repite peso ni
diámetro: se leen del catálogo nominal Viakon; las propiedades de otro
fabricante únicamente se usan en modo de referencia comparativa.
No inventar tensiones admisibles: cada hipótesis exige fuente y límite.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from calculos.regulacion_multivano import resolver_seccion_regulacion
from entradas.catalogos import CONDUCTORES_ACSR
from entradas.catalogo_viakon_acsr import CONDUCTORES_VIAKON_ACSR
from entradas.referencias_mecanicas_acsr import referencia_mecanica_nexans


COLUMNAS=(
    "Hipotesis","Temperatura_C","Viento_ms",
    "T_limite_kN","Fuente_limite","Criterio_diseno",
)


def _leer_hipotesis_usuario(tabla):
    if not isinstance(tabla,pd.DataFrame) or tabla.empty:
        raise ValueError("Definí al menos una hipótesis climática")
    if any(c not in tabla for c in COLUMNAS):
        raise ValueError("La tabla de hipótesis tiene columnas incompletas")
    t=tabla[list(COLUMNAS)].copy()
    if t.isna().any().any() or (t.astype(str).apply(
            lambda c:c.str.strip().eq("")).any().any()):
        raise ValueError(
            "Completá cada hipótesis: temperatura, viento, "
            "límite de tensión, fuente y criterio"
        )
    return t


def mostrar_calculo_directo(puntos, calibre, *, Cd=1.2, rho=1.225):
    """Presenta formulario compacto. None hasta que sea enviado con datos."""
    nombre=(CONDUCTORES_ACSR[calibre]["nombre_mostrado"]
            if calibre in CONDUCTORES_ACSR else calibre)
    ficha=CONDUCTORES_VIAKON_ACSR[nombre]
    st.subheader("Completar el cálculo sin modificar tu Excel")
    st.caption(
        "Los puntos ya están cargados. Solo faltan las propiedades "
        "termoelásticas y los estados climáticos con límites documentados."
    )
    with st.form("calculo_directo_checa"):
        st.markdown("**Propiedades del conductor**")
        fuente_tipo=st.radio(
            "Propiedades termoelásticas",
            [
                "Ficha técnica documentada",
                "Referencia Nexans por construcción (comparativa)",
            ],
        )
        c1,c2,c3=st.columns(3)
        with c1:
            temperatura=st.number_input(
                "Temperatura de referencia (°C)",value=20.0,
            )
        with c2:
            EA=st.text_input("Rigidez axial EA (kN)",value="")
        with c3:
            alpha=st.text_input("Dilatación α (1/°C)",value="")
        fuente=st.text_input(
            "Fuente documental de las propiedades",value=""
        )
        st.markdown("**Hipótesis climáticas y límites de diseño**")
        st.caption(
            "Añadí las filas necesarias. No hay valores de tensión "
            "admisible precargados. Un límite requiere su fuente técnica."
        )
        datos=pd.DataFrame([
            {"Hipotesis":"Estado_1","Temperatura_C":None,
             "Viento_ms":None,"T_limite_kN":None,
             "Fuente_limite":"","Criterio_diseno":""},
        ],columns=COLUMNAS)
        tabla=st.data_editor(
            datos,num_rows="dynamic",hide_index=True,
            use_container_width=True,
            key="tabla_climas_regulacion",
        )
        enviar=st.form_submit_button("Calcular tensión y flechas")
    if not enviar:
        return None
    hip=_leer_hipotesis_usuario(tabla)
    if fuente_tipo.startswith("Referencia"):
        referencia=referencia_mecanica_nexans(nombre)
        ea=referencia["EA_final_referencia_kN"]
        dilatacion=referencia["alpha_final_referencia_por_C"]
        origen=referencia["fuente"]+" | COMPARACIÓN, NO FICHA VIakON"
        st.warning(
            "Se usará la rigidez FINAL y dilatación FINAL de Nexans "
            "por construcción equivalente. Este resultado es "
            "COMPARATIVO y no aprueba un tendido real."
        )
    else:
        if not EA.strip() or not alpha.strip() or not fuente.strip():
            raise ValueError(
                "Ingresá EA, α y su fuente documental o elegí "
                "la referencia comparativa Nexans."
            )
        ea=float(EA)
        dilatacion=float(alpha)
        origen=fuente.strip()
    rotura=float(ficha["carga_rotura_kN"])
    limites=pd.to_numeric(hip["T_limite_kN"],errors="raise")
    if (limites>=rotura).any():
        raise ValueError(
            "Los límites introducidos deben ser menores que "
            "la ruptura nominal Viakon: "+str(round(rotura,3))+" kN"
        )
    return resolver_seccion_regulacion(
        puntos,hipotesis=hip,
        temperaturas_tabla_C=[0,10,20,30,40],
        peso_kN_m=float(ficha["peso_kg_m"])*9.80665/1000,
        diametro_m=float(ficha["diametro_m"]),
        EA_kN=ea,alpha_por_C=dilatacion,
        fuente_material=origen,
        temperatura_tendido_C=temperatura,
        H_min_kN=.05*rotura,H_max_kN=.95*rotura,
        Cd=Cd,rho_kg_m3=rho,
    )
