"""Aplicar configuraciones XYZ de retenidas a todos los estados de un poste.

El barrido utiliza la demanda completa de fuerza y momento previamente
calculada; no combina máximos de condiciones diferentes.

La solución de retenidas representa factibilidad estática de MOMENTO con
cables unilaterales y puntos de anclaje explícitos, NO reparto real por
rigidez y pretensión ni verificación de anclajes / cimentación.
"""
from __future__ import annotations

from collections import defaultdict
import math

import numpy as np
import pandas as pd

from .retenidas_xyz import RetenidaXYZ, estudiar_equilibrio_retenidas


COLUMNAS_RETENIDAS = (
    "Punto", "Retenida",
    "Amarre_X_m", "Amarre_Y_m", "Amarre_Z_m",
    "Anclaje_X_m", "Anclaje_Y_m", "Anclaje_Z_m",
)


def leer_configuraciones_retenidas(datos):
    """Coordenadas locales respecto a la base del poste (m), Z arriba."""
    if not isinstance(datos, pd.DataFrame):
        raise ValueError("Retenidas debe ser una tabla")
    faltan = [k for k in COLUMNAS_RETENIDAS if k not in datos.columns]
    if faltan:
        raise ValueError("Faltan columnas Retenidas: " + ", ".join(faltan))
    if datos[list(COLUMNAS_RETENIDAS)].isna().any().any():
        raise ValueError("Coordenadas o identificadores de retenida incompletos")
    grupos=defaultdict(list)
    for _,r in datos.iterrows():
        punto=str(r["Punto"]).strip()
        if not punto or punto=="nan":
            raise ValueError("Retenida sin punto")
        limite=None
        fuente=""
        if "T_limite_kN" in datos and not pd.isna(r["T_limite_kN"]):
            limite=float(r["T_limite_kN"])
            fuente=str(r.get("Fuente_limite","")).strip()
        g=RetenidaXYZ(
            nombre=str(r["Retenida"]).strip(),
            amarre_m=tuple(float(r[k]) for k in (
                "Amarre_X_m","Amarre_Y_m","Amarre_Z_m")),
            anclaje_m=tuple(float(r[k]) for k in (
                "Anclaje_X_m","Anclaje_Y_m","Anclaje_Z_m")),
            tension_limite_kN=limite,
            fuente_limite=fuente,
        )
        if any(x.nombre==g.nombre for x in grupos[punto]):
            raise ValueError(f"{punto}: retenidas duplicadas")
        grupos[punto].append(g)
    return dict(grupos)


def evaluar_retenidas_en_barrido(acciones, configuraciones,
                                tolerancia_momento_kNm=1e-4):
    """Retorna demanda por retenida y estado completo, sin aprobar estructuras."""
    if acciones is None or acciones.empty:
        raise ValueError("No hay acciones mecánicas")
    req=("Punto","Caso","Fx (kN)","Fy (kN)","Fz (kN)",
         "Mx (kN·m)","My (kN·m)","Mz (kN·m)")
    falta=[k for k in req if k not in acciones]
    if falta:
        raise ValueError("Faltan acciones: "+", ".join(falta))
    puntos=set(acciones["Punto"].astype(str))
    desconocidos=set(configuraciones)-puntos
    if desconocidos:
        raise ValueError(
            "Retenidas asignadas a puntos no calculados: "
            + ", ".join(sorted(desconocidos))
        )
    filas,detalles=[],[]
    for _,fila in acciones.iterrows():
        punto=str(fila["Punto"])
        if punto not in configuraciones:
            continue
        f=np.array([fila[k] for k in ("Fx (kN)","Fy (kN)","Fz (kN)")],float)
        m=np.array([fila[k] for k in ("Mx (kN·m)","My (kN·m)","Mz (kN·m)")],float)
        if not np.isfinite(f).all() or not np.isfinite(m).all():
            raise ValueError(f"{punto}/{fila['Caso']}: acciones no finitas")
        e=estudiar_equilibrio_retenidas(
            f,m,configuraciones[punto],
            tolerancia_momento_kNm=tolerancia_momento_kNm,
        )
        filas.append({
            "Punto":punto,"Caso":fila["Caso"],
            "Equilibrio momento":("FACTIBLE" if e.equilibrio_momentos
                                else "INSUFICIENTE"),
            "Residual momento (kN·m)":e.residual_momento_kNm,
            "Fx base (kN)":float(e.fuerza_resultante_base_kN[0]),
            "Fy base (kN)":float(e.fuerza_resultante_base_kN[1]),
            "Fz base (kN)":float(e.fuerza_resultante_base_kN[2]),
            "Capacidades documentadas":e.capacidades_documentadas,
            "Estado":"FACTIBILIDAD ESTÁTICA; NO VERIFICABLE",
        })
        for nombre,tension in e.tensiones_kN.items():
            detalles.append({
                "Punto":punto,"Caso":fila["Caso"],
                "Retenida":nombre,"Tensión solicitada (kN)":tension,
                "Estado":"NO VERIFICABLE — faltan compatibilidad y anclaje",
            })
    return pd.DataFrame(filas),pd.DataFrame(detalles)
