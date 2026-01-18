# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date
from typing import Dict, Any, Optional

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from analisis.io_excel import leer_puntos_excel
from analisis.catalogos import CONDUCTORES_ACSR
from analisis.engine import ejecutar_todo


# ============================================================
# Config / UI helpers
# ============================================================
def configurar_pagina() -> None:
    st.set_page_config(page_title="Análisis Mecánico", layout="wide")
    st.title("Análisis Mecánico (FASE 1) — Geometría + Cargas + Fuerzas por poste")


def ui_datos_proyecto() -> Dict[str, Any]:
    st.sidebar.header("Datos del proyecto")

    nombre = st.sidebar.text_input("Nombre del proyecto", value="Proyecto prueba")
    lugar = st.sidebar.text_input("Lugar / Municipio", value="Honduras")
    cliente = st.sidebar.text_input("Cliente (opcional)", value="")
    responsable = st.sidebar.text_input("Responsable (opcional)", value="")
    fecha = st.sidebar.date_input("Fecha", value=date.today())

    st.sidebar.divider()
    st.sidebar.header("Parámetros de cálculo")

    calibres = list(CONDUCTORES_ACSR.keys())
    calibre = st.sidebar.selectbox("Conductor", calibres, index=min(2, max(len(calibres) - 1, 0)))
    n_fases = st.sidebar.selectbox("Fases", [1, 2, 3], index=2)

    v_viento_ms = st.sidebar.number_input("Velocidad viento (m/s)", min_value=0.0, value=0.0, step=0.5)
    az_viento_deg = st.sidebar.number_input(
        "Dirección viento (°)", min_value=0.0, max_value=360.0, value=0.0, step=1.0
    )

    diametro_m = float(CONDUCTORES_ACSR[calibre]["diametro_m"])
    st.sidebar.caption(f"Diámetro (catálogo): {diametro_m * 1000:.2f} mm")

    Cd = st.sidebar.number_input("Cd", min_value=0.1, value=1.2, step=0.1)
    rho = st.sidebar.number_input("ρ aire (kg/m³)", min_value=0.5, value=1.225, step=0.01)

    st.sidebar.caption("Nota: 0°=Este, 90°=Norte. Dirección del viento en grados.")

    return {
        "nombre": nombre,
        "lugar": lugar,
        "cliente": cliente,
        "responsable": responsable,
        "fecha": str(fecha),
        "calibre": str(calibre),
        "n_fases": int(n_fases),
        "v_viento_ms": float(v_viento_ms),
        "az_viento_deg": float(az_viento_deg),
        "diametro_m": float(diametro_m),
        "Cd": float(Cd),
        "rho": float(rho),
    }


def mostrar_resumen_proyecto(proyecto: Dict[str, Any]) -> None:
    st.info(
        f"**Proyecto:** {proyecto['nombre']}  |  **Lugar:** {proyecto['lugar']}  |  "
        f"**Conductor:** {proyecto['calibre']}  |  **Fases:** {proyecto['n_fases']}  |  "
        f"**Viento:** {proyecto['v_viento_ms']} m/s a {proyecto['az_viento_deg']}°"
    )


def ui_cargar_excel() -> Optional[Any]:
    """Devuelve el objeto 'archivo' de Streamlit o None si no hay archivo."""
    st.subheader("Entrada")
    archivo = st.file_uploader("📄 Sube tu Excel (.xlsx)", type=["xlsx"])
    if not archivo:
        st.info("Sube un Excel con columnas: Punto, X, Y (opcional: Altitud (m), Poste, Espacio Retenida).")
        return None
    return archivo


# ============================================================
# Cálculo
# ============================================================
def ejecutar_calculo(df: pd.DataFrame, proyecto: Dict[str, Any]) -> Dict[str, Any]:
    return ejecutar_todo(
        df,
        calibre=proyecto["calibre"],
        n_fases=proyecto["n_fases"],
        v_viento_ms=proyecto["v_viento_ms"],
        az_viento_deg=proyecto["az_viento_deg"],
        diametro_m=proyecto["diametro_m"],
        Cd=proyecto["Cd"],
        rho=proyecto["rho"],
    )


