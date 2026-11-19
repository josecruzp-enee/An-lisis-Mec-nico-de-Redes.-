"""Interfaz de regulación con propiedades ENEE y límites Checa automáticos.

El archivo histórico de coordenadas no necesita columnas mecánicas.
Los modos manuales y comparativo Nexans permanecen como alternativas.
El perfil Checa es una referencia técnica, no una norma ENEE.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from entradas.catalogos import CONDUCTORES_ACSR
from Analisis_mecanico_conductores.conductores.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR
from Analisis_mecanico_conductores.conductores.referencias_mecanicas_acsr_nexans import referencia_mecanica_nexans
from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee,seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.verificaciones.perfil_limites_tension_checa import construir_hipotesis_checa_acsr
from motor_general import ejecutar_modulo


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


def mostrar_calculo_directo(puntos, calibre, *, Cd=1.2, rho=1.225, configuracion_barrido=None):
    """Presenta formulario compacto. None hasta que sea enviado con datos."""
    nombre=(CONDUCTORES_ACSR[calibre]["nombre_mostrado"]
            if calibre in CONDUCTORES_ACSR else calibre)
    ficha=CONDUCTORES_VIAKON_ACSR[nombre]
    st.subheader("Completar el cálculo sin modificar tu Excel")
    st.caption(
        "Los puntos ya están cargados. ENEE y Checa completan automáticamente "
        "las propiedades y los límites dinámicos; podés elegir alternativas."
    )
    with st.form("calculo_directo_checa"):
        st.markdown("**Propiedades del conductor**")
        fuente_tipo=st.radio(
            "Propiedades termoelásticas",
            [
                "ENEE — Tabla 16 (propiedades automáticas)",
                "Ficha técnica documentada",
                "Referencia Nexans por construcción (comparativa)",
            ],
        )
        estado_enee="Final"
        if fuente_tipo.startswith("ENEE"):
            # La selección es por construcción, no sólo por calibre:
            # 266.8 MCM OWL (Viakon) no figura en Tabla 16, pero sí PARTRIDGE.
            clave_calibre=str(ficha["calibre"]).replace(" MCM","")
            aves=[
                f for f in leer_catalogo_enee()
                if f["calibre"].replace(" MCM","")==clave_calibre
            ]
            if aves:
                opciones=[f["nombre"] for f in aves]
                nombre_enee=st.selectbox(
                    "Construcción ACSR ENEE",
                    opciones,
                    index=opciones.index(ficha["codigo"])
                    if ficha["codigo"] in opciones else 0,
                )
                estado_enee=st.selectbox(
                    "Módulo de elasticidad",["Final","Inicial"],
                    help="E final o inicial; no predice creep.",
                )
            else:
                nombre_enee=None
        temperatura=st.number_input(
            "Temperatura de tendido / referencia (°C)",value=20.0,
        )
        EA=alpha=fuente=""
        if fuente_tipo.startswith("ENEE"):
            try:
                if nombre_enee is None:
                    raise ValueError("No hay ficha ENEE para este calibre")
                vista=seleccionar_conductor_enee(
                    ficha["calibre"],nombre_enee,estado_enee
                )
            except (KeyError,ValueError) as exc:
                st.error(
                    "El conductor seleccionado no está en la Tabla 16 ENEE. "
                    "Elegí otra construcción o utilizá ficha manual. "
                    +str(exc)
                )
                vista=None
            if vista is not None:
                st.write(
                    f"**ENEE {vista['nombre']} · {estado_enee}:** "
                    f"EA = {vista['EA_kN']:,.2f} kN · "
                    f"α = {vista['alpha_por_C']:.6g} 1/°C · "
                    f"peso = {vista['peso_kg_m']:.4f} kg/m · "
                    f"diámetro = {vista['diametro_m']*1000:.2f} mm · "
                    f"rotura = {vista['ruptura_kN']:.3f} kN"
                )
                st.caption(vista["fuente"])
        elif fuente_tipo.startswith("Ficha"):
            c1,c2=st.columns(2)
            with c1:
                EA=st.text_input("Rigidez axial EA (kN)",value="")
            with c2:
                alpha=st.text_input("Dilatación α (1/°C)",value="")
            fuente=st.text_input(
                "Fuente documental de las propiedades",value=""
            )
        else:
            st.caption(
                "Referencia Nexans por construcción equivalente: "
                "valores comparativos, no ficha de producto."
            )
        st.markdown("**Criterio de tensión mecánica**")
        perfil_tension=st.radio(
            "Perfil de límites",
            [
                "Checa — TCD/THF ACSR (referencia técnica)",
                "Introducir límites documentados manualmente",
            ],
            help="Checa: 20 % RTS a 15 °C y 22.5 % RTS a -5 °C sin viento/hielo. No equivale a norma ENEE ni verifica límite estático.",
        )
        st.caption(
            "Checa controla TCD y horas frías; máximo viento/hielo sigue siendo "
            "barrido exploratorio hasta definir un límite estático documentado."
        )
        datos=pd.DataFrame([
            {"Hipotesis":"Estado_1","Temperatura_C":None,
             "Viento_ms":None,"T_limite_kN":None,
             "Fuente_limite":"","Criterio_diseno":""},
        ],columns=COLUMNAS)
        tabla=(
            st.data_editor(
                datos,num_rows="dynamic",hide_index=True,
                use_container_width=True,
                key="tabla_climas_regulacion",
            )
            if perfil_tension.startswith("Introducir") else None
        )
        enviar=st.form_submit_button("Calcular tensión y flechas")
    if not enviar:
        return None
    hip=(_leer_hipotesis_usuario(tabla) if tabla is not None else None)
    if fuente_tipo.startswith("ENEE"):
        if vista is None:
            st.error("No se puede calcular con conductor ENEE no catalogado.")
            return None
        propiedades=vista
        ea=propiedades["EA_kN"]
        dilatacion=propiedades["alpha_por_C"]
        origen=propiedades["fuente"]
        peso_kN_m=propiedades["peso_kN_m"]
        diametro_m=propiedades["diametro_m"]
        rotura=propiedades["ruptura_kN"]
        st.caption(
            "Modelo elástico lineal ENEE: no incluye predicción de creep."
        )
    elif fuente_tipo.startswith("Referencia"):
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
    if not fuente_tipo.startswith("ENEE"):
        rotura=float(ficha["carga_rotura_kN"])
        peso_kN_m=float(ficha["peso_kg_m"])*9.80665/1000
        diametro_m=float(ficha["diametro_m"])
    if hip is None:
        hip=construir_hipotesis_checa_acsr(rotura)
        st.dataframe(hip,use_container_width=True,hide_index=True)
        st.warning(
            "Checa: límites dinámicos TCD/THF. Viento e hielo del barrido "
            "no constituyen verificaciones normativas."
        )
    return ejecutar_modulo("conductores",
        puntos,
        propiedades={
            "peso_kN_m":peso_kN_m,
            "diametro_m":diametro_m,
            "EA_kN":ea,
            "alpha_por_C":dilatacion,
            "ruptura_kN":rotura,
            "fuente":origen,
        },
        temperatura_tendido_C=temperatura,
        perfil_tension=("Checa" if tabla is None else "Manual"),
        hipotesis_manuales=hip if tabla is not None else None,
        configuracion_barrido=configuracion_barrido,
        Cd=Cd,rho=rho,
    )
