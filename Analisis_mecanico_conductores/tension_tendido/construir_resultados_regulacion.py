"""Tablas de tensiones, flechas y tendido de la sección de regulación.

Estas funciones solo transforman soluciones físicas calculadas en filas
de resultados: ninguna selecciona tensiones ni modifica los estados.
Las columnas y las unidades preservan el contrato de Streamlit/CSV.
"""
from __future__ import annotations

import pandas as pd

from Analisis_mecanico_conductores.flechas.calcular_flecha_vertical_de_catenaria import (
    calcular_flecha_vertical_de_catenaria,
)


def crear_fila_hipotesis(caso, H_estado, tensiones, residual_m):
    """Resume una hipótesis: tensiones y límite en kN, residual en m."""
    limite=float(caso["T_limite_kN"])
    return {
        "Hipótesis":str(caso["Hipotesis"]),
        "Temperatura (°C)":float(caso["Temperatura_C"]),
        "Viento (m/s)":float(caso["Viento_ms"]),
        "H estado (kN)":H_estado,
        "T máxima sección (kN)":max(tensiones),
        "Límite (kN)":limite,
        "Relación T/límite":max(tensiones)/limite,
        "Fuente límite":str(caso["Fuente_limite"]),
        "Residual compatibilidad (m)":residual_m,
    }


def crear_filas_flechas(puntos, xyz, luces, caso, H_estado,
                       tensiones, cables, viento_kN_m):
    """Devuelve una fila por vano con flecha vertical en metros."""
    filas=[]
    for i,(c,a,b) in enumerate(zip(cables,xyz[:-1],xyz[1:])):
        filas.append({
            "Hipótesis":str(caso["Hipotesis"]),
            "Vano":str(puntos.iloc[i]["Punto"])+" → "+str(puntos.iloc[i+1]["Punto"]),
            "Luz (m)":float(luces[i]),
            "Flecha vertical (m)":calcular_flecha_vertical_de_catenaria(c,a,b),
            "T máxima vano (kN)":tensiones[i],
            "H estado (kN)":H_estado,
            "Viento transversal (kN/m)":viento_kN_m,
        })
    return filas


def construir_tablas_de_hipotesis(puntos, xyz, luces, hipotesis,
                                 H_referencia_kN, evaluar_estado):
    """Evalúa cada hipótesis climática y retorna dos DataFrames auditables."""
    filas_hipotesis=[]
    filas_flechas=[]
    for _,caso in hipotesis.iterrows():
        H,tensiones,cables,residual,viento=evaluar_estado(
            H_referencia_kN,float(caso["Temperatura_C"]),float(caso["Viento_ms"])
        )
        filas_hipotesis.append(crear_fila_hipotesis(caso,H,tensiones,residual))
        filas_flechas.extend(
            crear_filas_flechas(puntos,xyz,luces,caso,H,tensiones,cables,viento)
        )
    return pd.DataFrame(filas_hipotesis),pd.DataFrame(filas_flechas)


def construir_tabla_de_tendido(puntos, xyz, temperaturas_C,
                              H_referencia_kN, evaluar_estado):
    """Tabla sin viento: H, flecha y tensión de extremos por temperatura."""
    filas=[]
    for temperatura in temperaturas_C:
        H,_,cables,residual,_=evaluar_estado(
            H_referencia_kN,float(temperatura),0.
        )
        for i,(c,a,b) in enumerate(zip(cables,xyz[:-1],xyz[1:])):
            filas.append({
                "Temperatura (°C)":temperatura,
                "Vano":str(puntos.iloc[i]["Punto"])+" → "+str(puntos.iloc[i+1]["Punto"]),
                "H del estado (kN)":H,
                "Flecha vertical (m)":calcular_flecha_vertical_de_catenaria(c,a,b),
                "T extremo A (kN)":float(c.tension(0)),
                "T extremo B (kN)":float(c.tension(c.luz)),
                "Residual compatibilidad (m)":residual,
            })
    return pd.DataFrame(filas)
