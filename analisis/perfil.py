# analisis/perfil.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import numpy as np
import math

from .norma_postes import altura_poste_m
from .geometria import dist_utm
from .mecanica import peso_lineal_kN_m, tension_trabajo_kN

Point = Tuple[float, float]

# ============================================================
# Parámetros 
# ============================================================
OFFSET_AMARRE_DESDE_PUNTA_M_DEFAULT: float = 0.10  # m (amarre típico bajo la punta)
DESPEJE_MIN_M_DEFAULT: float = 0.00                # m (ponlo en 6.0, 7.0 etc si ya tienes norma)


# ============================================================
# Utilidades de alturas
# ============================================================
def altura_poste_por_df(df, tipo_poste: str, default_m: float = 12.0) -> np.ndarray:
    """
    Altura del poste (m) por punto.
    - Si Excel trae 'Altura_Poste_m', se usa por punto.
    - Si no, toma altura del catálogo/norma via altura_poste_m(tipo_poste).
    """
    if "Altura_Poste_m" in df.columns:
        return df["Altura_Poste_m"].astype(float).to_numpy()

    # altura_poste_m ya resuelve tipo_poste (ej: "PM-40", "PC-12-750", etc.)
    h = float(altura_poste_m(tipo_poste, default_m=default_m))
    return np.full(len(df), h, dtype=float)


def altura_amarre_abs(
    df,
    terreno: np.ndarray,
    h_poste: np.ndarray,
    *,
    offset_desde_punta_m: float = OFFSET_AMARRE_DESDE_PUNTA_M_DEFAULT,
) -> np.ndarray:
    """
    Altura absoluta del amarre (cota).
    - Si Excel trae 'Altura_Amarre_m', se interpreta como altura sobre terreno y se suma al terreno.
    - Si no, amarre = terreno + altura_poste - offset_desde_punta_m
    """
    if "Altura_Amarre_m" in df.columns:
        return terreno + df["Altura_Amarre_m"].astype(float).to_numpy()

    return terreno + h_poste - float(offset_desde_punta_m)


# ============================================================
# Sag / perfil
# ============================================================
def sag_parabolica_m(L: float, wv_kN_m: float, H_kN: float) -> float:
    """
    Parabólica (aprox):
        f = w*L^2 / (8*H)
    donde H ~ tensión horizontal.
    """
    if L <= 0 or H_kN <= 0:
        return 0.0
    return float(wv_kN_m * L * L / (8.0 * H_kN))


def sag_catenaria_m(Lh: float, wv_kN_m: float, H_kN: float) -> float:
    """
    Catenaria real (nivelada) por peso vertical (sin viento en vertical):

        f = (H/wv) * (cosh( (wv*Lh)/(2H) ) - 1)

    donde:
      - Lh: luz horizontal (m) (si no hay gran pendiente, Lh≈L)
      - wv_kN_m: carga vertical por peso (kN/m)
      - H_kN: componente horizontal de tensión (kN)
    """
    if Lh <= 0 or wv_kN_m <= 0 or H_kN <= 0:
        return 0.0
    x = (wv_kN_m * Lh) / (2.0 * H_kN)
    return float((H_kN / wv_kN_m) * (math.cosh(x) - 1.0))


def tension_soporte_catenaria_kN(Lh: float, wv_kN_m: float, H_kN: float) -> float:
    """
    Tensión en soporte (por fase) para catenaria nivelada:

        Ts = H * cosh( (wv*Lh)/(2H) )

    Devuelve kN.
    """
    if Lh <= 0 or wv_kN_m <= 0 or H_kN <= 0:
        return 0.0
    x = (wv_kN_m * Lh) / (2.0 * H_kN)
    return float(H_kN * math.cosh(x))


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
    - Flecha aplicada sobre la recta:
        cond = y_line - 4*f*r*(1-r)

    Nota: aquí dibujamos con parábola geométrica; la diferencia PARABOLA vs CATENARIA
    está en cómo calculas f (flecha).
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

    cond = y_line - 4.0 * sag_f * r * (1.0 - r)

    despeje = cond - terr
    return chain0 + s, terr, cond, float(np.min(despeje))


