"""Ruta histórica conservada. Implementación única: entradas.norma_postes."""
from entradas.norma_postes import *  # noqa: F401,F403
import importlib as _importlib
_implementacion = _importlib.import_module("entradas.norma_postes")


def __getattr__(nombre):
    return getattr(_implementacion, nombre)
