"""Envolventes reproducibles para los estados termo-mecánicos 3D.

Los seis componentes de cada caso se conservan juntos. Una envolvente no
forma vectores ficticios a partir de máximos de diferentes estados.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


_COMPONENTES = (
    ("Fx (kN)", "kN"), ("Fy (kN)", "kN"), ("Fz (kN)", "kN"),
    ("Mx (kN·m)", "kN·m"), ("My (kN·m)", "kN·m"),
    ("Mz (kN·m)", "kN·m"), ("H resultante (kN)", "kN"),
    ("M resultante (kN·m)", "kN·m"),
)


def _asegurar(tabla, columnas):
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        raise ValueError("Tabla de estados vacía")
    faltantes = set(columnas) - set(tabla.columns)
    if faltantes:
        raise ValueError("Faltan columnas: " + ", ".join(sorted(faltantes)))
    if tabla[list(columnas)].select_dtypes(include="number").isna().any().any():
        raise ValueError("Las magnitudes de estado deben ser finitas")


def preparar_acciones(nodos):
    """Añade módulo del momento horizontal sin alterar las acciones originales."""
    _asegurar(nodos, ("Punto", "Caso", "Mx (kN·m)", "My (kN·m)"))
    tabla = nodos.copy()
    tabla["M resultante (kN·m)"] = np.hypot(
        tabla["Mx (kN·m)"].astype(float), tabla["My (kN·m)"].astype(float)
    )
    return tabla


def envolventes_apoyos(nodos):
    """Caso de máximo absoluto de cada componente; conserva signo y estado."""
    tabla = preparar_acciones(nodos)
    _asegurar(tabla, [k for k, unidad in _COMPONENTES])
    resultados = []
    for punto, grupo in tabla.groupby("Punto", sort=False):
        for magnitud, unidad in _COMPONENTES:
            fila = grupo.loc[grupo[magnitud].abs().idxmax()]
            resultados.append({
                "Punto": punto, "Magnitud": magnitud,
                "Valor gobernante": float(fila[magnitud]),
                "Unidad": unidad, "Caso gobernante": fila["Caso"],
                "Viento (m/s)": fila["Viento (m/s)"],
                "Azimut viento (°)": fila["Azimut viento (°)"],
                "Temperatura (°C)": fila["Temperatura (°C)"],
                "H inicial (kN)": fila["H inicial (kN)"],
                "Estado": "SOLICITACIÓN, NO VERIFICABLE",
            })
    return pd.DataFrame(resultados)


def envolventes_vanos(vanos):
    """Tensión máxima de extremos y tensión horizontal de cada vano."""
    _asegurar(vanos, ("Vano", "Caso", "T extremo A (kN)",
                      "T extremo B (kN)", "H resuelta (kN)"))
    tabla = vanos.copy()
    tabla["T mayor extremo (kN)"] = tabla[
        ["T extremo A (kN)", "T extremo B (kN)"]
    ].max(axis=1)
    resultados = []
    for nombre, grupo in tabla.groupby("Vano", sort=False):
        for magnitud in ("T mayor extremo (kN)", "H resuelta (kN)"):
            fila = grupo.loc[grupo[magnitud].idxmax()]
            resultados.append({
                "Vano": nombre, "Magnitud": magnitud,
                "Valor gobernante": float(fila[magnitud]),
                "Unidad": "kN", "Caso gobernante": fila["Caso"],
                "Viento (m/s)": fila["Viento (m/s)"],
                "Azimut viento (°)": fila["Azimut viento (°)"],
                "Temperatura (°C)": fila["Temperatura (°C)"],
                "H inicial (kN)": fila["H inicial (kN)"],
                "Estado": "SOLICITACIÓN, NO VERIFICABLE",
            })
    return pd.DataFrame(resultados)


def mayores_por_apoyo(nodos):
    """Tabla ejecutiva: demanda máxima de fuerza/momento y caso correspondiente."""
    env = envolventes_apoyos(nodos)
    filas = []
    for punto, grupo in env.groupby("Punto", sort=False):
        horizontal = grupo.loc[grupo["Magnitud"] == "H resultante (kN)"].iloc[0]
        momento = grupo.loc[grupo["Magnitud"] == "M resultante (kN·m)"].iloc[0]
        filas.append({
            "Punto": punto,
            "H máxima (kN)": horizontal["Valor gobernante"],
            "Caso de H máxima": horizontal["Caso gobernante"],
            "M máxima (kN·m)": momento["Valor gobernante"],
            "Caso de M máxima": momento["Caso gobernante"],
            "Estado": "NO VERIFICABLE",
        })
    return pd.DataFrame(filas)
