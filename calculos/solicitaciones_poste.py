"""Solicitaciones 6D en la sección de terreno del poste.

Suma acciones de conductores (en puntos de amarre) y arrastre distribuido
sobre el fuste cónico. El viento del poste se integra analíticamente:
q(z)=0.5*rho*Cd*v²*D(z)/1000 [kN/m], con D lineal en z.

No calcula resistencia del concreto, pandeo, anclajes ni rigidez del terreno.
La reacción del terreno es OPUESTA a estas acciones externas.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from entradas.norma_postes import obtener_ficha_poste
from .validacion_mecanica import finito


def geometria_fuste(tipo_poste, empotramiento_m=None):
    """Geometría exterior catalogada, más empotramiento explícito/estimado."""
    ficha = obtener_ficha_poste(str(tipo_poste))
    campos = ("longitud_m", "diam_base_cm", "diam_punta_cm")
    if any(c not in ficha for c in campos):
        return None
    longitud = finito(ficha["longitud_m"], "longitud poste", 0, True)
    db = finito(ficha["diam_base_cm"], "diámetro base", 0, True)/100
    dt = finito(ficha["diam_punta_cm"], "diámetro punta", 0, True)/100
    if dt > db:
        raise ValueError("Diámetro de punta superior al diámetro de base")
    if empotramiento_m is None or pd.isna(empotramiento_m):
        # Regla de enterramiento aportada para el proyecto: 0.1 L(ft) + 2 ft.
        e = 0.1*longitud + 0.6096
        origen = "ESTIMADO: 10% longitud + 2 pies"
    else:
        e = finito(empotramiento_m, "empotramiento", 0, True)
        origen = "EXPLÍCITO EXCEL"
    if e >= longitud:
        raise ValueError("Empotramiento no puede superar longitud total")
    altura = longitud-e
    diametro_terreno = db+(dt-db)*e/longitud
    return {
        "Tipo poste": str(tipo_poste),
        "Altura expuesta (m)": altura,
        "Empotramiento (m)": e,
        "Diámetro terreno (m)": diametro_terreno,
        "Diámetro punta (m)": dt,
        "Origen empotramiento": origen,
        "Fuente geometría": ficha["fuente"],
    }


def viento_fuste(geometria, velocidad_ms, azimut_deg, rho_kg_m3=1.225, Cd_poste=1.2):
    """Resultante y momentos al nivel del terreno (kN, kN m).

    El fuste se idealiza circular con diámetro variable linealmente.
    Cd es editable; no se afirma que sea coeficiente normativo.
    """
    v=finito(velocidad_ms,"viento",0)
    az=finito(azimut_deg,"azimut")
    rho=finito(rho_kg_m3,"densidad",0,True)
    cd=finito(Cd_poste,"Cd poste",0,True)
    h=geometria["Altura expuesta (m)"]
    d0=geometria["Diámetro terreno (m)"]
    d1=geometria["Diámetro punta (m)"]
    presion=0.5*rho*cd*v*v/1000
    fuerza=presion*h*(d0+d1)/2
    momento=presion*h*h*(d0+2*d1)/6
    theta=math.radians(az)
    fx,fy=fuerza*math.cos(theta),fuerza*math.sin(theta)
    return np.array([fx,fy,0.,-momento*math.sin(theta),
                     momento*math.cos(theta),0.])


def combinar_solicitaciones_postes(nodos, postes, *, rho_kg_m3=1.225,
                                  Cd_poste=1.2):
    """Acciones externas totales en terreno por caso.

    Devuelve también evidencia de datos ausentes. Si falta geometría,
    las acciones del conductor se conservan, pero el total del poste
    se marca INCOMPLETO y no se publica como resultado total.
    """
    if nodos is None or nodos.empty:
        raise ValueError("No hay solicitaciones de conductores")
    if "Punto" not in postes or "Poste" not in postes:
        raise ValueError("Excel sin Punto o Poste")
    fichas = {}
    for _, item in postes.iterrows():
        punto=str(item["Punto"])
        if punto in fichas:
            raise ValueError("Poste duplicado: "+punto)
        e=item["Empotramiento_m"] if "Empotramiento_m" in postes else None
        fichas[punto]=geometria_fuste(item["Poste"], e)
    columnas=("Fx (kN)","Fy (kN)","Fz (kN)",
              "Mx (kN·m)","My (kN·m)","Mz (kN·m)")
    salida=[]
    for _, fila in nodos.iterrows():
        punto=str(fila["Punto"])
        if punto not in fichas:
            raise ValueError("Poste no encontrado: "+punto)
        registro=fila.to_dict()
        registro["Acciones de conductor Fx (kN)"]=fila["Fx (kN)"]
        registro["Acciones de conductor Fy (kN)"]=fila["Fy (kN)"]
        registro["Acciones de conductor Mx (kN·m)"]=fila["Mx (kN·m)"]
        registro["Acciones de conductor My (kN·m)"]=fila["My (kN·m)"]
        geometria=fichas[punto]
        if geometria is None:
            for col in columnas:
                registro[col]=float("nan")
            registro["Estado viento poste"]="INCOMPLETO: geometría no catalogada"
            registro["Origen empotramiento"]="NO VERIFICABLE"
        else:
            carga=viento_fuste(
                geometria,float(fila["Viento (m/s)"]),
                float(fila["Azimut viento (°)"]),
                rho_kg_m3=rho_kg_m3,Cd_poste=Cd_poste)
            for index,col in enumerate(columnas):
                registro[col]=float(fila[col])+float(carga[index])
            registro["Estado viento poste"]="INCLUIDO: fuste cónico idealizado"
            registro["Origen empotramiento"]=geometria["Origen empotramiento"]
        registro["H resultante (kN)"]=math.hypot(
            registro["Fx (kN)"],registro["Fy (kN)"])
        registro["M resultante (kN·m)"]=math.hypot(
            registro["Mx (kN·m)"],registro["My (kN·m)"])
        registro["Estado"]="SOLICITACIÓN, NO VERIFICABLE"
        salida.append(registro)
    return pd.DataFrame(salida)
