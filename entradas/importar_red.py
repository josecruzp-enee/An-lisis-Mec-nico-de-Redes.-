"""Importación EXPLÍCITA de red mecánica multicircuito desde Excel.

La hoja Puntos contiene apoyos y geometría de terreno.
La hoja Vanos declara cada conexión mecánica. No se deduce continuidad
por estar sobre la misma línea ni por el número de postes.

Columnas Puntos:
 Punto, X, Y, Altitud, Poste, Fijacion
Columnas Vanos:
 Vano, Inicio, Fin, Circuito, Seccion, Conductor,
 Conexion_Inicio, Conexion_Fin, Altura_Inicio_m, Altura_Fin_m

La rigidez de postes móviles y propiedades de conductores se suministran
en un contrato separado y verificable, nunca se inventan aquí.
"""
from __future__ import annotations

import pandas as pd

from entradas.io_excel import leer_puntos_excel
from calculos.modelo_red import RedMecanica


COLUMNAS_VANOS = (
    "Vano","Inicio","Fin","Circuito","Seccion","Conductor",
    "Conexion_Inicio","Conexion_Fin","Altura_Inicio_m","Altura_Fin_m",
)


def leer_red_excel(archivo):
    """Carga y valida la topología desde dos hojas, sin unir vanos por heurística."""
    libro=pd.ExcelFile(archivo)
    if "Puntos" not in libro.sheet_names or "Vanos" not in libro.sheet_names:
        raise ValueError("El libro mecánico requiere hojas 'Puntos' y 'Vanos'")
    puntos=leer_puntos_excel(libro.parse("Puntos"))
    if "Altitud" not in puntos or puntos["Altitud"].isna().any():
        raise ValueError("Cada apoyo requiere cota Altitud")
    if "Fijacion" not in puntos or puntos["Fijacion"].isna().any():
        raise ValueError(
            "Cada apoyo requiere Fijacion explícita (FIJO o MOVIL); "
            "no se presupone que el poste sea rígido"
        )
    if puntos["Poste"].astype(str).str.strip().eq("").any():
        raise ValueError("Cada apoyo requiere un identificador de Poste")
    datos=libro.parse("Vanos")
    faltan=[c for c in COLUMNAS_VANOS if c not in datos.columns]
    if faltan:
        raise ValueError("Hoja Vanos: faltan columnas "+", ".join(faltan))
    if datos.empty or datos[list(COLUMNAS_VANOS)].isna().any().any():
        raise ValueError("Hoja Vanos: contiene celdas requeridas vacías")
    apoyos=[]
    for _,r in puntos.iterrows():
        fijacion=str(r["Fijacion"]).strip().upper()
        apoyos.append({
            "nombre":str(r["Punto"]),
            "base_m":(float(r["X"]),float(r["Y"]),float(r["Altitud"])),
            "modelo_apoyo":str(r["Poste"]) if str(r["Poste"]).strip() else "SIN MODELO",
            "fijacion":fijacion,
        })
    vanos=[]
    for _,r in datos.iterrows():
        vanos.append({
            "nombre":str(r["Vano"]).strip(),
            "origen":str(r["Inicio"]).strip(),
            "destino":str(r["Fin"]).strip(),
            "circuito":str(r["Circuito"]).strip(),
            "seccion_tendido":str(r["Seccion"]).strip(),
            "conductor":str(r["Conductor"]).strip(),
            "conexion_origen":str(r["Conexion_Inicio"]).strip().upper(),
            "conexion_destino":str(r["Conexion_Fin"]).strip().upper(),
            "amarre_origen_m":(0,0,float(r["Altura_Inicio_m"])),
            "amarre_destino_m":(0,0,float(r["Altura_Fin_m"])),
        })
    return RedMecanica.desde_registros(apoyos,vanos)
