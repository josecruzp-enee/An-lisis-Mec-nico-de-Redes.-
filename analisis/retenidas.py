# analisis/retenidas.py
# -*- coding: utf-8 -*-
"""
ORDEN LÓGICO: 08 – CÁLCULO DE RETENIDAS

Este módulo calcula:
- Tensión en retenida
- Componente vertical
- Capacidad admisible
- Verificación de cumplimiento

NO decide si va retenida o no. (eso lo hace decision_soporte)
Puede calcular "solo donde aplica" si se le pasa un filtro.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math
import pandas as pd

from .mecanica import capacidad_retenida_admisible_kN


# =============================================================================
# Parámetros
# =============================================================================

@dataclass(frozen=True)
class ParamsRetenida:
    cable_retenida: str
    FS_retenida: float = 2.0
    ang_retenida_deg: float = 45.0  # respecto a horizontal


# =============================================================================
# Funciones base (cortas)
# =============================================================================

def _cos_safe(phi_rad: float) -> float:
    c = math.cos(phi_rad)
    if c <= 1e-9:
        raise ValueError("Ángulo de retenida inválido (cos(phi) <= 0).")
    return c


def tension_retenida_kN(H_kN: float, ang_retenida_deg: float) -> float:
    """
    T = H / cos(phi)
    """
    H = float(H_kN or 0.0)
    phi = math.radians(float(ang_retenida_deg))
    return float(H / _cos_safe(phi))


def componente_vertical_retenida_kN(T_kN: float, ang_retenida_deg: float) -> float:
    """
    V = T * sin(phi)
    """
    T = float(T_kN or 0.0)
    phi = math.radians(float(ang_retenida_deg))
    return float(T * math.sin(phi))


def componente_horizontal_retenida_kN(T_kN: float, ang_retenida_deg: float) -> float:
    """
    H_ret = T * cos(phi)
    """
    T = float(T_kN or 0.0)
    phi = math.radians(float(ang_retenida_deg))
    return float(T * math.cos(phi))


def capacidad_admisible_retenida_kN(params: ParamsRetenida) -> float:
    return float(
        capacidad_retenida_admisible_kN(
            cable_ret=params.cable_retenida,
            FS_ret=params.FS_retenida,
        )
    )


# =============================================================================
# Función principal (reporte por DataFrame)
# =============================================================================

def calcular_retenidas(
    df: pd.DataFrame,
    *,
    col_punto: str = "Punto",
    col_H: str = "H (kN)",                 # ✅ default alineado con tu app
    aplicar_si_col: Optional[str] = None,  # ej: "Solución" o "Retenidas_aplican"
    aplicar_si_val: Optional[str] = "RETENIDA",
    params: ParamsRetenida,
) -> pd.DataFrame:
    """
    Calcula demanda mecánica de retenida por punto.

    Parámetros:
    - df: DataFrame con al menos Punto y H
    - col_H: columna de demanda horizontal en el poste (kN)
    - aplicar_si_col/aplicar_si_val: si se define, solo calcula donde (df[col]==val)
      Ej: aplicar_si_col="Solución", aplicar_si_val="RETENIDA"
    - params: parámetros del sistema de retenida

    Retorna:
    - DataFrame con:
        H_sin_retenida (kN)
        T_retenida (kN)
        H_aporte_ret (kN)
        V_retenida (kN)
        H_poste_con_ret (kN)  (modelo idealizado)
        T_admisible_retenida (kN)
        Utilización retenida (%)
        Cumple retenida
    """

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    for c in (col_punto, col_H):
        if c not in out.columns:
            raise ValueError(f"Falta columna requerida: '{c}'.")

    # ¿Dónde aplica?
    if aplicar_si_col is None:
        aplica = pd.Series([True] * len(out), index=out.index)
    else:
        if aplicar_si_col not in out.columns:
            raise ValueError(f"aplicar_si_col='{aplicar_si_col}' no existe en df.")
        if aplicar_si_val is None:
            # interpreta como booleano
            aplica = out[aplicar_si_col].astype(bool)
        else:
            aplica = out[aplicar_si_col].astype(str).str.upper().eq(str(aplicar_si_val).upper())

    # Capacidad admisible (constante para el caso)
    T_adm = capacidad_admisible_retenida_kN(params)

    # Inicializar columnas
    out["H_sin_retenida (kN)"] = out[col_H].astype(float).fillna(0.0)

    T_list, Hret_list, V_list, Hcon_list = [], [], [], []
    util_list, cumple_list = [], []

    for idx, r in out.iterrows():
        H = float(r["H_sin_retenida (kN)"] or 0.0)

        if bool(aplica.loc[idx]) and H > 0:
            T = tension_retenida_kN(H, params.ang_retenida_deg)
            Hret = componente_horizontal_retenida_kN(T, params.ang_retenida_deg)  # ≈ H
            V = componente_vertical_retenida_kN(T, params.ang_retenida_deg)
            Hcon = max(H - Hret, 0.0)  # idealizado (equilibrio perfecto)
            util = 100.0 * (T / T_adm) if T_adm > 0 else 0.0
            cumple = "SI" if (T <= T_adm) else "NO"
        else:
            T, Hret, V, Hcon = 0.0, 0.0, 0.0, H
            util, cumple = 0.0, "-"

        T_list.append(T)
        Hret_list.append(Hret)
        V_list.append(V)
        Hcon_list.append(Hcon)
        util_list.append(util)
        cumple_list.append(cumple)

    out["T_retenida (kN)"] = [round(x, 4) for x in T_list]
    out["H_aporte_ret (kN)"] = [round(x, 4) for x in Hret_list]
    out["V_retenida (kN)"] = [round(x, 4) for x in V_list]
    out["H_poste_con_ret (kN)"] = [round(x, 4) for x in Hcon_list]

    out["T_admisible_retenida (kN)"] = round(float(T_adm), 4)
    out["Utilización retenida (%)"] = [round(x, 1) for x in util_list]
    out["Cumple retenida"] = cumple_list

    out["Ángulo retenida (°)"] = float(params.ang_retenida_deg)
    out["FS retenida"] = float(params.FS_retenida)
    out["Cable retenida"] = str(params.cable_retenida)

    # Orden amigable
    cols_order = [c for c in [
        col_punto,
        "H_sin_retenida (kN)",
        "T_retenida (kN)",
        "H_aporte_ret (kN)",
        "V_retenida (kN)",
        "H_poste_con_ret (kN)",
        "T_admisible_retenida (kN)",
        "Utilización retenida (%)",
        "Cumple retenida",
        "Ángulo retenida (°)",
        "FS retenida",
        "Cable retenida",
    ] if c in out.columns]

    return out[cols_order] if cols_order else out
