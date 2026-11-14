"""Cable 3D: problema de contorno termoelástico con viento LOCAL no lineal.

Las ecuaciones se integran en la coordenada material térmica s (m).
  dr/ds = (1 + |T|/EA) * t
  dT/ds = -(1 + |T|/EA) * [qg + qa(t)]
  t = T/|T|
  qa(t) = rho*Cd*D/2000 * |V - (V·t)t| * (V - (V·t)t)
qg: peso hacia abajo kN/m de cable deformado.

La coordenada s recorre la longitud natural expandida térmicamente
S0(T)=S0(T0)*(1+alpha*deltaT+deformacion_permanente).

Hipótesis FÍSICAS explícitas: cable flexible sin rigidez flexional,
elasticidad axial lineal, carga de viento estacionaria perpendicular a
la tangente LOCAL, Cd constante, peso por metro deformado y extremos
fijos. No modela dinámica, vibración, plasticidad ni interacción con
suspensiones móviles o postes flexibles.

SOLUCIÓN NUMÉRICA: scipy.integrate.solve_bvp. El arrastre NO se
sustituye por la proyección del viento sobre el eje recto del vano.
No hay aprobaciones estructurales en este módulo.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.integrate import solve_bvp

from .catenaria import resolver_catenaria
from .cambio_estado import longitud_natural
from .validacion_mecanica import finito, vector3


@dataclass(frozen=True)
class Cable3D:
    """Resultado de un vano con sus fuerzas en los dos anclajes (kN)."""
    s_material: np.ndarray
    xyz: np.ndarray
    tensiones_xyz: np.ndarray
    fuerza_a: np.ndarray
    fuerza_b: np.ndarray
    longitud_natural_20_m: float
    longitud_natural_estado_m: float
    longitud_deformada_m: float
    tension_maxima_kN: float
    residual_equilibrio_kN: float
    residual_frontera_m: float
    residual_ode_max: float
    nodos_malla: int
    modelo: str


def _aerodinamica(t, viento, rho, cd, diametro, peso):
    """Distribución q por metro real; recibe tangentes (3,N)."""
    componente = viento[:, None] - t*np.sum(t*viento[:, None], axis=0)
    norma = np.linalg.norm(componente, axis=0)
    arrastre = 0.5*rho*cd*diametro/1000 * componente*norma[None,:]
    arrastre[2] -= peso
    return arrastre


def resolver_cable_no_lineal(
    inicio, fin, *, peso_kN_m, diametro_m,
    EA_kN, alpha_por_C, H_tendido_kN,
    temperatura_tendido_C, temperatura_estado_C,
    velocidad_viento_ms, azimut_viento_deg,
    rho_kg_m3=1.225, Cd=1.2, deformacion_permanente=0.0,
    tolerancia=1e-5, max_nodos=12000, puntos=80,
    longitud_natural_referencia_m=None,
):
    """Resuelve el BVP 3D para UN vano con amarres fijos.

    El estado de referencia está tendido sin viento, a temperatura_tendido,
    con H horizontal prescrita. Para una sección con suspensión móvil,
    este solver se integrará después en el equilibrio GLOBAL de la red.
    """
    a=vector3(inicio,"inicio")
    b=vector3(fin,"fin")
    w=finito(peso_kN_m,"peso por metro",0,True)
    d=finito(diametro_m,"diámetro",0,True)
    ea=finito(EA_kN,"EA",0,True)
    alpha=finito(alpha_por_C,"alpha")
    H0=finito(H_tendido_kN,"H tendido",0,True)
    t0=finito(temperatura_tendido_C,"temperatura tendido")
    t1=finito(temperatura_estado_C,"temperatura estado")
    velocidad=finito(velocidad_viento_ms,"viento",0)
    rumbo=math.radians(finito(azimut_viento_deg,"azimut"))
    rho=finito(rho_kg_m3,"rho",0,True)
    cd=finito(Cd,"Cd",0,True)
    creep=finito(deformacion_permanente,"deformacion permanente",0)
    tol=finito(tolerancia,"tolerancia",0,True)
    if max_nodos < 100 or puntos < 10:
        raise ValueError("Malla insuficiente")
    factor=1+alpha*(t1-t0)+creep
    if factor<=0:
        raise ValueError("Longitud natural térmica no positiva")

    referencia=resolver_catenaria(a,b,[0,0,-w],H0)
    # Para el sistema global la longitud natural inicial proviene de
    # la configuración de tendido y NO puede actualizarse al mover apoyos.
    if longitud_natural_referencia_m is None:
        s0=longitud_natural(referencia,ea)
    else:
        s0=finito(longitud_natural_referencia_m,
                  "longitud natural referencia",0,True)
    s1=s0*factor
    rumbo_v=np.array([math.cos(rumbo),math.sin(rumbo),0.])
    V=velocidad*rumbo_v

    # Coordenadas LOCALES: reducen errores por UTM de grandes magnitudes.
    # Semilla de solución: estado sin viento, nunca reemplaza la solución.
    malla=np.linspace(0.,1.,int(puntos))
    x=malla*referencia.luz
    r=referencia.puntos(x).T-a[:,None]
    tens=H0*(referencia.e[:,None]+
             np.sinh((x-referencia.xc)/referencia.a)[None,:]*
             referencia.n[:,None])
    inicial=np.vstack([r,tens])

    def ecuaciones(u,y):
        F=y[3:6]
        magnitud=np.linalg.norm(F,axis=0)
        if np.any(magnitud <= 1e-12):
            # La física prohíbe tracción nula: la solución se rechazará
            # por residual o falta de convergencia, nunca se informará válida.
            magnitud=np.maximum(magnitud,1e-12)
        tangente=F/magnitud[None,:]
        estiramiento=1+magnitud/ea
        carga=_aerodinamica(tangente,V,rho,cd,d,w)
        return np.vstack([
            s1*estiramiento[None,:]*tangente,
            -s1*estiramiento[None,:]*carga,
        ])

    def fronteras(ya,yb):
        return np.r_[ya[:3],yb[:3]-(b-a)]

    sol=solve_bvp(ecuaciones,fronteras,malla,inicial,
                  tol=tol,bc_tol=tol,max_nodes=int(max_nodos),verbose=0)
    if sol.status != 0 or not sol.success:
        raise ValueError(
            f"Cable 3D sin convergencia (estado {sol.status}): {sol.message}"
        )

    material=np.linspace(0,s1,max(150,int(sol.x.size)))
    estados=sol.sol(material/s1)
    posiciones=estados[:3].T+a
    fuerzas=estados[3:6].T
    normas=np.linalg.norm(fuerzas,axis=1)
    if np.min(normas)<=0 or not np.isfinite(estados).all():
        raise ValueError("Solución 3D con tracción nula o números no finitos")

    # Integral independiente de la carga distribuida del estado final.
    muestra=np.linspace(0.,1.,max(501,int(sol.x.size)*4))
    yq=sol.sol(muestra)
    Fq=yq[3:6]
    nq=np.linalg.norm(Fq,axis=0)
    tq=Fq/nq[None,:]
    stretch=1+nq/ea
    carga=_aerodinamica(tq,V,rho,cd,d,w)*stretch[None,:]
    total=np.trapezoid(carga, muestra, axis=1)*s1
    fa=Fq[:,0].copy()
    fb=-Fq[:,-1].copy()
    resid_eq=float(np.linalg.norm(fa+fb-total))
    resid_bc=float(np.linalg.norm(fronteras(yq[:,0],yq[:,-1])))
    residual_ode=float(np.max(sol.rms_residuals))
    if resid_bc > 10*tol or resid_eq > max(1e-5,10*tol):
        raise ValueError(
            "Cable 3D con residuales superiores a tolerancia: "
            f"contorno={resid_bc:g} m, equilibrio={resid_eq:g} kN"
        )
    longitud_real=float(np.trapezoid(stretch,muestra)*s1)
    return Cable3D(
        s_material=material,xyz=posiciones,tensiones_xyz=fuerzas,
        fuerza_a=fa,fuerza_b=fb,
        longitud_natural_20_m=float(s0),
        longitud_natural_estado_m=float(s1),
        longitud_deformada_m=longitud_real,
        tension_maxima_kN=float(np.max(normas)),
        residual_equilibrio_kN=resid_eq,
        residual_frontera_m=resid_bc,
        residual_ode_max=residual_ode,
        nodos_malla=int(sol.x.size),
        modelo="BVP 3D no lineal: viento perpendicular a tangente local",
    )
