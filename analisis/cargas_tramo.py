# analisis/cargas_tramo.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from .mecanica import peso_lineal_kN_m
from .viento import viento_kN_m, proyectar_viento


def calcular_cargas_por_tramo(
    df_tramos: pd.DataFrame,
    calibre: str,
    n_fases: int,
    v_viento_ms: float,
    azimut_viento_deg: float,
    diametro_conductor_m: float,
    Cd: float = 1.2,
    rho: float = 1.225,
) -> pd.DataFrame:
    """
    Genera una tabla de cargas por tramo (kN/m) y cargas totales por tramo (kN).

    Requiere que df_tramos tenga como mínimo:
    - 'Tramo'
    - 'Distancia (m)'
    - 'Azimut (°)'

    Devuelve columnas:
    - Tramo
    - L (m)
    - Azimut tramo (°)
    - w_peso (kN/m) [por conductor]
    - w_peso_total (kN/m) [* n_fases]
    - w_viento (kN/m) [base, sin proyección, por conductor]
    - w_viento_eff (kN/m) [proyectado, por conductor]
    - w_viento_total (kN/m) [proyectado * n_fases]
    - w_resultante (kN/m) [sqrt(peso^2 + viento^2) total]
    - F_peso_tramo (kN) [w_peso_total * L]
    - F_viento_tramo (kN) [w_viento_total * L]
    - F_resultante_tramo (kN) [w_resultante * L]
    """
    req = ["Tramo", "Distancia (m)", "Azimut (°)"]
    for c in req:
        if c not in df_tramos.columns:
            raise ValueError(f"df_tramos debe contener la columna '{c}'.")

    # Cargas por conductor (kN/m)
    w_peso = float(peso_lineal_kN_m(calibre))
    w_viento_base = float(viento_kN_m(v_viento_ms, diametro_conductor_m, Cd=Cd, rho=rho))

    filas = []
    for _, row in df_tramos.iterrows():
        tramo = str(row["Tramo"])
        L = float(row["Distancia (m)"])
        az_tramo = float(row["Azimut (°)"])

        # Proyección del viento según orientación del tramo
        w_viento_eff = float(proyectar_viento(w_viento_base, az_tramo, float(azimut_viento_deg)))

        # Total por todas las fases (si modelas 1,2,3 conductores)
        w_peso_total = w_peso * int(n_fases)
        w_viento_total = w_viento_eff * int(n_fases)

        # Resultante total (kN/m)
        w_res = (w_peso_total**2 + w_viento_total**2) ** 0.5

        filas.append({
            "Tramo": tramo,
            "L (m)": round(L, 2),
            "Azimut tramo (°)": round(az_tramo, 2),

            "w_peso (kN/m)": round(w_peso, 6),
            "w_peso_total (kN/m)": round(w_peso_total, 6),

            "w_viento (kN/m)": round(w_viento_base, 6),
            "w_viento_eff (kN/m)": round(w_viento_eff, 6),
            "w_viento_total (kN/m)": round(w_viento_total, 6),

            "w_resultante (kN/m)": round(w_res, 6),

            "F_peso_tramo (kN)": round(w_peso_total * L, 3),
            "F_viento_tramo (kN)": round(w_viento_total * L, 3),
            "F_resultante_tramo (kN)": round(w_res * L, 3),
        })

    return pd.DataFrame(filas)
