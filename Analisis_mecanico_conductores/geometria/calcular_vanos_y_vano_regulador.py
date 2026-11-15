"""Geometría convencional de regulación para Excel ordinario de puntos.

Esta función no requiere hojas auxiliares ni valores mecánicos. Una
secuencia de puntos se trata como una sección de tendido propuesta para
el estudio geométrico; no infiere los anclajes reales, ni aprueba
condiciones de tensión o despejes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import vano_regulador
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import validar_puntos


def resumen_geometrico(puntos: pd.DataFrame):
    """Regresa tabla por tramo, luz de regulación y condiciones de altura."""
    validar_puntos(puntos)
    xyz=puntos[["X","Y"]].to_numpy(dtype=float)
    d=np.diff(xyz,axis=0)
    luces=np.linalg.norm(d,axis=1)
    nombres=puntos["Punto"].astype(str).tolist()
    elevacion="NO INFORMADA"
    if "Altitud" in puntos and puntos["Altitud"].notna().any():
        if puntos["Altitud"].isna().any():
            elevacion="INCOMPLETA"
        else:
            elevacion="INFORMADA"
    amarres="NO INFORMADOS"
    if "Altura_Amarre_m" in puntos and puntos["Altura_Amarre_m"].notna().any():
        if puntos["Altura_Amarre_m"].isna().any():
            amarres="INCOMPLETOS"
        else:
            amarres="INFORMADOS"
    tramo=pd.DataFrame({
        "Vano":[f"{nombres[i]} → {nombres[i+1]}" for i in range(len(luces))],
        "Luz horizontal (m)":luces,
        "Azimut matemático (°)":np.mod(np.degrees(np.arctan2(d[:,1],d[:,0])),360),
        "Acumulado (m)":np.cumsum(luces),
    })
    nivelado=True
    if elevacion=="INFORMADA":
        alt=puntos["Altitud"].to_numpy(dtype=float)
        nivelado=nivelado and float(np.ptp(alt))<1e-5
    elif elevacion=="INCOMPLETA":
        nivelado=False
    if amarres=="INFORMADOS":
        am=puntos["Altura_Amarre_m"].to_numpy(dtype=float)
        nivelado=nivelado and float(np.ptp(am))<1e-5
    elif amarres=="INCOMPLETOS":
        nivelado=False
    return {
        "tramos":tramo,
        "vano_regulador_m":vano_regulador(luces),
        "longitud_total_m":float(luces.sum()),
        "n_vanos":len(luces),
        "cotas":elevacion,
        "amarres":amarres,
        "nivelado_confirmado":(elevacion=="INFORMADA" and amarres=="INFORMADOS" and nivelado),
        "hipotesis_geometrica":(
            "Vano regulador aproximado de Checa; supone una misma "
            "sección de tendido. No verifica remates intermedios."
        ),
    }
