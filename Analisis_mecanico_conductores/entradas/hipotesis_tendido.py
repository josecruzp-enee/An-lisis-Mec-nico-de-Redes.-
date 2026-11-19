"""Lectura y validación de hipótesis de tendido desde tablas Excel.

No importa Streamlit ni ejecuta el motor de cálculo.
"""
from __future__ import annotations

import pandas as pd
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_inversa_de_un_vano import HipotesisTendido

COLUMNAS_HIPOTESIS = (
    "Hipotesis", "Temperatura_C", "Viento_ms", "Azimut_deg",
    "T_limite_kN", "Fuente_limite", "Criterio_diseno",
)


def leer_hipotesis_tabla(tabla):
    if not isinstance(tabla,pd.DataFrame) or tabla.empty:
        raise ValueError("Hoja Hipotesis vacía")
    falta=[c for c in COLUMNAS_HIPOTESIS if c not in tabla]
    if falta:
        raise ValueError("Hoja Hipotesis: faltan "+", ".join(falta))
    if tabla[list(COLUMNAS_HIPOTESIS)].isna().any().any():
        raise ValueError("Hoja Hipotesis: campos incompletos")
    return [
        HipotesisTendido(
            nombre=str(r["Hipotesis"]).strip(),
            temperatura_C=float(r["Temperatura_C"]),
            viento_ms=float(r["Viento_ms"]),
            azimut_viento_deg=float(r["Azimut_deg"]),
            tension_limite_kN=float(r["T_limite_kN"]),
            fuente_limite=str(r["Fuente_limite"]).strip(),
            criterio_diseno=str(r["Criterio_diseno"]).strip(),
        ) for _,r in tabla.iterrows()
    ]
