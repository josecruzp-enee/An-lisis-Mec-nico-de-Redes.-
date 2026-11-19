"""Ruta histórica de compatibilidad. Implementación única: salidas.reporte_pdf."""
from salidas.reporte_pdf import *  # noqa: F401,F403
from importlib import import_module as _import_module
_impl = _import_module("salidas.reporte_pdf")


def __getattr__(nombre):
    return getattr(_impl, nombre)
