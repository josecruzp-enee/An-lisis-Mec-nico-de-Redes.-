"""Exportación de resultados del Módulo 2 sin recalcular esfuerzos.

No convierte comprobaciones preliminares en aprobaciones de diseño.
"""
from __future__ import annotations


def tablas_resultado(resultado: dict) -> dict:
    """Expone las tablas ya calculadas, sin mutar datos ni aplicar criterios nuevos."""
    if not isinstance(resultado, dict):
        raise TypeError("Se esperaba un diccionario del motor de estructuras")
    return {nombre: valor for nombre, valor in resultado.items()
            if hasattr(valor, "to_csv")}
