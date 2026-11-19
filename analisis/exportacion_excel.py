"""Ruta histórica conservada. Implementación única: salidas.exportacion_excel."""
from salidas.exportacion_excel import *  # noqa: F401,F403
import importlib as _importlib
_implementacion = _importlib.import_module("salidas.exportacion_excel")


def __getattr__(nombre):
    return getattr(_implementacion, nombre)
