# analisis/retenidas.py
# -*- coding: utf-8 -*-
"""
ORDEN LÓGICO: 08 – CÁLCULO DE RETENIDAS

Este módulo calcula:
- Tensión en retenida
- Componente vertical
- Capacidad admisible
- Verificación de cumplimiento

NO decide si va retenida o no.
NO redistribuye esfuerzos al poste.
"""

from __future__ import annotations
from typing import Dict
import math
import pandas as pd

from .mecanica import capacidad_retenida_admisible_kN


# =============================================================================
# Funciones base
# =============================================================================

def tension_retenida_kN(H_nodo_kN: float, ang_retenida_deg: float) -> float:
    """
    Calcula la tensión en la retenida.

    T = H / cos(phi)
    """
    phi = math.radians(float(ang_retenida_deg))
    if math.cos(phi) <= 0:
        raise ValueError("Ángulo de retenida inválido (cos(phi) <= 0).")
    return float(H_nodo_kN / math.cos(phi))


def componente_vertical_retenida_kN(T_ret_kN: float, ang_retenida_deg: float) -> float:
    """
    Componente vertical de la retenida.
    """
    phi = math.radians(float(ang_retenida_deg))
    return float(T_ret_kN * math.sin(phi))


# =============================================================================
# Función principal por DataFrame
# =============================================================================

def calcular_retenidas(
    df_fuerzas_nodo: pd.DataFrame,
    *,
    col_H: str = "H_nodo (kN)",
    cable_retenida: str,
    FS_retenida: float = 2.0,
    ang_retenida_deg: float = 45.0,
) -> pd.DataFrame:
    """
    Calcula la demanda mecánica de retenidas por nodo.

    Parámetros:
    - df_fuerzas_nodo: DataFrame con fuerzas ya calculadas
    - col_H: columna con fuerza horizontal en nodo (kN)
    - cable_retenida: tipo de cable (catálogo)
    - FS_retenida: factor de seguridad
    - ang_retenida_deg: ángulo de la retenida respecto a horizontal

    Retorna:
    - DataFrame con cálculos de retenida
    """

    if df_fuerzas_nodo is None or df_fuerzas_nodo.empty:
        return pd.DataFrame()

    out = df_fuerzas_nodo.copy()

    if col_H not in out.columns:
        raise ValueError(f"No se encuentra la columna '{col_H}' en df_fuerzas_nodo.")

    # Capacidad admisible del sistema de retenida
    T_adm = capacidad_retenida_admisible_kN(
        cable_ret=cable_retenida,
        FS_ret=FS_retenida,
    )

    T_list = []
    V_list = []
    cumple_list = []

    for H in out[col_H].astype(float).tolist():
        T = tension_retenida_kN(H, ang_retenida_deg)
        V = componente_vertical_retenida_kN(T, ang_retenida_deg)

        T_list.append(T)
        V_list.append(V)
        cumple_list.append("SI" if T <= T_adm else "NO")

    out["T_retenida (kN)"] = T_list
    out["V_retenida (kN)"] = V_list
    out["T_admisible_retenida (kN)"] = T_adm
    out["Cumple retenida"] = cumple_list
    out["Ángulo retenida (°)"] = float(ang_retenida_deg)
    out["FS retenida"] = float(FS_retenida)
    out["Cable retenida"] = str(cable_retenida)

    return out
