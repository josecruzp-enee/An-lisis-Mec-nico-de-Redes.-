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
        st.info("Sube un Excel con columnas: Punto, X, Y (opcional: Altitud, Poste, Espacio Retenida).")
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


def _render_tab_resumen(res: Dict[str, Any], df_entrada: pd.DataFrame) -> None:
    _tabla(res["resumen"], "Resumen por punto (estructura / retenidas)")

    st.divider()
    st.subheader("Vista superior — Trayectoria y retenidas (desde Resumen por punto)")

    # --- Preparar datos del Excel ---
    df_local = df_entrada.copy()
    df_local.columns = [c.strip() for c in df_local.columns]

    def _pick_col(cands):
        for c in cands:
            if c in df_local.columns:
                return c
        return None

    col_x = _pick_col(["X (m)", "X", "x"])
    col_y = _pick_col(["Y (m)", "Y", "y"])
    col_p = _pick_col(["Punto", "PUNTO"])
    col_esp = _pick_col(["Espacio Retenida", "ESPACIO RETENIDA", "EspacioRetenida"])

    if col_x is None or col_y is None:
        st.warning("No se puede dibujar la vista superior: faltan columnas X/Y en el Excel.")
        return

    x = pd.to_numeric(df_local[col_x], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(df_local[col_y], errors="coerce").to_numpy(dtype=float)

    if np.isnan(x).any() or np.isnan(y).any():
        st.warning("No se puede dibujar la vista superior: hay valores no numéricos en X/Y.")
        return

    puntos = df_local[col_p].astype(str).str.strip().tolist() if col_p else [f"P{i+1}" for i in range(len(df_local))]

    # --- Tomar Retenidas desde la tabla resumen ---
    df_r = res["resumen"].copy()
    df_r.columns = [c.strip() for c in df_r.columns]

    def _pick_col_r(cands):
        for c in cands:
            if c in df_r.columns:
                return c
        return None

    col_r_p = _pick_col_r(["Punto", "PUNTO"])
    col_ret = _pick_col_r(["Retenidas", "RETENIDAS"])
    if col_r_p is None or col_ret is None:
        st.warning("La tabla resumen no trae 'Punto' y/o 'Retenidas'.")
        return

    mapa_ret = {}
    for _, row in df_r.iterrows():
        p = str(row[col_r_p]).strip()
        try:
            mapa_ret[p] = int(row[col_ret])
        except Exception:
            mapa_ret[p] = 0

    # --- Espacio retenida (SI/NO) del excel ---
    def _norm_si_no(v):
        s = str(v).strip().upper()
        if s in ("SI", "SÍ", "1", "TRUE", "YES"):
            return "SI"
        if s in ("NO", "0", "FALSE", "N"):
            return "NO"
        return s

    mapa_esp = {}
    if col_esp:
        for i, p in enumerate(puntos):
            mapa_esp[p] = _norm_si_no(df_local[col_esp].iloc[i])

    # --- Controles ---
    L = float(st.slider("Longitud visual de flecha (m)", 5.0, 80.0, 25.0, 1.0))
    lado_por_defecto = st.selectbox("Lado por defecto si no hay 'Espacio Retenida'", ["IZQUIERDA", "DERECHA"], index=0)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(x, y, linewidth=2, label="Trayectoria")
    ax.scatter(x, y, zorder=3)

    for i in range(len(x)):
        ax.text(x[i], y[i], f" {puntos[i]}", fontsize=8, va="bottom")

    # Flechas con quiver
    def _flecha(ax, x0, y0, dx, dy, L):
        ax.quiver(
            [x0], [y0], [dx], [dy],
            angles="xy", scale_units="xy", scale=1 / L,
            width=0.003, headwidth=6, headlength=7, headaxislength=6,
            alpha=0.9
        )

    for i, p in enumerate(puntos):
        r = mapa_ret.get(p, 0)
        if r <= 0:
            continue

        # Tangente (aprox) para normal
        if 0 < i < len(x) - 1:
            tx = (x[i + 1] - x[i - 1])
            ty = (y[i + 1] - y[i - 1])
        elif i == 0:
            tx = (x[1] - x[0])
            ty = (y[1] - y[0])
        else:
            tx = (x[-1] - x[-2])
            ty = (y[-1] - y[-2])

        norm = float(np.hypot(tx, ty))
        if norm == 0:
            continue
        tx, ty = tx / norm, ty / norm

        # Normales
        nxL, nyL = -ty, tx
        nxR, nyR = ty, -tx

        esp = mapa_esp.get(p, "")
        if esp == "SI":
            use_left = True
        elif esp == "NO":
            use_left = False
        else:
            use_left = (lado_por_defecto == "IZQUIERDA")

        if r == 1:
            dx, dy = (nxL, nyL) if use_left else (nxR, nyR)
            _flecha(ax, x[i], y[i], dx, dy, L)
        else:
            _flecha(ax, x[i], y[i], nxL, nyL, L)
            _flecha(ax, x[i], y[i], nxR, nyR, L)

    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")
    ax.set_title("Trayectoria y retenidas (vista superior)")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.axis("equal")
    ax.legend()

    st.pyplot(fig)


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

    # Perfil (malla)
    X_prof = np.asarray(perfil.get("X_prof", []), dtype=float)
    G_prof = np.asarray(perfil.get("G_prof", []), dtype=float)
    Y_prof = np.asarray(perfil.get("Y_prof", []), dtype=float)

    if X_prof.size == 0 or G_prof.size == 0 or Y_prof.size == 0:
        st.warning("No hay datos suficientes para graficar el perfil (X_prof/G_prof/Y_prof vacíos).")
        return

    # --- limpiar NaN/inf (Streamlit Cloud se rompe si hay NaNs) ---
    mask = np.isfinite(X_prof) & np.isfinite(G_prof) & np.isfinite(Y_prof)
    X_prof, G_prof, Y_prof = X_prof[mask], G_prof[mask], Y_prof[mask]
    if X_prof.size == 0:
        st.warning("El perfil quedó vacío tras filtrar NaN/inf.")
        return

    # --- ordenar por X (importante para plot e interp) ---
    order = np.argsort(X_prof)
    X_prof, G_prof, Y_prof = X_prof[order], G_prof[order], Y_prof[order]

    # --- asegurar X estrictamente creciente para interp ---
    X_i, idx = np.unique(X_prof, return_index=True)
    G_i = G_prof[idx]
    Y_i = Y_prof[idx]
    if X_i.size < 2:
        st.warning("No hay suficientes puntos únicos para graficar/interpolar el perfil.")
        return

    # ============================================================
    # Preparar postes (opcional) desde df de entrada
    # ============================================================
    df_local = df.copy()
    df_local.columns = [c.strip() for c in df_local.columns]

    def _pick_col(posibles):
        for c in posibles:
            if c in df_local.columns:
                return c
        return None

    col_x = _pick_col(["X (m)", "X", "x", "X_m"])
    col_y = _pick_col(["Y (m)", "Y", "y", "Y_m"])
    col_poste = _pick_col(["Poste", "POSTE"])
    col_punto = _pick_col(["Punto", "PUNTO"])

    postes: list[str] = []
    dist_puntos = np.array([], dtype=float)

    if col_x is not None and col_y is not None:
        x_raw = pd.to_numeric(df_local[col_x], errors="coerce").to_numpy(dtype=float)
        y_raw = pd.to_numeric(df_local[col_y], errors="coerce").to_numpy(dtype=float)

        if not (np.isnan(x_raw).any() or np.isnan(y_raw).any()):
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

    # ============================================================
    # Plot perfil
    # ============================================================
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(X_i, G_i, label="Terreno", linewidth=2)
    ax.plot(X_i, Y_i, label="Conductor", linewidth=2)

    # Catálogo simple de alturas (opcional) para dibujar postes
    ALTURA_POSTE_M = {
        "PC-30": 9.0, "PC-35": 10.5, "PC-40": 12.0, "PC-40A": 12.0, "PC-45": 13.5, "PC-50": 15.0,
        "PM-30": 9.0, "PM-35": 10.5, "PM-40": 12.0, "PM-45": 13.5, "PM-50": 15.0,
    }

    if len(postes) > 0 and dist_puntos.size > 0:
        # Interpolar terreno/conductor del perfil en las distancias de puntos
        G_puntos = np.interp(dist_puntos, X_i, G_i)
        Y_puntos = np.interp(dist_puntos, X_i, Y_i)

        n = min(len(postes), len(dist_puntos))
        for i in range(n):
            tipo = postes[i]
            if not tipo:
                continue

            t = str(tipo).upper().strip().replace(" ", "").replace("_", "-")
            if "-" not in t and len(t) >= 4:  # casos tipo "PM40"
                t = t[:2] + "-" + t[2:]

            h = ALTURA_POSTE_M.get(t, 12.0)

            x_i_pt = float(dist_puntos[i])
            y_base = float(G_puntos[i])
            y_top = y_base + h

            ax.plot([x_i_pt, x_i_pt], [y_base, y_top], linestyle="--", linewidth=2, alpha=0.7)
            ax.scatter([x_i_pt], [float(Y_puntos[i])], zorder=5)

            etiqueta = f"{df_local[col_punto].iloc[i]} {t}" if col_punto is not None else t
            ax.text(x_i_pt, y_top + 0.3, etiqueta, ha="center", fontsize=8)
    else:
        st.caption("Postes no dibujados (falta columna 'Poste' o no se pudo calcular distancia por punto).")

    ax.set_xlabel("Distancia acumulada (m)")
    ax.set_ylabel("Cota / Altitud (m)")
    ax.set_title("Perfil longitudinal del conductor")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()

    # En Cloud ayuda a evitar render roto
    st.pyplot(fig, clear_figure=True)




def _render_tab_retenidas(res: Dict[str, Any]) -> None:
    st.subheader("Retenidas (tensión / verificación)")

    df_ret = res.get("retenidas", None)
    if df_ret is None or df_ret.empty:
        st.info("No hay resultados de retenidas (o no se calcularon).")
        return

    st.dataframe(df_ret, use_container_width=True)

    if "Cumple retenida" in df_ret.columns:
        n = len(df_ret)
        n_no = int((df_ret["Cumple retenida"] == "NO").sum())
        n_si = int((df_ret["Cumple retenida"] == "SI").sum())
        st.caption(f"Cumple: {n_si} / {n}  |  No cumple: {n_no}")


def mostrar_tabs_resultados(df: pd.DataFrame, res: Dict[str, Any]) -> None:
    tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Entrada", "Resumen por punto", "Cargas por tramo", "Fuerzas por poste", "Decisión", "Retenidas", "Perfil"]
    )

    with tab0:
        _render_tab_entrada(df)

    with tab1:
        _render_tab_resumen(res, df)

    with tab2:
        _render_tab_cargas(res)

    with tab3:
        _render_tab_fuerzas(res)

    with tab4:
        _render_tab_decision(res)

    with tab5:
        _render_tab_retenidas(res)

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
