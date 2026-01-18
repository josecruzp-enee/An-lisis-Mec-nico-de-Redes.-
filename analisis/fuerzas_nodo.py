# analisis/fuerzas_nodo.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict
import numpy as np
import pandas as pd


def _unit_vector_from_azimut_deg(az_deg: float) -> np.ndarray:
    """
    Vector unitario en la dirección del tramo (azimut en grados, 0°=E, 90°=N).
    """
    th = np.deg2rad(float(az_deg))
    return np.array([np.cos(th), np.sin(th)], dtype=float)


def calcular_fuerzas_en_nodos(
    df_tramos: pd.DataFrame,
    df_resumen: pd.DataFrame,
    *,
    usar_col_w: str = "w_viento_eff (kN/m)",   # 👈 usa SOLO viento lateral para planta
    azimut_viento_deg: float = 0.0,            # 👈 dirección global del viento
) -> pd.DataFrame:
    """
    Fuerzas en nodos por cargas laterales de viento (planta).

    - Para cada tramo: F = w_eff(kN/m) * L(m)
    - Se reparte 50% al nodo A y 50% al nodo B
    - Dirección = azimut del viento (0°=E, 90°=N)

    Nota: Esto NO incluye “fuerza por deflexión” (eso es otro término).
    """

    if df_tramos is None or df_tramos.empty:
        return pd.DataFrame()

    req = ["Tramo", "Distancia (m)", usar_col_w]
    for c in req:
        if c not in df_tramos.columns:
            raise ValueError(f"df_tramos debe incluir columna '{c}'.")

    if df_resumen is None or df_resumen.empty or "Punto" not in df_resumen.columns:
        raise ValueError("df_resumen debe incluir columna 'Punto'.")

    tr = df_tramos.copy()
    res = df_resumen.copy()

    def _split_tramo(s: str):
        s = str(s).strip()
        for sep in ["→", "->", "—>", "=>"]:
            if sep in s:
                a, b = s.split(sep, 1)
                return a.strip(), b.strip()
        parts = s.replace("-", " ").replace(">", " ").split()
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        raise ValueError(f"No pude interpretar Tramo='{s}'")

    A_list, B_list = [], []
    for s in tr["Tramo"].tolist():
        a, b = _split_tramo(s)
        A_list.append(a)
        B_list.append(b)

    tr["_A"] = A_list
    tr["_B"] = B_list

    # F_total por tramo (kN) = w_eff * L
    tr["_Ftramo_kN"] = tr[usar_col_w].astype(float) * tr["Distancia (m)"].astype(float)

    # Dirección global del viento (unitario)
    u_w = _unit_vector_from_azimut_deg(float(azimut_viento_deg))

    contrib: Dict[str, np.ndarray] = {}

    def _add(p: str, fx: float, fy: float):
        if p not in contrib:
            contrib[p] = np.array([0.0, 0.0], dtype=float)
        contrib[p][0] += float(fx)
        contrib[p][1] += float(fy)

    for a, b, FkN in zip(tr["_A"], tr["_B"], tr["_Ftramo_kN"].astype(float).tolist()):
        Fvec = float(FkN) * u_w
        # ✅ mitad a cada extremo, MISMA dirección
        _add(a, 0.5 * Fvec[0], 0.5 * Fvec[1])
        _add(b, 0.5 * Fvec[0], 0.5 * Fvec[1])

    out = res.copy()
    Fx_col, Fy_col, H_col = [], [], []
    for p in out["Punto"].astype(str).tolist():
        v = contrib.get(p, np.array([0.0, 0.0], dtype=float))
        fx, fy = float(v[0]), float(v[1])
        Fx_col.append(fx)
        Fy_col.append(fy)
        H_col.append(float((fx*fx + fy*fy) ** 0.5))

    out["Fx (kN)"] = Fx_col
    out["Fy (kN)"] = Fy_col
    out["H (kN)"] = H_col

    cols = []
    for c in ["Punto", "Poste", "Espacio Retenida", "Deflexión (°)", "Estructura", "Retenidas",
              "Fx (kN)", "Fy (kN)", "H (kN)"]:
        if c in out.columns:
            cols.append(c)
    return out[cols] if cols else out


    def _add(p: str, fx: float, fy: float):
        if p not in contrib:
            contrib[p] = np.array([0.0, 0.0], dtype=float)
        contrib[p][0] += float(fx)
        contrib[p][1] += float(fy)

    for a, b, fx, fy in zip(tr["_A"], tr["_B"], tr["_Fx_AB"], tr["_Fy_AB"]):
        _add(a, fx, fy)     # nodo A
        _add(b, -fx, -fy)   # nodo B

    # Construir salida por punto
    out = res.copy()
    Fx_col, Fy_col, H_col = [], [], []
    for p in out["Punto"].astype(str).tolist():
        v = contrib.get(p, np.array([0.0, 0.0], dtype=float))
        fx, fy = float(v[0]), float(v[1])
        Fx_col.append(fx)
        Fy_col.append(fy)
        H_col.append(float((fx*fx + fy*fy) ** 0.5))

    out["Fx (kN)"] = Fx_col
    out["Fy (kN)"] = Fy_col
    out["H (kN)"] = H_col

    # Orden sugerido (si existen)
    cols = []
    for c in ["Punto", "Poste", "Espacio Retenida", "Deflexión (°)", "Estructura", "Retenidas", "Fx (kN)", "Fy (kN)", "H (kN)"]:
        if c in out.columns:
            cols.append(c)
    return out[cols] if cols else out
