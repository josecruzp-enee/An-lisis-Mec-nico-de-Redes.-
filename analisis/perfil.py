# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np

from .catalogos import POSTES, OFFSET_AMARRE_DESDE_PUNTA_M, DESPEJE_MIN_M
from .geometria import dist_utm, distancias_tramos
from .mecanica import peso_lineal_kN_m, tension_trabajo_kN

def altura_poste_por_df(df, tipo_poste: str) -> np.ndarray:
    if "Altura_Poste_m" in df.columns:
        return df["Altura_Poste_m"].astype(float).to_numpy()
    return np.full(len(df), float(POSTES[tipo_poste]["altura_m"]))

def altura_amarre_abs(df, terreno: np.ndarray, h_poste: np.ndarray) -> np.ndarray:
    if "Altura_Amarre_m" in df.columns:
        return terreno + df["Altura_Amarre_m"].astype(float).to_numpy()
    return terreno + h_poste - float(OFFSET_AMARRE_DESDE_PUNTA_M)

def sag_parabolica_m(L: float, w_kN_m: float, T_kN: float) -> float:
    if L <= 0 or T_kN <= 0:
        return 0.0
    return float(w_kN_m * L * L / (8.0 * T_kN))

def evaluar_despeje_por_vano(chain0, L, g0, g1, y0, y1, sag_f, npts=80):
    if L <= 0:
        s = np.array([0.0])
        ch = chain0 + s
        terr = np.array([g0])
        cond = np.array([y0])
        return ch, terr, cond, float(np.min(cond - terr))

    s = np.linspace(0, L, npts)
    r = s / L

    terr = g0 + (g1 - g0) * r
    y_line = y0 + (y1 - y0) * r
    cond = y_line - 4.0 * sag_f * r * (1.0 - r)

    despeje = cond - terr
    return chain0 + s, terr, cond, float(np.min(despeje))

def analizar_perfil(df, tipo_poste: str, calibre: str, n_fases: int):
    if "Altitude" not in df.columns:
        return None  # perfil no aplica

    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    tramos, total_m = distancias_tramos(puntos, etiquetas)
    chain_nodes = [0.0]
    for _n, d, _a in tramos:
        chain_nodes.append(chain_nodes[-1] + float(d))
    chain_nodes = np.array(chain_nodes, float)

    terreno = df["Altitude"].astype(float).to_numpy()
    h_poste = altura_poste_por_df(df, tipo_poste)
    amarre = altura_amarre_abs(df, terreno, h_poste)

    w = peso_lineal_kN_m(calibre) * n_fases
    T = tension_trabajo_kN(calibre) * n_fases

    filas_vanos = []
    X_prof, G_prof, Y_prof = [], [], []

    for i in range(len(puntos)-1):
        L = dist_utm(puntos[i], puntos[i+1])
        f = sag_parabolica_m(L, w, T)

        ch0 = float(chain_nodes[i])
        g0, g1 = float(terreno[i]), float(terreno[i+1])
        y0, y1 = float(amarre[i]), float(amarre[i+1])

        ch, g, y, min_clear = evaluar_despeje_por_vano(ch0, L, g0, g1, y0, y1, f, npts=90)
        X_prof.append(ch); G_prof.append(g); Y_prof.append(y)

        filas_vanos.append({
            "Tramo": f"{etiquetas[i]} → {etiquetas[i+1]}",
            "Longitud (m)": round(L, 2),
            "Sag f (m)": round(f, 2),
            "Despeje mín (m)": round(min_clear, 2),
            "Cumple despeje": "SI" if (min_clear >= DESPEJE_MIN_M) else "NO",
        })

    return {
        "tramos": tramos,
        "total_m": float(total_m),
        "chain_nodes": chain_nodes,
        "terreno": terreno,
        "amarre": amarre,
        "X_prof": np.concatenate(X_prof) if X_prof else np.array([]),
        "G_prof": np.concatenate(G_prof) if G_prof else np.array([]),
        "Y_prof": np.concatenate(Y_prof) if Y_prof else np.array([]),
        "tabla_vanos": filas_vanos,
    }

