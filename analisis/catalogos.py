# analisis/catalogos.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict

CONDUCTORES_ACSR: Dict[str, Dict[str, float]] = {
    "2 ACSR":      {"peso_kg_m": 0.1359, "TR_kgf": 1265},
    "1/0 ACSR":    {"peso_kg_m": 0.2159, "TR_kgf": 1940},
    "2/0 ACSR":    {"peso_kg_m": 0.2721, "TR_kgf": 2425},
    "3/0 ACSR":    {"peso_kg_m": 0.3429, "TR_kgf": 3030},
    "4/0 ACSR":    {"peso_kg_m": 0.4325, "TR_kgf": 3820},
    "266.8 MCM":   {"peso_kg_m": 0.5454, "TR_kgf": 5100},
    "336.4 MCM":   {"peso_kg_m": 0.6874, "TR_kgf": 6375},
    "477 MCM":     {"peso_kg_m": 0.9141, "TR_kgf": 7802},
    "795 MCM":     {"peso_kg_m": 1.5220, "TR_kgf": 12950},
}

RETENIDAS_RECOMENDADAS: Dict[str, str] = {
    "2 ACSR": "1/4\" EHS",
    "1/0 ACSR": "1/4\" EHS",
    "2/0 ACSR": "1/4\" EHS",
    "3/0 ACSR": "5/16\" EHS",
    "4/0 ACSR": "5/16\" EHS",
    "266.8 MCM": "5/16\" EHS",
    "336.4 MCM": "3/8\" EHS",
    "477 MCM": "3/8\" EHS",
    "795 MCM": "3/8\" EHS",
}

POSTES: Dict[str, Dict[str, float]] = {
    "PC-30": {"H_max_kN": 12.0, "altura_m": 9.0},
    "PC-35": {"H_max_kN": 14.0, "altura_m": 10.5},
    "PC-40": {"H_max_kN": 16.0, "altura_m": 12.0},
    "PM-40": {"H_max_kN": 16.0, "altura_m": 12.0},
    "PT-35": {"H_max_kN": 10.0, "altura_m": 10.5},
    "PT-40": {"H_max_kN": 12.0, "altura_m": 12.0},
}

CAP_RETENIDA_ULT_LBF: Dict[str, float] = {
    '1/4" EHS':  7000,
    '5/16" EHS': 12000,
    '3/8" EHS':  17000,
}
