# Catálogo compartido de conductores ACSR
# -*- coding: utf-8 -*-
"""
CATÁLOGOS (SOLO DATOS, SIN CÁLCULOS)

Este archivo contiene únicamente tablas/catálogos provenientes de normas / especificaciones.
Cualquier conversión de unidades, cálculo de momentos, factores de seguridad, verificación,
etc., debe implementarse en módulos aparte (por ejemplo: Analisis_mecanico_estructuras/calculos/mecanica.py).
"""

from __future__ import annotations
from typing import Dict, List, Any

# ============================================================
# Conductores ACSR (peso y tensión de ruptura)
# ============================================================

# Las fichas ACSR tienen una sola fuente nominal en TODO el repositorio.
# Este bloque conserva claves históricas de Fase 1 por compatibilidad.
# En calibres con varias aves, la clave histórica designa explícitamente
# una construcción predeterminada; no afirma equivalencia entre variantes.
from comun.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR

_VIAKON_PARA_CLAVE_HISTORICA = {
    "2 ACSR": "2 ACSR — SPARROW",
    "1/0 ACSR": "1/0 ACSR — RAVEN",
    "2/0 ACSR": "2/0 ACSR — QUAIL",
    "3/0 ACSR": "3/0 ACSR — PIGEON",
    "4/0 ACSR": "4/0 ACSR — PENGUIN",
    "266.8 MCM": "266.8 MCM — OWL",
    "336.4 MCM": "336.4 MCM — LINNET",
    "477 MCM": "477 MCM — HAWK",
    "795 MCM": "795 MCM — DRAKE",
}

CONDUCTORES_ACSR: Dict[str, Dict[str, float]] = {
    historico: dict(CONDUCTORES_VIAKON_ACSR[construccion])
    for historico, construccion in _VIAKON_PARA_CLAVE_HISTORICA.items()
}

