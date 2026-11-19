"""Ruta de compatibilidad; implementación única en analisis.calculos.perfil.

No añadir algoritmos aquí: mantener el código de cálculo en su origen.
"""
from analisis.calculos.perfil import *  # noqa: F401,F403
from analisis.calculos import perfil as _implementacion


def __getattr__(nombre):
    """Conservar acceso a símbolos privados usados por consumidores antiguos."""
    return getattr(_implementacion, nombre)
