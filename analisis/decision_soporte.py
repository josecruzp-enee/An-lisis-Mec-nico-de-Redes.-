# analisis/decision_soporte.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict
import pandas as pd

from .catalogos import POSTES


def _si_no(v) -> str:
    s = str(v).strip().upper()
    return "SI" if s in ("SI", "S", "TRUE", "1") else "NO"


def H_max_poste_kN(tipo_poste: str, default: float = 9999.0) -> float:
    return float(POSTES.get(str(tipo_poste).strip(), {}).get("H_max_kN", default))


def decidir_soporte(
    df_resumen: pd.DataFrame,
    df_fuerzas_nodo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Une resumen + fuerzas y decide solución por poste.

    Reglas (FASE 1 estructural):
    - Si Retenidas > 0:
        - si Espacio Retenida = SI  => RETENIDA
        - si Espacio Retenida = NO  => AUTOSOPORTADO
    - Si Retenidas == 0:
        - si Cumple poste => POSTE SOLO
        - si NO cumple    => AUTOSOPORTADO
    """
    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío")
    if df_fuerzas_nodo is None or df_fuerzas_nodo.empty:
        raise ValueError("df_fuerzas_nodo vacío")
    if "Punto" not in df_resumen.columns or "Punto" not in df_fuerzas_nodo.columns:
        raise ValueError("Ambos DataFrames deben tener columna 'Punto'.")

    df = df_resumen.merge(
        df_fuerzas_nodo[["Punto", "H (kN)", "Fx (kN)", "Fy (kN)"]],
        on="Punto",
        how="left",
    )

    # columnas mínimas esperadas
    for c in ["Poste", "Espacio Retenida", "Retenidas"]:
        if c not in df.columns:
            raise ValueError(f"df_resumen debe incluir columna '{c}'.")

    Hmax_list, util_list, cumple_list = [], [], []
    sol_list, motivo_list = [], []

    for _, r in df.iterrows():
        poste = str(r["Poste"]).strip()
        espacio = _si_no(r["Espacio Retenida"])
        ret = int(r["Retenidas"])
        H = float(r.get("H (kN)", 0.0) or 0.0)

        Hmax = H_max_poste_kN(poste)
        util = (100.0 * H / Hmax) if Hmax > 0 else 0.0
        cumple_poste = "SI" if (H <= Hmax) else "NO"

        # decisión
        if ret > 0:
            if espacio == "SI":
                sol = "RETENIDA"
                motivo = "Estructura requiere retenida"
            else:
                sol = "AUTOSOPORTADO"
                motivo = "Estructura requiere retenida pero no hay espacio"
        else:
            if cumple_poste == "SI":
                sol = "POSTE SOLO"
                motivo = "Paso / sin retenida"
            else:
                sol = "AUTOSOPORTADO"
                motivo = "No cumple poste solo"

        Hmax_list.append(Hmax)
        util_list.append(util)
        cumple_list.append(cumple_poste)
        sol_list.append(sol)
        motivo_list.append(motivo)

    df["H_max (kN)"] = [round(x, 2) for x in Hmax_list]
    df["Utilización poste (%)"] = [round(x, 1) for x in util_list]
    df["Cumple poste"] = cumple_list
    df["Solución"] = sol_list
    df["Motivo"] = motivo_list

    # orden amigable
    cols = [c for c in [
        "Punto", "Estructura", "Deflexión (°)", "Retenidas", "Espacio Retenida",
        "Poste", "H (kN)", "H_max (kN)", "Utilización poste (%)", "Cumple poste",
        "Solución", "Motivo", "Fx (kN)", "Fy (kN)",
    ] if c in df.columns]

    return df[cols]
