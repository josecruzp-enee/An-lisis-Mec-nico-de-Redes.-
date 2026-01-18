# analisis/io_excel.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def _norm_si_no(v) -> str:
    s = str(v).strip().upper()
    return "SI" if s in ("SI", "S", "TRUE", "1") else "NO"


def _norm_col(c: str) -> str:
    """
    Normaliza nombres de columnas:
    - quita espacios extra
    - pone en MAYÚSCULA
    - estandariza variantes como "X (m)" -> "X (M)"
    """
    return str(c).strip().upper()


# Mapa de columnas aceptadas -> columna interna
MAPA_COLUMNAS = {
    # Punto
    "PUNTO": "Punto",

    # Coordenadas
    "X": "X",
    "X (M)": "X",
    "X(M)": "X",
    "ESTE": "X",

    "Y": "Y",
    "Y (M)": "Y",
    "Y(M)": "Y",
    "NORTE": "Y",

    # Altitud (opcional)
    "ALTITUD (msnm)": "Altitud (m)",
    

    # Poste (opcional)
    "POSTE": "Poste",

    # Espacio para retenida (opcional)
    "ESPACIO RETENIDA": "Espacio Retenida",
    "ESPACIO PARA RETENIDA": "Espacio Retenida",
    "ESPACIO_RETENIDA": "Espacio Retenida",
}


def leer_puntos_excel(archivo) -> pd.DataFrame:
    """
    Lee puntos desde Excel y normaliza columnas a:
      - Punto (obligatoria)
      - X, Y (obligatorias)
      - Altitude (opcional)
      - Poste (opcional; si no viene, se crea vacío)
      - Espacio Retenida (opcional; si no viene, se asume SI)
    """
    df = pd.read_excel(archivo)

    # Normalizar encabezados
    cols_norm = [_norm_col(c) for c in df.columns]
    df.columns = cols_norm

    # Renombrar usando el mapa (solo las que existan)
    rename_dict = {c: MAPA_COLUMNAS[c] for c in df.columns if c in MAPA_COLUMNAS}
    df = df.rename(columns=rename_dict)

    # Validación de obligatorias
    for c in ["Punto", "X", "Y"]:
        if c not in df.columns:
            raise ValueError(
                f"Falta columna obligatoria '{c}' en el Excel. "
                f"Columnas detectadas: {list(df.columns)}"
            )

    df = df.copy()

    # Tipos base
    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["X"] = df["X"].astype(float)
    df["Y"] = df["Y"].astype(float)

    # Altitude opcional
    if "Altitude" in df.columns:
        df["Altitude"] = df["Altitude"].astype(float)

    # Poste opcional
    if "Poste" not in df.columns:
        df["Poste"] = ""
    else:
        df["Poste"] = df["Poste"].astype(str).str.strip()

    # Espacio Retenida opcional (normalizado a SI/NO)
    if "Espacio Retenida" in df.columns:
        df["Espacio Retenida"] = df["Espacio Retenida"].apply(_norm_si_no)
    else:
        df["Espacio Retenida"] = "SI"

    return df
