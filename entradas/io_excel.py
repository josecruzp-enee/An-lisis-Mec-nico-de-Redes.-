
# analisis/io_excel.py
# -*- coding: utf-8 -*-
"""
Importación y normalización de puntos desde Excel.

Responsabilidades:
- Leer el archivo.
- Normalizar encabezados.
- Validar y convertir los datos.
- Conservar información opcional.
- Entregar un DataFrame compatible con el motor.

No realiza cálculos mecánicos ni selecciona estructuras.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from .validacion_entrada import validar_puntos_excel


# ============================================================
# 1. NORMALIZACIÓN DE ENCABEZADOS
# ============================================================

def _norm_col(columna: str) -> str:
    """Normaliza espacios, tildes y mayúsculas."""
    texto = unicodedata.normalize("NFKD", str(columna))
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    texto = texto.upper().strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


MAPA_COLUMNAS = {
    # Identificación
    "PUNTO": "Punto",
    "FIJACION": "Fijacion",

    # Coordenadas UTM
    "X": "X",
    "X (M)": "X",
    "X(M)": "X",
    "ESTE": "X",

    "Y": "Y",
    "Y (M)": "Y",
    "Y(M)": "Y",
    "NORTE": "Y",

    # Elevación del terreno
    "ALTITUD": "Altitud",
    "ALTITUD (M)": "Altitud",
    "ALTITUD(M)": "Altitud",
    "ALTITUD (MSNM)": "Altitud",
    "ELEVACION": "Altitud",
    "ELEVACION (M)": "Altitud",

    # Tipo de poste
    "POSTE": "Poste",
    "TIPO POSTE": "Poste",
    "TIPO DE POSTE": "Poste",

    # Disponibilidad de retenida
    "ESPACIO RETENIDA": "Espacio Retenida",
    "ESPACIO PARA RETENIDA": "Espacio Retenida",
    "ESPACIO_RETENIDA": "Espacio Retenida",

    # Geometría del poste
    "ALTURA_POSTE_M": "Altura_Poste_m",
    "ALTURA POSTE (M)": "Altura_Poste_m",
    "LONGITUD POSTE (M)": "Altura_Poste_m",

    "EMPOTRAMIENTO_M": "Empotramiento_m",
    "EMPOTRAMIENTO (M)": "Empotramiento_m",

    "ALTURA_AMARRE_M": "Altura_Amarre_m",
    "ALTURA AMARRE (M)": "Altura_Amarre_m",
}


# ============================================================
# 2. DISPONIBILIDAD DE RETENIDAS
# ============================================================

def _norm_si_no(valor) -> str:
    """Devuelve SI, NO o NO VERIFICABLE."""
    if pd.isna(valor) or str(valor).strip() == "":
        return "NO VERIFICABLE"

    texto = _norm_col(str(valor))

    if texto in ("SI", "S", "TRUE", "1", "1.0"):
        return "SI"

    if texto in ("NO", "N", "FALSE", "0", "0.0"):
        return "NO"

    if texto in (
        "NO VERIFICABLE",
        "DESCONOCIDO",
        "PENDIENTE",
    ):
        return "NO VERIFICABLE"

    raise ValueError(
        f"Espacio Retenida: valor no reconocido '{valor}'."
    )


# ============================================================
# 3. VALIDACIONES NUMÉRICAS
# ============================================================

def _convertir_numerica(
    df: pd.DataFrame,
    columna: str,
    *,
    obligatorio: bool = False,
    positivo: bool = False,
) -> None:
    """Convierte valores y reporta la fila Excel inválida."""
    if columna not in df.columns:
        return

    original = df[columna]
    valores = pd.to_numeric(original, errors="coerce")

    if obligatorio:
        invalidos = valores.isna() | ~np.isfinite(valores)
    else:
        hay_dato = original.notna() & (
            original.astype(str).str.strip() != ""
        )
        invalidos = hay_dato & (
            valores.isna() | ~np.isfinite(valores)
        )

    if positivo:
        invalidos = invalidos | (
            valores.notna() & (valores <= 0)
        )

    if invalidos.any():
        filas = (np.flatnonzero(invalidos.to_numpy()) + 2).tolist()
        raise ValueError(
            f"Columna '{columna}': datos inválidos "
            f"en las filas de Excel {filas}."
        )

    df[columna] = valores.astype(float)


# ============================================================
# 4. LECTURA PRINCIPAL
# ============================================================

def leer_puntos_excel(archivo) -> pd.DataFrame:
    """
    Columnas obligatorias:
        Punto, X, Y

    Columnas opcionales:
        Altitud
        Poste
        Espacio Retenida
        Altura_Poste_m
        Empotramiento_m
        Altura_Amarre_m

    Coordenadas y longitudes expresadas en metros.
    """
    df = archivo.copy() if isinstance(archivo, pd.DataFrame) else pd.read_excel(archivo)

    if df.empty:
        raise ValueError("El archivo Excel está vacío.")

    # Normalizar y renombrar columnas
    df.columns = [_norm_col(c) for c in df.columns]

    df = df.rename(
        columns={
            c: MAPA_COLUMNAS[c]
            for c in df.columns
            if c in MAPA_COLUMNAS
        }
    )

    if df.columns.duplicated().any():
        duplicadas = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(
            f"Encabezados duplicados: {duplicadas}"
        )

    # Columnas obligatorias
    for columna in ("Punto", "X", "Y"):
        if columna not in df.columns:
            raise ValueError(
                f"Falta columna obligatoria '{columna}'."
            )

    df = df.copy()

    # Identificadores
    puntos = df["Punto"].astype("string").str.strip()

    invalidos = puntos.isna() | puntos.eq("").fillna(True)

    if invalidos.any():
        filas = (np.flatnonzero(invalidos.to_numpy()) + 2).tolist()
        raise ValueError(
            f"Identificadores de punto vacíos en filas {filas}."
        )

    df["Punto"] = puntos.astype(str)

    # Coordenadas obligatorias
    for columna in ("X", "Y"):
        _convertir_numerica(
            df,
            columna,
            obligatorio=True,
        )

    # Valores opcionales
    for columna in (
        "Altitud",
        "Altura_Poste_m",
        "Empotramiento_m",
        "Altura_Amarre_m",
    ):
        _convertir_numerica(
            df,
            columna,
            positivo=columna != "Altitud",
        )

    # Tipo de poste
    if "Poste" not in df.columns:
        df["Poste"] = ""
    else:
        df["Poste"] = df["Poste"].fillna("").astype(str).str.strip()

    # Disponibilidad para retenidas
    if "Espacio Retenida" not in df.columns:
        df["Espacio Retenida"] = "NO VERIFICABLE"
    else:
        valores = []
        for indice, valor in enumerate(df["Espacio Retenida"]):
            try:
                valores.append(_norm_si_no(valor))
            except ValueError as error:
                raise ValueError(
                    f"Fila {indice + 2}: {error}"
                ) from error

        df["Espacio Retenida"] = valores

    # Validación geométrica final
    validar_puntos_excel(df)

    return df
