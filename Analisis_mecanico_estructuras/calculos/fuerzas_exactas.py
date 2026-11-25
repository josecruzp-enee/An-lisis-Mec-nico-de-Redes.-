"""Etapa 2.1: ensamblaje de fuerzas de extremo, sin recalcular catenarias.

Contrato: una fila por hipótesis, condición, vano, apoyo y conductor.
Si no existe columna Conductor, las filas representan un conductor
equivalente individual; n_fases replica únicamente conductores idénticos.
Todas las fuerzas son del cable SOBRE el apoyo, en kN, XYZ global.
"""
import numpy as np
import pandas as pd

def ensamblar_fuerzas_exactas(detalle: pd.DataFrame, *, n_fases: int = 1):
    if isinstance(n_fases, bool) or not isinstance(n_fases, int) or n_fases < 1:
        raise ValueError("n_fases debe ser entero positivo")
    keys = ["Hipótesis", "Condición", "Vano", "Apoyo"]
    axes = ["Fx (kN)", "Fy (kN)", "Fz (kN)"]
    if detalle.empty or not set(keys + axes).issubset(detalle.columns):
        raise ValueError("Detalle de extremos vacío o incompleto")
    d = detalle.copy()
    if "Conductor" in d:
        if n_fases != 1:
            raise ValueError("No multiplicar conductores explícitos")
        keys.append("Conductor")
    for col in keys:
        if d[col].isna().any():
            raise ValueError(f"Identificador faltante: {col}")
        d[col] = d[col].astype(str).str.strip()
        if d[col].eq("").any():
            raise ValueError(f"Identificador vacío: {col}")
    if d.duplicated(keys).any():
        raise ValueError("Extremos duplicados")
    d[axes] = d[axes].astype(float)
    if not np.isfinite(d[axes].to_numpy()).all():
        raise ValueError("Fuerzas no finitas")
    group = [k for k in keys if k != "Apoyo"]
    topology = {}
    for case, part in d.groupby(["Hipótesis", "Condición"], sort=False):
        edges = set()
        for edge, ends in part.groupby([k for k in group if k not in ("Hipótesis", "Condición")], sort=False):
            if len(ends) != 2 or ends["Apoyo"].nunique() != 2:
                raise ValueError(f"Vano sin dos extremos distintos: {edge}")
            edges.add((edge, tuple(sorted(ends["Apoyo"]))))
        topology[case] = edges
    if any(edges != next(iter(topology.values())) for edges in topology.values()):
        raise ValueError("Topología incompleta o diferente entre hipótesis")
    d[axes] *= n_fases
    s = d.groupby(["Hipótesis", "Condición", "Apoyo"], sort=False, as_index=False)[axes].sum()
    s["H (kN)"] = np.hypot(s[axes[0]], s[axes[1]])
    s["F resultante (kN)"] = np.linalg.norm(s[axes].to_numpy(), axis=1)
    return s
