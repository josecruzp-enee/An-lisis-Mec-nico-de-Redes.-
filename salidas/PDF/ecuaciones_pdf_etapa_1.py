"""Ecuaciones presentadas con notación matemática, sin recalcular resultados."""
from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from reportlab.platypus import Image, KeepTogether, Spacer


# Las expresiones reproducen la formulación implementada en los módulos
# catenaria, cambio_estado y evaluador de estados. No son calculadoras.
ECUACIONES = {
    "3.1.": [
        r"$L_r=\sqrt{\frac{\sum_i L_i^3}{\sum_i L_i}}$",
    ],
    "3.2.": [
        r"$a=\frac{H}{\Vert\mathbf{q}\Vert}$",
        r"$z(x)=a\left[\cosh\left(\frac{x-x_c}{a}\right)-\cosh\left(\frac{x_c}{a}\right)\right]$",
        r"$T(x)=H\cosh\left(\frac{x-x_c}{a}\right)$",
    ],
    "3.3.": [
        r"$L_n=\int_0^{L}\frac{ds}{1+T(s)/(EA)}$",
        r"$\sum_i L_{n,i,2}=\left(1+\alpha\Delta\theta+\varepsilon_p\right)\sum_i L_{n,i,1}$",
    ],
    "3.4.": [
        r"$w_v=\frac{\rho C_d D V^2}{2\,(1000)}\quad[\mathrm{kN/m}]$",
    ],
    "3.5.": [
        r"$R(H_0)=\max_j\left(\frac{T_{\max,j}(H_0)}{T_{\mathrm{lim},j}}\right)\leq 1$",
    ],
}


def imagen_ecuacion(formula: str, *, ancho_maximo: float):
    """Imagen nítida en memoria. Matplotlib mathtext funciona sin LaTeX externo."""
    fig = plt.figure(figsize=(9.0, 0.56), dpi=220)
    fig.patch.set_alpha(0)
    fig.text(0.5, 0.52, formula, ha="center", va="center",
             fontsize=15, color="black")
    buf = BytesIO()
    try:
        fig.savefig(buf, format="png", dpi=220, transparent=True,
                    bbox_inches="tight", pad_inches=0.16)
    finally:
        plt.close(fig)
    buf.seek(0)
    imagen = Image(buf)
    escala = min(ancho_maximo / imagen.drawWidth, 1.0, 42 / imagen.drawHeight)
    imagen.drawWidth *= escala
    imagen.drawHeight *= escala
    imagen.hAlign = "CENTER"
    return imagen


def formulas_para_seccion(titulo: str, ancho: float):
    clave = titulo.split(" ", 1)[0]
    if clave not in ECUACIONES:
        return []
    contenido = []
    for formula in ECUACIONES[clave]:
        contenido.append(Spacer(1, 4))
        contenido.append(imagen_ecuacion(formula, ancho_maximo=ancho))
    return contenido


NOMENCLATURA = [
    ("L_i, L_r", "Luz del vano i y vano regulador", "m"),
    ("H, H_0", "Componente de tensión perpendicular a la carga resultante y valor de referencia", "kN"),
    ("T(x)", "Tracción en la abscisa x del conductor", "kN"),
    ("EA", "Rigidez axial documentada del conductor", "kN"),
    ("L_n", "Longitud natural descargada", "m"),
    ("q, w_v", "Carga distribuida vectorial y componente aerodinámica", "kN/m"),
    ("alpha", "Coeficiente lineal de dilatación térmica", "1/°C"),
    ("Delta theta", "Diferencia de temperatura del conductor", "°C"),
    ("epsilon_p", "Deformación permanente impuesta; nula en el caso actual", "adimensional"),
    ("rho, C_d, D, V", "Densidad del aire, coeficiente de arrastre, diámetro expuesto y velocidad", "kg/m³; —; m; m/s"),
    ("R(H_0)", "Mayor utilización de las hipótesis de tensión documentadas", "adimensional"),
]
