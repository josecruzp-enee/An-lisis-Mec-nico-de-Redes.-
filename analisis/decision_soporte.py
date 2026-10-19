# analisis/decision_soporte.py
# -*- coding: utf-8 -*-
"""
ORDEN LÓGICO: 11 – DECISIÓN ESTRUCTURAL FINAL

Decide la solución estructural por punto usando:
- H_poste real (post–equilibrio)
- Requerimiento geométrico de retenida
- Cumplimiento de cimentación

Regla: funciones cortas, una responsabilidad por función.
"""

from __future__ import annotations
import pandas as pd
from typing import Dict, Tuple

from .norma_postes import H_max_poste_kN


# =============================================================================
# UTILIDADES ATÓMICAS
# =============================================================================

def _si_no(v) -> str:
    s = str(v).strip().upper()
    return "SI" if s in ("SI", "S", "TRUE", "1") else "NO"


def capacidad_poste_kN(tipo_poste: str) -> float:
    return float(H_max_poste_kN(tipo_poste))


def utilizacion_poste_pct(H_poste_kN: float, Hmax_kN: float) -> float:
    return (100.0 * H_poste_kN / Hmax_kN) if Hmax_kN > 0 else float("nan")


def cumple_poste(H_poste_kN: float, Hmax_kN: float) -> str:
    import math
    if not math.isfinite(H_poste_kN) or not math.isfinite(Hmax_kN) or Hmax_kN <= 0:
        return 'NO VERIFICABLE'
    return 'SI' if H_poste_kN <= Hmax_kN else 'NO'


# =============================================================================
# VALIDACIONES
# =============================================================================

def _validar_df(nombre: str, df: pd.DataFrame, columnas: list[str]) -> None:
    if df is None or df.empty:
        raise ValueError(f"{nombre} vacío o None")
    for c in columnas:
        if c not in df.columns:
            raise ValueError(f"{nombre} debe incluir columna '{c}'")


# =============================================================================
# DECISIÓN POR FILA (LÓGICA PURA)
# =============================================================================

def decidir_fila(r: pd.Series) -> Tuple[str, str]:
    """La ruta heredada carece de verificaciones completas; nunca aprueba por geometría."""
    if r.get('Cumple poste') == 'NO' or r.get('Cumple cimentación') == 'NO':
        return 'NO CUMPLE', 'Una verificación disponible falla; evaluar otra alternativa'
    return 'NO VERIFICABLE', 'Faltan verificaciones de material, anclajes y suelo'


# =============================================================================
# EVALUACIÓN POR FILA (CÁLCULO)
# =============================================================================

def evaluar_poste_fila(r: pd.Series) -> Dict[str, object]:
    """
    Calcula métricas del poste para una fila.
    """
    poste = str(r.get("Poste", "")).strip()
    H_poste = float(r.get("H_poste (kN)", 0.0) or 0.0)

    Hmax = capacidad_poste_kN(poste)
    util = utilizacion_poste_pct(H_poste, Hmax)
    cumple_p = cumple_poste(H_poste, Hmax)

    return {
        "H_max (kN)": round(Hmax, 2),
        "Utilización poste (%)": round(util, 1),
        "Cumple poste": cumple_p,
    }


# =============================================================================
# FUNCIÓN ORQUESTADORA (DATAFRAME)
# =============================================================================

def decidir_soporte(
    df_resumen: pd.DataFrame,
    df_equilibrio: pd.DataFrame,
    df_cimentacion: pd.DataFrame,
) -> pd.DataFrame:
    """
    Decide la solución estructural final por punto.
    Base mecánica: df_equilibrio
    Metadatos: df_resumen
    Veredicto suelo: df_cimentacion
    """

    # ---- Validaciones
    _validar_df("df_equilibrio", df_equilibrio, ["Punto", "H_poste (kN)"])
    _validar_df("df_resumen", df_resumen, ["Punto", "Poste", "Espacio Retenida", "Retenidas"])
    _validar_df("df_cimentacion", df_cimentacion, ["Punto", "Cumple cimentación"])

    if "Punto" not in df_equilibrio.columns and df_equilibrio.index.name == "Punto":
        df_equilibrio = df_equilibrio.reset_index()
    for _df in (df_resumen, df_equilibrio, df_cimentacion):
        if "Punto" in _df.columns:
            _df["Punto"] = _df["Punto"].astype(str).str.strip()
    
    # ---- DF base = mecánica real
    df = df_equilibrio.copy()

    # ---- Enriquecer con geometría / entrada
    df = df.merge(
        df_resumen[["Punto", "Poste", "Espacio Retenida", "Retenidas",
                    "Estructura", "Deflexión (°)"]],
        on="Punto",
        how="left",
    )

    # ---- Enriquecer con cimentación
    df = df.merge(
        df_cimentacion[["Punto", "Cumple cimentación"]],
        on="Punto",
        how="left",
    )

    # ---- Métricas del poste
    metricas = df.apply(evaluar_poste_fila, axis=1, result_type="expand")
    df = pd.concat([df, metricas], axis=1)

    # ---- Decisión estructural
    decisiones = df.apply(decidir_fila, axis=1, result_type="expand")
    decisiones.columns = ["Solución", "Motivo"]
    df = pd.concat([df, decisiones], axis=1)

    # ---- Orden de salida
    columnas_salida = [
        "Punto",
        "Estructura",
        "Deflexión (°)",
        "Retenidas",
        "Espacio Retenida",
        "Poste",
        "H_poste (kN)",
        "H_max (kN)",
        "Utilización poste (%)",
        "Cumple poste",
        "Cumple cimentación",
        "Solución",
        "Motivo",
    ]

    return df[[c for c in columnas_salida if c in df.columns]]

