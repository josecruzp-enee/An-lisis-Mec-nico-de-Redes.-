# -*- coding: utf-8 -*-
from __future__ import annotations

def kg_m_to_kN_m(kg_m: float) -> float:
    # (kg/m)*g -> N/m -> kN/m
    return float(kg_m * 9.81 / 1000.0)

