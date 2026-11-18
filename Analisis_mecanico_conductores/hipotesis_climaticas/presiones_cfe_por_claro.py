"""Presiones CFE 05 00 03, hoja 2/6 (Manual_lineas.pdf, página PDF 154).

Valores de presión sobre CONDUCTORES, Pa, para velocidad regional 120 km/h.
La presión incluye el coeficiente de arrastre del cable C_d=1 ya aplicado
en el estudio CFE; no multiplicar de nuevo por C_d ni obtenerla con rho*V²/2.
La presión depende del claro, NO del valor de P ni de TH1/TH2.
"""
from __future__ import annotations

import math

# claro interpostal (m): presión máxima (Pa), presión reducida (Pa).
PRESIONES_CFE_120 = {
    5:(458,84),35:(426,78),40:(422,77),45:(418,77),50:(414,76),55:(411,75),
    60:(407,75),65:(404,74),70:(401,74),75:(399,73),80:(396,73),
    85:(393,72),90:(391,72),95:(389,71),100:(386,71),105:(384,70),
    110:(382,70),115:(380,70),120:(378,69),125:(376,69),
    130:(375,69),135:(373,68),140:(371,68),145:(370,68),
    150:(368,67),155:(367,67),160:(365,67),165:(364,67),
    170:(362,66),175:(361,66),180:(360,66),185:(359,66),
    190:(357,65),195:(356,65),200:(355,65),205:(354,65),
    210:(353,65),220:(351,64),225:(350,64),230:(349,64),
    235:(348,64),240:(347,64),245:(346,63),250:(345,63),
    255:(344,63),260:(343,63),265:(342,63),270:(342,63),
    275:(341,63),280:(340,62),285:(339,62),290:(339,62),
    295:(338,62),300:(337,62),
}

def presion_cfe_por_claro(claro_m, velocidad_kmh):
    """Presión tabular [Pa] interpolada linealmente, sin extrapolación.

    Solo los casos CFE de VR 120 km/h (máximo) y 109 km/h (reducido)
    son identificables en esta tabla. Cero implica ausencia de viento.
    """
    claro=float(claro_m)
    v=float(velocidad_kmh)
    if not math.isfinite(claro) or claro<=0 or not math.isfinite(v):
        raise ValueError("Claro o viento CFE inválido")
    if abs(v)<1e-9:
        return 0.
    if abs(v-120.)<1e-7:
        col=0
    elif abs(v-109.)<1e-7:
        col=1
    else:
        raise ValueError("Presión CFE disponible solo para 120 km/h máximo o 109 km/h reducido")
    ll=sorted(PRESIONES_CFE_120)
    if claro<ll[0] or claro>ll[-1]:
        raise ValueError(f"Claro {claro:g} m fuera del intervalo CFE documentado {ll[0]}–{ll[-1]} m")
    if claro in PRESIONES_CFE_120:
        return float(PRESIONES_CFE_120[claro][col])
    for izq,der in zip(ll[:-1],ll[1:]):
        if izq<claro<der:
            a=PRESIONES_CFE_120[izq][col]
            b=PRESIONES_CFE_120[der][col]
            return float(a+(b-a)*(claro-izq)/(der-izq))
    raise RuntimeError("Intervalo CFE no identificado")
