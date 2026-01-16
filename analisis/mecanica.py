# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from typing import Dict

from .catalogos import (
    CONDUCTORES_ACSR,
    RETENIDAS_RECOMENDADAS,
    POSTES,
    G_KGF_TO_KN,
    FRACCION_TRABAJO_DEFAULT,
    ANG_RETENIDA_DEFAULT_DEG,
)

def tension_trabajo_kN(calibre: str, fraccion: float = FRACCION_TRABAJO_DEFAULT) -> float:
    dat = CONDUCTORES_ACSR[calibre]
    TR_kN = dat["TR_kgf"] * G_KGF_TO_KN
    return float(TR_kN * fraccion)

def demanda_horizontal_kN(tipo_estructura: str, T_kN: float, n_fases: int, angulo_deg: float) -> float:
    t = tipo_estructura.strip().lower()
    if t in ("remate", "inicio", "fin"):
        return float(n_fases * T_kN)
    if t == "paso":
        return 0.0
    if t in ("ángulo", "angulo", "giro"):
        return float(n_fases * 2.0 * T_kN * math.sin(math.radians(angulo_deg) / 2.0))
    if t == "doble remate":
        return float(n_fases * 2.0 * T_kN)
    raise ValueError(f"Tipo de estructura desconocido: {tipo_estructura}")

def tension_retenida_kN(H_kN: float, ang_ret_deg: float = ANG_RETENIDA_DEFAULT_DEG) -> float:
    if H_kN <= 0:
        return 0.0
    return float(H_kN / math.cos(math.radians(ang_ret_deg)))

def capacidad_poste_kN(tipo_poste: str) -> float:
    return float(POSTES[tipo_poste]["H_max_kN"])

def cable_retenida_recomendado(calibre: str) -> str:
    return RETENIDAS_RECOMENDADAS.get(calibre, "N/D")

