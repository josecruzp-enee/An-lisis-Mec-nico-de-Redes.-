"""Cribado resistente TRAZABLE de postes por sección y caso de carga.

No se deducen resistencias de diámetros exteriores ni de las cargas de
rotura del catálogo. La hoja Capacidades aporta resistencias DE DISEÑO,
justificadas externamente, para cada sección evaluada.

La comprobación compara acciones individuales:
  |Mx|/Mx_Rd, |My|/My_Rd, |V|/V_Rd, |N|/N_Rd, |Mz|/Mz_Rd
No se supone una superficie de interacción axial-flexión-cortante-torsión.
Un cociente >1 identifica un exceso inequívoco del límite individual
declarado. Valores <=1 NO significan que el poste cumpla: quedan
interacciones, esbeltez, efectos de segundo orden, detalles, anclaje y suelo.

Los límites deben corresponder al MISMO método de diseño y combinaciones
que las acciones, documentados por el proyectista.
"""
from __future__ import annotations

import math
import pandas as pd
import numpy as np

from .validacion_mecanica import finito

COLUMNAS_CAPACIDADES = (
    "Punto", "Altura_corte_m", "Mx_Rd_kNm", "My_Rd_kNm",
    "V_Rd_kN", "N_Rd_kN", "Mz_Rd_kNm",
    "Fuente", "Criterio_diseno",
)
DEMANDAS = (
    ("Mx (kN·m)", "Mx_Rd_kNm"),
    ("My (kN·m)", "My_Rd_kNm"),
    ("V transversal (kN)", "V_Rd_kN"),
    ("N axial (kN)", "N_Rd_kN"),
    ("Mz (kN·m)", "Mz_Rd_kNm"),
)


def validar_capacidades(capacidades):
    """Cada punto y cota debe tener límites positivos y referencias."""
    if not isinstance(capacidades, pd.DataFrame) or capacidades.empty:
        raise ValueError("Hoja Capacidades vacía")
    faltan = [c for c in COLUMNAS_CAPACIDADES if c not in capacidades]
    if faltan:
        raise ValueError("Hoja Capacidades: faltan " + ", ".join(faltan))
    out = capacidades.copy()
    for c in ("Punto", "Fuente", "Criterio_diseno"):
        if out[c].isna().any() or out[c].astype(str).str.strip().isin(("", "nan")).any():
            raise ValueError(f"Capacidades: {c} no puede estar vacío")
        out[c] = out[c].astype(str).str.strip()
    for c in ("Altura_corte_m",) + tuple(col for _, col in DEMANDAS):
        out[c] = out[c].map(
            lambda x: finito(x,c,0,c!="Altura_corte_m")
        )
    if out.duplicated(["Punto", "Altura_corte_m"]).any():
        raise ValueError("Capacidades con secciones duplicadas")
    return out


def cribar_resistencia_postes(secciones, capacidades, *, tolerancia_cota_m=1e-5):
    """Compara SIN interpolar resistencias: empareja cada corte con su cota.

    Requiere todas las secciones para todos los apoyos que figuran en el
    cálculo. Sin cobertura completa se marca NO VERIFICABLE, nunca CUMPLE.
    """
    if secciones is None or not isinstance(secciones, pd.DataFrame) or secciones.empty:
        raise ValueError("No existen solicitaciones de secciones")
    limites = validar_capacidades(capacidades)
    t = finito(tolerancia_cota_m, "tolerancia de cota", 0, True)
    requeridas = ["Punto", "Caso", "Altura corte (m)", "Estado sección"]
    requeridas += [d for d,_ in DEMANDAS]
    faltan = [c for c in requeridas if c not in secciones]
    if faltan:
        raise ValueError("Solicitaciones: faltan columnas " + ", ".join(faltan))
    registros = []
    for _, fila in secciones.iterrows():
        punto = str(fila["Punto"])
        base = {"Punto":punto, "Caso":fila["Caso"],
                "Altura corte (m)":fila.get("Altura corte (m)"),
                "Estado resistencia":"NO VERIFICABLE",
                "Ratio máximo individual":float("nan"),
                "Magnitud gobernante":None,
                "Fuente":None,
                "Criterio_diseno":None}
        if fila["Estado sección"] != "SOLICITACIÓN, RESISTENCIA NO VERIFICABLE":
            base["Motivo"] = "Sin geometría o solicitación completa"
            registros.append(base)
            continue
        z = finito(fila["Altura corte (m)"],"altura de corte",0)
        candidatas = limites.loc[
            (limites["Punto"]==punto)
            & (np.abs(limites["Altura_corte_m"]-z)<=t)
        ]
        if candidatas.empty:
            base["Motivo"] = "Sin capacidad documentada en esta sección"
            registros.append(base)
            continue
        if len(candidatas)>1:
            raise ValueError(
                f"{punto}/{z:g} m: varias capacidades dentro de tolerancia"
            )
        limite = candidatas.iloc[0]
        ratios={}
        for demanda,capacidad in DEMANDAS:
            valor=finito(fila[demanda],demanda)
            ratio=abs(valor)/float(limite[capacidad])
            ratios[demanda]=ratio
            base[f"Ratio {demanda}"]=ratio
        peor=max(ratios,key=ratios.get)
        maximo=ratios[peor]
        base.update({
            "Ratio máximo individual":maximo,
            "Magnitud gobernante":peor,
            "Fuente":limite["Fuente"],
            "Criterio_diseno":limite["Criterio_diseno"],
            "Estado resistencia": (
                "EXCEDE LÍMITE INDIVIDUAL DOCUMENTADO"
                if maximo>1+1e-9 else
                "EN RANGO INDIVIDUAL; INTERACCIÓN NO VERIFICADA"
            ),
            "Motivo": (
                "La demanda supera un límite de diseño declarado"
                if maximo>1+1e-9 else
                "Faltan interacciones, estabilidad y verificaciones complementarias"
            ),
        })
        registros.append(base)
    return pd.DataFrame(registros)


def resumen_resistencia_postes(cribado):
    """El resultado por poste retiene el caso crítico real y cobertura."""
    if cribado is None or cribado.empty:
        raise ValueError("No hay cribado resistente")
    filas=[]
    for punto, grupo in cribado.groupby("Punto",sort=False):
        pendiente=grupo["Estado resistencia"].eq("NO VERIFICABLE").sum()
        excedidas=grupo["Estado resistencia"].eq(
            "EXCEDE LÍMITE INDIVIDUAL DOCUMENTADO"
        ).sum()
        validas=grupo.loc[grupo["Ratio máximo individual"].notna()]
        peor=validas.loc[validas["Ratio máximo individual"].idxmax()] if not validas.empty else None
        estado = (
            "EXCEDE LÍMITE INDIVIDUAL DOCUMENTADO" if excedidas else
            "NO VERIFICABLE — FALTAN SECCIONES" if pendiente else
            "INTERACCIÓN Y ESTABILIDAD PENDIENTES"
        )
        filas.append({
            "Punto":punto,
            "Estados-sección examinados":len(grupo),
            "Sin capacidad documentada":int(pendiente),
            "Secciones-caso con exceso":int(excedidas),
            "Ratio individual crítico": (
                float(peor["Ratio máximo individual"]) if peor is not None
                else float("nan")
            ),
            "Caso gobernante":peor["Caso"] if peor is not None else None,
            "Altura crítica (m)": (
                peor["Altura corte (m)"] if peor is not None else None
            ),
            "Magnitud crítica": (
                peor["Magnitud gobernante"] if peor is not None else None
            ),
            "Estado":estado,
        })
    return pd.DataFrame(filas)
