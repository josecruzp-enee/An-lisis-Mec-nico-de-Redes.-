"""Acceso del Módulo 1 al catálogo único de conductores ACSR.

Los datos están en comun/ y son compartidos por los módulos sin
importarse entre sí. Este archivo mantiene la API existente.
"""
from comun.catalogo_acsr_viakon import *  # noqa: F401,F403
from comun import catalogo_acsr_viakon as _catalogo


def __getattr__(nombre):
    return getattr(_catalogo, nombre)