# ============================================================
# Motor de perfil
# ============================================================
def analizar_perfil(
    df,
    tipo_poste: str,
    calibre: str,
    *,
    fraccion_trabajo: float = 0.20,
    modo_sag: str = "CATENARIA",  # "CATENARIA" | "PARABOLA"
    offset_amarre_desde_punta_m: float = OFFSET_AMARRE_DESDE_PUNTA_M_DEFAULT,
    despeje_min_m: float = DESPEJE_MIN_M_DEFAULT,
) -> Optional[Dict]:
    """
    Analiza perfil longitudinal si existe columna 'Altitude'.

    - wv: solo peso (vertical) por conductor (NO multiplicar por fases)
    - H: tensión horizontal por fase (aquí se usa tensión de trabajo)

    Nota: el viento se usa en planta (esfuerzos laterales), no en la flecha vertical.
    """
    if "Altitud" not in df.columns:
        return None

    puntos: List[Point] = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    # chainage (distancia acumulada por tramos)
    chain_nodes = [0.0]
    for i in range(len(puntos) - 1):
        d = float(dist_utm(puntos[i], puntos[i + 1]))
        chain_nodes.append(chain_nodes[-1] + d)
    chain_nodes = np.array(chain_nodes, dtype=float)

    terreno = df["Altitud"].astype(float).to_numpy()
    h_poste = altura_poste_por_df(df, tipo_poste)
    amarre = altura_amarre_abs(df, terreno, h_poste, offset_desde_punta_m=offset_amarre_desde_punta_m)

    # Parámetros por conductor
    wv = float(peso_lineal_kN_m(calibre))                     # kN/m (peso)
    H = float(tension_trabajo_kN(calibre, fraccion_trabajo))  # kN (tensión horizontal aprox)

    modo = str(modo_sag).strip().upper()

    filas_vanos: List[Dict] = []
    X_prof, G_prof, Y_prof = [], [], []

    for i in range(len(puntos) - 1):
        L = float(dist_utm(puntos[i], puntos[i + 1]))  # m (usamos L≈Lh en FASE 2 puedes meter proyección)
        Lh = L

        if modo == "CATENARIA":
            f = sag_catenaria_m(Lh, wv, H)
            Ts = tension_soporte_catenaria_kN(Lh, wv, H)
        else:
            f = sag_parabolica_m(L, wv, H)
            Ts = H  # referencia

        ch0 = float(chain_nodes[i])
        g0, g1 = float(terreno[i]), float(terreno[i + 1])
        y0, y1 = float(amarre[i]), float(amarre[i + 1])

        ch, g, y, min_clear = evaluar_despeje_por_vano(
            chain0=ch0, L=L,
            g0=g0, g1=g1,
            y0=y0, y1=y1,
            sag_f=f,
            npts=90,
        )

        X_prof.append(ch)
        G_prof.append(g)
        Y_prof.append(y)

        filas_vanos.append({
            "Tramo": f"{etiquetas[i]} → {etiquetas[i + 1]}",
            "Longitud (m)": round(L, 2),
            "Modo sag": modo,
            "wv (kN/m)": round(wv, 5),
            "H (kN)": round(H, 3),
            "Ts (kN)": round(float(Ts), 3),
            "Sag f (m)": round(float(f), 3),
            "Despeje mín (m)": round(float(min_clear), 3),
            "Cumple despeje": "SI" if (min_clear >= float(despeje_min_m)) else "NO",
        })

    return {
        "total_m": float(chain_nodes[-1]) if len(chain_nodes) else 0.0,
        "chain_nodes": chain_nodes,
        "terreno": terreno,
        "amarre": amarre,
        "X_prof": np.concatenate(X_prof) if X_prof else np.array([], dtype=float),
        "G_prof": np.concatenate(G_prof) if G_prof else np.array([], dtype=float),
        "Y_prof": np.concatenate(Y_prof) if Y_prof else np.array([], dtype=float),
        "tabla_vanos": filas_vanos,
        "meta": {
            "tipo_poste": str(tipo_poste),
            "calibre": str(calibre),
            "fraccion_trabajo": float(fraccion_trabajo),
            "modo_sag": modo,
            "offset_amarre_desde_punta_m": float(offset_amarre_desde_punta_m),
            "despeje_min_m": float(despeje_min_m),
        }
    }
