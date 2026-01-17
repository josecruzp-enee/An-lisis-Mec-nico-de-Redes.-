# analisis/exportacion_excel.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from io import BytesIO
from typing import Dict

import pandas as pd


def _nombre_hoja_seguro(nombre: str) -> str:
    """
    Excel limita nombre de hoja a 31 chars y no permite: : \ / ? * [ ]
    """
    s = str(nombre).strip()
    for ch in [":", "\\", "/", "?", "*", "[", "]"]:
        s = s.replace(ch, "-")
    s = s[:31] if len(s) > 31 else s
    return s or "Hoja"


def generar_excel_resultados(
    *,
    df_entrada: pd.DataFrame,
    tablas: Dict[str, pd.DataFrame],
) -> bytes:
    """
    Devuelve bytes .xlsx con múltiples hojas.
    - df_entrada: hoja "Entrada"
    - tablas: dict {nombre_hoja: dataframe}
      Ej: {"Tramos": df_tramos, "Cargas_Tramo": df_cargas, ...}
    """
    bio = BytesIO()

    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        # Entrada
        df_entrada.to_excel(writer, sheet_name="Entrada", index=False)

        # Otras tablas
        usados = set(["Entrada"])
        for nombre, df in (tablas or {}).items():
            if df is None:
                continue
            if not isinstance(df, pd.DataFrame):
                continue

            sheet = _nombre_hoja_seguro(nombre)

            # evitar duplicados
            base = sheet
            k = 2
            while sheet in usados:
                suf = f"_{k}"
                sheet = _nombre_hoja_seguro(base[: (31 - len(suf))] + suf)
                k += 1

            usados.add(sheet)
            df.to_excel(writer, sheet_name=sheet, index=False)

    bio.seek(0)
    return bio.getvalue()
