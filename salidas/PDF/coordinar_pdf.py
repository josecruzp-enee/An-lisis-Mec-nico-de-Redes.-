"""Coordinador extensible de PDF para Etapa 1, Etapa 2, etc.

Los generadores reciben RESULTADOS YA CALCULADOS; no ejecutan ingeniería.
Se conserva el registro en un solo lugar y la salida se devuelve en bytes.
Para unir etapas, generar_memoria_pdf(etapas=[1,2], datos_por_etapa=...).
"""
from __future__ import annotations

from io import BytesIO
from typing import Callable

from pypdf import PdfReader, PdfWriter

Generador = Callable[..., bytes]
_GENERADORES: dict[int, Generador] = {}


def registrar_generador(etapa: int, generador: Generador) -> None:
    """Registra etapas sin incorporar su lógica dentro del coordinador."""
    if not isinstance(etapa, int) or etapa < 1:
        raise ValueError("La etapa debe ser un entero positivo")
    if not callable(generador):
        raise TypeError("El generador debe ser invocable")
    _GENERADORES[etapa] = generador


def generar_memoria_pdf(*, etapas: list[int], datos_por_etapa: dict[int, dict]) -> bytes:
    """Genera y combina los PDF de las etapas seleccionadas en su orden.

    datos_por_etapa: {1: {"resultado": ..., "puntos": ...,
                       "proyecto": ..., "propiedades": ...}}.
    No se fabrican resultados ni se omiten etapas que falten.
    """
    if not etapas or len(set(etapas)) != len(etapas):
        raise ValueError("Se requiere una lista no vacía de etapas únicas")
    escritor = PdfWriter()
    for etapa in etapas:
        if etapa not in _GENERADORES:
            raise ValueError(f"No existe generador PDF registrado para la etapa {etapa}")
        if etapa not in datos_por_etapa:
            raise ValueError(f"Faltan datos de la etapa {etapa}")
        contenido = _GENERADORES[etapa](**datos_por_etapa[etapa])
        if not isinstance(contenido, bytes) or not contenido.startswith(b"%PDF"):
            raise ValueError(f"La etapa {etapa} no devolvió un PDF válido")
        lector = PdfReader(BytesIO(contenido))
        if not lector.pages:
            raise ValueError(f"El PDF de la etapa {etapa} está vacío")
        escritor.append_pages_from_reader(lector)
    destino = BytesIO()
    escritor.write(destino)
    return destino.getvalue()


from .generar_pdf_etapa_1 import generar_pdf_etapa_1  # noqa: E402

registrar_generador(1, generar_pdf_etapa_1)
