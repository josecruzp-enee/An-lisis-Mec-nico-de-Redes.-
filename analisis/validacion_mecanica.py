"""Validación común: SI en m, kN, kN/m, °C; nunca sustituir faltantes por cero."""
from __future__ import annotations
import numpy as np


def finito(valor: float, nombre: str, minimo=None, estricto=False) -> float:
    """Convierte un escalar finito y comprueba su dominio físico."""
    valor = float(valor)
    if not np.isfinite(valor):
        raise ValueError(f"{nombre}: se requiere un número finito")
    if minimo is not None and (valor < minimo or (estricto and valor == minimo)):
        raise ValueError(f"{nombre}: debe ser {'>' if estricto else '>='} {minimo}")
    return valor


def vector3(valor, nombre: str) -> np.ndarray:
    """Valida coordenadas o fuerzas cartesianas; Z es positivo hacia arriba."""
    vector = np.asarray(valor, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError(f"{nombre}: se requieren tres componentes finitas")
    return vector


def validar_puntos(df) -> None:
    """Impide etiquetas ambiguas, vanos nulos y coordenadas no finitas."""
    if len(df) < 2:
        raise ValueError("Se necesitan al menos dos puntos")
    nombres = df['Punto'].astype(str).str.strip()
    if nombres.isin(['', 'nan', 'None']).any() or nombres.duplicated().any():
        raise ValueError("Los puntos deben tener identificadores únicos y no vacíos")
    xy = df[['X', 'Y']].to_numpy(dtype=float)
    if not np.isfinite(xy).all() or (np.linalg.norm(np.diff(xy, axis=0), axis=1) == 0).any():
        raise ValueError("Coordenadas inválidas o vano horizontal nulo")
