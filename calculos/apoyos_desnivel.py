"""Acciones 3D de conductores a desnivel, sin viento.

Recibe cotas de terreno y alturas reales de amarre por punto. Cada vano
se modela como cable retenido en sus extremos: NO modela poleas, suspensión
móvil, redistribución elástica ni cambios de estado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from calculos.catenaria_desnivel import resolver_catenaria_desnivel
from calculos.mecanica import peso_lineal_kN_m


def _puntos_amarre(df):
    requeridas = ("Punto", "X", "Y", "Altitud", "Altura_Amarre_m")
    faltan = [c for c in requeridas if c not in df.columns]
    if faltan:
        raise ValueError(
            "Para vanos desnivelados se requieren columnas " + ", ".join(faltan))
    datos = df[list(requeridas)].copy()
    if datos.isna().any().any():
        raise ValueError("Hay cotas o alturas de amarre faltantes")
    alturas = datos["Altura_Amarre_m"].to_numpy(dtype=float)
    if not np.isfinite(alturas).all() or (alturas <= 0).any():
        raise ValueError("Alturas de amarre deben ser positivas y finitas")
    pts = datos[["X", "Y", "Altitud"]].to_numpy(dtype=float)
    pts[:, 2] += alturas
    if not np.isfinite(pts).all():
        raise ValueError("Coordenadas 3D no finitas")
    return pts


def calcular_apoyos_desnivel(df, *, calibre, n_fases, H_tendido_kN,
                            despeje_min_m=None):
    """Retorna tabla de fuerzas y perfil para cada vano sin viento.

    H_tendido_kN es tensión horizontal POR conductor y POR vano.
    Sin verificación de compatibilidad entre vanos ni temperatura.
    """
    if int(n_fases) != n_fases or int(n_fases) < 1:
        raise ValueError("Número de conductores inválido")
    if despeje_min_m is not None and (
        not np.isfinite(despeje_min_m) or despeje_min_m <= 0):
        raise ValueError("Despeje mínimo inválido")

    pts = _puntos_amarre(df)
    w = float(peso_lineal_kN_m(calibre))
    nombres = df["Punto"].astype(str).tolist()
    terreno = df["Altitud"].to_numpy(dtype=float)
    fuerzas = {p: np.zeros(3, dtype=float) for p in nombres}
    filas, curvas = [], []
    cadena = 0.0

    for i in range(len(df) - 1):
        cable = resolver_catenaria_desnivel(
            pts[i], pts[i + 1], w, H_tendido_kN)
        fa, fb = cable.fuerzas_extremos
        fuerzas[nombres[i]] += int(n_fases) * fa
        fuerzas[nombres[i + 1]] += int(n_fases) * fb
        L = cable.longitud_horizontal

        x, despeje = cable.minimo_terreno_lineal(
            float(terreno[i]), float(terreno[i + 1]))
        flecha = cable.flecha_respecto_cuerda(float(pts[i + 1, 2]))
        cumple = ("NO VERIFICABLE" if despeje_min_m is None
                  else ("SI" if despeje >= despeje_min_m else "NO"))

        filas.append({
            "Tramo": f"{nombres[i]} → {nombres[i + 1]}",
            "Longitud (m)": L,
            "Longitud real cable (m)": cable.longitud_real,
            "Modo sag": "CATENARIA DESNIVEL",
            "wv (kN/m)": w,
            "H (kN)": float(H_tendido_kN),
            "Ts A (kN)": cable.tension_extremo(0),
            "Ts B (kN)": cable.tension_extremo(L),
            "Ts (kN)": max(cable.tension_extremo(0),cable.tension_extremo(L)),
            "Sag f (m)": flecha,
            "Despeje mín (m)": despeje,
            "Cumple despeje": cumple,
        })
        xs = np.linspace(0, L, 100)
        cotas = cable.altura(xs)
        suelo = terreno[i] + (terreno[i + 1] - terreno[i]) * xs/L
        curvas.append((cadena + xs, suelo, cotas))
        cadena += L

    filas_fuerzas = []
    for p in nombres:
        fx, fy, fz = map(float, fuerzas[p])
        filas_fuerzas.append({
            "Punto": p, "Fx (kN)": fx, "Fy (kN)": fy,
            "Fz (kN)": fz, "H (kN)": float(np.hypot(fx, fy)),
            "Estado cálculo": "PRELIMINAR 3D",
        })

    perfil = {
        "total_m": cadena,
        "chain_nodes": np.r_[0, np.cumsum([
            fila["Longitud (m)"] for fila in filas])],
        "terreno": terreno,
        "amarre": pts[:, 2],
        "X_prof": np.concatenate([v[0] for v in curvas]),
        "G_prof": np.concatenate([v[1] for v in curvas]),
        "Y_prof": np.concatenate([v[2] for v in curvas]),
        "tabla_vanos": filas,
        "meta": {
            "modo_sag": "CATENARIA DESNIVEL",
            "despeje_min_m": despeje_min_m,
            "alcance": "Sin viento, terreno lineal y amarres explícitos; no valida construcción",
        },
    }
    return pd.DataFrame(filas_fuerzas), perfil
