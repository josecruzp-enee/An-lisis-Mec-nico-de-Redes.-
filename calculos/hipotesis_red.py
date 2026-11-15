"""Resultados completos por vano y apoyo de una red con conexión EXPLÍCITA.

Usa el ensamblador global 3D existente en cada hipótesis climática; no
aproxima ni reinterpreta la unión. Para FIJA/ANCLAJE, cada tramo tiene
longitud natural retenida. Para DESLIZANTE conserva el total y equilibra
la tensión. SUSPENSION de grapa real sigue estrictamente prohibida.

Las flechas se buscan sobre el interpolador BVP continuo. Se entregan
reacciones vectoriales por apoyo y la hipótesis física que gobierna.
NO se aprueba resistencia del poste ni libramiento frente a terreno.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .ensamblador_global import resolver_equilibrio_global
from .barrido_no_lineal_3d import _extremo_minimo
from .modelo_red import RedMecanica
from .validacion_mecanica import finito


COLUMNAS_HIPOTESIS=("Hipotesis","Temperatura_C","Viento_ms","Azimut_deg")


def _flecha_y_punto(cable, a, b):
    """Flecha en Z respecto de cuerda proyectada sobre planta y ubicación 3D."""
    d=b-a
    d2=float(d[:2]@d[:2])
    if d2<=1e-12:
        raise ValueError("Vano sin proyección horizontal: flecha no definida")
    def relativa(u):
        p=cable.puntos(u)
        posicion=float((p[:2]-a[:2])@d[:2]/d2)
        return float(p[2]-a[2]-posicion*d[2])
    negativo,u=_extremo_minimo(cable,relativa)
    return max(0.,-negativo),cable.puntos(u)


def calcular_hipotesis_red(
    red:RedMecanica, materiales, hipotesis:pd.DataFrame, *,
    rigideces=None, fuerzas_adicionales=None,
    Cd=1.2, rho_kg_m3=1.225,
    tolerancia_bvp=1e-5,
):
    """Entrega tablas auditable de cargas, vanos y secciones para una red.

    Una fila de hipótesis es una COMBINACIÓN SIMULTÁNEA de T, viento
    y azimut; no se combinan envolventes independientes.
    """
    if not isinstance(red,RedMecanica):
        raise ValueError("Se necesita una red mecánica explícita")
    red.validar()
    if not isinstance(hipotesis,pd.DataFrame) or hipotesis.empty:
        raise ValueError("Sin hipótesis climáticas")
    faltan=[x for x in COLUMNAS_HIPOTESIS if x not in hipotesis]
    if faltan:
        raise ValueError("Faltan columnas: "+", ".join(faltan))
    if hipotesis[list(COLUMNAS_HIPOTESIS)].isna().any().any():
        raise ValueError("Hipótesis climáticas incompletas")
    nombres=hipotesis["Hipotesis"].astype(str).str.strip()
    if nombres.eq("").any() or nombres.duplicated().any():
        raise ValueError("Hipótesis con nombres vacíos o duplicados")
    if any(n.fijacion=="MOVIL" for n in red.apoyos.values()) and not rigideces:
        raise ValueError("Apoyos MOVIL requieren rigidez documentada")
    t_vanos=[]
    t_apoyos=[]
    t_secciones=[]
    for _,h in hipotesis.iterrows():
        caso=str(h["Hipotesis"]).strip()
        temp=finito(h["Temperatura_C"],"temperatura")
        viento=finito(h["Viento_ms"],"viento",0)
        rumbo=finito(h["Azimut_deg"],"azimut")
        try:
            res=resolver_equilibrio_global(
                red,materiales,temperatura_C=temp,
                viento_ms=viento,azimut_deg=rumbo,
                rigideces=rigideces,fuerzas_adicionales=fuerzas_adicionales,
                Cd=Cd,rho_kg_m3=rho_kg_m3,tolerancia_bvp=tolerancia_bvp,
            )
        except ValueError as exc:
            raise ValueError(f"Hipótesis {caso}: {exc}") from exc
        for nombre,cable in res.vanos.items():
            vano=red.vanos[nombre]
            a=np.asarray(red.apoyos[vano.origen].base_m,dtype=float)+vano.amarre_origen_m
            b=np.asarray(red.apoyos[vano.destino].base_m,dtype=float)+vano.amarre_destino_m
            a=a+res.desplazamientos_m[vano.origen]
            b=b+res.desplazamientos_m[vano.destino]
            flecha,p=_flecha_y_punto(cable,a,b)
            t_vanos.append({
                "Hipótesis":caso,"Circuito":vano.circuito,
                "Sección":vano.seccion_tendido,"Vano":nombre,
                "Inicio":vano.origen,"Fin":vano.destino,
                "Conexión inicio":vano.conexion_origen,
                "Conexión fin":vano.conexion_destino,
                "Luz horizontal (m)":float(np.linalg.norm((b-a)[:2])),
                "Desnivel amarres (m)":float(b[2]-a[2]),
                "Temperatura (°C)":temp,"Viento (m/s)":viento,
                "Azimut (°)":rumbo,
                "T máxima (kN)":cable.tension_maxima_kN,
                "T extremo A (kN)":float(np.linalg.norm(cable.fuerza_a)),
                "T extremo B (kN)":float(np.linalg.norm(cable.fuerza_b)),
                "Flecha vertical sobre cuerda (m)":flecha,
                "X flecha (m)":float(p[0]),"Y flecha (m)":float(p[1]),
                "Z flecha (m)":float(p[2]),
                "Longitud cable (m)":cable.longitud_deformada_m,
                "Residual equilibrio BVP (kN)":cable.residual_equilibrio_kN,
                "Fuente material":materiales[vano.conductor]["fuente"],
                "Modelo":"BVP 3D + unión explícita; sin resistencia del poste",
            })
        for nombre in red.apoyos:
            f=res.fuerzas_conductor_kN[nombre]
            reaccion=res.reacciones_anclajes_kN.get(nombre)
            despl=res.desplazamientos_m[nombre]
            t_apoyos.append({
                "Hipótesis":caso,"Apoyo":nombre,"Temperatura (°C)":temp,
                "Viento (m/s)":viento,"Azimut (°)":rumbo,
                "Fx conductor (kN)":float(f[0]),
                "Fy conductor (kN)":float(f[1]),
                "Fz conductor (kN)":float(f[2]),
                "H conductor (kN)":float(np.linalg.norm(f[:2])),
                "Desplazamiento X (m)":float(despl[0]),
                "Desplazamiento Y (m)":float(despl[1]),
                "Desplazamiento Z (m)":float(despl[2]),
                "Reacción X (kN)":float(reaccion[0]) if reaccion is not None else float("nan"),
                "Reacción Y (kN)":float(reaccion[1]) if reaccion is not None else float("nan"),
                "Reacción Z (kN)":float(reaccion[2]) if reaccion is not None else float("nan"),
                "Estado":"ACCIONES, NO APROBACIÓN ESTRUCTURAL",
            })
        for clave,sec in res.secciones_deslizantes.items():
            t_secciones.append({
                "Hipótesis":caso,"Circuito":clave[0],"Sección":clave[1],
                "Tipo":"GUÍA DESLIZANTE IDEAL",
                "Longitud natural referencia total (m)":sec.longitud_natural_total_m,
                "Residual máximo continuidad (kN)":sec.residual_max_kN,
                "Evaluaciones sección":sec.evaluaciones,
            })
    vanos=pd.DataFrame(t_vanos)
    apoyos=pd.DataFrame(t_apoyos)
    gobernantes=(vanos.loc[vanos.groupby("Vano")["T máxima (kN)"].idxmax()]
                 .reset_index(drop=True))
    return {
        "vanos":vanos,
        "apoyos":apoyos,
        "secciones_deslizantes":pd.DataFrame(t_secciones),
        "tensiones_gobernantes":gobernantes,
        "estado":(
            "CONDICIONES FÍSICAS DECLARADAS; "
            "SIN APROBACIÓN DE CONDUCTORES, APOYOS NI LIBRAMIENTOS"
        ),
    }
