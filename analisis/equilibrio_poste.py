# analisis/equilibrio_poste.py
# -*- coding: utf-8 -*-
"""
ORDEN LÓGICO: 09 – EQUILIBRIO POSTE–RETENIDA

Este módulo:
- Distribuye la fuerza horizontal entre poste y retenida
- Calcula la fuerza residual que queda en el poste
- Recalcula el momento real del poste

NO decide si va retenida o no.
NO verifica capacidades normativas.
"""

from __future__ import annotations
import math
import pandas as pd


# =============================================================================
# Funciones base
# =============================================================================

def componente_horizontal_retenida_kN(T_ret_kN: float, ang_retenida_deg: float) -> float:
    """
    Componente horizontal aportada por la retenida.
    """
    phi = math.radians(float(ang_retenida_deg))
    return float(T_ret_kN * math.cos(phi))


def fuerza_residual_poste_kN(H_nodo_kN: float, H_ret_kN: float) -> float:
    """
    Fuerza horizontal que queda en el poste.
    """
    H_poste = float(H_nodo_kN - H_ret_kN)
    return max(H_poste, 0.0)


def momento_poste_kNm(H_poste_kN: float, h_amarre_m: float) -> float:
    """
    Momento solicitante real en el poste.
    """
    return float(H_poste_kN * h_amarre_m)


# =============================================================================
# Función principal por DataFrame
# =============================================================================

def equilibrar_poste_retenida(
    df: pd.DataFrame,
    *,
    col_H_nodo: str = "H_nodo (kN)",
    col_T_ret: str = "T_retenida (kN)",
    col_h_amarre: str = "h_amarre (m)",
    col_ang_ret: str = "Ángulo retenida (°)",
    col_flag_retenida: str | None = None,
) -> pd.DataFrame:
    """
    Calcula el equilibrio poste–retenida por nodo.

    Parámetros:
    - df: DataFrame con fuerzas y (si aplica) retenidas
    - col_H_nodo: fuerza horizontal total en nodo
    - col_T_ret: tensión en retenida
    - col_h_amarre: altura de amarre
    - col_ang_ret: ángulo de la retenida
    - col_flag_retenida: columna opcional SI/NO para existencia de retenida

    Retorna:
    - DataFrame con H_poste y M_poste reales
    """

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    for c in [col_H_nodo, col_h_amarre]:
        if c not in out.columns:
            raise ValueError(f"Falta columna requerida: '{c}'.")

    H_poste_list = []
    M_poste_list = []
    H_ret_list = []

    for i, row in out.iterrows():
        H_nodo = float(row[col_H_nodo])
        h = float(row[col_h_amarre])

        tiene_retenida = True
        if col_flag_retenida and col_flag_retenida in out.columns:
            tiene_retenida = str(row[col_flag_retenida]).strip().upper() == "SI"

        if tiene_retenida and col_T_ret in out.columns and col_ang_ret in out.columns:
            T_ret = float(row[col_T_ret])
            ang = float(row[col_ang_ret])
            H_ret = componente_horizontal_retenida_kN(T_ret, ang)
        else:
            H_ret = 0.0

        H_poste = fuerza_residual_poste_kN(H_nodo, H_ret)
        M_poste = momento_poste_kNm(H_poste, h)

        H_ret_list.append(H_ret)
        H_poste_list.append(H_poste)
        M_poste_list.append(M_poste)

    out["H_retenida (kN)"] = H_ret_list
    out["H_poste (kN)"] = H_poste_list
    out["M_poste_real (kN·m)"] = M_poste_list

    return out
