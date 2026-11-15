"""Evaluación conservadora y trazable de límites de tensión de diseño.

Este módulo NO establece porcentajes normativos por defecto. Los límites
de cálculo (T_limite_kN) deben estar documentados para cada clase de
estado, según criterio aprobado y fuente técnica.

La clasificación del caso puede venir del análisis; no se infiere de
velocidad o temperatura mediante umbrales arbitrarios. Sin una clase
definida o sin límite verificable, NO VERIFICABLE.

Conserva cada (Vano, Caso), sin reconstruir tensiones combinando máximos
de condiciones climáticas diferentes.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

COLUMNAS_CRITERIO = (
    "Clase_estado", "T_limite_kN", "Fuente_limite", "Criterio_diseno"
)


def validar_criterios_tension(criterios: pd.DataFrame) -> pd.DataFrame:
    """Comprueba límites reales con fuente y clase inequívoca."""
    if not isinstance(criterios, pd.DataFrame) or criterios.empty:
        raise ValueError("Criterios de tensión ausentes o vacíos")
    faltan=[c for c in COLUMNAS_CRITERIO if c not in criterios.columns]
    if faltan:
        raise ValueError("Faltan columnas de criterios: "+", ".join(faltan))
    datos=criterios.loc[:,COLUMNAS_CRITERIO].copy()
    for c in ("Clase_estado", "Fuente_limite", "Criterio_diseno"):
        if datos[c].isna().any():
            raise ValueError(f"{c}: campo requerido")
        datos[c]=datos[c].astype(str).str.strip()
        if datos[c].isin(("", "nan", "None")).any():
            raise ValueError(f"{c}: campo vacío")
    if datos["Clase_estado"].duplicated().any():
        raise ValueError("Clase_estado duplicada: límite ambiguo")
    try:
        valores=pd.to_numeric(datos["T_limite_kN"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError("T_limite_kN debe ser numérico") from exc
    if not np.isfinite(valores.to_numpy(dtype=float)).all() or (valores<=0).any():
        raise ValueError("T_limite_kN debe ser positivo y finito")
    datos["T_limite_kN"]=valores.astype(float)
    return datos


def evaluar_tensiones_diseno(vanos: pd.DataFrame,
                             clases_por_caso: pd.DataFrame,
                             criterios: pd.DataFrame) -> pd.DataFrame:
    """Compara tensión máxima real del vano con límites documentados.

    clases_por_caso: columnas Caso, Clase_estado.
    Un caso debe corresponder a UNA sola clase; falta de asignación
    produce NO VERIFICABLE y nunca se sustituye por un default.
    """
    if not isinstance(vanos, pd.DataFrame) or vanos.empty:
        raise ValueError("No hay resultados de vanos")
    columnas=("Vano", "Caso", "T máxima (kN)")
    if any(c not in vanos for c in columnas):
        raise ValueError("Faltan columnas de tensión por vano")
    if not isinstance(clases_por_caso,pd.DataFrame):
        raise ValueError("Falta asignación de clases por caso")
    if any(c not in clases_por_caso for c in ("Caso","Clase_estado")):
        raise ValueError("La asignación requiere Caso y Clase_estado")
    if clases_por_caso["Caso"].isna().any() or clases_por_caso["Caso"].duplicated().any():
        raise ValueError("Clases: caso vacío o duplicado")
    lim=validar_criterios_tension(criterios)
    res=vanos.loc[:,columnas].copy()
    if res[["Caso", "Vano"]].isna().any().any() or res.duplicated(["Caso","Vano"]).any():
        raise ValueError("Resultados sin identificación única de vano/caso")
    valores=pd.to_numeric(res["T máxima (kN)"],errors="raise")
    if not np.isfinite(valores.to_numpy(dtype=float)).all() or (valores<=0).any():
        raise ValueError("Tensión no positiva o no finita")
    clases=clases_por_caso[["Caso", "Clase_estado"]].copy()
    res=res.merge(clases,how="left",on="Caso",validate="many_to_one")
    res=res.merge(lim,how="left",on="Clase_estado",validate="many_to_one")
    ratio=res["T máxima (kN)"]/res["T_limite_kN"]
    res["Ratio T / límite diseño"]=ratio
    res["Estado tensión diseño"] = np.where(
        res["T_limite_kN"].isna(),
        "NO VERIFICABLE — SIN CLASE O LÍMITE DOCUMENTADO",
        np.where(
            ratio>1+1e-9,
            "SUPERA LÍMITE DOCUMENTADO",
            "BAJO LÍMITE DOCUMENTADO; OTRAS VERIFICACIONES PENDIENTES",
        ),
    )
    return res


def resumen_tension_diseno(evaluacion: pd.DataFrame) -> pd.DataFrame:
    """Identifica excedencias y ausencias sin esconder casos no verificados."""
    if not isinstance(evaluacion,pd.DataFrame) or evaluacion.empty:
        raise ValueError("No hay evaluación para resumir")
    filas=[]
    for vano,grupo in evaluacion.groupby("Vano",sort=False):
        no_ver=grupo["Estado tensión diseño"].str.startswith("NO VERIFICABLE")
        sobre=grupo["Estado tensión diseño"].str.startswith("SUPERA")
        comprobados=grupo.loc[~no_ver]
        critico=(comprobados.loc[comprobados["Ratio T / límite diseño"].idxmax()]
                 if not comprobados.empty else None)
        estado=("SUPERA LÍMITE DOCUMENTADO" if sobre.any()
                else "NO VERIFICABLE — CASOS SIN CRITERIO" if no_ver.any()
                else "BAJO LÍMITES; OTRAS VERIFICACIONES PENDIENTES")
        filas.append({
            "Vano":vano,
            "Casos evaluados":len(grupo),
            "Casos sin criterio":int(no_ver.sum()),
            "Casos que exceden":int(sobre.sum()),
            "Caso crítico documentado":critico["Caso"] if critico is not None else None,
            "Ratio crítico T/límite":(float(critico["Ratio T / límite diseño"])
                                      if critico is not None else float("nan")),
            "Estado":estado,
        })
    return pd.DataFrame(filas)
