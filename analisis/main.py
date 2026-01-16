# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
import os
import pandas as pd

from .catalogos import CONDUCTORES_ACSR, POSTES
from .io_excel import leer_puntos_xlsx, extraer_listas
from .geometria import deflexion, distancias_tramos, clasificar_estructura_por_angulo
from .mecanica import (
    tension_trabajo_kN, demanda_horizontal_H_kN, tension_retenida_kN,
    fila_resultado
)
from .perfil import analizar_perfil
from .reporte_pdf import generar_pdf

def resumen_resultados(resultados: list[dict]) -> str:
    n = len(resultados)
    n_ok = sum(1 for r in resultados if str(r.get("Cumple poste","")).upper() == "SI")
    n_no = n - n_ok
    n_ret = sum(1 for r in resultados if str(r.get("Solución","")).upper() == "RETENIDA")
    n_auto = sum(1 for r in resultados if str(r.get("Solución","")).upper() == "AUTOSOPORTADO")
    peor = max((float(r.get("Utiliz. poste (%)", 0)) for r in resultados), default=0.0)
    return f"Puntos={n} | Cumple={n_ok} | No cumple={n_no} | Retenida={n_ret} | Auto={n_auto} | Peor util={peor:.1f}%"

def correr(ruta_xlsx: str, calibre: str, n_fases: int, tipo_poste: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    df = leer_puntos_xlsx(ruta_xlsx)
    puntos, etiquetas, espacio = extraer_listas(df)

    # Distancias
    tramos, total_m = distancias_tramos(puntos, etiquetas)

    # Mecánica base
    T_work = tension_trabajo_kN(calibre)

    resultados: list[dict] = []

    # Inicio (remate)
    H0 = demanda_horizontal_H_kN("Remate", T_work, n_fases, 0.0)
    Tret0 = tension_retenida_kN(H0)
    resultados.append(fila_resultado(
        punto=etiquetas[0], defl="-", estructura="Remate", ret=1, espacio_ret=espacio[0],
        H_kN=H0, Tret_kN=Tret0, calibre=calibre, n_fases=n_fases, tipo_poste=tipo_poste
    ))

    # Intermedios
    for i in range(1, len(puntos)-1):
        ang = deflexion(puntos[i-1], puntos[i], puntos[i+1])
        estructura, ret = clasificar_estructura_por_angulo(ang)
        H = demanda_horizontal_H_kN(estructura, T_work, n_fases, ang)
        Tret = tension_retenida_kN(H)

        resultados.append(fila_resultado(
            punto=etiquetas[i], defl=round(ang,2), estructura=estructura, ret=ret, espacio_ret=espacio[i],
            H_kN=H, Tret_kN=Tret, calibre=calibre, n_fases=n_fases, tipo_poste=tipo_poste
        ))

    # Fin (remate)
    Hf = demanda_horizontal_H_kN("Remate", T_work, n_fases, 0.0)
    Tretf = tension_retenida_kN(Hf)
    resultados.append(fila_resultado(
        punto=etiquetas[-1], defl="-", estructura="Remate", ret=1, espacio_ret=espacio[-1],
        H_kN=Hf, Tret_kN=Tretf, calibre=calibre, n_fases=n_fases, tipo_poste=tipo_poste
    ))

    # Perfil (si hay Altitude)
    perfil = analizar_perfil(df, tipo_poste=tipo_poste, calibre=calibre, n_fases=n_fases)

    # Export XLSX
    df_res = pd.DataFrame(resultados)
    out_xlsx = os.path.join(out_dir, "resultados_analisis_mecanico.xlsx")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Entrada", index=False)
        df_res.to_excel(w, sheet_name="Resultados", index=False)
        pd.DataFrame(tramos, columns=["Tramo","Distancia(m)","Acumulado(m)"]).to_excel(w, sheet_name="Tramos", index=False)
        if perfil is not None:
            pd.DataFrame(perfil["tabla_vanos"]).to_excel(w, sheet_name="Perfil_Vanos", index=False)

    # PDF
    out_pdf = os.path.join(out_dir, "analisis_mecanico.pdf")
    resumen_linea = f"Conductor={calibre} | Fases={n_fases} | Poste={tipo_poste} | Total={total_m:,.2f} m | {resumen_resultados(resultados)}"
    generar_pdf(out_pdf, puntos, etiquetas, resultados, tramos, total_m, resumen_linea, perfil=perfil)

    return out_pdf, out_xlsx

def build_parser():
    p = argparse.ArgumentParser(description="Análisis mecánico de líneas (UTM) - Retenidas/Auto + PDF/XLSX")
    p.add_argument("--excel", required=True, help="Ruta a puntos.xlsx")
    p.add_argument("--conductor", required=True, choices=list(CONDUCTORES_ACSR.keys()), help="Calibre ACSR")
    p.add_argument("--fases", type=int, default=3, choices=[1,2,3], help="Número de fases")
    p.add_argument("--poste", required=True, choices=list(POSTES.keys()), help="Tipo de poste (ej. PC-40)")
    p.add_argument("--out", default="outputs", help="Carpeta de salida")
    return p

def main():
    args = build_parser().parse_args()
    out_pdf, out_xlsx = correr(args.excel, args.conductor, args.fases, args.poste, args.out)
    print(f"✅ PDF:  {out_pdf}")
    print(f"✅ XLSX: {out_xlsx}")

if __name__ == "__main__":
    main()
