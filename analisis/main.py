# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os

from .io_excel import leer_puntos_excel
from .geometria import deflexion_deg, distancias_tramos, clasificar_por_angulo
from .mecanica import (
    tension_trabajo_kN,
    demanda_horizontal_kN,
    tension_retenida_kN,
    capacidad_poste_kN,
    cable_retenida_recomendado,
)
from .reporte_pdf import generar_reporte_pdf

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--excel", required=True, help="Ruta del Excel con Punto,X,Y")
    p.add_argument("--calibre", required=True, help='Ej: "2/0 ACSR"')
    p.add_argument("--fases", type=int, default=3)
    p.add_argument("--poste", required=True, help='Ej: "PC-40"')
    p.add_argument("--out", default="outputs/analisis_mecanico_linea.pdf")
    args = p.parse_args()

    df, puntos, etiquetas = leer_puntos_excel(args.excel)

    T = tension_trabajo_kN(args.calibre)
    Hmax = capacidad_poste_kN(args.poste)
    cable_ret = cable_retenida_recomendado(args.calibre)

    resultados = []

    # Inicio
    H0 = demanda_horizontal_kN("Remate", T, args.fases, 0.0)
    resultados.append({
        "Punto": etiquetas[0],
        "Deflexión (°)": "-",
        "Estructura": "Remate",
        "H (kN)": round(H0, 2),
        "T_guy (kN)": round(tension_retenida_kN(H0), 2),
        "Cable Guy": cable_ret,
        "Poste": args.poste,
        "Cap (kN)": Hmax,
        "Cumple": "SI" if H0 <= Hmax else "NO",
    })

    # Intermedios
    for i in range(1, len(puntos) - 1):
        ang = deflexion_deg(puntos[i-1], puntos[i], puntos[i+1])
        tipo, _ret = clasificar_por_angulo(ang)
        H = demanda_horizontal_kN(tipo, T, args.fases, ang)
        resultados.append({
            "Punto": etiquetas[i],
            "Deflexión (°)": round(ang, 2),
            "Estructura": tipo,
            "H (kN)": round(H, 2),
            "T_guy (kN)": round(tension_retenida_kN(H), 2) if H > 0 else 0.0,
            "Cable Guy": cable_ret if H > 0 else "-",
            "Poste": args.poste,
            "Cap (kN)": Hmax,
            "Cumple": "SI" if H <= Hmax else "NO",
        })

    # Fin
    Hf = demanda_horizontal_kN("Remate", T, args.fases, 0.0)
    resultados.append({
        "Punto": etiquetas[-1],
        "Deflexión (°)": "-",
        "Estructura": "Remate",
        "H (kN)": round(Hf, 2),
        "T_guy (kN)": round(tension_retenida_kN(Hf), 2),
        "Cable Guy": cable_ret,
        "Poste": args.poste,
        "Cap (kN)": Hmax,
        "Cumple": "SI" if Hf <= Hmax else "NO",
    })

    tramos, total = distancias_tramos(puntos, etiquetas)

    meta = {
        "excel": args.excel,
        "calibre": args.calibre,
        "fases": args.fases,
        "poste": args.poste,
    }

    generar_reporte_pdf(
        out_pdf=args.out,
        meta=meta,
        tabla_resultados=resultados,
        tramos=tramos,
        puntos=puntos,
        etiquetas=etiquetas,
    )

    print(f"✅ PDF generado: {args.out}")

if __name__ == "__main__":
    main()

