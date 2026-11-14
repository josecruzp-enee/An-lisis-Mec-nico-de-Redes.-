"""Resumen auditable de calidad numérica de los estados de conductor.

No interpreta convergencia como cumplimiento mecánico. Resume residuales
del BVP por caso, sin combinar esfuerzos máximos de escenarios distintos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


CAMPOS = (
    ("Residual equilibrio (kN)", "kN"),
    ("Residual contorno (m)", "m"),
    ("Residual compatibilidad (m)", "m"),
    ("Error poligonal longitud (m)", "m"),
    ("Residual BVP RMS máximo", "adimensional escalado"),
)


def resumen_calidad_bvp(tabla):
    if not isinstance(tabla,pd.DataFrame) or tabla.empty:
        raise ValueError("No hay vanos para auditar")
    falta=[c for c in ("Vano","Caso")+tuple(k for k,_ in CAMPOS)
           if c not in tabla]
    if falta:
        raise ValueError("Faltan campos de calidad: "+", ".join(falta))
    filas=[]
    for nombre,unidad in CAMPOS:
        valores=tabla[nombre].to_numpy(dtype=float)
        if not np.isfinite(valores).all() or (valores<0).any():
            raise ValueError("Residual inválido: "+nombre)
        indice=int(np.argmax(valores))
        fila=tabla.iloc[indice]
        filas.append({
            "Indicador":nombre,
            "Máximo":float(valores[indice]),
            "Unidad":unidad,
            "Caso crítico del indicador":fila["Caso"],
            "Vano":fila["Vano"],
        })
    return pd.DataFrame(filas)
