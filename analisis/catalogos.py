# -*- coding: utf-8 -*-
G_KGF_TO_KN = 9.81 / 1000  # kgf -> kN

# ACSR: peso kg/m y TR en kgf (tabla base)
CONDUCTORES_ACSR = {
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

RETENIDAS_RECOMENDADAS = {
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

# Placeholder: capacidad horizontal admisible del poste (kN)
POSTES = {
    "PC-30": {"H_max_kN": 12.0},

