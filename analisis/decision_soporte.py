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
    return (100.0 * H_poste_kN / Hmax_kN) if Hmax_kN > 0 else float("inf")


def cumple_poste(H_poste_kN: float, Hmax_kN: float) -> str:
    return "SI" if Hmax_kN > 0 and H_poste_kN <= Hmax_kN else "NO"


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
    """Clasificación preliminar: nunca aprueba una alternativa sin verificar."""
    espacio = _si_no(r["Espacio Retenida"])
    ret_req = int(r["Retenidas"])
    cumple_cim = _si_no(r.get("Cumple cimentación", "NO"))
    cumple_p = _si_no(r.get("Cumple poste", "NO"))
    cumple_ret = _si_no(r.get("Cumple retenida", "NO"))

    if ret_req > 0:
        if espacio == "NO":
            return "REQUIERE DISEÑO", "No hay espacio: verificar solución autosoportada"
        if cumple_ret != "SI":
            return "REQUIERE DISEÑO", "Retenida sin capacidad comprobada o insuficiente"
        if cumple_p != "SI" or cumple_cim != "SI":
            return "REQUIERE DISEÑO", "Verificar poste y cimentación con retenida"
        return "RETENIDA", "Verificación preliminar; comprobar anclaje y suelo"

    if cumple_p == "SI" and cumple_cim == "SI":
        return "POSTE SOLO", "Verificación preliminar; revisar todas las hipótesis de carga"
    return "REQUIERE DISEÑO", "No se acredita capacidad del poste o cimentación"


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
    df_resumen = df_resumen.copy()\n    df_equilibrio = df_equilibrio.copy()\n    df_cimentacion = df_cimentacion.copy()\n    for _df in (df_resumen, df_equilibrio, df_cimentacion):\n        _df["Punto"] = _df["Punto"].astype(str).str.strip()
    
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

