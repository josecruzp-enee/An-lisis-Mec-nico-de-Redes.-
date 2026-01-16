# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Tuple
import pandas as pd

Point = Tuple[float, float]

def leer_puntos_excel(path: str):
    df = pd.read_excel(path)
    req = ["Punto", "X", "Y"]
    for c in req:
        if c not in df.columns:
            raise ValueError(f"Falta columna obligatoria '{c}' en el Excel.")

    df = df.copy()
    df["Punto"] = df["Punto"].astype(str)
    df["X"] = df["X"].astype(float)
    df["Y"] = df["Y"].astype(float)

    puntos: List[Point] = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()
    return df, puntos, etiquetas
