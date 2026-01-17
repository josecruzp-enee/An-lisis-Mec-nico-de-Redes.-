# analisis/cargas_tramo.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Tuple
import pandas as pd

from .mecanica import peso_lineal_kN_m
from .viento import viento_kN_m, proyectar_viento

def calcular_cargas_por_tramo(
    df_tramos: pd.DataFrame,
    *,
    calibre: str,
    n_fases: int,
    v_viento_ms: float,
    azimut_viento_deg: float,
    diametro_conductor_m: float,
    Cd: float = 1.2,
    rho: float = 1.225,
) -> pd.DataFrame:
    """
    Construye tabla de cargas por tramo:
    - w_peso (kN/m) = peso_lineal_kN_m(calibre) * n_fases
    - w_viento (kN/m) = viento_kN_m(V, D, Cd, rho)
    - w_viento_eff (kN/m) = proyección sobre el tramo según azimut
    - w_resultante (kN/m) = sqrt(w_peso^2 + w_viento_eff^2)

    Requiere que df_tramos tenga columna "Azimut (°)" y "Distancia (m)" (y "Tramo").
    """
    if df_tramos is None or df_tramos.empty:
        return pd.DataFrame()

    out = df_tramos.copy()

    # Validaciones mínimas
    if "Azimut (°)" not in out.columns:
        raise ValueError("df_tramos debe incluir columna 'Azimut (°)'.")
    if "Distancia (m)" not in out.columns:
        raise ValueError("df_tramos debe incluir columna 'Distancia (m)'.")
    if "Tramo" not in out.columns:
        # por si tu calcular_tramos lo nombra distinto
        raise ValueError("df_tramos debe incluir columna 'Tramo'.")

    # Peso lineal por metro (kN/m) total por fases
    w_peso = float(peso_lineal_kN_m(calibre)) * int(n_fases)

    # Viento base (kN/m)
    w_viento = float(viento_kN_m(float(v_viento_ms), float(diametro_conductor_m), Cd=float(Cd), rho=float(rho)))

    # Proyección del viento por tramo
    w_eff_list: List[float] = []
    w_res_list: List[float] = []

    for az_tramo in out["Azimut (°)"].astype(float).tolist():
        w_eff = proyectar_viento(w_viento, float(az_tramo), float(azimut_viento_deg))
        w_eff_list.append(float(w_eff))
        w_res_list.append((w_peso**2 + w_eff**2) ** 0.5)

    out["w_peso (kN/m)"] = w_peso
    out["w_viento (kN/m)"] = w_viento
    out["w_viento_eff (kN/m)"] = w_eff_list
    out["w_resultante (kN/m)"] = w_res_list

    # Carga total por tramo (kN) (por si la quieres usar después)
    out["W_resultante_tramo (kN)"] = out["w_resultante (kN/m)"].astype(float) * out["Distancia (m)"].astype(float)

    # Orden amigable de columnas (si existen)
    cols_order = [c for c in [
        "Tramo", "ΔX (m)", "ΔY (m)", "Distancia (m)", "Acumulado (m)", "Azimut (°)",
        "w_peso (kN/m)", "w_viento (kN/m)", "w_viento_eff (kN/m)", "w_resultante (kN/m)",
        "W_resultante_tramo (kN)",
    ] if c in out.columns]

    return out[cols_order] if cols_order else out