# ============================================================
# Render de resultados
# ============================================================
def _tabla(df: pd.DataFrame, title: str) -> None:
    st.subheader(title)
    st.dataframe(df, use_container_width=True)


def _render_tab_entrada(df: pd.DataFrame) -> None:
    _tabla(df, "Entrada")


def _render_tab_resumen(res: Dict[str, Any]) -> None:
    _tabla(res["resumen"], "Resumen por punto (estructura / retenidas)")


def _render_tab_cargas(res: Dict[str, Any]) -> None:
    _tabla(res["cargas_tramo"], "Cargas por tramo (peso + viento)")


def _render_tab_fuerzas(res: Dict[str, Any]) -> None:
    _tabla(res["fuerzas_nodo"], "Fuerzas por poste (suma vectorial)")


def _render_tab_decision(res: Dict[str, Any]) -> None:
    _tabla(res["decision"], "Decisión por punto (poste / retenida / autosoportado)")


def _render_tab_perfil(res: Dict[str, Any]) -> None:
    st.subheader("Perfil longitudinal (si existe Altitud)")

    perfil = res.get("perfil")
    if not perfil:
        st.info("No se detectó columna 'Altitud' en el Excel, así que no se calculó el perfil.")
        return

    # Tabla por vanos
    df_vanos = pd.DataFrame(perfil.get("tabla_vanos", []))
    if not df_vanos.empty:
        st.dataframe(df_vanos, use_container_width=True)

        # KPI global
        if "Despeje mín (m)" in df_vanos.columns:
            try:
                despeje_min_global = float(df_vanos["Despeje mín (m)"].astype(float).min())
                st.metric("Despeje mínimo global (m)", f"{despeje_min_global:.3f}")
            except Exception:
                pass
    else:
        st.warning("Perfil calculado, pero la tabla de vanos está vacía.")

    # Gráfica (Terreno vs Conductor)
    X = perfil.get("X_prof")
    G = perfil.get("G_prof")
    Y = perfil.get("Y_prof")

    if X is None or G is None or Y is None or len(X) == 0:
        st.warning("Perfil calculado, pero no hay series para graficar (X_prof/G_prof/Y_prof).")
        return

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(X, G, label="Terreno")
    ax.plot(X, Y, label="Conductor")
    ax.set_xlabel("Distancia acumulada (m)")
    ax.set_ylabel("Cota (m)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    st.pyplot(fig, clear_figure=True)


def mostrar_tabs_resultados(df: pd.DataFrame, res: Dict[str, Any]) -> None:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Entrada", "Resumen por punto", "Cargas por tramo", "Fuerzas por poste", "Decisión", "Perfil"]
    )

    with tab1:
        _render_tab_entrada(df)

    with tab2:
        _render_tab_resumen(res)

    with tab3:
        _render_tab_cargas(res)

    with tab4:
        _render_tab_fuerzas(res)

    with tab5:
        _render_tab_decision(res)

    with tab6:
        _render_tab_perfil(res)


def mostrar_kpis(res: Dict[str, Any]) -> None:
    total_m = float(res.get("total_m", 0.0))
    st.success(f"✅ Longitud total: {total_m:,.2f} m")


# ============================================================
# Main
# ============================================================
def main() -> None:
    configurar_pagina()

    proyecto = ui_datos_proyecto()
    mostrar_resumen_proyecto(proyecto)

    archivo = ui_cargar_excel()
    if not archivo:
        st.stop()

    try:
        df = leer_puntos_excel(archivo)
        res = ejecutar_calculo(df, proyecto)

        mostrar_tabs_resultados(df, res)
        mostrar_kpis(res)

    except Exception as e:
        st.error("❌ Error procesando el archivo.")
        st.exception(e)


if __name__ == "__main__":
    main()
