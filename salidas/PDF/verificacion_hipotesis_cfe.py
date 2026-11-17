"""Trazabilidad de las cinco hipótesis CFE contra los resultados por vano.

Usa tensiones máximas YA calculadas. No predice cumplimiento faltante:
si una hipótesis no fue evaluada, emite SIN EVALUAR.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    construir_hipotesis_cfe,
)


def verificar_cinco_hipotesis(tabla, *, ruptura_kN, nombre_conductor,
                              viento_max_kmh, viento_reducido_kmh, hielo_mm):
    inicial, final = construir_hipotesis_cfe(
        float(ruptura_kN),
        viento_max_kmh=float(viento_max_kmh),
        viento_reducido_kmh=float(viento_reducido_kmh),
        hielo_mm=float(hielo_mm),
        nombre_conductor=nombre_conductor,
    )
    condiciones = [("Inicial", inicial[0])] + [("Final", h) for h in final]
    resultados = []
    for idx, (estado, hip) in enumerate(condiciones, 1):
        # Los estados térmicos y climáticos tienen identificación exacta
        # por temperatura, carga y estado, sin deducirlos de la flecha.
        filas = tabla[tabla["Condición"] == estado]
        m = (
            np.isclose(filas["Temperatura (°C)"].to_numpy(float),hip.temperatura_C)
            & np.isclose(filas["Viento (km/h)"].to_numpy(float),hip.viento_kmh)
            & np.isclose(filas["Hielo (mm)"].to_numpy(float),hip.hielo_mm)
        )
        candidatos = filas.loc[m]
        # Para 0 viento + hielo=0 los estados térmicos son una identidad
        # suficiente. Para viento/hielo exigimos etiqueta de escenario.
        if hip.viento_kmh>0 or hip.hielo_mm>0:
            patron = "reducido" if hip.temperatura_C == -10 else "máximo"
            candidatos = candidatos[
                candidatos["Hipótesis"].astype(str).str.contains(
                    patron,case=False,regex=False,
                )
            ]
        if candidatos.empty:
            tension = None
            utilizacion = None
            veredicto = "SIN EVALUAR"
        else:
            tension = float(candidatos["T máx. (kN)"].max())
            utilizacion = tension/float(hip.limite_tension_kN)
            veredicto = "CUMPLE" if utilizacion<=1.000001 else "NO CUMPLE"
        resultados.append({
            "Código":f"H{idx}",
            "Condición":estado,
            "Hipótesis":hip.nombre,
            "Temperatura (°C)":hip.temperatura_C,
            "Viento (km/h)":hip.viento_kmh,
            "Hielo (mm)":hip.hielo_mm,
            "Límite (kN)":hip.limite_tension_kN,
            "T máxima (kN)":tension,
            "Utilización":utilizacion,
            "Estado":veredicto,
            "Vanos evaluados":len(candidatos),
        })
    return pd.DataFrame(resultados)
