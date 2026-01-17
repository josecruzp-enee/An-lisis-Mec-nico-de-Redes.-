# analisis/engine.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from .geometria import calcular_tramos, calcular_deflexiones, clasificar_por_angulo

def ejecutar_geometria(df: pd.DataFrame) -> dict:
    """
    Motor único (sin Streamlit) para:
    - Tramos (distancia, acumulado, azimut)
    - Deflexión por punto interior
    - Clasificación (Paso/Ángulo/Doble remate/Giro) + retenidas
    - Resumen por punto (incluye remates)
    """
    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    df_tramos = calcular_tramos(puntos, etiquetas)
    df_def = calcular_deflexiones(puntos, etiquetas)

    if not df_def.empty:
        estructuras = []
        retenidas = []
        for ang in df_def["Deflexión (°)"].tolist():
            est, ret = clasificar_por_angulo(float(ang))
            estructuras.append(est)
            retenidas.append(ret)
        df_def["Estructura"] = estructuras
        df_def["Retenidas"] = retenidas

    resumen = df[["Punto", "Poste", "Espacio Retenida"]].copy()
    resumen["Deflexión (°)"] = "-"
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = 1

    if not df_def.empty:
        mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
        for i in range(1, len(resumen) - 1):
            p = resumen.loc[i, "Punto"]
            if p in mapa.index:
                resumen.loc[i, "Deflexión (°)"] = float(mapa.loc[p, "Deflexión (°)"])
                resumen.loc[i, "Estructura"] = str(mapa.loc[p, "Estructura"])
                resumen.loc[i, "Retenidas"] = int(mapa.loc[p, "Retenidas"])

    return {
        "tramos": df_tramos,
        "deflexiones": df_def,
        "resumen": resumen,
    }
