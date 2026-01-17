# analisis/engine_mecanico.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from .catalogos import CONDUCTORES_ACSR
from .mecanica import peso_lineal_kN_m, tension_trabajo_kN, retenida_recomendada

def parametros_conductor(calibre: str, fraccion_trabajo: float) -> pd.DataFrame:
    """
    Devuelve una tabla (DataFrame) con parámetros mecánicos base del conductor,
    lista para mostrar en Streamlit y exportar a Excel/PDF.

    - Peso lineal (kN/m)
    - TR (kgf)
    - TR (kN)
    - Tensión de trabajo (kN)
    - Retenida recomendada
    """
    if calibre not in CONDUCTORES_ACSR:
        raise ValueError(f"Calibre no válido: {calibre}")

    peso_kN_m = peso_lineal_kN_m(calibre)
    twork_kN = tension_trabajo_kN(calibre, fraccion_trabajo)
    ret = retenida_recomendada(calibre)

    tr_kgf = CONDUCTORES_ACSR[calibre]["TR_kgf"]

    # TR kN lo obtenemos "al revés": Twork = TR*k
    # => TR = Twork/k (evita duplicar conversiones aquí)
    tr_kN = twork_kN / float(fraccion_trabajo) if fraccion_trabajo else 0.0

    return pd.DataFrame([{
        "Conductor": calibre,
        "Peso lineal (kN/m)": round(float(peso_kN_m), 6),
        "TR (kgf)": round(float(tr_kgf), 1),
        "TR (kN)": round(float(tr_kN), 3),
        "Fracción trabajo": float(fraccion_trabajo),
        "Tensión trabajo (kN)": round(float(twork_kN), 3),
        "Retenida recomendada": ret,
    }])
