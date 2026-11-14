"""Controles preliminares de tensión de conductores por caso y vano.

Compara tensión máxima calculada con carga NOMINAL DE RUPTURA
documentada para el código de ave seleccionado.

Esto NO calcula admisibilidad de tendido o carga normativa; tales límites
dependen del procedimiento de diseño, la normativa aplicable, condiciones
EDA/EDS, amortiguamiento y parámetros del material real.

Si T>=ruptura el estado es incompatible con integridad física del cable
idealizado. Si T<ruptura, NO hay certificación de seguridad.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from entradas.catalogo_viakon_acsr import ficha_viakon_acsr


def diagnosticar_tensiones(vanos, conductor):
    """Conserva el caso físico completo, sin reconstruir máximos artificiales."""
    if not isinstance(vanos,pd.DataFrame) or vanos.empty:
        raise ValueError("Sin estados de tensión para diagnóstico")
    req=("Vano","Caso","T máxima (kN)")
    falta=[c for c in req if c not in vanos]
    if falta:
        raise ValueError("Faltan campos de tensión: "+", ".join(falta))
    rotura=float(ficha_viakon_acsr(conductor)["carga_rotura_kN"])
    salida=vanos[["Vano","Caso","T máxima (kN)"]].copy()
    valores=pd.to_numeric(salida["T máxima (kN)"],errors="raise")
    if not np.isfinite(valores).all() or (valores<=0).any():
        raise ValueError("Tensiones no finitas o no positivas")
    salida["Conductor"]=conductor
    salida["Carga nominal ruptura (kN)"]=rotura
    salida["Relación T máxima / ruptura"]=valores/rotura
    salida["Estado de ruptura nominal"]=[
        "ALCANZA O SUPERA LA RUPTURA NOMINAL"
        if x>=1 else "BAJO RUPTURA NOMINAL; NO ES CUMPLIMIENTO"
        for x in salida["Relación T máxima / ruptura"]
    ]
    salida["Límite admisible diseño"]="PENDIENTE DE CRITERIO NORMATIVO"
    return salida


def resumen_tensiones(vanos_diagnosticados):
    """Máximo por vano, preservando el caso y el motivo."""
    if vanos_diagnosticados is None or vanos_diagnosticados.empty:
        raise ValueError("Sin diagnóstico de tensiones")
    filas=[]
    for nombre,grupo in vanos_diagnosticados.groupby("Vano",sort=False):
        peor=grupo.loc[grupo["Relación T máxima / ruptura"].idxmax()]
        filas.append({
            "Vano":nombre,
            "Conductor":peor["Conductor"],
            "T máxima (kN)":float(peor["T máxima (kN)"]),
            "Carga nominal ruptura (kN)":float(peor["Carga nominal ruptura (kN)"]),
            "Relación máxima a ruptura":float(peor["Relación T máxima / ruptura"]),
            "Caso crítico":peor["Caso"],
            "Estado":peor["Estado de ruptura nominal"],
        })
    return pd.DataFrame(filas)
