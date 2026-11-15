"""Contrato Excel para ejecutar una red mecánica sin propiedades ficticias.

Puntos/Vanos se leen mediante importar_red. Las hojas adicionales
Materiales e Hipotesis no inventan propiedades ni límites normativos.
Los resultados son solicitaciones, no aprobación de estructuras.
"""
from __future__ import annotations
import pandas as pd
from calculos.validacion_mecanica import finito

COLUMNAS_MATERIALES=(
    "Conductor","Peso_kN_m","Diametro_m","EA_kN","Alpha_por_C",
    "H_tendido_kN","Temperatura_tendido_C","Fuente",
)
COLUMNAS_ESTADOS=("Hipotesis","Temperatura_C","Viento_ms","Azimut_deg")


def leer_materiales_excel(datos, nombres_conductores):
    if not isinstance(datos,pd.DataFrame) or datos.empty:
        raise ValueError("Hoja Materiales requerida")
    faltan=[c for c in COLUMNAS_MATERIALES if c not in datos]
    if faltan:
        raise ValueError("Hoja Materiales: faltan columnas "+", ".join(faltan))
    if datos[list(COLUMNAS_MATERIALES)].isna().any().any():
        raise ValueError("Hoja Materiales: no se permiten vacíos")
    materiales={}
    for _,r in datos.iterrows():
        nombre=str(r["Conductor"]).strip()
        fuente=str(r["Fuente"]).strip()
        if not nombre or not fuente or nombre in materiales:
            raise ValueError("Conductor o fuente vacíos, o conductor duplicado")
        materiales[nombre]={
            "peso_kN_m":finito(r["Peso_kN_m"],"peso",0,True),
            "diametro_m":finito(r["Diametro_m"],"diámetro",0,True),
            "EA_kN":finito(r["EA_kN"],"EA",0,True),
            "alpha_por_C":finito(r["Alpha_por_C"],"alpha"),
            "H_tendido_kN":finito(r["H_tendido_kN"],"H tendido",0,True),
            "temperatura_tendido_C":finito(r["Temperatura_tendido_C"],"T tendido"),
            "fuente":fuente,
        }
    faltantes=set(nombres_conductores)-set(materiales)
    if faltantes:
        raise ValueError("Faltan materiales de conductor: "+", ".join(sorted(faltantes)))
    return materiales


def leer_estados_excel(datos):
    if not isinstance(datos,pd.DataFrame) or datos.empty:
        raise ValueError("Hoja Hipotesis requerida")
    faltan=[c for c in COLUMNAS_ESTADOS if c not in datos]
    if faltan:
        raise ValueError("Hoja Hipotesis: faltan columnas "+", ".join(faltan))
    estados=datos[list(COLUMNAS_ESTADOS)].copy()
    if estados.isna().any().any():
        raise ValueError("Hoja Hipotesis: campos vacíos")
    estados["Hipotesis"]=estados["Hipotesis"].astype(str).str.strip()
    if estados["Hipotesis"].eq("").any() or estados["Hipotesis"].duplicated().any():
        raise ValueError("Hipótesis vacías o duplicadas")
    for c,minimo in (("Temperatura_C",None),("Viento_ms",0),("Azimut_deg",None)):
        estados[c]=[finito(v,c,minimo) for v in estados[c]]
    return estados
