"""Ruta histórica de compatibilidad. Implementación única: entradas.datos_proyecto."""
from entradas.datos_proyecto import *  # noqa: F401,F403
from importlib import import_module as _import_module
_impl = _import_module("entradas.datos_proyecto")


def __getattr__(nombre):
    return getattr(_impl, nombre)
