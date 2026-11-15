"""Cálculo de flecha vertical para una catenaria con amarres nivelados.

Entrada: solución de catenaria, coordenadas A y B en metros.
Salida: distancia vertical máxima bajo la cota de ambos amarres (m).
No representa libramiento respecto del terreno.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize_scalar


def calcular_flecha_vertical_de_catenaria(cable, inicio_m, fin_m):
    """Busca la mínima elevación de la curva; devuelve flecha vertical (m)."""
    a=np.asarray(inicio_m,dtype=float)
    b=np.asarray(fin_m,dtype=float)
    if np.linalg.norm((b-a)[:2])<=0:
        raise ValueError("Flecha sin luz horizontal")
    if abs(float(b[2]-a[2]))>1e-5:
        raise ValueError("Flecha convencional requiere amarres nivelados")
    elevacion=lambda x:float(cable.puntos(float(x))[2])
    minimo=min(
        elevacion(0.),elevacion(cable.luz),
        float(minimize_scalar(elevacion,bounds=(0.,cable.luz),
                              method="bounded").fun),
    )
    return max(0.,float(a[2])-minimo)
