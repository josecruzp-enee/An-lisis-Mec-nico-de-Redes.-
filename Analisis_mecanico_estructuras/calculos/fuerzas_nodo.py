# calculos/fuerzas_nodo.py
"""Modelo preliminar de cargas en apoyos de vanos nivelados.

X Este, Y Norte, Z arriba. Tensión horizontal H impuesta por conductor.
Distribución de peso y viento por mitades. No valida estructuras.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def _extremos(tramo):
    for sep in ("→", "->", "—>", "=>"):
        if sep in str(tramo):
            a, b = (s.strip() for s in str(tramo).split(sep, 1))
            if a and b and a != b:
                return a, b
    raise ValueError(f"Tramo inválido: {tramo}")


def _positivo(valor, nombre, admite_cero=False):
    v = float(valor)
    if not math.isfinite(v) or v < 0 or (v == 0 and not admite_cero):
        raise ValueError(f"{nombre}: debe ser finito y positivo")
    return v


def calcular_fuerzas_en_nodos(
    df_tramos: pd.DataFrame,
    df_resumen: pd.DataFrame,
    *,
    H_tendido_kN: float,
    n_fases: int,
    azimut_viento_deg: float = 0.0,
) -> pd.DataFrame:
    """Fuerzas del cable SOBRE los apoyos (kN).

    Cada tramo tiene n_fases conductores idénticos.
    q_viento_base es por conductor, se multiplica una vez por n_fases.
    q_n = q_base sin(theta) abs(sin(theta)), dirección normal al vano.
    """
    Ht = _positivo(H_tendido_kN, "H_tendido_kN")
    if isinstance(n_fases, bool) or not isinstance(n_fases, int) or n_fases <= 0:
        raise ValueError("n_fases debe ser un entero positivo")
    if df_tramos is None or df_tramos.empty or df_resumen is None or df_resumen.empty:
        raise ValueError("Tramos o nodos vacíos")
    for c in ("Tramo", "Distancia (m)", "Azimut (°)", "w_peso (kN/m)", "w_viento (kN/m)"):
        if c not in df_tramos.columns:
            raise ValueError(f"Falta columna {c}")
    if "Punto" not in df_resumen.columns:
        raise ValueError("Falta columna Punto")
    puntos = df_resumen["Punto"].astype(str).str.strip().tolist()
    if len(set(puntos)) != len(puntos):
        raise ValueError("Puntos duplicados")
    cargas = {p: np.zeros(3) for p in puntos}
    azv = math.radians(float(azimut_viento_deg))
    if not math.isfinite(azv):
        raise ValueError("Azimut de viento inválido")
    viento = np.array([math.cos(azv), math.sin(azv)])

    for _, tramo in df_tramos.iterrows():
        a, b = _extremos(tramo["Tramo"])
        if a not in cargas or b not in cargas:
            raise ValueError(f"Extremos no encontrados: {a}, {b}")
        luz = _positivo(tramo["Distancia (m)"], "longitud del vano")
        az = math.radians(float(tramo["Azimut (°)"]))
        if not math.isfinite(az):
            raise ValueError("Azimut de tramo inválido")
        tangente = np.array([math.cos(az), math.sin(az)])
        normal = np.array([-tangente[1], tangente[0]])
        peso = _positivo(tramo["w_peso (kN/m)"], "peso lineal", True)
        viento_base = _positivo(tramo["w_viento (kN/m)"], "carga base viento", True)
        seno = float(np.dot(viento, normal))
        q_normal = viento_base * seno * abs(seno) * n_fases
        viento_apoyo = 0.5 * luz * q_normal * normal
        vertical_apoyo = -0.5 * luz * peso
        tension = Ht * n_fases * tangente
        cargas[a] += [tension[0]+viento_apoyo[0], tension[1]+viento_apoyo[1], vertical_apoyo]
        cargas[b] += [-tension[0]+viento_apoyo[0], -tension[1]+viento_apoyo[1], vertical_apoyo]

    resultados = []
    for p in puntos:
        fx, fy, fz = map(float, cargas[p])
        resultados.append({
            "Punto": p, "Fx (kN)": fx, "Fy (kN)": fy,
            "Fz (kN)": fz, "H (kN)": math.hypot(fx, fy),
            "Estado cálculo": "PRELIMINAR",
        })
    return pd.DataFrame(resultados)
