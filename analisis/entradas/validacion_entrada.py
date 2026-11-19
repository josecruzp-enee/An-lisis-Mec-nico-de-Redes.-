"""Ruta histórica conservada. Implementación única: entradas.validacion_entrada."""
from entradas.validacion_entrada import *  # noqa: F401,F403
import importlib as _importlib
_implementacion = _importlib.import_module("entradas.validacion_entrada")


def __getattr__(nombre):
    return getattr(_implementacion, nombre)
