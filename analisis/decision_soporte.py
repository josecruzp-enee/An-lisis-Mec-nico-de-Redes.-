# analisis/decision_soporte.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import pandas as pd

from .norma_postes import H_max_poste_kN
from .unidades import kgf_to_kN  # ya lo tienes


def _si_no(v) -> str:
    s = str(v).strip().upper()
    return "SI" if s in ("SI", "S", "TRUE", "1") else "NO"


def H_max_poste_kN(tipo_poste: str, default: float = 9999.0) -> float:
    return float(POSTES.get(str(tipo_poste).strip(), {}).get("H_max_kN", default))


# ---------- índices normativos ----------
_PC_IDX: Dict[str, Dict[str, Any]] = {str(r["id"]).strip(): r for r in POSTES_CONCRETO_TABLA_1}
_CLASE_IDX: Dict[int, Dict[str, Any]] = {int(r["clase"]): r for r in POSTES_CLASES_APENDICE}


def _momento_ruptura_concreto_kNm(id_poste_norma: str) -> float:
    """Mrupt = Hrupt * href, con Hrupt en kgf (tabla), href = L - 0.30"""
    row = _PC_IDX.get(str(id_poste_norma).strip())
    if not row:
        return 0.0
    L = float(row["longitud_m"])
    href = L - float(APLICACION_CARGA_DESDE_PUNTA_M)
    Hrupt_kN = kgf_to_kN(float(row["carga_ruptura_kgf"]))
    return Hrupt_kN * href


def _momento_ruptura_clase_kNm(clase: int, longitud_m: float) -> float:
    """Mrupt = Hclase * href, con Hclase en kN (tabla), href = L - 0.30"""
    row = _CLASE_IDX.get(int(clase))
    if not row:
        return 0.0
    L = float(longitud_m)
    href = L - float(APLICACION_CARGA_DESDE_PUNTA_M)
    Hrupt_kN = float(row["carga_horizontal_kN"])
    return Hrupt_kN * href


def decidir_soporte(
    df_resumen: pd.DataFrame,
    df_fuerzas_nodo: pd.DataFrame,
    df_momento_poste: Optional[pd.DataFrame] = None,
    *,
    FS_poste: float = 2.0,  # puedes mandarlo desde UI
) -> pd.DataFrame:
    """
    Une resumen + fuerzas y decide solución por poste.

    - Si hay df_momento_poste con 'M_poste (kN·m)', se usa verificación por MOMENTO (normativa).
    - Si no, cae a H_max legacy (como hoy).
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

    # si viene momento_poste, lo incorporamos
    if df_momento_poste is not None and (not df_momento_poste.empty) and ("Punto" in df_momento_poste.columns):
        # esperamos columnas de momento_poste.py
        cols_m = ["Punto"]
        for c in ["h_amarre (m)", "M_poste (kN·m)", "He (m)", "Fp (kN)"]:
            if c in df_momento_poste.columns:
                cols_m.append(c)
        df = df.merge(df_momento_poste[cols_m], on="Punto", how="left")

    for c in ["Poste", "Espacio Retenida", "Retenidas"]:
        if c not in df.columns:
            raise ValueError(f"df_resumen debe incluir columna '{c}'.")

    # columnas opcionales para modo normativo
    # - Poste_Norma: por ejemplo "PC-12-750"
    # - Clase_Poste: 1..7
    # - Longitud_Poste_m: requerido si usas Clase_Poste
    # (si no están, cae a legacy)
    tiene_poste_norma = "Poste_Norma" in df.columns
    tiene_clase = "Clase_Poste" in df.columns

    Hcap_list, util_list, cumple_list = [], [], []
    sol_list, motivo_list = [], []

    fs = float(FS_poste) if float(FS_poste) > 0 else 1.0

    for _, r in df.iterrows():
        poste_legacy = str(r["Poste"]).strip()
        espacio = _si_no(r["Espacio Retenida"])
        ret = int(r["Retenidas"])
        H = float(r.get("H (kN)", 0.0) or 0.0)

        # ---------------------------
        # Capacidad: normativo por momento si podemos
        # ---------------------------
        M_dem = r.get("M_poste (kN·m)", None)
        M_dem_val = None
        try:
            if M_dem is not None and str(M_dem).strip() not in ("", "nan", "None"):
                M_dem_val = float(M_dem)
        except Exception:
            M_dem_val = None

        # intentamos obtener Mrupt normativo
        Mrupt = 0.0
        modo = "LEGACY"

        if M_dem_val is not None:
            # 1) Poste de concreto por tabla (si hay Poste_Norma válido)
            if tiene_poste_norma:
                pn = str(r.get("Poste_Norma", "")).strip()
                if pn in _PC_IDX:
                    Mrupt = _momento_ruptura_concreto_kNm(pn)
                    modo = "NORMATIVO_CONCRETO"

            # 2) Si no, intentamos por clase (si existe)
            if (modo == "LEGACY") and tiene_clase:
                try:
                    clase = int(r.get("Clase_Poste", 0))
                    L = float(r.get("Longitud_Poste_m", 0.0))
                    if clase in _CLASE_IDX and L > 0:
                        Mrupt = _momento_ruptura_clase_kNm(clase, L)
                        modo = "NORMATIVO_CLASE"
                except Exception:
                    pass

        if modo.startswith("NORMATIVO") and Mrupt > 0 and M_dem_val is not None:
            # chequeo por momento
            Madm = Mrupt / fs
            util = (100.0 * M_dem_val / Madm) if Madm > 0 else 0.0
            cumple_poste = "SI" if (M_dem_val <= Madm) else "NO"

            # para mostrar algo equivalente en kN (opcional): Hcap equiv = Madm / h
            h = float(r.get("h_amarre (m)", 0.0) or 0.0)
            Hcap = (Madm / h) if h > 0 else 0.0
            motivo_cap = f"Chequeo por MOMENTO ({modo})"
        else:
            # cae a legacy (como hoy)
            Hcap = H_max_poste_kN(poste_legacy)
            util = (100.0 * H / Hcap) if Hcap > 0 else 0.0
            cumple_poste = "SI" if (H <= Hcap) else "NO"
            motivo_cap = "Chequeo por H_max (LEGACY)"

        # ---------------------------
        # decisión (tu lógica intacta)
        # ---------------------------
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

        Hcap_list.append(Hcap)
        util_list.append(util)
        cumple_list.append(cumple_poste)
        sol_list.append(sol)
        motivo_list.append(f"{motivo} | {motivo_cap}")

    df["H_cap (kN)"] = [round(x, 2) for x in Hcap_list]
    df["Utilización poste (%)"] = [round(x, 1) for x in util_list]
    df["Cumple poste"] = cumple_list
    df["Solución"] = sol_list
    df["Motivo"] = motivo_list

    cols = [c for c in [
        "Punto", "Estructura", "Deflexión (°)", "Retenidas", "Espacio Retenida",
        "Poste",
        "Poste_Norma", "Clase_Poste", "Longitud_Poste_m",
        "H (kN)", "H_cap (kN)", "Utilización poste (%)", "Cumple poste",
        "h_amarre (m)", "M_poste (kN·m)",
        "Solución", "Motivo", "Fx (kN)", "Fy (kN)",
    ] if c in df.columns]

    return df[cols]
