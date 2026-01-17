# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st

from analisis.io_excel import leer_puntos_excel
from analisis.geometria import (
    calcular_tramos,
    calcular_deflexiones,
    clasificar_por_angulo,
)

st.set_page_config(page_title="Análisis Mecánico - Geometría", layout="wide")
st.title("Análisis Mecánico (FASE 1) — Geometría (Distancias + Deflexión)")

archivo = st.file_uploader("📄 Sube tu Excel (.xlsx)", type=["xlsx"])

if not archivo:
    st.info("Sube un Excel con columnas: Punto, X, Y (opcional: Poste, Espacio Retenida).")
    st.stop()

try:
    # -----------------------
    # 1) Lectura de entrada
    # -----------------------
    df = leer_puntos_excel(archivo)

    st.subheader("Entrada")
    st.dataframe(df, use_container_width=True)

    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    # -----------------------
    # 2) Tramos y distancias
    # -----------------------
    df_tramos = calcular_tramos(puntos, etiquetas)

    st.subheader("Tramos y distancias")
    st.dataframe(df_tramos, use_container_width=True)

    total = float(df_tramos["Distancia (m)"].sum())
    st.success(f"✅ Longitud total: {total:,.2f} m")

    # -----------------------
    # 3) Deflexión + clasificación
    # -----------------------
    st.subheader("Deflexión y clasificación por punto")

    df_def = calcular_deflexiones(puntos, etiquetas)  # P2..P(n-1)

    if df_def.empty:
        st.info("Se requieren al menos 3 puntos para calcular deflexiones.")
    else:
        estructuras = []
        retenidas = []
        for ang in df_def["Deflexión (°)"].tolist():
            est, ret = clasificar_por_angulo(float(ang))
            estructuras.append(est)
            retenidas.append(ret)

        df_def["Estructura"] = estructuras
        df_def["Retenidas"] = retenidas

        st.dataframe(df_def, use_container_width=True)

    # -----------------------
    # 4) Resumen por punto (incluye remates)
    # -----------------------
    st.subheader("Resumen por punto (incluye remates)")

    # Creamos una tabla por punto con estructura y retenidas
    # P1 y último = Remate
    resumen = df[["Punto", "Poste", "Espacio Retenida"]].copy()
    resumen["Deflexión (°)"] = "-"
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = 1

    # Insertamos deflexiones/clasificación para puntos interiores
    if not df_def.empty:
        mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
        for i in range(1, len(resumen) - 1):
            p = resumen.loc[i, "Punto"]
            if p in mapa.index:
                resumen.loc[i, "Deflexión (°)"] = float(mapa.loc[p, "Deflexión (°)"])
                resumen.loc[i, "Estructura"] = str(mapa.loc[p, "Estructura"])
                resumen.loc[i, "Retenidas"] = int(mapa.loc[p, "Retenidas"])

        # Para puntos interiores “Paso” normalmente retenidas=0 (según tu función)
        # Aquí ya viene desde clasificar_por_angulo()

    st.dataframe(resumen, use_container_width=True)

except Exception as e:
    st.error("❌ Error procesando el archivo.")
    st.exception(e)
