"""Corridas mecánicas por vano fijo, con el perfil Checa existente.

NO determina H a partir de flechas ENEE, claros de diseño, SAGSEC ni P
predefinidos. El estado de instalación usa E INICIAL, y los cambios de
estado conservan la longitud natural de cada vano tras el amarre.

La segunda serie, 'Elasticidad final SIN creep', sustituye E inicial por
E final a LONGITUD NATURAL CONSERVADA, mediante una ecuación explícita
de compatibilidad. NO equivale al estado final histórico del conductor
si no se conoce su deformación permanente. No se declara certificación.

Cd y rho son los mismos parámetros del motor existente: no se
introducen coeficientes alternativos propios de este módulo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import (
    calcular_flecha_y_desviacion_3d,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    _geometria,
)
from Analisis_mecanico_conductores.tension_tendido.evaluar_vanos_amarrados_independientes import (
    EvaluadorVanosAmarrados,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_analisis_integral_de_conductores import (
    ejecutar_analisis_integral,
)


def _referencia_final_mismo_largo(a,b,peso,EA_inicial,EA_final,H_inicial):
    """H con E final que conserva exactamente la longitud natural sin creep."""
    q=np.array([0.,0.,-float(peso)])
    original=resolver_catenaria(a,b,q,float(H_inicial))
    objetivo=longitud_natural(original,float(EA_inicial))

    def residuo(H):
        cable=resolver_catenaria(a,b,q,float(H))
        return longitud_natural(cable,float(EA_final))-objetivo

    # H es positivo. Con mayor H la longitud descargada decrece.
    bajo=max(float(peso)*np.linalg.norm(np.asarray(b)-np.asarray(a))/200.,1e-5)
    alto=max(float(H_inicial)*2,1.)
    if residuo(bajo)<0:
        raise ValueError("No existe raíz de H final en el intervalo físico")
    for _ in range(40):
        if residuo(alto)<=0:break
        alto*=2
    else:
        raise ValueError("No se pudo acotar tensión final; revisar propiedades")
    resultado=float(brentq(residuo,bajo,alto,xtol=1e-9))
    if abs(residuo(resultado))>1e-7:
        raise ValueError("Compatibilidad inicial/final fuera de tolerancia")
    return resultado


def ejecutar_corridas_por_vano_checa(
    puntos, conductor_inicial, conductor_final,
    temperaturas_C=tuple(range(-10,51,5)), *,
    temperatura_tendido_C=20., Cd=1.2, rho=1.225,
):
    """Dos series de elasticidad, una instalación y misma longitud natural.

    El H de tendido es común y viene de las restricciones Checa TCD/THF
    implementadas en el motor histórico. Cada vano tiene su propia
    longitud descargada tras el amarre; el cambio de estado es individual.
    """
    claves=("peso_kN_m","diametro_m","ruptura_kN")
    for campo in claves:
        if not np.isclose(
            float(conductor_inicial[campo]),float(conductor_final[campo]),
            rtol=1e-12,atol=1e-12,
        ):
            raise ValueError("Las fichas inicial/final no corresponden al mismo conductor")
    if not temperaturas_C:
        raise ValueError("Se requieren temperaturas")
    if any(not np.isfinite(float(t)) for t in temperaturas_C):
        raise ValueError("Temperatura no finita")

    resultado_base=ejecutar_analisis_integral(
        puntos,propiedades=conductor_inicial,
        temperatura_tendido_C=temperatura_tendido_C,
        perfil_tension="Checa",
        configuracion_barrido=None,Cd=Cd,rho=rho,
    )
    if resultado_base.cota_busqueda_activa:
        raise ValueError(
            "No se encontró tensión gobernada por Checa antes del tope de búsqueda; "
            "no se utilizará un extremo de búsqueda como tensión física"
        )
    xyz,luces=_geometria(puntos)
    filas=[]
    peso=float(conductor_inicial["peso_kN_m"])
    diametro=float(conductor_inicial["diametro_m"])
    EA_ini=float(conductor_inicial["EA_kN"])
    EA_fin=float(conductor_final["EA_kN"])
    alpha_ini=float(conductor_inicial["alpha_por_C"])
    alpha_fin=float(conductor_final["alpha_por_C"])

    # La referencia se asigna separadamente a cada vano fijado; no se
    # permite redistribuir material entre amarres en el cambio de estado.
    for i,(a,b) in enumerate(zip(xyz[:-1],xyz[1:])):
        H_ini=float(resultado_base.H_tendido_kN)
        H_fin=_referencia_final_mismo_largo(
            a,b,peso,EA_ini,EA_fin,H_ini,
        )
        identificador=str(puntos.iloc[i]["Punto"])+" → "+str(puntos.iloc[i+1]["Punto"])
        segmento=np.vstack((a,b))
        for condicion,H_referencia,EA,alpha in (
            ("Inicial — tendido Checa",H_ini,EA_ini,alpha_ini),
            ("Elasticidad final SIN creep",H_fin,EA_fin,alpha_fin),
        ):
            motor=EvaluadorVanosAmarrados(
                segmento,peso,diametro,EA,alpha,
                float(temperatura_tendido_C),Cd,rho,
            )
            for temp in temperaturas_C:
                h,tens,cables,residual,_=motor.evaluar_estado(
                    H_referencia,float(temp),0.,
                )
                flecha,lateral=calcular_flecha_y_desviacion_3d(
                    cables[0],a,b,
                )
                # Para el estado real se calcula P con H del estado, no se
                # usa como entrada ni se extrae de tablas externas.
                filas.append({
                    "Condición":condicion,
                    "Vano":identificador,
                    "Luz horizontal (m)":float(luces[i]),
                    "Temperatura (°C)":float(temp),
                    "Viento (km/h)":0.,
                    "H (kN)":float(h[0]),
                    "T máxima (kN)":float(tens[0]),
                    "Flecha vertical (m)":float(flecha),
                    "Desviación lateral (m)":float(lateral),
                    "P de estado (m)":float(h[0])/peso,
                    "Residual compatibilidad (m)":float(residual[0]),
                    "H referencia tendido (kN)":H_ini,
                    "Origen del criterio":"Checa TCD/THF",
                    "Fuente conductor":str(conductor_inicial["fuente"]),
                })
    return resultado_base,pd.DataFrame(filas)
