# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st

from analisis.io_excel import leer_puntos_excel
from analisis.catalogos import CONDUCTORES_ACSR
from analisis.engine import ejecutar_todo


st.set_page_config(page_title="Análisis Mecánico", layout="wide")
st.title("Análisis Mecánico (FASE 1) — Geometría + Cargas + Fuerzas por poste")

# -----------------------
# Sidebar (parámetros)
# -----------------------
st.sidebar.header("Viento y cargas por tramo")

calibre = st.sidebar.selectbox("Conductor", list(CONDUCTORES_ACSR.keys()), index=2)
n_fases = st.sidebar.selectbox("Fases", [1, 2, 3], index=2)

v_viento_ms = st.sidebar.number_input("Velocidad viento (m/s)", min_value=0.0, value=0.0, step=0.5)
az_viento_deg = st.sidebar.number_input("Dirección viento (°)", min_value=0.0, max_value=360.0, value=0.0, step=1.0)

diametro_m = st.sidebar.number_input("Diámetro conductor (m)", min_value=0.0001, value=0.0100, step=0.0005, format="%.4f")
Cd = st.sidebar.number_input("Cd", min_value=0.1, value=1.2, step=0.1)
rho = st.sidebar.number_input("ρ aire (kg/m³)", min_value=0.5, value=1.225, step=0.01)

st.sidebar.caption("Nota: 0°=Este, 90°=Norte. Dirección del viento en grados.")

# -----------------------
# Entrada (Excel)
# -----------------------
archivo = st.file_uploader("📄 Sube tu Excel (.xlsx)", type=["xlsx"])

if not archivo:
    st.info("Sube un Excel con columnas: Punto, X, Y (opcional: Poste, Espacio Retenida).")
    st.stop()

try:
    df = leer_puntos_excel(archivo)

    # -----------------------
    # Ejecutar motor
    # -----------------------
    res = ejecutar_todo(
        df,
        calibre=calibre,
        n_fases=int(n_fases),
        v_viento_ms=float(v_viento_ms),
        az_viento_deg=float(az_viento_deg),
        diametro_m=float(diametro_m),
        Cd=float(Cd),
        rho=float(rho),
    )

    # -----------------------
    # Mostrar resultados
    # -----------------------
    st.subheader("Entrada")
    st.dataframe(df, use_container_width=True)

    st.subheader("Resumen por punto (estructura / retenidas)")
    st.dataframe(res["resumen"], use_container_width=True)

    st.subheader("Cargas por tramo (peso + viento)")
    st.dataframe(res["cargas_tramo"], use_container_width=True)

    st.subheader("Fuerzas por poste (suma vectorial)")
    st.dataframe(res["fuerzas_nodo"], use_container_width=True)

    # -----------------------
    # KPIs
    # -----------------------
    total_m = float(res.get("total_m", 0.0))
    st.success(f"✅ Longitud total: {total_m:,.2f} m")

except Exception as e:
    st.error("❌ Error procesando el archivo.")
    st.exception(e)
