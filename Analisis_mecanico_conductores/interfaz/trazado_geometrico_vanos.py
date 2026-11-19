"""Vista superior del trazado: apoyos, vanos, longitudes y remates.

No calcula cargas ni propone retenidas. Consume la misma geometría y
segmentación de remates del motor CFE, sin alterar sus ecuaciones.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from Analisis_mecanico_conductores.motor_conductores import (
    dividir_secciones_por_remates,
)


def crear_figura_trazado(puntos):
    """Devuelve (figura, tabla de vanos, tabla de secciones) de los datos XYZ."""
    secciones = dividir_secciones_por_remates(puntos)
    p = puntos.reset_index(drop=True)
    xs = p["X"].to_numpy(dtype=float)
    ys = p["Y"].to_numpy(dtype=float)
    if not (np.isfinite(xs).all() and np.isfinite(ys).all()):
        raise ValueError("Coordenadas X/Y inválidas para el dibujo")
    if len(p) < 2:
        raise ValueError("Se requieren dos puntos para dibujar la línea")

    import pandas as pd
    vanos = []
    seccion_filas = []
    fig, ax = plt.subplots(figsize=(10, 5))
    colores = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for isec, (nombre, segmento) in enumerate(secciones):
        color = colores[isec % len(colores)]
        xx = segmento["X"].to_numpy(dtype=float)
        yy = segmento["Y"].to_numpy(dtype=float)
        ax.plot(xx, yy, "-o", linewidth=2.2, markersize=4.5,
                color=color, label=f"{nombre}: {segmento.iloc[0]['Punto']}–{segmento.iloc[-1]['Punto']}")
        seccion_filas.append({
            "Sección": nombre,
            "Remate inicial": str(segmento.iloc[0]["Punto"]),
            "Remate final": str(segmento.iloc[-1]["Punto"]),
            "Número de vanos": len(segmento)-1,
        })
        for i in range(len(segmento)-1):
            dx, dy = xx[i+1]-xx[i], yy[i+1]-yy[i]
            longitud = float(np.hypot(dx, dy))
            if longitud <= 0:
                raise ValueError("Vano con claro horizontal nulo")
            vanos.append({
                "Sección": nombre,
                "Vano": f"{segmento.iloc[i]['Punto']} → {segmento.iloc[i+1]['Punto']}",
                "Claro horizontal (m)": longitud,
            })
            mx, my = (xx[i]+xx[i+1])/2, (yy[i]+yy[i+1])/2
            # Etiqueta desplazada en puntos de pantalla, incluso si toda
            # la línea tiene Y constante o está orientada norte-sur.
            ax.annotate(f"{longitud:.1f} m", (mx, my),
                        xytext=(0, 11 if i % 2 == 0 else -18),
                        textcoords="offset points", ha="center", va="center",
                        fontsize=9, color=color,
                        bbox={"boxstyle":"round,pad=0.2","facecolor":"white",
                              "edgecolor":"none","alpha":0.85})
    remates = {
        str(sub.iloc[0]["Punto"]) for _, sub in secciones
    } | {
        str(sub.iloc[-1]["Punto"]) for _, sub in secciones
    }
    mask = np.array([str(n) in remates for n in p["Punto"]], dtype=bool)
    ax.scatter(xs[mask], ys[mask], s=120, marker="s",
               facecolor="white", edgecolor="#b91c1c", linewidth=2,
               label="Remate", zorder=5)
    ax.scatter(xs[~mask], ys[~mask], s=60, marker="o",
               facecolor="white", edgecolor="#334155", linewidth=2,
               label="Apoyo de paso", zorder=5)
    for x, y, nombre in zip(xs, ys, p["Punto"]):
        ax.annotate(str(nombre), (x,y), xytext=(5, 10),
                    textcoords="offset points", fontsize=10, fontweight="bold")
    ax.set(title="Trazado en planta — apoyos, vanos y secciones de tendido",
           xlabel="Coordenada X (m)", ylabel="Coordenada Y (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.margins(0.16)
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    return fig, pd.DataFrame(vanos), pd.DataFrame(seccion_filas)
