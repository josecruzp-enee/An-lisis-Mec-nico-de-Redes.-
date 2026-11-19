"""Ruta histórica conservada. Implementación única: entradas.catalogos."""
from entradas.catalogos import *  # noqa: F401,F403
import importlib as _importlib
_implementacion = _importlib.import_module("entradas.catalogos")


def __getattr__(nombre):
    return getattr(_implementacion, nombre)
