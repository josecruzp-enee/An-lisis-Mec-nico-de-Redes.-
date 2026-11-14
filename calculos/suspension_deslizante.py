"""Compatibilidad de secciones de cable que deslizan por guías IDEALES.

Ley constitutiva de la guía DESLIZANTE (no de una grapa de suspensión):
- contacto geométrico en el punto XYZ declarado;
- longitud natural total CONSERVADA entre anclajes extremos;
- fuerza de tracción de igual magnitud a ambos lados en cada guía;
- deslizamiento sin fricción ni pérdida de energía;
- las reacciones de cambio de dirección se transmiten al apoyo;
- no se presupone capacidad resistente del herraje.

Cada vano se resuelve con BVP no lineal (viento sobre tangente local).
La conservación de longitud y la igualdad de tensión de las guías se
resuelven conjuntamente para TODOS los vanos de una sección. No se
emplea vano regulador ni se igualan las tensiones sobre el eje horizontal.

IMPORTANTE: una grapa que impide el deslizamiento se modela mediante
SUSPENSION, no DESLIZANTE; no se resuelve en este módulo.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import root

from .catenaria import resolver_catenaria
from .cambio_estado import longitud_natural
from .cable_no_lineal import resolver_cable_no_lineal
from .validacion_mecanica import finito


@dataclass
class ResultadoSeccion:
    circuito: str
    seccion: str
    vanos: dict
    longitudes_naturales_referencia_m: dict
    longitud_natural_total_m: float
    residuales_continuidad_kN: dict
    desplazamientos_materiales_m: dict
    fuerzas_apoyos_kN: dict
    evaluaciones: int
    residual_max_kN: float
    estado: str


def _ordenar_vanos(red, circuito, seccion):
    """Recorre la cadena desde uno de sus anclajes, sin usar orden de Excel."""
    grupo=[
        v for v in red.vanos.values()
        if (v.circuito,v.seccion_tendido)==(circuito,seccion)
    ]
    if not grupo:
        raise ValueError("La sección solicitada no existe")
    incidencias={}
    for v in grupo:
        incidencias.setdefault(v.origen,[]).append(v)
        incidencias.setdefault(v.destino,[]).append(v)
    extremos=[
        n for n,aristas in incidencias.items()
        if len(aristas)==1
    ]
    if len(extremos)!=2:
        raise ValueError("La sección no es una cadena entre dos anclajes")
    n=sorted(extremos)[0]
    orden=[]
    visitados=set()
    while len(orden)<len(grupo):
        opciones=[v for v in incidencias[n] if v.nombre not in visitados]
        if len(opciones)!=1:
            raise ValueError("No es posible ordenar la cadena física")
        v=opciones[0]
        visitados.add(v.nombre)
        siguiente=v.destino if v.origen==n else v.origen
        orden.append((v,n,siguiente,n==v.origen))
        n=siguiente
    if n!=sorted(extremos)[1]:
        raise ValueError("La sección no termina en el otro anclaje")
    return orden


def _pesos(logits, referencia):
    """Fracciones positivas y suma exacta de longitudes naturales."""
    exp=np.exp(logits-np.max(logits))
    fracciones=exp/np.sum(exp)
    return referencia.sum()*fracciones


def resolver_seccion_deslizante(
    red, materiales, *, circuito, seccion,
    temperatura_C, viento_ms, azimut_deg,
    rho_kg_m3=1.225, Cd=1.2,
    tolerancia_equilibrio_kN=1e-4, tolerancia_bvp=1e-5,
    max_evaluaciones=80, apoyos_desplazados_m=None,
):
    """Resuelve una sección completa sobre guías sin fricción y apoyos dados.

    Se puede suministrar desplazamientos de apoyo, pero el equilibrio de
    estos apoyos corresponde a un ENSAMBLADOR GLOBAL externo. No se puede
    presentar una única sección como aprobación de postes.
    """
    red.validar()
    orden=_ordenar_vanos(red,circuito,seccion)
    if len(orden)<2:
        raise ValueError("Se requieren dos o más vanos para guía deslizante")
    desplazamientos=apoyos_desplazados_m or {}
    for nodo in desplazamientos:
        if nodo not in red.apoyos:
            raise ValueError(f"Desplazamiento de apoyo inexistente: {nodo}")
    for v in red.vanos.values():
        if (v.circuito,v.seccion_tendido)==(circuito,seccion):
            continue
    nombre_cable=orden[0][0].conductor
    if nombre_cable not in materiales:
        raise ValueError("Propiedades del conductor inexistentes")
    m=materiales[nombre_cable]
    campos=("peso_kN_m","diametro_m","EA_kN","alpha_por_C",
            "H_tendido_kN","temperatura_tendido_C","fuente")
    if any(c not in m for c in campos) or not str(m.get("fuente","")).strip():
        raise ValueError("Se requiere ficha del conductor con fuente")
    if any(v.conductor!=nombre_cable for v,*_ in orden):
        raise ValueError("Una sección no puede cambiar de conductor")
    for i,(v,a,b,directo) in enumerate(orden):
        entrada=v.conexion_origen if directo else v.conexion_destino
        salida=v.conexion_destino if directo else v.conexion_origen
        if i==0 and entrada not in ("ANCLAJE","FIJA"):
            raise ValueError("La sección debe iniciar con un anclaje")
        if i==len(orden)-1 and salida not in ("ANCLAJE","FIJA"):
            raise ValueError("La sección debe terminar con un anclaje")
        if i>0 and entrada!="DESLIZANTE":
            raise ValueError("Solo se resuelve guía DESLIZANTE ideal")
        if i<len(orden)-1 and salida!="DESLIZANTE":
            raise ValueError("Solo se resuelve guía DESLIZANTE ideal")
    referencias=[]
    extremos=[]
    puntos=[]
    for v,a,b,directo in orden:
        p=(np.asarray(red.apoyos[v.origen].base_m)
           +np.asarray(v.amarre_origen_m))
        q=(np.asarray(red.apoyos[v.destino].base_m)
           +np.asarray(v.amarre_destino_m))
        if not directo:
            p,q=q,p
        puntos.append((p,q))
        referencia=resolver_catenaria(
            p,q,[0,0,-float(m["peso_kN_m"])],
            float(m["H_tendido_kN"])
        )
        referencias.append(longitud_natural(referencia,m["EA_kN"]))
    referencias=np.array(referencias,dtype=float)
    if not np.isfinite(referencias).all() or (referencias<=0).any():
        raise ValueError("Longitudes naturales no válidas")
    total=float(referencias.sum())
    M=len(orden)
    llamadas=0

    def resolver_configuracion(logits):
        nonlocal llamadas
        llamadas+=1
        longitud=_pesos(np.r_[logits,0.],referencias)
        cables=[]
        for idx,(v,a,b,directo) in enumerate(orden):
            p,q=puntos[idx]
            p=p+np.asarray(desplazamientos.get(a,(0,0,0)),dtype=float)
            q=q+np.asarray(desplazamientos.get(b,(0,0,0)),dtype=float)
            cable=resolver_cable_no_lineal(
                p,q,
                peso_kN_m=m["peso_kN_m"],
                diametro_m=m["diametro_m"],
                EA_kN=m["EA_kN"],
                alpha_por_C=m["alpha_por_C"],
                H_tendido_kN=m["H_tendido_kN"],
                temperatura_tendido_C=m["temperatura_tendido_C"],
                temperatura_estado_C=temperatura_C,
                velocidad_viento_ms=viento_ms,
                azimut_viento_deg=azimut_deg,
                rho_kg_m3=rho_kg_m3,Cd=Cd,
                tolerancia=tolerancia_bvp,
                longitud_natural_referencia_m=float(longitud[idx]),
            )
            cables.append(cable)
        continuidad=np.array([
            np.linalg.norm(cables[i].tensiones_xyz[-1])
            - np.linalg.norm(cables[i+1].tensiones_xyz[0])
            for i in range(M-1)
        ])
        return longitud,cables,continuidad

    inicial=np.log(referencias/referencias[-1])[:-1]
    try:
        sol=root(lambda x:resolver_configuracion(x)[2],inicial,
                 method="hybr",options={"maxfev":int(max_evaluaciones),
                                        "xtol":1e-9})
    except (OverflowError,FloatingPointError) as exc:
        raise ValueError("Inestabilidad numérica en continuidad de la sección") from exc
    longitud,cables,diferencia=resolver_configuracion(sol.x)
    err=float(np.max(np.abs(diferencia)))
    tol=finito(tolerancia_equilibrio_kN,"tolerancia",0,True)
    if not sol.success or not np.isfinite(err) or err>tol:
        raise ValueError(
            f"Sección {seccion} sin equilibrio de tensión en guía: "
            f"{err:.6g} kN; estado solver: {sol.message}"
        )
    fuerzas={n:np.zeros(3) for n in red.apoyos}
    for ((v,a,b,directo),cable) in zip(orden,cables):
        fuerzas[a]+=cable.fuerza_a
        fuerzas[b]+=cable.fuerza_b
    identificadores=[item[0].nombre for item in orden]
    return ResultadoSeccion(
        circuito=circuito,seccion=seccion,
        vanos=dict(zip(identificadores,cables)),
        longitudes_naturales_referencia_m=dict(zip(identificadores,map(float,longitud))),
        longitud_natural_total_m=total,
        residuales_continuidad_kN={
            orden[i][2]:float(diferencia[i]) for i in range(M-1)
        },
        desplazamientos_materiales_m={
            orden[i][2]:float(np.sum(longitud[:i+1]-referencias[:i+1]))
            for i in range(M-1)
        },
        fuerzas_apoyos_kN=fuerzas,
        evaluaciones=llamadas,
        residual_max_kN=err,
        estado="GUÍA DESLIZANTE IDEAL; CAPACIDADES NO VERIFICABLES",
    )
