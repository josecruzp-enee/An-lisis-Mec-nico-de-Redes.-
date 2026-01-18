# analisis/momento_poste.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional
import pandas as pd

from .norma_postes import h_amarre_tipica_m


def calcular_momento_poste(
    df_fuerzas_nodo: pd.DataFrame,
    df_resumen: Optional[pd.DataFrame] = None,
    *,
    col_punto: str = "Punto",
    col_H: str = "H (kN)",
    col_poste: str = "Poste",
    col_altura_amarre_excel: str = "Altura_Amarre_m",  # altura SOBRE TERRENO (m)
    default_h_amarre_m: float = 7.5,
    he_offset_m: float = 0.10,
    incluir_fp: bool = False,
) -> pd.DataFrame:
    """
    Momento en la base del poste (modelo simple):

        M_base (kN·m) = H (kN) * h_amarre (m)

    Donde h_amarre se toma así:
      1) Si el Excel trae 'Altura_Amarre_m' => se asume altura SOBRE TERRENO (m).
      2) Si no, se usa h_amarre_tipica_m(Poste) según norma/catálogo.

    Parámetros:
    - incluir_fp: si True agrega He y Fp como métricas auxiliares:
        He = h_amarre + he_offset_m
        Fp = M_base / He

    Devuelve:
    - Punto, Poste, H (kN), h_amarre (m), M_base (kN·m) (+ He, Fp si incluir_fp)
    """

    if df_fuerzas_nodo is None or df_fuerzas_nodo.empty:
        raise ValueError("df_fuerzas_nodo vacío o None")
    if col_punto not in df_fuerzas_nodo.columns:
        raise ValueError(f"df_fuerzas_nodo debe incluir '{col_punto}'")
    if col_H not in df_fuerzas_nodo.columns:
        raise ValueError(f"df_fuerzas_nodo debe incluir '{col_H}'")

    out = df_fuerzas_nodo.copy()
    out[col_punto] = out[col_punto].astype(str).str.strip()

    # Traer Poste y/o Altura_Amarre_m desde df_resumen
    if df_resumen is not None and (not df_resumen.empty) and (col_punto in df_resumen.columns):
        aux_cols = [col_punto]
        if col_poste in df_resumen.columns:
            aux_cols.append(col_poste)
        if col_altura_amarre_excel in df_resumen.columns:
            aux_cols.append(col_altura_amarre_excel)

        aux = df_resumen[aux_cols].copy()
        aux[col_punto] = aux[col_punto].astype(str).str.strip()

        out = out.merge(aux, on=col_punto, how="left")

    # Normalizar H
    out[col_H] = pd.to_numeric(out[col_H], errors="coerce").fillna(0.0)

    # 1) h desde excel (altura sobre terreno)
    h_excel = None
    if col_altura_amarre_excel in out.columns:
        h_excel = pd.to_numeric(out[col_altura_amarre_excel], errors="coerce")

    # 2) h típica por poste
    def _h_tipica(tipo: object) -> float:
        t = "" if tipo is None else str(tipo).strip()
        h = float(h_amarre_tipica_m(t, default_m=default_h_amarre_m))
        return h if h > 0 else float(default_h_amarre_m)

    if col_poste in out.columns:
        h_tip = out[col_poste].apply(_h_tipica)
    else:
        h_tip = pd.Series([float(default_h_amarre_m)] * len(out), index=out.index)

    # Selección final: usar excel si es válida (>0), si no usar típica
    if h_excel is not None:
        out["h_amarre (m)"] = h_excel.where(h_excel > 0, h_tip)
    else:
        out["h_amarre (m)"] = h_tip

    out["M_base (kN·m)"] = out[col_H] * out["h_amarre (m)"]

    if incluir_fp:
        out["He (m)"] = out["h_amarre (m)"] + float(he_offset_m)
        out["Fp (kN)"] = out["M_base (kN·m)"] / out["He (m)"].replace(0, pd.NA)

    # Redondeos
    out["h_amarre (m)"] = out["h_amarre (m)"].astype(float).round(2)
    out["M_base (kN·m)"] = out["M_base (kN·m)"].astype(float).round(2)
    if incluir_fp:
        out["He (m)"] = out["He (m)"].astype(float).round(2)
        out["Fp (kN)"] = pd.to_numeric(out["Fp (kN)"], errors="coerce").round(3)

    # Orden limpio
    base_cols = [col_punto]
    if col_poste in out.columns:
        base_cols.append(col_poste)
    base_cols += [col_H, "h_amarre (m)", "M_base (kN·m)"]
    if incluir_fp:
        base_cols += ["He (m)", "Fp (kN)"]

    # Filtrar solo columnas existentes
    base_cols = [c for c in base_cols if c in out.columns]
    return out[base_cols]
