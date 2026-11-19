"""Comparación multivano con guías deslizantes ideales usando el BVP existente.

NO confundir con las espigas fijas de la tabla de diseño CFE.
La referencia final H50 procede del optimizador de la corrida por vano.
Las guías deslizantes no equivalen a suspensión ENEE sin identificar herrajes.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.calculos.modelo_red import RedMecanica
from Analisis_mecanico_conductores.tension_tendido.resolver_seccion_deslizante_ideal import (
    resolver_seccion_deslizante,
)


def construir_red_deslizante_de_puntos(puntos, conductor):
    """P1 y Pn anclados; intermedios deslizantes IDEALES explícitos."""
    if len(puntos)<3:
        raise ValueError("La comparación deslizante requiere al menos tres apoyos")
    req=("Punto","X","Y","Altitud","Altura_Amarre_m")
    if any(c not in puntos for c in req) or puntos[list(req)].isna().any().any():
        raise ValueError("Completar cotas del terreno y alturas de amarre de todos los apoyos")
    nodos=[]
    for _,r in puntos.iterrows():
        nodos.append(dict(
            nombre=str(r["Punto"]),
            base_m=(float(r["X"]),float(r["Y"]),float(r["Altitud"])),
            modelo_apoyo="FIJO_GEOMETRICAMENTE; NO VERIFICADO ENEE",
            fijacion="FIJO",
        ))
    vanos=[]
    for i in range(len(puntos)-1):
        a,b=puntos.iloc[i],puntos.iloc[i+1]
        vanos.append(dict(
            nombre=str(a["Punto"])+" → "+str(b["Punto"]),
            origen=str(a["Punto"]),destino=str(b["Punto"]),
            circuito="C1",seccion_tendido="S1",conductor=conductor,
            amarre_origen_m=(0.,0.,float(a["Altura_Amarre_m"])),
            amarre_destino_m=(0.,0.,float(b["Altura_Amarre_m"])),
            conexion_origen="ANCLAJE" if i==0 else "DESLIZANTE",
            conexion_destino="ANCLAJE" if i==len(puntos)-2 else "DESLIZANTE",
        ))
    return RedMecanica.desde_registros(nodos,vanos)


def calcular_comparacion_multivano_final(puntos, ficha_final, H50_kN,
                                        *, temperaturas_C=(50.,16.,0.),
                                        viento_ms=0., azimut_deg=90.,
                                        Cd=1.,rho_kg_m3=1.225):
    """Resuelve longitud natural TOTAL y continuidad de tensiones en apoyos.

    No optimiza nuevamente H50; compara la misma referencia del cálculo CFE
    fijo, con otro tipo físico de conexión. Rechaza falta de convergencia.
    """
    conductor=str(ficha_final["nombre"]).upper()
    red=construir_red_deslizante_de_puntos(puntos,conductor)
    material={conductor:{
        "peso_kN_m":float(ficha_final["peso_kN_m"]),
        "diametro_m":float(ficha_final["diametro_m"]),
        "EA_kN":float(ficha_final["EA_kN"]),
        "alpha_por_C":float(ficha_final["alpha_por_C"]),
        "H_tendido_kN":float(H50_kN),
        "temperatura_tendido_C":50.,
        "fuente":str(ficha_final["fuente"]),
    }}
    filas=[]
    for T in temperaturas_C:
        resultado=resolver_seccion_deslizante(
            red,materiales=material,circuito="C1",seccion="S1",
            temperatura_C=float(T),viento_ms=float(viento_ms),
            azimut_deg=float(azimut_deg),
            rho_kg_m3=float(rho_kg_m3),Cd=float(Cd),
        )
        if resultado.residual_max_kN>1e-4:
            raise ValueError("No se satisfizo continuidad de tensión en apoyo")
        for vano,cable in resultado.vanos.items():
            v=red.vanos[vano]
            a=np.asarray(red.apoyos[v.origen].base_m)+np.asarray(v.amarre_origen_m)
            b=np.asarray(red.apoyos[v.destino].base_m)+np.asarray(v.amarre_destino_m)
            u=np.linspace(0.,1.,501)
            cable_xyz=cable.puntos(u)
            cuerda=a[None,:]+u[:,None]*(b-a)[None,:]
            vertical=np.maximum(cuerda[:,2]-cable_xyz[:,2],0.)
            horizontal=np.linalg.norm(cable_xyz[:,:2]-cuerda[:,:2],axis=1)
            filas.append({
                "Condición":"Final — guía deslizante ideal",
                "Vano":vano,
                "Temperatura (°C)":float(T),
                "Viento (m/s)":float(viento_ms),
                "Flecha vertical (m)":float(vertical.max()),
                "Desplazamiento XY cuerda (m)":float(horizontal.max()),
                "T máx. (kN)":float(cable.tension_maxima_kN),
                "Continuidad residual máx. (kN)":float(resultado.residual_max_kN),
                "Longitud natural total sección (m)":
                    float(resultado.longitud_natural_total_m),
                "Estado":resultado.estado,
            })
    return pd.DataFrame(filas)
