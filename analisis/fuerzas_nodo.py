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
    usar_col_w: str = "w_resultante (kN/m)",
) -> pd.DataFrame:
    """
    Calcula fuerzas equivalentes en nodos por suma vectorial (modelo completo).

    Entradas:
    - df_tramos: debe incluir columnas:
        Tramo, Distancia (m), Azimut (°), y usar_col_w (kN/m)
      (Tramo tipo "P1 → P2" o "P1 -> P2" o "P1→P2")
    - df_resumen: tabla por punto (incluye remates) con columna "Punto"
      (si ya tienes Poste/Espacio Retenida/Deflexión/Estructura/Retenidas, mejor)

    Salida:
    - DataFrame por punto con:
        Fx (kN), Fy (kN), H (kN), H_izq (kN), H_der (kN)
      donde:
        H_izq = contribución del tramo anterior (hacia el nodo)
        H_der = contribución del tramo siguiente (hacia el nodo)
    """
    if df_tramos is None or df_tramos.empty:
        return pd.DataFrame()

    req = ["Tramo", "Distancia (m)", "Azimut (°)", usar_col_w]
    for c in req:
        if c not in df_tramos.columns:
            raise ValueError(f"df_tramos debe incluir columna '{c}'.")

    if df_resumen is None or df_resumen.empty or "Punto" not in df_resumen.columns:
        raise ValueError("df_resumen debe incluir columna 'Punto'.")

    # Copias
    tr = df_tramos.copy()
    res = df_resumen.copy()

    # Parseo de tramo -> (A, B)
    # Acepta flechas variadas: "→", "->", "—>", etc.
    def _split_tramo(s: str):
        s = str(s).strip()
        for sep in ["→", "->", "—>", "=>"]:
            if sep in s:
                a, b = s.split(sep, 1)
                return a.strip(), b.strip()
        # fallback: si viene "P1 P2"
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

    # Carga total por tramo (kN): W = w * L
    tr["_WkN"] = tr[usar_col_w].astype(float) * tr["Distancia (m)"].astype(float)

    # Vector unitario del tramo (A->B)
    # y lo proyectamos a un vector fuerza equivalente.
    Fx_AB, Fy_AB = [], []
    for az, W in zip(tr["Azimut (°)"].astype(float).tolist(), tr["_WkN"].astype(float).tolist()):
        u = _unit_vector_from_azimut_deg(az)
        F = float(W) * u
        Fx_AB.append(float(F[0]))
        Fy_AB.append(float(F[1]))

    tr["_Fx_AB"] = Fx_AB
    tr["_Fy_AB"] = Fy_AB

    # Reglas de contribución al nodo:
    # - En nodo A (inicio del tramo): la fuerza "tira" en dirección A->B  => +F_AB
    # - En nodo B (fin del tramo): la fuerza "tira" en dirección B->A     => -F_AB
    # (esto es consistente para sumar en nodos y ver resultante)
    contrib: Dict[str, np.ndarray] = {}

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
