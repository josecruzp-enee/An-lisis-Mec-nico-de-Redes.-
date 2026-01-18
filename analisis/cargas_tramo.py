# analisis/cargas_tramo.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List
import pandas as pd
import math
from .viento import viento_kN_m, proyectar_viento
from .mecanica import peso_lineal_kN_m
from .viento import proyectar_viento


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
    Cargas mecánicas por tramo usando modelo aerodinámico físico.

    MODELO TEÓRICO:
    - Peso:
        w_v = (kg/m) · g                  [N/m]
    - Viento (arrastre):
        w_w = 0.5 · rho · Cd · D · v²     [N/m]
    - Proyección:
        w_eff = w_w · |sin(theta)|
    - Resultante:
        w_t = sqrt(w_v² + w_eff²)

    Todas las magnitudes se manejan en kN y kN/m.
    """

    if df_tramos is None or df_tramos.empty:
        return pd.DataFrame()

    out = df_tramos.copy()

    # ------------------------------
    # Validaciones mínimas
    # ------------------------------
    for c in ["Tramo", "Azimut (°)", "Distancia (m)"]:
        if c not in out.columns:
            raise ValueError(f"df_tramos debe incluir columna '{c}'.")

    # ------------------------------
    # 1) Peso lineal total (kN/m)
    # ------------------------------
    # peso_lineal_kN_m ya incluye g
    w_peso = float(peso_lineal_kN_m(calibre)) * int(n_fases)

    # ------------------------------
    # 2) Viento lineal base (kN/m)
    # ------------------------------
    if float(v_viento_ms) < 0:
        raise ValueError("v_viento_ms no puede ser negativo.")
        

    w_viento = viento_kN_m(
        velocidad_ms=float(v_viento_ms),
        diametro_m=float(diametro_conductor_m),
        Cd=float(Cd),
        rho=float(rho),
    )

    # ------------------------------
    # 3) Proyección por tramo
    # ------------------------------
    w_eff_list: List[float] = []
    w_res_list: List[float] = []

    for az_tramo in out["Azimut (°)"].astype(float).tolist():
        w_eff = proyectar_viento(
            w_kN_m=w_viento,
            azimut_tramo_deg=float(az_tramo),
            azimut_viento_deg=float(azimut_viento_deg),
        )
        w_eff_list.append(float(w_eff))
        w_res_list.append(math.sqrt(w_peso ** 2 + w_eff ** 2))

    # ------------------------------
    # 4) Resultados
    # ------------------------------
    out["w_peso (kN/m)"] = w_peso
    out["w_viento (kN/m)"] = w_viento
    out["w_viento_eff (kN/m)"] = w_eff_list
    out["w_resultante (kN/m)"] = w_res_list

    out["W_resultante_tramo (kN)"] = (
        out["w_resultante (kN/m)"].astype(float)
        * out["Distancia (m)"].astype(float)
    )

    # Metadato técnico (útil para reportes)
    out["Modelo viento"] = "Aerodinámico (0.5·ρ·Cd·D·v²)"

    # ------------------------------
    # Orden amigable
    # ------------------------------
    cols_order = [c for c in [
        "Tramo", "ΔX (m)", "ΔY (m)", "Distancia (m)", "Acumulado (m)", "Azimut (°)",
        "w_peso (kN/m)", "w_viento (kN/m)", "w_viento_eff (kN/m)",
        "w_resultante (kN/m)", "W_resultante_tramo (kN)",
        "Modelo viento",
    ] if c in out.columns]

    return out[cols_order] if cols_order else out
