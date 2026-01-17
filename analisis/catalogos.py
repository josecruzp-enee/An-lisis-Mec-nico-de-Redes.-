# analisis/catalogos.py
# -*- coding: utf-8 -*-
"""
CATÁLOGOS (SOLO DATOS, SIN CÁLCULOS)

Este archivo contiene únicamente tablas/catálogos provenientes de normas / especificaciones.
Cualquier conversión de unidades, cálculo de momentos, factores de seguridad, verificación,
etc., debe implementarse en módulos aparte (por ejemplo: analisis/normas.py o analisis/mecanica.py).
"""

from __future__ import annotations
from typing import Dict, List, Any

# ============================================================
# Conductores ACSR (peso y tensión de ruptura)
# ============================================================

CONDUCTORES_ACSR: Dict[str, Dict[str, float]] = {
    "2 ACSR":    {"peso_kg_m": 135.7/1000.0, "TR_kgf": 1292,  "diametro_m": 8.01/1000.0},
    "1/0 ACSR":  {"peso_kg_m": 216.2/1000.0, "TR_kgf": 1986, "diametro_m": 10.11/1000.0},
    "2/0 ACSR":  {"peso_kg_m": 272.0/1000.0, "TR_kgf": 2398, "diametro_m": 11.34/1000.0},
    "3/0 ACSR":  {"peso_kg_m": 344.3/1000.0, "TR_kgf": 2996, "diametro_m": 12.75/1000.0},
    "4/0 ACSR":  {"peso_kg_m": 433.1/1000.0, "TR_kgf": 3776, "diametro_m": 14.31/1000.0},
    "266.8 MCM": {"peso_kg_m": 511.1/1000.0, "TR_kgf": 4330, "diametro_m": 16.07/1000.0},
    "336.4 MCM": {"peso_kg_m": 689.9/1000.0, "TR_kgf": 6423, "diametro_m": 18.29/1000.0},
    "477 MCM":   {"peso_kg_m": 975.8/1000.0, "TR_kgf": 8825, "diametro_m": 21.77/1000.0},
    "795 MCM":   {"peso_kg_m": 1626.0/1000.0, "TR_kgf": 14283, "diametro_m": 28.11/1000.0},
}

# ============================================================
# Retenidas recomendadas por calibre de conductor
# ============================================================

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

# Capacidad última típica de retenidas (EHS) en lbf
CAP_RETENIDA_ULT_LBF: Dict[str, float] = {
    '1/4" EHS':  7000,
    '5/16" EHS': 12000,
    '3/8" EHS':  17000,
}

# ============================================================
# Norma / Especificación: Postes de concreto (TABLA 1)
# (Datos “crudos”: sin conversiones, sin cálculos)
# ============================================================

POSTES_CONCRETO_TABLA_1: List[Dict[str, Any]] = [
    # Columnas:
    # - id: descripción corta
    # - longitud_m
    # - diam_punta_cm (diámetro exterior mínimo en punta)
    # - diam_base_cm  (diámetro exterior mínimo en base)
    # - carga_ruptura_kgf
    # - carga_ruptura_lbf
    # - notas (opcional)
    {"id": "PC-9-450",         "longitud_m": 9.15,  "diam_punta_cm": 13.00, "diam_base_cm": 26.5,  "carga_ruptura_kgf": 450,  "carga_ruptura_lbf":  990, "notas": ""},
    {"id": "PC-10-450",        "longitud_m": 10.67, "diam_punta_cm": 15.00, "diam_base_cm": 30.9,  "carga_ruptura_kgf": 450,  "carga_ruptura_lbf":  990, "notas": ""},
    {"id": "PC-12-750",        "longitud_m": 12.19, "diam_punta_cm": 15.00, "diam_base_cm": 33.0,  "carga_ruptura_kgf": 750,  "carga_ruptura_lbf": 1650, "notas": ""},
    {"id": "PC-14-750",        "longitud_m": 13.71, "diam_punta_cm": 15.00, "diam_base_cm": 36.0,  "carga_ruptura_kgf": 750,  "carga_ruptura_lbf": 1650, "notas": ""},
    {"id": "PC-12-900-AUT",    "longitud_m": 12.19, "diam_punta_cm": 25.40, "diam_base_cm": 43.18, "carga_ruptura_kgf": 900,  "carga_ruptura_lbf": 1980, "notas": "Autosoportado"},
    {"id": "PC-14-900-AUT",    "longitud_m": 13.71, "diam_punta_cm": 25.40, "diam_base_cm": 45.72, "carga_ruptura_kgf": 900,  "carga_ruptura_lbf": 1980, "notas": "Autosoportado"},
    {"id": "PC-15-2000-AUT",   "longitud_m": 15.24, "diam_punta_cm": 25.40, "diam_base_cm": 51.44, "carga_ruptura_kgf": 2000, "carga_ruptura_lbf": 4400, "notas": "Autosoportado"},
    {"id": "PC-18-2000-AUT",   "longitud_m": 18.29, "diam_punta_cm": 25.40, "diam_base_cm": 52.71, "carga_ruptura_kgf": 2000, "carga_ruptura_lbf": 4400, "notas": "Autosoportado"},
]

# Notas de la tabla (también datos):
POSTES_CONCRETO_TABLA_1_NOTAS: List[str] = [
    "La descripción corta: PC-9-450 => PC = Poste Concreto; 9 = altura (m); 450 = carga de ruptura (kgf).",
    "Conicidad: 1.5 cm/m.",
]

# ============================================================
# Norma / Especificación: Apéndice (Esfuerzos en línea de tierra)
# (Clases 1–7: carga horizontal usada para diseñar clases)
# Datos “crudos”: sin conversiones
# ============================================================

POSTES_CLASES_APENDICE: List[Dict[str, Any]] = [
    # Columnas:
    # - clase
    # - carga_horizontal_kN
    # - carga_horizontal_kgf_aprox
    {"clase": 1, "carga_horizontal_kN": 20.0, "carga_horizontal_kgf_aprox": 2040},
    {"clase": 2, "carga_horizontal_kN": 16.5, "carga_horizontal_kgf_aprox": 1680},
    {"clase": 3, "carga_horizontal_kN": 13.3, "carga_horizontal_kgf_aprox": 1360},
    {"clase": 4, "carga_horizontal_kN": 10.7, "carga_horizontal_kgf_aprox": 1090},
    {"clase": 5, "carga_horizontal_kN": 8.4,  "carga_horizontal_kgf_aprox": 860},
    {"clase": 6, "carga_horizontal_kN": 6.7,  "carga_horizontal_kgf_aprox": 680},
    {"clase": 7, "carga_horizontal_kN": 5.3,  "carga_horizontal_kgf_aprox": 540},
]

# Regla normativa asociada al apéndice (dato):
APLICACION_CARGA_DESDE_PUNTA_M: float = 0.30  # 300 mm bajo la cima del poste (altura de referencia)

# Texto explicativo del apéndice (dato):
POSTES_CLASES_APENDICE_NOTAS: List[str] = [
    "Las circunferencias mínimas a 2 m de la base (otra tabla) se calculan para no exceder esfuerzos a nivel de tierra.",
    "Las cargas horizontales para diseñar las 7 clases se aplican a 300 mm de la cima del poste.",
    "Las clases se definen para que postes de diferentes especies tengan aproximadamente la misma capacidad de carga.",
]
