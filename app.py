# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
from datetime import date

from analisis.io_excel import leer_puntos_excel
from analisis.catalogos import CONDUCTORES_ACSR
from analisis.engine import ejecutar_todo


# ============================================================
# UI: Datos del proyecto (solo captura + resumen)
# ============================================================
def ui_datos_proyecto() -> dict:
    st.sidebar.header("Datos del proyecto")

    nombre = st.sidebar.text_input("Nombre del proyecto", value="Proyecto prueba")
    lugar = st.sidebar.text_input("Lugar / Municipio", value="Honduras")
    cliente = st.sidebar.text_input("Cliente (opcional)", value="")
    responsable = st.sidebar.text_input("Responsable (opcional)", value="")
    fecha = st.sidebar.date_input("Fecha", value=date.today())

    st.sidebar.divider()
    st.sidebar.header("Parámetros de cálculo")

    calibre = st.sidebar.selectbox("Conductor", list(CONDUCTORES_ACSR.keys()), index=2)
    n_fases = st.sidebar.selectbox("Fases", [1, 2, 3], index=2)

    v_viento_ms = st.sidebar.number_input("Velocidad viento (m/s)", min_value=0.0, value=0.0, step=0.5)
    az_viento_deg = st.sidebar.number_input("Dirección viento (°)", min_value=0.0, max_value=360.0, value=0.0, step=1.0)

    diametro_m = float(CONDUCTORES_ACSR[calibre]["diametro_m"])
    st.sidebar.caption(f"Diámetro (catálogo): {diametro_m*1000:.2f} mm")
    Cd = st.sidebar.number_input("Cd", min_value=0.1, value=1.2, step=0.1)
    rho = st.sidebar.number_input("ρ aire (kg/m³)", min_value=0.5, value=1.225, step=0.01)

    st.sidebar.caption("Nota: 0°=Este, 90°=Norte. Dirección del viento en grados.")

    proyecto = {
        "nombre": nombre,
        "lugar": lugar,
        "cliente": cliente,
        "responsable": responsable,
        "fecha": str(fecha),
        "calibre": calibre,
        "n_fases": int(n_fases),
        "v_viento_ms": float(v_viento_ms),
        "az_viento_deg": float(az_viento_deg),
        "Cd": float(Cd),
        "rho": float(rho),
    }
    return proyecto


# ============================================================
# App
# ============================================================
st.set_page_config(page_title="Análisis Mecánico", layout="wide")
st.title("Análisis Mecánico (FASE 1) — Geometría + Cargas + Fuerzas por poste")

# Sidebar: ficha del proyecto + parámetros
proyecto = ui_datos_proyecto()

# Resumen del proyecto (en el cuerpo)
st.info(
    f"**Proyecto:** {proyecto['nombre']}  |  **Lugar:** {proyecto['lugar']}  |  "
    f"**Conductor:** {proyecto['calibre']}  |  **Fases:** {proyecto['n_fases']}  |  "
    f"**Viento:** {proyecto['v_viento_ms']} m/s a {proyecto['az_viento_deg']}°"
)

# -----------------------
# Entrada (Excel)
# -----------------------
archivo = st.file_uploader("📄 Sube tu Excel (.xlsx)", type=["xlsx"])

if not archivo:
    st.info("Sube un Excel con columnas: Punto, X, Y (opcional: Altitude, Poste, Espacio Retenida).")
    st.stop()

try:
    df = leer_puntos_excel(archivo)

    # -----------------------
    # Ejecutar motor
    # -----------------------
    res = ejecutar_todo(
        df,
        calibre=proyecto["calibre"],
        n_fases=proyecto["n_fases"],
        v_viento_ms=proyecto["v_viento_ms"],
        az_viento_deg=proyecto["az_viento_deg"],
        diametro_m=float(diametro_m),
        Cd=proyecto["Cd"],
        rho=proyecto["rho"],
    )

    # -----------------------
    # Tabs de resultados
    # -----------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Entrada", "Resumen por punto", "Cargas por tramo", "Fuerzas por poste", "Decisión"]
    )

    with tab1:
        st.subheader("Entrada")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Resumen por punto (estructura / retenidas)")
        st.dataframe(res["resumen"], use_container_width=True)

    with tab3:
        st.subheader("Cargas por tramo (peso + viento)")
        st.dataframe(res["cargas_tramo"], use_container_width=True)

    with tab4:
        st.subheader("Fuerzas por poste (suma vectorial)")
        st.dataframe(res["fuerzas_nodo"], use_container_width=True)

    with tab5:
        st.subheader("Decisión por punto (poste / retenida / autosoportado)")
        st.dataframe(res["decision"], use_container_width=True)

    # -----------------------
    # KPIs
    # -----------------------
    total_m = float(res.get("total_m", 0.0))
    st.success(f"✅ Longitud total: {total_m:,.2f} m")

except Exception as e:
    st.error("❌ Error procesando el archivo.")
    st.exception(e)
