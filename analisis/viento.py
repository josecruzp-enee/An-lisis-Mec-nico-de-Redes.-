# analisis/viento.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import math

# Aire estándar a nivel del mar (ajustable luego)
RHO_AIRE = 1.225  # kg/m³

def viento_kN_m(
    velocidad_ms: float,
    diametro_m: float,
    Cd: float = 1.2,
    rho: float = RHO_AIRE,
) -> float:
    """
    Carga de viento por metro de conductor (kN/m).

    Fórmula:
        w = 0.5 * rho * Cd * D * V^2   [N/m] -> kN/m

    Parámetros:
    - velocidad_ms: velocidad del viento (m/s)
    - diametro_m: diámetro del conductor (m)
    - Cd: coeficiente aerodinámico (≈1.2 cilindro)
    - rho: densidad del aire (kg/m³)

    Retorna:
    - w_kN_m: carga horizontal por metro (kN/m)
    """
    if velocidad_ms <= 0 or diametro_m <= 0:
        return 0.0

    w_N_m = 0.5 * rho * Cd * diametro_m * velocidad_ms ** 2
    return float(w_N_m / 1000.0)


def proyectar_viento(
    w_kN_m: float,
    azimut_tramo_deg: float,
    azimut_viento_deg: float,
) -> float:
    """
    Proyección efectiva del viento sobre el tramo (kN/m).

    Usa el ángulo relativo entre:
    - dirección del viento
    - dirección del conductor (tramo)

    w_eff = w * |sin(theta)|

    donde theta = az_viento - az_tramo
    """
    theta = math.radians(azimut_viento_deg - azimut_tra_
