"""Verificaciones auditables de tres estados; ausencia de datos nunca aprueba."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import math


class Estado(str, Enum):
    """Vocabulario único para interfaz, decisión y exportaciones."""
    CUMPLE = 'CUMPLE'
    NO_CUMPLE = 'NO CUMPLE'
    NO_VERIFICABLE = 'NO VERIFICABLE'


@dataclass(frozen=True)
class Verificacion:
    """Una demanda, una resistencia compatible y la procedencia del criterio."""
    nombre: str
    estado: Estado
    demanda: float | None = None
    capacidad: float | None = None
    utilizacion: float | None = None
    unidad: str = ''
    fuente: str = ''
    motivo: str = ''
    caso: str = ''

    def como_dict(self):
        """Serializa sin perder el motivo de un resultado incompleto."""
        return asdict(self)


def verificar_capacidad(nombre, demanda, capacidad, unidad, fuente='', caso=''):
    """Sólo compara capacidades admisibles/de diseño con fuente y demanda finitas."""
    valido = (demanda is not None and capacidad is not None and bool(fuente.strip()))
    valido = valido and math.isfinite(demanda) and math.isfinite(capacidad)
    if not valido or capacidad <= 0 or demanda < 0:
        return Verificacion(nombre, Estado.NO_VERIFICABLE, unidad=unidad,
                            fuente=fuente, caso=caso, motivo='Falta demanda/capacidad válida o fuente')
    uso = demanda/capacidad
    estado = Estado.CUMPLE if uso <= 1 else Estado.NO_CUMPLE
    return Verificacion(nombre, estado, demanda, capacidad, uso, unidad, fuente, caso=caso)


def estado_conjunto(verificaciones):
    """Una falla conocida gobierna; un conjunto vacío o incompleto no cumple."""
    estados = [v.estado for v in verificaciones]
    if Estado.NO_CUMPLE in estados:
        return Estado.NO_CUMPLE
    if not estados or Estado.NO_VERIFICABLE in estados:
        return Estado.NO_VERIFICABLE
    return Estado.CUMPLE
