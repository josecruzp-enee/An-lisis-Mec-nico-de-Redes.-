# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st

from analisis.io_excel import leer_puntos_excel
from analisis.geometria import calcular_tramos  # función que devuelve DataFrame

st.set_page_config(page_title="Análisis Mecánico - Distancias", layout="wide")
st.title("Análisis Mecánico (FASE 1) — Distancias")

archivo = st.file_uploader("📄 Sube tu Excel (.xlsx)", type=["xlsx"])

if not archivo:
    st.info("Sube un Excel con columnas: Punto, X, Y (opcional: Poste, Espacio Retenida).")
    st.stop()

try:
    df = leer_puntos_excel(archivo)

    st.subheader("Entrada")
    st.dataframe(df, use_container_width=True)

    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    df_tramos = calcular_tramos(puntos, etiquetas)

    st.subheader("Tramos y distancias")
    st.dataframe(df_tramos, use_container_width=True)

    total = float(df_tramos["Distancia (m)"].sum())
    st.success(f"✅ Longitud total: {total:,.2f} m")

except Exception as e:
    st.error("❌ Error procesando el archivo.")
    st.exception(e)

