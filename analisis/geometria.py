# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

Point = Tuple[float, float]

def dist_utm(p1: Point, p2: Point) -> float:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return float((dx*dx + dy*dy) ** 0.5)

def azimut_deg(p1: Point, p2: Point) -> float:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    return float(np.degrees(np.arctan2(dy, dx)) % 360)

def deflexion_deg(p1: Point, p2: Point, p3: Point) -> float:
    a1 = azimut_deg(p2, p1)
    a2 = azimut_deg(p2, p3)
    diff = abs(a2 - a1)
    return float(360 - diff if diff > 180 else diff)

def bisectriz_deg(az1: float, az2: float) -> float:
    delta = (az2 - az1 + 360) % 360
    if delta > 180:
        return float((az2 + (360 - delta) / 2) % 360)
    return float((az1 + delta / 2) % 360)

def opuesta_deg(d: float) -> float:
    return float((d + 180) % 360)

def distancias_tramos(puntos: List[Point], etiquetas: List[str] | None = None):
    tramos = []
    acum = 0.0
    for i in range(len(puntos) - 1):
        d = dist_utm(puntos[i], puntos[i + 1])
        acum += d
        nombre = f"{etiquetas[i]} → {etiquetas[i+1]}" if etiquetas else f"P{i+1} → P{i+2}"
        tramos.append((nombre, d, acum))
    return tramos, float(acum)

def clasificar_por_angulo(ang: float) -> tuple[str, int]:
    # tu criterio
    if ang > 60:
        return "Giro", 2
    if ang > 30:
        return "Doble remate", 3
    if ang > 5:
        return "Ángulo", 1
    return "Paso", 0

