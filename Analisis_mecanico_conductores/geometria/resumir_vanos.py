"""Resumen geométrico de vanos independientes para Excel ordinario de puntos.

Esta función no requiere hojas auxiliares ni valores mecánicos. Una
secuencia de puntos se trata como una sección de tendido propuesta para
el estudio geométrico; no infiere los anclajes reales, ni aprueba
condiciones de tensión o despejes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import validar_puntos


def resumen_geometrico(puntos: pd.DataFrame):
    """Devuelve luces por tramo, azimut y disponibilidad de cotas."""
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
    # La componente Z se obtiene de la cota del terreno + el amarre.
    # Si no están informadas ambas columnas completas, no se inventa
    # desnivel ni se presenta un valor z como medido.
    z_completa=(elevacion=="INFORMADA" and amarres=="INFORMADOS")
    if z_completa:
        z=(puntos["Altitud"].astype(float)+
           puntos["Altura_Amarre_m"].astype(float)).to_numpy()
        desniveles=np.diff(z)
    else:
        desniveles=np.full(len(luces),np.nan)
    tramo=pd.DataFrame({
        "Vano":[f"{nombres[i]} → {nombres[i+1]}" for i in range(len(luces))],
        "Luz horizontal (m)":luces,
        "Desnivel entre amarres (m)":desniveles,
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
        "longitud_total_m":float(luces.sum()),
        "n_vanos":len(luces),
        "cotas":elevacion,
        "amarres":amarres,
        "nivelado_confirmado":bool(z_completa and np.ptp(z)<1e-5),
        "desniveles_conocidos":z_completa,
        "requiere_3d":bool(z_completa and np.any(np.abs(desniveles)>1e-5)),
        "hipotesis_geometrica":(
            "Se calculan vanos independientes; no se infieren remates "
            "intermedios ni se calcula un claro equivalente."
        ),
    }
