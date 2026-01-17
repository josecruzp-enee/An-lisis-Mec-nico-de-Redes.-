# analisis/unidades.py
# -*- coding: utf-8 -*-
from __future__ import annotations

G = 9.81  # m/s^2

def kgf_to_kN(kgf: float) -> float:
    return float(kgf) * 9.81 / 1000.0

def kg_m_to_kN_m(kg_m: float) -> float:
    # (kg/m)*g = N/m -> kN/m
    return float(kg_m) * 9.81 / 1000.0

def lbf_to_kN(lbf: float) -> float:
    return float(lbf) / 224.809

def kN_to_lbf(kN: float) -> float:
    return float(kN) * 224.809
