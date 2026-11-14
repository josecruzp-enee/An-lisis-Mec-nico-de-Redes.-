"""Ensamblador mecánico GLOBAL 3D para cables y apoyos trasladables.

Cada vano utiliza un problema de contorno no lineal con carga local de
viento. La longitud natural de tendido se fija UNA VEZ sobre la geometría
de referencia y se conserva durante las iteraciones de los desplazamientos.

Versión del ensamblador: conexiones ANCLAJE/FIJA y DESLIZANTE ideal
con conservación de longitud total y tensión continua en cada guía.
Nodos trasladables con rigidez 3x3 DOCUMENTADA. Las suspensiones con
grapa real, rotaciones, retenidas y cimentación no lineal SE RECHAZAN. Este solver
NO representa todavía toda la red físicamente y NO aprueba estructuras.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np
from scipy.optimize import least_squares

from .modelo_red import RedMecanica
from .catenaria import resolver_catenaria
from .cambio_estado import longitud_natural
from .cable_no_lineal import resolver_cable_no_lineal
from .suspension_deslizante import resolver_seccion_deslizante
from .validacion_mecanica import finito, vector3


@dataclass
class ResultadoRed:
    desplazamientos_m: dict
    fuerzas_conductor_kN: dict
    fuerzas_rigidez_kN: dict
    fuerzas_externas_kN: dict
    reacciones_anclajes_kN: dict
    residuales_equilibrio_kN: dict
    vanos: dict
    iteraciones: int
    residual_max_kN: float
    estado: str
    secciones_deslizantes: dict = field(default_factory=dict)


def _material(ficha,nombre):
    campos=("peso_kN_m","diametro_m","EA_kN","alpha_por_C",
            "H_tendido_kN","temperatura_tendido_C","fuente")
    faltan=[x for x in campos if x not in ficha]
    if faltan:
        raise ValueError(f"{nombre}: faltan propiedades {faltan}")
    if not str(ficha["fuente"]).strip():
        raise ValueError(f"{nombre}: falta fuente verificable")
    for clave in campos[:-1]:
        minimo=0 if clave in ("peso_kN_m","diametro_m","EA_kN",
                              "H_tendido_kN") else None
        finito(ficha[clave],f"{nombre}/{clave}",minimo,minimo is not None)


def _rigidez_traslacion(apoyo,k):
    if not isinstance(k,dict) or not k.get("fuente"):
        raise ValueError(f"{apoyo}: rigidez sin fuente")
    matriz=np.asarray(k.get("K_kN_m"),dtype=float)
    if matriz.shape!=(3,3) or not np.isfinite(matriz).all():
        raise ValueError(f"{apoyo}: K debe ser 3x3 finita")
    if not np.allclose(matriz,matriz.T,atol=1e-10):
        raise ValueError(f"{apoyo}: K no simétrica")
    if float(np.min(np.linalg.eigvalsh(matriz)))<=0:
        raise ValueError(f"{apoyo}: K no definida positiva")
    return matriz


def _preparar(red, materiales,rigideces):
    if not isinstance(red,RedMecanica):
        raise ValueError("Se requiere RedMecanica validada")
    red.validar()
    if any(v.conexion_origen == "SUSPENSION" or
           v.conexion_destino == "SUSPENSION"
           for v in red.vanos.values()):
        raise ValueError(
            "Suspensión con grapa real no implementada: "
            "no está permitido convertirla a guía deslizante o anclaje"
        )
    matrices={}
    for nombre,n in red.apoyos.items():
        if n.fijacion=="MOVIL":
            matrices[nombre]=_rigidez_traslacion(nombre,rigideces.get(nombre))
    for v in red.vanos.values():
        if v.conductor not in materiales:
            raise ValueError(f"{v.nombre}: material no encontrado")
        _material(materiales[v.conductor],v.conductor)
    # Precalcular longitud natural en tendido antes de mover los apoyos.
    longitud0={}
    for v in red.vanos.values():
        ficha=materiales[v.conductor]
        a=np.asarray(red.apoyos[v.origen].base_m)+v.amarre_origen_m
        b=np.asarray(red.apoyos[v.destino].base_m)+v.amarre_destino_m
        ref=resolver_catenaria(
            a,b,[0,0,-float(ficha["peso_kN_m"])],
            ficha["H_tendido_kN"]
        )
        longitud0[v.nombre]=longitud_natural(ref,ficha["EA_kN"])
    return matrices,longitud0


def resolver_equilibrio_global(
    red:RedMecanica, materiales, *,
    temperatura_C, viento_ms, azimut_deg,
    rigideces=None, fuerzas_adicionales=None,
    rho_kg_m3=1.225, Cd=1.2,
    tolerancia_residual_kN=1e-4, tolerancia_bvp=1e-5,
    max_evaluaciones=40, max_desplazamiento_m=None,
):
    """Resuelve simultáneamente traslaciones nodales y cables incidentes.

    Fuentes y condiciones de referencia obligatorias. El viento del fuste y
    peso de estructuras NO se añaden automáticamente: 'fuerzas_adicionales'
    debe incluir cualquier carga externa conocida que sea relevante.
    """
    rigideces=rigideces or {}
    fuerzas_adicionales=fuerzas_adicionales or {}
    matrices,longitudes=_preparar(red,materiales,rigideces)
    t=finito(temperatura_C,"temperatura")
    v=finito(viento_ms,"viento",0)
    az=finito(azimut_deg,"azimut")
    rho=finito(rho_kg_m3,"rho",0,True)
    cd=finito(Cd,"Cd",0,True)
    tol=finito(tolerancia_residual_kN,"tolerancia residual",0,True)
    if max_desplazamiento_m is not None:
        max_u=finito(max_desplazamiento_m,"max desplazamiento",0,True)
    else:
        max_u=None
    for nombre in fuerzas_adicionales:
        if nombre not in red.apoyos:
            raise ValueError(f"{nombre}: fuerza externa sobre apoyo inexistente")
    adicionales={
        n: vector3(fuerzas_adicionales[n],f"fuerza adicional {n}")
        if n in fuerzas_adicionales else np.zeros(3)
        for n in red.apoyos
    }
    moviles=tuple(matrices)
    def evaluar(x):
        desplazamientos={n:np.zeros(3) for n in red.apoyos}
        for i,n in enumerate(moviles):
            desplazamientos[n]=np.array(x[3*i:3*i+3])
        fuerzas={n:np.zeros(3) for n in red.apoyos}
        vanos={}
        secciones_deslizantes={}
        grupos=red._agrupar_secciones()
        identificadores_deslizantes=set()
        for (circuito,seccion),grupo in grupos.items():
            if any(v.conexion_origen=="DESLIZANTE" or
                   v.conexion_destino=="DESLIZANTE" for v in grupo):
                if len(grupo)<2:
                    raise ValueError("Guía deslizante sin sección de varios vanos")
                resultado_seccion=resolver_seccion_deslizante(
                    red,materiales,circuito=circuito,seccion=seccion,
                    temperatura_C=t,viento_ms=v,azimut_deg=az,
                    rho_kg_m3=rho,Cd=cd,
                    tolerancia_equilibrio_kN=tol,
                    tolerancia_bvp=tolerancia_bvp,
                    apoyos_desplazados_m=desplazamientos,
                )
                secciones_deslizantes[(circuito,seccion)]=resultado_seccion
                identificadores_deslizantes.update(
                    vano.nombre for vano in grupo
                )
                vanos.update(resultado_seccion.vanos)
                for nombre,fuerza in resultado_seccion.fuerzas_apoyos_kN.items():
                    fuerzas[nombre]+=fuerza
        for vano in red.vanos.values():
            if vano.nombre in identificadores_deslizantes:
                continue
            m=materiales[vano.conductor]
            a=(np.asarray(red.apoyos[vano.origen].base_m)
               +vano.amarre_origen_m+desplazamientos[vano.origen])
            b=(np.asarray(red.apoyos[vano.destino].base_m)
               +vano.amarre_destino_m+desplazamientos[vano.destino])
            cable=resolver_cable_no_lineal(
                a,b,peso_kN_m=m["peso_kN_m"],
                diametro_m=m["diametro_m"],
                EA_kN=m["EA_kN"],alpha_por_C=m["alpha_por_C"],
                H_tendido_kN=m["H_tendido_kN"],
                temperatura_tendido_C=m["temperatura_tendido_C"],
                temperatura_estado_C=t,
                velocidad_viento_ms=v,azimut_viento_deg=az,
                rho_kg_m3=rho,Cd=cd,tolerancia=tolerancia_bvp,
                longitud_natural_referencia_m=longitudes[vano.nombre],
            )
            fuerzas[vano.origen]+=cable.fuerza_a
            fuerzas[vano.destino]+=cable.fuerza_b
            vanos[vano.nombre]=cable
        elasticidad={n:matrices[n]@desplazamientos[n] for n in moviles}
        residual={
            n: fuerzas[n]+adicionales[n]-
               elasticidad.get(n,np.zeros(3))
            for n in red.apoyos
        }
        return desplazamientos,fuerzas,elasticidad,residual,vanos,secciones_deslizantes

    if moviles:
        inicial=np.zeros(3*len(moviles))
        def fun(x):
            return np.concatenate([
                evaluar(x)[3][n] for n in moviles
            ])
        if max_u is not None:
            sol=least_squares(
                fun,inicial,bounds=(-max_u,max_u),
                xtol=1e-9,ftol=1e-9,gtol=1e-9,
                max_nfev=int(max_evaluaciones)
            )
        else:
            sol=least_squares(
                fun,inicial,xtol=1e-9,ftol=1e-9,gtol=1e-9,
                max_nfev=int(max_evaluaciones)
            )
        if not sol.success:
            raise ValueError(
                f"Equilibrio global sin convergencia: {sol.message}"
            )
        x=sol.x
        evaluaciones=sol.nfev
    else:
        x=np.array([])
        evaluaciones=1
    desplazamientos,fuerzas,elasticidad,residuales,vanos,secciones_deslizantes=evaluar(x)
    max_res=max((float(np.linalg.norm(residuales[n]))
                 for n in moviles),default=0.)
    if max_res>tol:
        raise ValueError(
            f"El equilibrio global supera tolerancia: {max_res:g} kN"
        )
    reacciones={
        n:-(fuerzas[n]+adicionales[n])
        for n in red.apoyos if n not in matrices
    }
    return ResultadoRed(
        desplazamientos_m=desplazamientos,
        fuerzas_conductor_kN=fuerzas,
        fuerzas_rigidez_kN=elasticidad,
        fuerzas_externas_kN=adicionales,
        reacciones_anclajes_kN=reacciones,
        residuales_equilibrio_kN=residuales,
        vanos=vanos,
        iteraciones=evaluaciones,
        residual_max_kN=max_res,
        estado="EQUILIBRIO DE TRASLACIÓN Y GUÍAS IDEALES; NO VERIFICACIÓN ESTRUCTURAL",
        secciones_deslizantes=secciones_deslizantes,
    )
