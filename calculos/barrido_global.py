"""Barrido de estados sobre un ensamblador GLOBAL de red mecánica.

Un caso completo se resuelve desde las mismas condiciones de referencia.
NO se interpolan componentes ni se construyen vectores combinando máximos
de casos diferentes. La topología no admitida por el solver genera error.

Sólo válido para el subconjunto físico permitido por ensamblador_global.py:
conexiones ANCLAJE/FIJA y apoyos FIJO/MOVIL con rigidez traslacional.
"""
from __future__ import annotations

from dataclasses import replace
import math

import pandas as pd

from .ensamblador_global import resolver_equilibrio_global
from .validacion_mecanica import finito


def _lista(valores,nombre,positivo=False):
    if not valores:
        raise ValueError(f"{nombre}: lista vacía")
    return [
        finito(v,nombre,0,True) if positivo else finito(v,nombre)
        for v in valores
    ]


def barrido_red_global(
    red, materiales, *, temperaturas_C,
    tensiones_iniciales_kN, direcciones_viento_deg,
    viento_min_ms, viento_max_ms, incremento_ms=1,
    rigideces=None, fuerzas_adicionales=None,
    rho_kg_m3=1.225,Cd=1.2,limite_casos=100,
):
    """Evalúa la red completa soportada para todas las combinaciones."""
    from calculos.barrido_3d import _secuencia_viento

    temperaturas=_lista(temperaturas_C,"temperaturas")
    tensiones=_lista(tensiones_iniciales_kN,"tensiones",True)
    direcciones=_lista(direcciones_viento_deg,"direcciones")
    velocidades=_secuencia_viento(viento_min_ms,viento_max_ms,incremento_ms)
    cantidad=len(temperaturas)*len(tensiones)*len(direcciones)*len(velocidades)
    if cantidad>limite_casos:
        raise ValueError(
            f"{cantidad} casos superan el máximo {limite_casos}. "
            "Divida el cálculo en lotes reproducibles."
        )
    nodos=[];vanos=[];estados=[]
    for H in tensiones:
        # H inicial se aplica a cada conductor solo como condición de estudio.
        # Propiedades originales quedan inmutables.
        propiedades={
            nombre:{**ficha,"H_tendido_kN":H}
            for nombre,ficha in materiales.items()
        }
        for T in temperaturas:
            for az in direcciones:
                for v in velocidades:
                    caso=f"H0={H:g};T={T:g};V={v:g};Az={az:g}"
                    res=resolver_equilibrio_global(
                        red,propiedades,
                        temperatura_C=T,viento_ms=v,azimut_deg=az,
                        rigideces=rigideces,
                        fuerzas_adicionales=fuerzas_adicionales,
                        rho_kg_m3=rho_kg_m3,Cd=Cd,
                    )
                    estados.append({
                        "Caso":caso,"Viento (m/s)":v,
                        "Temperatura (°C)":T,
                        "H inicial (kN)":H,
                        "Azimut (°)":az,
                        "Residual máximo global (kN)":res.residual_max_kN,
                        "Evaluaciones":res.iteraciones,
                        "Estado":res.estado,
                    })
                    for nombre in red.apoyos:
                        f=res.fuerzas_conductor_kN[nombre]
                        u=res.desplazamientos_m[nombre]
                        reaccion=res.reacciones_anclajes_kN.get(nombre)
                        nodos.append({
                            "Caso":caso,"Punto":nombre,
                            "Fx conductores (kN)":float(f[0]),
                            "Fy conductores (kN)":float(f[1]),
                            "Fz conductores (kN)":float(f[2]),
                            "ux (m)":float(u[0]),"uy (m)":float(u[1]),
                            "uz (m)":float(u[2]),
                            "Reacción X (kN)":float(reaccion[0]) if reaccion is not None else None,
                            "Reacción Y (kN)":float(reaccion[1]) if reaccion is not None else None,
                            "Reacción Z (kN)":float(reaccion[2]) if reaccion is not None else None,
                        })
                    for nombre,cable in res.vanos.items():
                        vanos.append({
                            "Caso":caso,"Vano":nombre,
                            "Tensión máxima (kN)":cable.tension_maxima_kN,
                            "Longitud deformada (m)":cable.longitud_deformada_m,
                            "Residual equilibrio vano (kN)":cable.residual_equilibrio_kN,
                            "Residual frontera vano (m)":cable.residual_frontera_m,
                        })
    return {
        "estados":pd.DataFrame(estados),
        "apoyos":pd.DataFrame(nodos),
        "vanos":pd.DataFrame(vanos),
        "modelo":"RED GLOBAL: traslaciones + cables BVP; dominio restringido",
    }
