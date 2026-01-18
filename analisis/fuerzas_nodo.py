# analisis/fuerzas_nodo.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Tuple, List
import numpy as np
import pandas as pd


# =============================================================================
# Utilidades atómicas
# =============================================================================

def _unit_vector_from_azimut_deg(az_deg: float) -> np.ndarray:
    """Vector unitario en dirección de azimut (0°=E, 90°=N)."""
    th = np.deg2rad(float(az_deg))
    return np.array([np.cos(th), np.sin(th)], dtype=float)


def _split_tramo(tramo: str) -> Tuple[str, str]:
    """Convierte 'P1→P2' (u otros separadores) en ('P1','P2')."""
    s = str(tramo).strip()
    for sep in ("→", "->", "—>", "=>"):
        if sep in s:
            a, b = s.split(sep, 1)
            return a.strip(), b.strip()

    # fallback: intentar separar por espacios / signos
    parts = s.replace("-", " ").replace(">", " ").split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()

    raise ValueError(f"No pude interpretar Tramo='{s}'")


def _validar_entrada(df_tramos: pd.DataFrame, df_resumen: pd.DataFrame, usar_col_w: str) -> None:
    if df_tramos is None or df_tramos.empty:
        raise ValueError("df_tramos vacío o None")
    for c in ("Tramo", "Distancia (m)", usar_col_w):
        if c not in df_tramos.columns:
            raise ValueError(f"df_tramos debe incluir columna '{c}'")

    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío o None")
    if "Punto" not in df_resumen.columns:
        raise ValueError("df_resumen debe incluir columna 'Punto'")


def _extraer_extremos_tramos(df_tramos: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas _A y _B al df de tramos."""
    tr = df_tramos.copy()
    A_list: List[str] = []
    B_list: List[str] = []
    for s in tr["Tramo"].tolist():
        a, b = _split_tramo(s)
        A_list.append(a)
        B_list.append(b)
    tr["_A"] = A_list
    tr["_B"] = B_list
    return tr


def _fuerza_tramo_kN(df_tramos: pd.DataFrame, usar_col_w: str) -> pd.Series:
    """F_total por tramo: F = w_eff(kN/m) * L(m)."""
    return df_tramos[usar_col_w].astype(float) * df_tramos["Distancia (m)"].astype(float)


def _acumular_contribuciones(
    tr: pd.DataFrame,
    F_tramo_kN: pd.Series,
    u_viento: np.ndarray,
) -> Dict[str, np.ndarray]:
    """
    Reparte 50% a cada extremo del tramo.
    Direccion: azimut del viento (u_viento).
    """
    contrib: Dict[str, np.ndarray] = {}

    def _add(p: str, fx: float, fy: float) -> None:
        if p not in contrib:
            contrib[p] = np.array([0.0, 0.0], dtype=float)
        contrib[p][0] += float(fx)
        contrib[p][1] += float(fy)

    for a, b, FkN in zip(tr["_A"], tr["_B"], F_tramo_kN.astype(float).tolist()):
        Fvec = float(FkN) * u_viento
        _add(a, 0.5 * Fvec[0], 0.5 * Fvec[1])
        _add(b, 0.5 * Fvec[0], 0.5 * Fvec[1])

    return contrib


def _armar_salida_por_punto(df_resumen: pd.DataFrame, contrib: Dict[str, np.ndarray]) -> pd.DataFrame:
    """Devuelve SOLO Punto, Fx, Fy, H (contrato limpio)."""
    puntos = df_resumen["Punto"].astype(str).tolist()

    Fx, Fy, H = [], [], []
    for p in puntos:
        v = contrib.get(p, np.array([0.0, 0.0], dtype=float))
        fx, fy = float(v[0]), float(v[1])
        Fx.append(fx)
        Fy.append(fy)
        H.append(float((fx * fx + fy * fy) ** 0.5))

    return pd.DataFrame({
        "Punto": puntos,
        "Fx (kN)": Fx,
        "Fy (kN)": Fy,
        "H (kN)": H,
    })


# =============================================================================
# API pública
# =============================================================================

def calcular_fuerzas_en_nodos(
    df_tramos: pd.DataFrame,
    df_resumen: pd.DataFrame,
    *,
    usar_col_w: str = "w_viento_eff (kN/m)",
    azimut_viento_deg: float = 0.0,
) -> pd.DataFrame:
    """
    Fuerzas en nodos por cargas laterales de viento (planta).

    MODELO:
    - Por tramo: F = w_eff(kN/m) * L(m)
    - Se reparte 50% a nodo A y 50% a nodo B
    - Dirección = azimut del viento (unitario)

    SALIDA (contrato):
    - Punto, Fx (kN), Fy (kN), H (kN)

    Nota: No mezcla Poste/Estructura/Retenidas. Eso se une en engine.py.
    """
    _validar_entrada(df_tramos, df_resumen, usar_col_w)

    tr = _extraer_extremos_tramos(df_tramos)
    F_tramo_kN = _fuerza_tramo_kN(tr, usar_col_w)

    u_viento = _unit_vector_from_azimut_deg(float(azimut_viento_deg))
    contrib = _acumular_contribuciones(tr, F_tramo_kN, u_viento)

    return _armar_salida_por_punto(df_resumen, contrib)
