"""Ruta de compatibilidad; implementación única en analisis.calculos.cimentacion.

No añadir algoritmos aquí: mantener el código de cálculo en su origen.
"""
from analisis.calculos.cimentacion import *  # noqa: F401,F403
from analisis.calculos import cimentacion as _implementacion


def __getattr__(nombre):
    """Conservar acceso a símbolos privados usados por consumidores antiguos."""
    return getattr(_implementacion, nombre)
