"""Barrido termoelástico 3D con viento normal a la tangente LOCAL.

Este motor usa el BVP no lineal por vano con amarres FIJOS.
Conserva las columnas y controles de trazabilidad del barrido anterior,
pero NO identifica por sí mismo suspensiones, remates o continuidad física.
Para redes conectadas usar el ensamblador global y su propia topología.

Cada caso se resuelve por completo, sin interpolar cargas ni mezclar
resultados. Los mínimos de flecha/despeje se encuentran sobre la curva
numérica del BVP, no sobre la cuerda ni sobre una tabla dispersa.
"""
from __future__ import annotations

from collections import defaultdict
import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from .barrido_3d import _verificar_vanos, _secuencia_viento
from .cable_no_lineal import resolver_cable_no_lineal
from .validacion_mecanica import finito


def _extremo_minimo(cable, funcion, tolerancia=1e-8):
    """Mínimo sobre u material: busca en subintervalos, también extremos.

    La discretización de búsqueda no sustituye el BVP: los candidatos
    se refinan con evaluaciones directas de la solución numérica continua.
    """
    rejilla = np.linspace(0., 1., 33)
    valores = np.array([funcion(u) for u in rejilla])
    candidatos = [(float(valores[0]), 0.), (float(valores[-1]), 1.)]
    for i in range(1,len(rejilla)-1):
        if valores[i] <= valores[i-1] and valores[i] <= valores[i+1]:
            res=minimize_scalar(
                funcion,bounds=(float(rejilla[i-1]),
                                float(rejilla[i+1])),
                method="bounded",options={"xatol":tolerancia},
            )
            if not res.success:
                raise ValueError("No convergió mínimo geométrico del conductor")
            candidatos.append((float(res.fun),float(res.x)))
    valor,ubicacion=min(candidatos,key=lambda x:x[0])
    return valor,ubicacion


def _geometria_cable(cable, vano, a, b):
    """Flecha respecto cuerda espacial y despeje frente a terreno lineal."""
    eje=b[:2]-a[:2]
    norma2=float(eje@eje)
    if norma2<=0:
        raise ValueError("Vano sin proyección horizontal")
    terreno_a=float(vano["base_inicio_m"][2])
    terreno_b=float(vano["base_fin_m"][2])

    def progresiva(p):
        return float(((p[:2]-a[:2])@eje)/norma2)

    def vertical_cuerda(u):
        p=cable.puntos(u)
        return float(
            p[2]-(a[2]+(b[2]-a[2])*progresiva(p))
        )

    def vertical_terreno(u):
        p=cable.puntos(u)
        z=terreno_a+(terreno_b-terreno_a)*progresiva(p)
        return float(p[2]-z)

    negativo,uf=_extremo_minimo(cable,vertical_cuerda)
    despeje,ud=_extremo_minimo(cable,vertical_terreno)
    p=cable.puntos(uf)
    lateral=float(
        abs(eje[0]*(p[1]-a[1])-eje[1]*(p[0]-a[0]))
        /math.sqrt(norma2)
    )
    return {
        "Flecha vertical respecto cuerda (m)":max(0.,-negativo),
        "Desviación lateral en punto de flecha (m)":lateral,
        "Despeje sobre terreno lineal (m)":float(despeje),
        "Modelo terreno":"INTERPOLACIÓN ENTRE APOYOS; NO VERIFICADO",
    }


