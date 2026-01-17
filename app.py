# analisis/io_excel.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

def _norm_si_no(v) -> str:
    s = str(v).strip().upper()
    return "SI" if s in ("SI", "S", "TRUE", "1") else "NO"

def leer_puntos_excel(archivo) -> pd.DataFrame:
    # archivo puede ser ruta (CLI) o UploadedFile (Streamlit)
    df = pd.read_excel(archivo)
    df.columns = [str(c).strip() for c in df.columns]

    for c in ["Punto", "X", "Y"]:
        if c not in df.columns:
            raise ValueError(f"Falta columna obligatoria '{c}' en el Excel.")

    df = df.copy()
    df["Punto"] = df["Punto"].astype(str)
    df["X"] = df["X"].astype(float)
    df["Y"] = df["Y"].astype(float)

    if "Poste" not in df.columns:
        df["Poste"] = ""

    if "Espacio Retenida" in df.columns:
        df["Espacio Retenida"] = df["Espacio Retenida"].apply(_norm_si_no)
    elif "Espacio_Retenida" in df.columns:
        df["Espacio_Retenida"] = df["Espacio_Retenida"].apply(_norm_si_no)
        df = df.rename(columns={"Espacio_Retenida": "Espacio Retenida"})
    else:
        df["Espacio Retenida"] = "SI"

    return df

