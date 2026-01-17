# analisis/momento_poste.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from .norma_postes import h_amarre_tipica_m


def _h_amarre_por_poste(tipo_poste: str, default_m: float = 7.5) -> float:
    return float(h_amarre_tipica_m(tipo_poste, default_m=default_m))


def calcular_momento_poste(
    df_fuerzas_nodo: pd.DataFrame,
    df_resumen: pd.DataFrame | None = None,
    *,
    col_H: str = "H (kN)",
    col_poste: str = "Poste",
    col_h_amarre: str = "Altura_Amarre_m",   # opcional en Excel (altura respecto al terreno)
    he_offset_m: float = 0.10,               # teoría: +0.10 m desde la punta
    default_h_amarre_m: float = 7.5,
) -> pd.DataFrame:
    """
    Calcula Momento en poste y Fuerza equivalente en punta:

    - h (m): altura de aplicación
        * si df_resumen trae col_h_amarre, se usa esa
        * si no, se toma una altura típica según tipo de poste (catálogo)
    - M (kN·m) = H(kN) * h(m)
    - He (m) = h + 0.10
    - Fp (kN) = M / He

    Devuelve un DataFrame con columnas nuevas:
    - h_amarre (m)
    - M_poste (kN·m)
    - He (m)
    - Fp (kN)
    """
    if df_fuerzas_nodo is None or df_fuerzas_nodo.empty:
        raise ValueError("df_fuerzas_nodo vacío")

    if col_H not in df_fuerzas_nodo.columns:
        raise ValueError(f"df_fuerzas_nodo debe incluir '{col_H}'")

    out = df_fuerzas_nodo.copy()

    # Si df_resumen viene, traemos Poste y/o Altura_Amarre_m por Punto
    if df_resumen is not None and (not df_resumen.empty) and ("Punto" in out.columns) and ("Punto" in df_resumen.columns):
        cols_merge = ["Punto"]
        if col_poste in df_resumen.columns:
            cols_merge.append(col_poste)
        if col_h_amarre in df_resumen.columns:
            cols_merge.append(col_h_amarre)

        aux = df_resumen[cols_merge].copy()
        out = out.merge(aux, on="Punto", how="left", suffixes=("", "_res"))

    # Determinar h por fila
    h_list = []
    for _, r in out.iterrows():
        # 1) Si viene altura explícita en Excel, úsala
        h_val = r.get(col_h_amarre, None)
        if h_val is not None and str(h_val).strip() not in ("", "nan", "None"):
            try:
                h = float(h_val)
                if h > 0:
                    h_list.append(h)
                    continue
            except Exception:
                pass

        # 2) Si no, usar catálogo por poste
        poste = r.get(col_poste, "")
        h_list.append(_h_amarre_por_poste(str(poste), default_m=default_h_amarre_m))

    out["h_amarre (m)"] = [float(x) for x in h_list]

    # Momento y fuerza equivalente
    out["M_poste (kN·m)"] = out[col_H].astype(float) * out["h_amarre (m)"].astype(float)
    out["He (m)"] = out["h_amarre (m)"].astype(float) + float(he_offset_m)

    # Evitar división por cero
    out["Fp (kN)"] = out["M_poste (kN·m)"] / out["He (m)"].replace(0, pd.NA)

    # Redondeo suave para tabla
    for c, nd in [("h_amarre (m)", 2), ("M_poste (kN·m)", 2), ("He (m)", 2), ("Fp (kN)", 3)]:
        if c in out.columns:
            out[c] = out[c].astype(float).round(nd)

    return out
