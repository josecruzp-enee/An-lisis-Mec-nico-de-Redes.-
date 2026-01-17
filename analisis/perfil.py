# analisis/perfil.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import numpy as np

from .catalogos import POSTES
from .config import OFFSET_AMARRE_DESDE_PUNTA_M, DESPEJE_MIN_M
from .geometria import dist_utm, distancias_tramos
from .mecanica import peso_lineal_kN_m, tension_trabajo_kN

Point = Tuple[float, float]


# ============================================================
# Utilidades de alturas
# ============================================================
def altura_poste_por_df(df, tipo_poste: str) -> np.ndarray:
    """
    Altura del poste (m) por punto.
    - Si Excel trae 'Altura_Poste_m', se usa por punto.
    - Si no, toma altura del catálogo POSTES[tipo_poste]['altura_m'].
    """
    if "Altura_Poste_m" in df.columns:
        return df["Altura_Poste_m"].astype(float).to_numpy()

    # Si en tu catálogo aún NO tienes 'altura_m', esto levantará KeyError.
    # Recomiendo que POSTES incluya altura_m por tipo de poste.
    return np.full(len(df), float(POSTES[tipo_poste]["altura_m"]), dtype=float)


def altura_amarre_abs(df, terreno: np.ndarray, h_poste: np.ndarray) -> np.ndarray:
    """
    Altura absoluta del amarre (msnm si Altitude está en msnm).
    - Si Excel trae 'Altura_Amarre_m', se suma al terreno.
    - Si no, amarre = terreno + altura_poste - OFFSET_AMARRE_DESDE_PUNTA_M
    """
    if "Altura_Amarre_m" in df.columns:
        return terreno + df["Altura_Amarre_m"].astype(float).to_numpy()

    return terreno + h_poste - float(OFFSET_AMARRE_DESDE_PUNTA_M)


# ============================================================
# Sag / perfil
# ============================================================
def sag_parabolica_m(L: float, w_kN_m: float, T_kN: float) -> float:
    """
    Flecha parabólica aproximada:
        f = w*L^2 / (8*T)
    donde:
      - w_kN_m: carga vertical por metro (kN/m) (peso del conductor)
      - T_kN: componente horizontal de tensión (kN) (aprox tensión de trabajo)
    """
    if L <= 0 or T_kN <= 0:
        return 0.0
    return float(w_kN_m * L * L / (8.0 * T_kN))


def evaluar_despeje_por_vano(
    chain0: float,
    L: float,
    g0: float,
    g1: float,
    y0: float,
    y1: float,
    sag_f: float,
    npts: int = 80,
):
    """
    Evalúa el perfil del conductor en un vano asumiendo:
    - Terreno lineal entre apoyos (g0->g1)
    - Línea recta entre amarres (y0->y1)
    - Parabólica de flecha aplicada sobre la recta:
        cond = y_line - 4*f*r*(1-r)
    Devuelve arrays de chainage, terreno, conductor, y despeje mínimo del vano.
    """
    if L <= 0:
        s = np.array([0.0])
        ch = chain0 + s
        terr = np.array([g0])
        cond = np.array([y0])
        return ch, terr, cond, float(np.min(cond - terr))

    s = np.linspace(0.0, L, int(npts))
    r = s / L

    terr = g0 + (g1 - g0) * r
    y_line = y0 + (y1 - y0) * r

    # parábola simétrica con flecha máxima f en el centro
    cond = y_line - 4.0 * sag_f * r * (1.0 - r)

    despeje = cond - terr
    return chain0 + s, terr, cond, float(np.min(despeje))


# ============================================================
# Motor de perfil
# ============================================================
def analizar_perfil(df, tipo_poste: str, calibre: str) -> Optional[Dict]:
    """
    Analiza perfil longitudinal si existe columna 'Altitude'.
    Retorna dict con series del perfil y tabla por vano.

    Nota:
    - Para despeje y flecha se recomienda trabajar por conductor (NO multiplicar por n_fases).
    - Si luego quieres considerar varios conductores, se evalúa el peor caso aparte.
    """
    if "Altitude" not in df.columns:
        return None  # perfil no aplica

    puntos: List[Point] = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    tramos, total_m = distancias_tramos(puntos, etiquetas)

    # chainage de nodos
    chain_nodes = [0.0]
    for _n, d, _a in tramos:
        chain_nodes.append(chain_nodes[-1] + float(d))
    chain_nodes = np.array(chain_nodes, dtype=float)

    terreno = df["Altitude"].astype(float).to_numpy()
    h_poste = altura_poste_por_df(df, tipo_poste)
    amarre = altura_amarre_abs(df, terreno, h_poste)

    # Parámetros por CONDUCTOR (para sag/despeje)
    w = float(peso_lineal_kN_m(calibre))          # kN/m
    T = float(tension_trabajo_kN(calibre))        # kN

    filas_vanos: List[Dict] = []
    X_prof, G_prof, Y_prof = [], [], []

    for i in range(len(puntos) - 1):
        L = dist_utm(puntos[i], puntos[i + 1])
        f = sag_parabolica_m(L, w, T)

        ch0 = float(chain_nodes[i])
        g0, g1 = float(terreno[i]), float(terreno[i + 1])
        y0, y1 = float(amarre[i]), float(amarre[i + 1])

        ch, g, y, min_clear = evaluar_despeje_por_vano(
            chain0=ch0, L=L,
            g0=g0, g1=g1,
            y0=y0, y1=y1,
            sag_f=f,
            npts=90
        )

        X_prof.append(ch)
        G_prof.append(g)
        Y_prof.append(y)

        filas_vanos.append({
            "Tramo": f"{etiquetas[i]} → {etiquetas[i + 1]}",
            "Longitud (m)": round(float(L), 2),
            "Sag f (m)": round(float(f), 2),
            "Despeje mín (m)": round(float(min_clear), 2),
            "Cumple despeje": "SI" if (min_clear >= float(DESPEJE_MIN_M)) else "NO",
        })

    return {
        "tramos": tramos,
        "total_m": float(total_m),
        "chain_nodes": chain_nodes,
        "terreno": terreno,
        "amarre": amarre,
        "X_prof": np.concatenate(X_prof) if X_prof else np.array([], dtype=float),
        "G_prof": np.concatenate(G_prof) if G_prof else np.array([], dtype=float),
        "Y_prof": np.concatenate(Y_prof) if Y_prof else np.array([], dtype=float),
        "tabla_vanos": filas_vanos,
    }
