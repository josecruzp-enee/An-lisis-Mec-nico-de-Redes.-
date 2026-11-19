"""Ruta histórica de compatibilidad. Implementación única: entradas.io_excel."""
from entradas.io_excel import *  # noqa: F401,F403
from importlib import import_module as _import_module
_impl = _import_module("entradas.io_excel")


def __getattr__(nombre):
    return getattr(_impl, nombre)
