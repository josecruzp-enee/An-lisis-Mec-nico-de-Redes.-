# analisis/cimentacion.py
# -*- coding: utf-8 -*-
"""
ORDEN LÓGICO: 10 – CIMENTACIÓN / EMPOTRAMIENTO DE POSTES

Este módulo calcula:
- Cortante en la base del poste
- Momento en la base
- Reacción del suelo equivalente
- Verificación simplificada con suelo admisible

NO decide tipo de estructura.
NO modifica fuerzas del sistema.
"""

from __future__ import annotations
from typing import Dict
import pandas as pd


# =============================================================================
# Funciones base
# =============================================================================

def cortante_base_kN(H_poste_kN: float) -> float:
    """
    Cortante horizontal en la base del poste.
    """
    return float(H_poste_kN)


def momento_base_kNm(H_poste_kN: float, h_amarre_m: float) -> float:
    """
    Momento solicitante en la base del poste.
    """
    return float(H_poste_kN * h_amarre_m)


def reaccion_suelo_equivalente_kN(M_base_kNm: float, profundidad_empotramiento_m: float) -> float:
    """
    Reacción horizontal equivalente del suelo.
    Modelo simplificado: R ≈ M / d
    """
    if profundidad_empotramiento_m <= 0:
        raise ValueError("La profundidad de empotramiento debe ser > 0.")
    return float(M_base_kNm / profundidad_empotramiento_m)


# =============================================================================
# Función principal por DataFrame
# =============================================================================

def evaluar_cimentacion(
    df: pd.DataFrame,
    *,
    col_H_poste: str = "H_poste (kN)",
    col_h_amarre: str = "h_amarre (m)",
    profundidad_empotramiento_m: float = 2.0,
    capacidad_suelo_kN: float = 50.0,
) -> pd.DataFrame:
    """
    Evalúa la demanda en la cimentación del poste.

    Parámetros:
    - df: DataFrame con resultados mecánicos
    - col_H_poste: fuerza horizontal real en poste
    - col_h_amarre: altura de aplicación de la fuerza
    - profundidad_empotramiento_m: profundidad efectiva del empotramiento
    - capacidad_suelo_kN: reacción horizontal admisible del suelo

    Retorna:
    - DataFrame con verificación de cimentación
    """

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    for c in [col_H_poste, col_h_amarre]:
        if c not in out.columns:
            raise ValueError(f"Falta columna requerida: '{c}'.")

    V_base_list = []
    M_base_list = []
    R_suelo_list = []
    cumple_list = []

    for _, row in out.iterrows():
        H_poste = float(row[col_H_poste])
        h = float(row[col_h_amarre])

        Vb = cortante_base_kN(H_poste)
        Mb = momento_base_kNm(H_poste, h)
        R = reaccion_suelo_equivalente_kN(Mb, profundidad_empotramiento_m)

        V_base_list.append(Vb)
        M_base_list.append(Mb)
        R_suelo_list.append(R)
        cumple_list.append("SI" if R <= capacidad_suelo_kN else "NO")

    out["V_base (kN)"] = V_base_list
    out["M_base (kN·m)"] = M_base_list
    out["R_suelo_eq (kN)"] = R_suelo_list
    out["Capacidad_suelo (kN)"] = float(capacidad_suelo_kN)
    out["Profundidad_empotramiento (m)"] = float(profundidad_empotramiento_m)
    out["Cumple cimentación"] = cumple_list

    return out