def ejecutar_barrido_no_lineal_3d(
    vanos, *, peso_kN_m, diametro_m, EA_kN, alpha_por_C,
    temperatura_tendido_C, temperaturas_C, tensiones_iniciales_kN,
    viento_max_ms, viento_min_ms=0, incremento_viento_ms=1,
    direcciones_viento_deg=(0,), Cd=1.2, rho_kg_m3=1.225,
    cantidad_conductores=1, fuente_conductor="",
    tolerancia_bvp=1e-5,
):
    """Barrido de amarres fijos con viento local, sin asumir continuidad."""
    geometria=_verificar_vanos(vanos)
    w=finito(peso_kN_m,"peso",0,True)
    d=finito(diametro_m,"diámetro",0,True)
    ea=finito(EA_kN,"EA",0,True)
    alpha=finito(alpha_por_C,"alpha")
    t0=finito(temperatura_tendido_C,"temperatura tendido")
    cd=finito(Cd,"Cd",0,True)
    rho=finito(rho_kg_m3,"densidad aire",0,True)
    tol=finito(tolerancia_bvp,"tolerancia BVP",0,True)
    if isinstance(cantidad_conductores,bool) or not isinstance(cantidad_conductores,int) or cantidad_conductores<1:
        raise ValueError("Cantidad de conductores debe ser entero positivo")
    if not isinstance(fuente_conductor,str) or not fuente_conductor.strip():
        raise ValueError("Falta fuente de propiedades del conductor")
    if not temperaturas_C or not tensiones_iniciales_kN or not direcciones_viento_deg:
        raise ValueError("Se requieren temperaturas, tensiones y direcciones")
    temperaturas=[finito(x,"temperatura") for x in temperaturas_C]
    tensiones=[finito(x,"H inicial",0,True) for x in tensiones_iniciales_kN]
    azimuts=[finito(x,"azimut")%360 for x in direcciones_viento_deg]
    velocidades=_secuencia_viento(
        viento_min_ms,viento_max_ms,incremento_viento_ms
    )

    filas_vanos,filas_nodos,filas_extremos=[],[],[]
    for h0 in tensiones:
        for t in temperaturas:
            for rumbo in azimuts:
                for viento in velocidades:
                    caso=f"H0={h0:g};T={t:g};V={viento:g};Az={rumbo:g}"
                    nodos=defaultdict(lambda:np.zeros(6))
                    for vano,a,b,ra,rb in geometria:
                        cable=resolver_cable_no_lineal(
                            a,b,peso_kN_m=w,diametro_m=d,
                            EA_kN=ea,alpha_por_C=alpha,
                            H_tendido_kN=h0,temperatura_tendido_C=t0,
                            temperatura_estado_C=t,
                            velocidad_viento_ms=viento,
                            azimut_viento_deg=rumbo,
                            rho_kg_m3=rho,Cd=cd,tolerancia=tol,
                        )
                        if cable.residual_equilibrio_kN>max(1e-5,10*tol):
                            raise ValueError(
                                f"{caso}/{vano['nombre']}: falla equilibrio BVP"
                            )
                        fa,fb=cable.fuerza_a,cable.fuerza_b
                        for extremo,nombre,brazo,fuerza in (
                            ("A",vano["inicio"],ra,fa),
                            ("B",vano["fin"],rb,fb),
                        ):
                            f=cantidad_conductores*fuerza
                            momento=np.cross(brazo,f)
                            nodos[nombre][:3]+=f
                            nodos[nombre][3:]+=momento
                            filas_extremos.append({
                                "Caso":caso,"Vano":vano["nombre"],
                                "Extremo":extremo,"Punto":nombre,
                                "Temperatura (°C)":t,
                                "Viento (m/s)":viento,
                                "Azimut viento (°)":rumbo,
                                "H inicial (kN)":h0,
                                "Conductores idénticos":cantidad_conductores,
                                "Altura amarre (m)":float(brazo[2]),
                                "Fx (kN)":float(f[0]),
                                "Fy (kN)":float(f[1]),
                                "Fz (kN)":float(f[2]),
                                "Mx (kN·m)":float(momento[0]),
                                "My (kN·m)":float(momento[1]),
                                "Mz (kN·m)":float(momento[2]),
                                "Fuente conductor":fuente_conductor,
                                "Estado":"ACCIONES DE CONDUCTOR, NO VERIFICACIÓN",
                            })
                        geom=_geometria_cable(cable,vano,a,b)
                        # La componente horizontal NO es constante cuando
                        # el viento depende de la tangente local del cable.
                        # Compatibilidad: discrepancia entre integral de
                        # alargamiento y poligonal de la solución BVP.
                        u=np.linspace(0,1,1001)
                        p=cable.puntos(u)
                        longitud_poligonal=float(np.sum(
                            np.linalg.norm(np.diff(p,axis=0),axis=1)
                        ))
                        error_longitud=abs(
                            longitud_poligonal-cable.longitud_deformada_m
                        )
                        filas_vanos.append({
                            "Caso":caso,"Vano":vano["nombre"],**geom,
                            "Temperatura (°C)":t,"Viento (m/s)":viento,
                            "Azimut viento (°)":rumbo,"H inicial (kN)":h0,
                            "H resuelta (kN)":float(np.linalg.norm(fa[:2])),
                            "Definición H":"Componente horizontal en extremo A; NO constante",
                            "T extremo A (kN)":float(np.linalg.norm(fa)),
                            "T extremo B (kN)":float(np.linalg.norm(fb)),
                            "T máxima (kN)":cable.tension_maxima_kN,
                            "Longitud cable (m)":cable.longitud_deformada_m,
                            "Residual equilibrio (kN)":cable.residual_equilibrio_kN,
                            "Residual compatibilidad (m)":error_longitud,
                            "Residual contorno (m)":cable.residual_frontera_m,
                            "Residual BVP RMS máximo":cable.residual_ode_max,
                            "Nodos malla BVP":cable.nodos_malla,
                            "Iteraciones":"BVP adaptativo",
                            "Fuente conductor":fuente_conductor,
                            "Modelo":"BVP 3D; viento normal a tangente local",
                        })
                    for nombre,f in nodos.items():
                        fx,fy,fz,mx,my,mz=map(float,f)
                        filas_nodos.append({
                            "Caso":caso,"Punto":nombre,
                            "Temperatura (°C)":t,
                            "Viento (m/s)":viento,
                            "Azimut viento (°)":rumbo,
                            "H inicial (kN)":h0,
                            "Fx (kN)":fx,"Fy (kN)":fy,"Fz (kN)":fz,
                            "Mx (kN·m)":mx,"My (kN·m)":my,"Mz (kN·m)":mz,
                            "H resultante (kN)":math.hypot(fx,fy),
                            "Estado":"SOLICITACIÓN, NO VERIFICABLE",
                        })
    return {
        "vanos":pd.DataFrame(filas_vanos),
        "nodos":pd.DataFrame(filas_nodos),
        "extremos":pd.DataFrame(filas_extremos),
        "parametros":{
            "velocidades_m_s":velocidades,
            "tensiones_iniciales_kN":tensiones,
            "temperaturas_C":temperaturas,
            "direcciones_viento_deg":azimuts,
            "modelo":"BVP termoelástico 3D, arrastre normal a la tangente local",
            "alcance":"Amarres FIJOS; sin topología ni verificación estructural",
        },
    }
