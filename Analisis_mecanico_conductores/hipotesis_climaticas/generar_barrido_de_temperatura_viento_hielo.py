"""Barrido EXPLORATORIO de estados de conductor sin límites normativos supuestos.

El barrido usa la H de tendido ya obtenida con hipótesis documentadas.
La tabla de temperaturas sin viento y la de velocidades a una temperatura
de referencia son independientes. La matriz cruzada se activa expresamente.
Hielo opcional: carga gravitatoria cilíndrica de espesor radial uniforme,
con densidad suministrada, y diámetro aumentado para arrastre por viento.
No incluye desprendimiento de hielo, viento dependiente de dirección global
ni cálculo de eventos climáticos coincidentes a efectos normativos.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    calcular_cargas_transversales_por_vano,
)
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito

GRAVEDAD=9.80665


@dataclass(frozen=True)
class ConfiguracionBarrido:
    """Rangos en °C y km/h, espesor de hielo radial en mm.

    viento_t_ref_C=None utiliza temperatura de tendido.
    modo_matriz_completa=False: 51 temperaturas + 27 vientos (menos
    duplicados de estados, si ocurren), no 51×27.
    El hielo se ejecuta a temperatura_hielo_C indicada, con v=0 y
    opcionalmente v=viento_max_kmh; NO constituye criterio normativo.
    """
    temperatura_min_C: float=0.
    temperatura_max_C: float=50.
    temperatura_paso_C: float=1.
    viento_max_kmh: float=130.
    viento_paso_kmh: float=5.
    viento_t_ref_C: float|None=None
    modo_matriz_completa: bool=False
    incluir_hielo: bool=False
    hielo_max_mm: float=20.
    hielo_paso_mm: float=5.
    densidad_hielo_kg_m3: float=900.
    temperatura_hielo_C: float=0.
    combinar_hielo_viento: bool=False


def _secuencia(inicio,fin,paso,nombre):
    """Crea valores inclusive, exige divisibilidad y limita tamaño."""
    a=finito(inicio,nombre)
    b=finito(fin,nombre)
    p=finito(paso,"incremento "+nombre,0,True)
    if b<a:
        raise ValueError(nombre+": máximo inferior al mínimo")
    n=round((b-a)/p)
    if n>300 or not np.isclose(a+n*p,b,rtol=0,atol=1e-8):
        raise ValueError(nombre+": rango no divisible por paso o demasiados valores")
    return [float(a+i*p) for i in range(n+1)]


def _casos_climaticos(config, temperatura_tendido_C):
    """Devuelve casos únicos; no supone simultaneidad en modo independiente."""
    temperaturas=_secuencia(
        config.temperatura_min_C,config.temperatura_max_C,
        config.temperatura_paso_C,"temperatura"
    )
    vientos=_secuencia(0.,config.viento_max_kmh,config.viento_paso_kmh,"viento")
    tref=(finito(config.viento_t_ref_C,"temperatura del viento")
          if config.viento_t_ref_C is not None else temperatura_tendido_C)
    if config.modo_matriz_completa:
        estados=[(t,v,0.,"Matriz T×V (exploratoria)")
                 for t in temperaturas for v in vientos]
    else:
        estados=[(t,0.,0.,"Temperatura, sin viento") for t in temperaturas]
        estados += [(tref,v,0.,"Viento a T de referencia") for v in vientos]
    if config.incluir_hielo:
        espesores=_secuencia(0.,config.hielo_max_mm,config.hielo_paso_mm,"hielo")
        if not any(x>0 for x in espesores):
            raise ValueError("Activar hielo requiere un espesor máximo positivo")
        densidad=finito(config.densidad_hielo_kg_m3,"densidad del hielo",0,True)
        _=densidad
        t_hielo=finito(config.temperatura_hielo_C,"temperatura del hielo")
        velocidades=(0.,config.viento_max_kmh) if config.combinar_hielo_viento else (0.,)
        estados += [
            (t_hielo,v,espesor,"Hielo+viento (exploratoria)" if v else "Manguito de hielo")
            for espesor in espesores if espesor>0 for v in velocidades
        ]
    unicos={}
    for t,v,espesor,tipo in estados:
        unicos.setdefault((t,v,espesor),(t,v,espesor,tipo))
    if len(unicos)>9000:
        raise ValueError("Barrido demasiado extenso; ajustá los pasos")
    return list(unicos.values())


def _peso_hielo_kN_m(diametro_m, espesor_mm, densidad_kg_m3):
    """Peso añadido del cilindro anular de hielo, kN/m de conductor."""
    e=espesor_mm/1000
    area_anillo=pi*((diametro_m/2+e)**2-(diametro_m/2)**2)
    return area_anillo*densidad_kg_m3*GRAVEDAD/1000


def _flecha_y_desplazamiento(cable,inicio,fin):
    """Flecha vertical y desviación lateral máximas respecto a la cuerda.

    Sólo para amarres al mismo nivel; el vano puede girar en planta.
    """
    vector=fin[:2]-inicio[:2]
    longitud=float(np.linalg.norm(vector))
    if longitud<=0 or abs(float(fin[2]-inicio[2]))>1e-5:
        raise ValueError("Barrido convencional requiere amarres nivelados")
    p=cable.puntos(cable.minimo_lineal([0,0,1]))
    flecha=max(0.,float(inicio[2]-p[2]))
    normal=np.array([-vector[1],vector[0],0.])/longitud
    xneg=cable.minimo_lineal(normal)
    xpos=cable.minimo_lineal(-normal)
    lateral=max(
        abs(float(np.dot(cable.puntos(xneg)-inicio,normal))),
        abs(float(np.dot(cable.puntos(xpos)-inicio,normal))),
    )
    return flecha,lateral


def _resolver_estado(evaluador, H0, temperatura_C, viento_kmh, hielo_mm,
                     densidad_hielo_kg_m3):
    """Resuelve carga de viento + hielo con una sola formulación termoelástica."""
    viento_ms=viento_kmh/3.6
    if hielo_mm==0:
        return evaluador.evaluar_estado(H0,temperatura_C,viento_ms)
    peso_extra=_peso_hielo_kN_m(
        evaluador.diametro,hielo_mm,densidad_hielo_kg_m3
    )
    peso_total=evaluador.peso+peso_extra
    diametro_total=evaluador.diametro+2*hielo_mm/1000
    cargas,viento=calcular_cargas_transversales_por_vano(
        evaluador.xyz,peso_total,diametro_total,viento_ms,evaluador.cd,evaluador.rho
    )
    pares=[]
    for (a,b),(q_inicial_incorrecto,q_final) in zip(
        zip(evaluador.xyz[:-1],evaluador.xyz[1:]),cargas
    ):
        # La longitud natural de referencia se calcula SIN hielo.
        q_inicial=np.array([0.,0.,-evaluador.peso])
        pares.append((a,b,q_inicial,q_final))
    res=resolver_cambio_estado(
        pares,H0,evaluador.ea,evaluador.alpha,
        temperatura_C-evaluador.temperatura_tendido,tolerancia_m=1e-8
    )
    H=res["H_kN"]
    cables=[resolver_catenaria(a,b,q1,H) for a,b,q0,q1 in pares]
    tensiones=[max(float(c.tension(0)),float(c.tension(c.luz))) for c in cables]
    return H,tensiones,cables,res["residual_m"],viento


def ejecutar_barrido_climatico(puntos, H_tendido_kN, evaluador, configuracion):
    """Devuelve filas por estado/vano y casos gobernantes exploratorios.

    Entradas: puntos ordenados de una sección nivelada; evaluador ya
    configurado con EA, alpha, peso y diámetro de UNA ficha de conductor;
    H de referencia resuelta previamente con hipótesis documentadas.

    Salida: dict con 'detalle', 'gobernantes' y 'configuracion'.
    Las magnitudes máximas no equivalen a aprobación normativa.
    """
    if not isinstance(configuracion,ConfiguracionBarrido):
        raise TypeError("Se requiere ConfiguracionBarrido")
    H0=finito(H_tendido_kN,"H tendido",0,True)
    casos=_casos_climaticos(configuracion,evaluador.temperatura_tendido)
    filas=[]
    for temperatura,viento_kmh,hielo_mm,tipo in casos:
        try:
            H,tensiones,cables,residual,viento=_resolver_estado(
                evaluador,H0,temperatura,viento_kmh,hielo_mm,
                configuracion.densidad_hielo_kg_m3
            )
        except (ValueError,OverflowError,FloatingPointError) as error:
            raise ValueError(
                f"Error en barrido: T={temperatura} °C, viento={viento_kmh} "
                f"km/h, hielo={hielo_mm} mm: {error}"
            ) from error
        for i,(c,a,b) in enumerate(zip(
            cables,evaluador.xyz[:-1],evaluador.xyz[1:]
        )):
            flecha,lateral=_flecha_y_desplazamiento(c,a,b)
            filas.append({
                "Tipo de corrida":tipo,
                "Vano":str(puntos.iloc[i]["Punto"])+" → "+str(puntos.iloc[i+1]["Punto"]),
                "Temperatura (°C)":temperatura,
                "Viento (km/h)":viento_kmh,
                "Viento (m/s)":viento_kmh/3.6,
                "Hielo radial (mm)":hielo_mm,
                "H estado (kN)":H,
                "T máxima vano (kN)":tensiones[i],
                "Flecha vertical (m)":flecha,
                "Desviación lateral máxima (m)":lateral,
                "Carga viento (kN/m)":viento,
                "Residual compatibilidad (m)":residual,
                "Estado":"EXPLORATORIO; NO LÍMITE DE DISEÑO",
            })
    detalle=pd.DataFrame(filas)
    mapa={
        "Máxima tensión":"T máxima vano (kN)",
        "Máxima flecha vertical":"Flecha vertical (m)",
        "Máxima desviación lateral":"Desviación lateral máxima (m)",
    }
    gobernantes=pd.DataFrame([
        {"Condición gobernante":nombre,**detalle.loc[detalle[col].idxmax()].to_dict()}
        for nombre,col in mapa.items()
    ])
    return {
        "detalle":detalle,"gobernantes":gobernantes,
        "total_estados":len(casos),
        "configuracion":configuracion,
    }
