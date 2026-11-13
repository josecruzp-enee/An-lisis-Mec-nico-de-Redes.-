# -*- coding: utf-8 -*-
"""
geometria.py
Cálculos geométricos en planta UTM:
- Distancias entre puntos
- Azimut
- Deflexión
- Clasificación de estructura por ángulo

Este módulo NO tiene lógica mecánica ni UI.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List, Tuple

# =========================
# Tipos básicos
# =========================
Point = Tuple[float, float]


# =========================
# Geometría básica
# =========================
def dist_utm(p1: Point, p2: Point) -> float:
    """Distancia euclidiana en planta UTM (m)."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return float(np.hypot(dx, dy))


def azimut_deg(p1: Point, p2: Point) -> float:
    """
    Azimut desde p1 hacia p2 en grados (0–360).
    0° = Este, 90° = Norte.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return float(np.degrees(np.arctan2(dy, dx)) % 360)


def deflexion_deg(p1: Point, p2: Point, p3: Point) -> float:
    """
    Deflexión en el punto p2 entre los tramos p2->p1 y p2->p3 (0–180°).
    """
    az_in = azimut_deg(p2, p1)
    az_out = azimut_deg(p2, p3)
    diff = abs(az_out - az_in)
    return float(360 - diff if diff > 180 else diff)


def bisectriz_deg(az1: float, az2: float) -> float:
    """
    Bisectriz entre dos azimutes (grados).
    """
    delta = (az2 - az1 + 360) % 360
    if delta > 180:
        return float((az2 + (360 - delta) / 2) % 360)
    return float((az1 + delta / 2) % 360)


def opuesta_deg(az: float) -> float:
    """Dirección opuesta (180°)."""
    return float((az + 180) % 360)


# =========================
# Tramos
# =========================
def calcular_tramos(
    puntos: List[Point],
    etiquetas: List[str] | None = None
) -> pd.DataFrame:
    """
    Calcula distancias, acumulado y azimut por tramo.

    Retorna DataFrame con:
    - Tramo
    - ΔX (m)
    - ΔY (m)
    - Distancia (m)
    - Acumulado (m)
    - Azimut (°)
    """
    if len(puntos) < 2:
        raise ValueError("Se requieren al menos 2 puntos para calcular tramos.")

    filas = []
    acumulado = 0.0

    for i in range(len(puntos) - 1):
        p1 = puntos[i]
        p2 = puntos[i + 1]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        d = dist_utm(p1, p2)
        az = azimut_deg(p1, p2)

        acumulado += d

        nombre = (
            f"{etiquetas[i]} → {etiquetas[i+1]}"
            if etiquetas
            else f"P{i+1} → P{i+2}"
        )

        filas.append({
            "Tramo": nombre,
            "ΔX (m)": dx,
            "ΔY (m)": dy,
            "Distancia (m)": d,
            "Acumulado (m)": acumulado,
            "Azimut (°)": az,
        })

    df = pd.DataFrame(filas)

    # Redondeo solo para presentación
    for col in ["ΔX (m)", "ΔY (m)", "Distancia (m)", "Acumulado (m)", "Azimut (°)"]:
        df[col] = df[col].astype(float).round(2)

    return df


# =========================
# Deflexiones por punto
# =========================
def calcular_deflexiones(
    puntos: List[Point],
    etiquetas: List[str]
) -> pd.DataFrame:
    """
    Calcula deflexión por punto interior (P2..P(n-1)).

    Retorna DataFrame con:
    - Punto
    - Deflexión (°)
    """
    if len(puntos) < 3:
        return pd.DataFrame(columns=["Punto", "Deflexión (°)"])

    filas = []
    for i in range(1, len(puntos) - 1):
        ang = deflexion_deg(puntos[i - 1], puntos[i], puntos[i + 1])
        filas.append({
            "Punto": etiquetas[i],
            "Deflexión (°)": round(float(ang), 2),
        })

    return pd.DataFrame(filas)


# =========================
# Clasificación estructural
# =========================
def clasificar_por_angulo(ang: float) -> tuple[str, int]:
    """
    Clasifica estructura según deflexión.

    Retorna:
    - Tipo de estructura
    - Número de retenidas recomendadas
    """
    if ang > 90:
        return "Giro", 2
    if ang > 60:
        return "Giro", 2
    if ang > 30:
        return "Doble remate", 3
    if ang > 5:
        return "Ángulo", 1
    return "Paso", 0
