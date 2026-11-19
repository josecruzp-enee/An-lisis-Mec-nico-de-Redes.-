"""Auditoría de equilibrio y trazabilidad de cargas por vano y apoyo.

Cada registro conserva el CASO, el extremo y el punto. No mezcla máximos
de viento, temperatura o tensión provenientes de estados diferentes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COMPONENTES = ("Fx (kN)", "Fy (kN)", "Fz (kN)",
               "Mx (kN·m)", "My (kN·m)", "Mz (kN·m)")


def auditar_reacciones_por_vano(extremos, nodos, *, tolerancia=1e-9):
    """Comprueba sumas de seis componentes por (Caso,Punto).

    Valida que ningún vano o apoyo haya desaparecido de la agregación.
    La conservación de fuerzas en el propio cable se comprueba en el
    solucionador de catenarias; aquí se comprueba la transmisión al poste.
    """
    if extremos is None or nodos is None or extremos.empty or nodos.empty:
        raise ValueError("No existen extremos y cargas nodales para auditoría")
    if not np.isfinite(float(tolerancia)) or tolerancia <= 0:
        raise ValueError("Tolerancia de auditoría inválida")
    claves=["Caso", "Punto"]
    for tabla in (extremos, nodos):
        faltan=[c for c in claves + list(COMPONENTES) if c not in tabla]
        if faltan:
            raise ValueError("Faltan columnas de cargas: "+", ".join(faltan))
        if not np.isfinite(tabla[list(COMPONENTES)].to_numpy(dtype=float)).all():
            raise ValueError("Cargas no finitas en la auditoría")
    acumuladas=(
        extremos.groupby(claves, as_index=False)[list(COMPONENTES)]
        .sum().set_index(claves)
    )
    valores=nodos.set_index(claves)
    if not valores.index.is_unique:
        raise ValueError("Registro nodal duplicado")
    if set(acumuladas.index)!=set(valores.index):
        raise ValueError("Los extremos y los nodos no tienen los mismos casos/apoyos")
    diferencia=acumuladas.loc[valores.index,list(COMPONENTES)]-valores[list(COMPONENTES)]
    maximo=float(np.abs(diferencia.to_numpy()).max())
    if maximo>tolerancia:
        raise ValueError(f"Cargas de vanos y apoyos no equilibradas: {maximo:g}")
    return {
        "Filas extremos":len(extremos),
        "Filas nodos":len(nodos),
        "Residual máximo carga o momento":maximo,
        "Estado":"AUDITORÍA DE AGREGACIÓN SUPERADA",
    }
