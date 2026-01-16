# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .geometria import dist_utm, azimut_deg, deflexion_deg, distancias_tramos
from .catalogos import FRACCION_TRABAJO_DEFAULT, ANG_RETENIDA_DEFAULT_DEG

Point = Tuple[float, float]

def _tabla_ax(ax, rows: List[Dict], titulo: str, fontsize=9, scale=(1.02, 1.4)):
    ax.axis("off")
    ax.set_title(titulo, fontsize=13, fontweight="bold", pad=10)
    if not rows:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        return

    cols = list(rows[0].keys())
    cell_text = [list(r.values()) for r in rows]

    tbl = ax.table(
        cellText=cell_text,
        colLabels=cols,
        loc="center",
        cellLoc="center",
        colColours=["#d9d9d9"] * len(cols),
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    tbl.scale(scale[0], scale[1])

    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_text_props(weight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#f4f4f4")

def pagina_formulas(pdf: PdfPages, meta: Dict):
    fig, ax = plt.subplots(1, 1, figsize=(11.7, 8.3))  # A4 horizontal
    ax.axis("off")

    title = "Página de fórmulas y supuestos (Modelo base)"
    ax.text(0.5, 0.93, title, ha="center", va="center", fontsize=18, fontweight="bold")

    lines = [
        "Geometría (planta UTM):",
        "• Distancia:  L = √((x2−x1)^2 + (y2−y1)^2)",
        "• Azimut:     az = atan2(Δy, Δx)  (convertido a grados 0–360)",
        "• Deflexión:  |az_salida − az_entrada| (ajustada a 0–180)",
        "",
        "Clasificación por ángulo:",
        "• 0–5°: Paso | >5–30°: Ángulo | >30–60°: Doble remate | >60–90°: Giro",
        "",
        "Conductor:",
        f"• Tensión de trabajo:  T_work = {meta.get('fraccion_trabajo', FRACCION_TRABAJO_DEFAULT):.2f} · TR",
        "",
        "Demanda horizontal (por punto):",
        "• Remate: H = n_fases · T_work",
        "• Paso:   H = 0",
        "• Ángulo/Giro: H = n_fases · 2·T_work·sin(θ/2)",
        "• Doble remate: H = n_fases · 2·T_work",
        "",
        "Retenida (modelo geométrico simple):",
        f"• Ángulo retenida vs suelo: {meta.get('ang_retenida_deg', ANG_RETENIDA_DEFAULT_DEG):.0f}°",
        "• Tensión en retenida:  T_guy = H / cos(α)",
        "",
        "Nota:",
        "• Este modelo es base/rápido. No incluye hielo, temperatura, creep, ni NESC/ASCE completo.",
    ]

    y = 0.86
    for t in lines:
        ax.text(0.05, y, t, ha="left", va="top", fontsize=12)
        y -= 0.045 if t else 0.03

    pdf.savefig(fig)
    plt.close(fig)

def pagina_planta(pdf: PdfPages, puntos: List[Point], etiquetas: List[str], titulo: str):
    fig, ax = plt.subplots(1, 1, figsize=(16.5, 11.7))
    ax.plot([p[0] for p in puntos], [p[1] for p in puntos], "k-o", lw=2)

    for i, (x, y) in enumerate(puntos):
        ax.text(x + 2, y + 2, etiquetas[i], fontsize=10)

    ax.set_title(titulo, fontsize=18, fontweight="bold")
    ax.set_xlabel("X (UTM)")
    ax.set_ylabel("Y (UTM)")
    ax.set_aspect("equal")
    ax.grid(True)
    pdf.savefig(fig)
    plt.close(fig)

def generar_reporte_pdf(
    out_pdf: str,
    meta: Dict,
    tabla_resultados: List[Dict],
    tramos: List[Tuple[str, float, float]],
    puntos: List[Point],
    etiquetas: List[str],
):
    os.makedirs(os.path.dirname(out_pdf) or ".", exist_ok=True)

    with PdfPages(out_pdf) as pdf:
        # Página 1: tablas
        fig, axs = plt.subplots(2, 1, figsize=(16.5, 11.7))
        fig.suptitle("ANÁLISIS MECÁNICO DE LÍNEA (MODELO BASE)", fontsize=20, fontweight="bold", y=0.98)

        _tabla_ax(axs[0], tabla_resultados, "Resultados mecánicos por punto", fontsize=8.5, scale=(1.02, 1.25))

        tr_rows = [{"Tramo": n, "Distancia (m)": f"{d:,.2f}", "Acumulado (m)": f"{a:,.2f}"} for n, d, a in tramos]
        _tabla_ax(axs[1], tr_rows, "Distancias por tramo (UTM)", fontsize=10, scale=(1.02, 1.55))

        plt.subplots_adjust(top=0.90, bottom=0.04, hspace=0.25)
        pdf.savefig(fig)
        plt.close(fig)

        # Página 2: planta
        pagina_planta(pdf, puntos, etiquetas, "Planta UTM - Trayectoria")

        # Página 3: fórmulas
        pagina_formulas(pdf, meta)

