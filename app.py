# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date
from typing import Dict, Any, Optional

import numpy as np
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


def _render_tab_perfil(df: pd.DataFrame, res: Dict[str, Any]) -> None:
    st.subheader("Perfil longitudinal (si existe Altitud)")
    perfil = res.get("perfil")

    if not perfil:
        st.info("No se detectó columna 'Altitud' en el Excel, así que no se calculó el perfil.")
        return

    # Tabla de vanos
    df_vanos = pd.DataFrame(perfil.get("tabla_vanos", []))
    if not df_vanos.empty:
        st.dataframe(df_vanos, use_container_width=True)

    # Perfil suave (malla)
    X_prof = np.asarray(perfil.get("X_prof", []), dtype=float)
    G_prof = np.asarray(perfil.get("G_prof", []), dtype=float)
    Y_prof = np.asarray(perfil.get("Y_prof", []), dtype=float)

    if X_prof.size == 0 or G_prof.size == 0 or Y_prof.size == 0:
        st.warning("No hay datos suficientes para graficar el perfil (X_prof/G_prof/Y_prof vacíos).")
        return

    # ============================================================
    # 1) Detectar nombres de columnas (vienen como "X (m)" y "Y (m)")
    # ============================================================
    df_local = df.copy()
    df_local.columns = [c.strip() for c in df_local.columns]

    def _pick_col(posibles):
        for c in posibles:
            if c in df_local.columns:
                return c
        return None

    col_x = _pick_col(["X (m)", "X", "x", "X_m", "X_m)"])
    col_y = _pick_col(["Y (m)", "Y", "y", "Y_m", "Y_m)"])
    col_poste = _pick_col(["Poste", "POSTE"])
    col_punto = _pick_col(["Punto", "PUNTO"])

    if col_x is None or col_y is None:
        st.warning("No se pudo simular postes: faltan columnas 'X (m)'/'Y (m)' (o 'X'/'Y').")
        postes = []
        dist_puntos = np.array([], dtype=float)
    else:
        x_raw = pd.to_numeric(df_local[col_x], errors="coerce").to_numpy(dtype=float)
        y_raw = pd.to_numeric(df_local[col_y], errors="coerce").to_numpy(dtype=float)

        if np.isnan(x_raw).any() or np.isnan(y_raw).any():
            st.warning("No se pudo simular postes: hay valores no numéricos en columnas X/Y.")
            postes = []
            dist_puntos = np.array([], dtype=float)
        else:
            dx = np.diff(x_raw, prepend=x_raw[0])
            dy = np.diff(y_raw, prepend=y_raw[0])
            dist_puntos = np.cumsum(np.sqrt(dx**2 + dy**2))

            if col_poste is not None:
                postes = (
                    df_local[col_poste]
                    .astype(str)
                    .str.strip()
                    .replace({"nan": ""})
                    .tolist()
                )
            else:
                postes = []

    # ============================================================
    # 2) Catálogo de alturas típicas (m) — AJUSTABLE
    #    (Puse valores típicos; tú los alineas a tu estándar)
    # ============================================================
    ALTURA_POSTE_M = {
        # Concreto (PC)
        "PC-30": 9.0,
        "PC-35": 10.5,
        "PC-40": 12.0,
        "PC-40A": 12.0,
        "PC-45": 13.5,
        "PC-50": 15.0,

        # Madera (PM)
        "PM-30": 9.0,
        "PM-35": 10.5,
        "PM-40": 12.0,
        "PM-45": 13.5,
        "PM-50": 15.0,
    }

    # ============================================================
    # 3) Plot
    # ============================================================
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(X_prof, G_prof, label="Terreno", linewidth=2)
    ax.plot(X_prof, Y_prof, label="Conductor", linewidth=2)

    # ============================================================
    # 4) Dibujar postes usando distancias reales por punto
    # ============================================================
    if len(postes) > 0 and dist_puntos.size > 0:
        # Interpolar terreno/conductor del perfil en las distancias de puntos
        G_puntos = np.interp(dist_puntos, X_prof, G_prof)
        Y_puntos = np.interp(dist_puntos, X_prof, Y_prof)

        n = min(len(postes), len(dist_puntos))

        for i in range(n):
            tipo = postes[i]
            if not tipo:
                continue

            # Normalización: "PM 40" -> "PM-40", "pm-40" -> "PM-40"
            t = str(tipo).upper().strip()
            t = t.replace(" ", "").replace("_", "-")
            if "-" not in t and len(t) >= 4:
                # casos raros tipo "PM40"
                t = t[:2] + "-" + t[2:]

            h = ALTURA_POSTE_M.get(t, 12.0)  # default 12 m si no está en el catálogo

            x = float(dist_puntos[i])
            y_base = float(G_puntos[i])
            y_top = y_base + h

            # Poste (línea vertical)
            ax.plot([x, x], [y_base, y_top], linestyle="--", linewidth=2, alpha=0.7)

            # Punto de amarre (marcamos conductor en el poste)
            ax.scatter([x], [float(Y_puntos[i])], zorder=5)

            # Etiqueta: Punto + tipo de poste si existe "Punto"
            if col_punto is not None:
                etiqueta = f"{df_local[col_punto].iloc[i]} {t}"
            else:
                etiqueta = t

            ax.text(x, y_top + 0.3, etiqueta, ha="center", fontsize=8)
    else:
        st.info("No se dibujaron postes (falta columna 'Poste' o no se pudo calcular distancia por punto).")

    ax.set_xlabel("Distancia acumulada (m)")
    ax.set_ylabel("Cota / Altitud (m)")
    ax.set_title("Perfil longitudinal del conductor")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()

    st.pyplot(fig)



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
        _render_tab_perfil(df, res)


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
