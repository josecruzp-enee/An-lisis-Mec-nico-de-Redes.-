"""Diseño mecánico por claro de diseño y tabla por claros regla.

CFE DCCIAMBT 2014: 05 00 02 y 07 FT 01. El diseño básico parte de
una flecha final a 50°C y verifica límites de tracción bajo hipótesis
climáticas. SAGSEC no publica aquí su formulación constitutiva completa:
este motor es un modelo termoelástico explícito y auditable, NO SAGSEC.

Un solo estado de referencia FINAL determina la longitud natural final.
La longitud natural INICIAL se obtiene mediante deformación permanente
FÍSICAMENTE DEFINIDA: L0_final = L0_inicial*(1+epsilon_permanente).
El módulo EA cambia con la condición. Sin epsilon documentada se permite
cero únicamente como comparación SIN CREEP, nunca como condición final CFE
certificada. Los P NO se suministran desde tablas ENEE.

Se distingue el claro de diseño (establece el referente) de los claros
regla (filas que calculan estados). Cada fila se dimensiona con las
hipótesis mecánicas; geometría real puede evaluarse por vano independizado.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
import numpy as np
import pandas as pd
from scipy.optimize import brentq

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural
from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, HipotesisDisenoCFE,
    calcular_parametro_cfe_desde_limites,
)
from Analisis_mecanico_conductores.tension_tendido.evaluar_vanos_amarrados_independientes import (
    EvaluadorVanosAmarrados,
)
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import (
    calcular_flecha_y_desviacion_3d,
)


@dataclass(frozen=True)
class DisenoCFE:
    claro_diseno_m: float
    flecha_final_referencia_50C_m: float
    epsilon_permanente: float = 0.
    temperatura_referencia_C: float = 50.
    densidad_hielo_kg_m3: float = 900.
    Cd: float = 1.
    rho_kg_m3: float = 1.225

    def validar(self):
        if self.claro_diseno_m <= 0 or self.flecha_final_referencia_50C_m <= 0:
            raise ValueError("Claro de diseño y flecha de referencia deben ser positivos")
        if self.epsilon_permanente < 0 or self.epsilon_permanente > .1:
            raise ValueError("Deformación permanente fuera de dominio permitido [0, 0.1]")
        if self.temperatura_referencia_C != 50.:
            raise ValueError("Esta edición usa referencia a 50 °C")
        if self.Cd <= 0 or self.rho_kg_m3 <= 0 or self.densidad_hielo_kg_m3 <= 0:
            raise ValueError("Propiedades aerodinámicas o hielo inválidas")


def _puntos(L):
    return np.array([[0., 0., 0.], [float(L), 0., 0.]])


def _H_50_desde_flecha(luz, flecha, peso):
    """Resolver catenaria exacta para flecha declarada, sin parábola."""
    L=float(luz); f=float(flecha); w=float(peso)
    if L<=0 or f<=0 or w<=0:
        raise ValueError("Luz, flecha y peso deben ser positivos")
    def residuo(H):
        a=H/w
        return 2*a*np.sinh(L/(4*a))**2 - f
    bajo=max(w*L/200.,1e-7)
    alto=max(w*L**2/(8*f)*10,1.)
    if residuo(bajo)<0 or residuo(alto)>0:
        raise ValueError("No se pudo acotar catenaria para flecha de referencia")
    return float(brentq(residuo,bajo,alto))


def _H_inicial_por_compatibilidad(luz, H_final_50, prop, deformacion_permanente):
    """Recupera H inicial a 50°C desde longitud natural, sin P ENEE."""
    xyz=_puntos(luz)
    q=np.array([0.,0.,-prop.peso_kN_m])
    c_final=resolver_catenaria(xyz[0],xyz[1],q,H_final_50)
    L_n_final=longitud_natural(c_final,prop.EA_final_kN)
    objetivo=L_n_final/(1.+deformacion_permanente)
    def error(H):
        return longitud_natural(
            resolver_catenaria(xyz[0],xyz[1],q,H),prop.EA_inicial_kN
        )-objetivo
    bajo=max(prop.peso_kN_m*luz/200.,1e-7)
    alto=max(H_final_50*4.,prop.ruptura_kN*2.)
    if error(bajo)<0:
        raise ValueError("Estado inicial sin raíz física por tensión mínima")
    for _ in range(35):
        if error(alto)<=0:
            break
        alto*=2.
    else:
        raise ValueError("Estado inicial sin raíz: revisar epsilon y parámetros")
    return float(brentq(error,bajo,alto,xtol=1e-9))


def _eval(luz, H50, estado, prop, clima, diseno):
    xyz=_puntos(luz)
    ini=estado=="Inicial"
    evaluador=EvaluadorVanosAmarrados(
        xyz,prop.peso_kN_m,prop.diametro_m,
        prop.EA_inicial_kN if ini else prop.EA_final_kN,
        prop.alpha_inicial_por_C if ini else prop.alpha_final_por_C,
        50.,diseno.Cd,diseno.rho_kg_m3,
    )
    hs, tensiones, cables, residuales, _=evaluador.evaluar_estado_con_hielo(
        float(H50),float(clima.temperatura_C),float(clima.viento_kmh)/3.6,
        float(clima.hielo_mm),diseno.densidad_hielo_kg_m3,
    )
    flecha,lateral=calcular_flecha_y_desviacion_3d(
        cables[0],xyz[0],xyz[1],
    )
    return {
        "H (kN)":float(hs[0]),"T máxima (kN)":float(tensiones[0]),
        "Flecha (m)":float(flecha),"Desviación lateral (m)":float(lateral),
        "Residual (m)":float(residuales[0]),
    }


def _limites_por_estado(prop):
    """Criterios porcentuales de diseño básico CFE, no certificación ENEE."""
    return {
        "Final": [
            ("16°C sin viento",16.,0.,0.,.20),
            ("0°C sin viento",0.,0.,0.,.25),
        ],
        "Inicial": [("0°C sin viento",0.,0.,0.,.33)],
    }


def _valida_fuerza(luz,H_final,prop,diseno,hip_final,hip_inicial):
    """Máxima utilización combinada de ambas condiciones ligadas por epsilon."""
    H_ini=_H_inicial_por_compatibilidad(luz,H_final,prop,diseno.epsilon_permanente)
    ratios=[]
    for caso in hip_final:
        res=_eval(luz,H_final,"Final",prop,caso,diseno)
        ratios.append(res["T máxima (kN)"]/caso.limite_tension_kN)
    for caso in hip_inicial:
        res=_eval(luz,H_ini,"Inicial",prop,caso,diseno)
        ratios.append(res["T máxima (kN)"]/caso.limite_tension_kN)
    return max(ratios),H_ini


def calcular_referencia_diseno(prop,diseno,hip_final,hip_inicial):
    """Selecciona referencia final en CLARO DE DISEÑO.

    Se parte de flecha de referencia final y se controla conjuntamente
    toda restricción final e inicial. Un valor H50 menor implica mayor
    flecha y menor tensión de tendido, pero no necesariamente menor
    esfuerzo en todo el rango; no se extrapola sin solución factible.
    """
    prop.validar();diseno.validar()
    hip_final=list(hip_final);hip_inicial=list(hip_inicial)
    for h in hip_final+hip_inicial: h.validar()
    if not hip_final or not hip_inicial:
        raise ValueError("Se requieren hipótesis de tensión inicial y final")
    L=diseno.claro_diseno_m
    h_flecha=_H_50_desde_flecha(L,diseno.flecha_final_referencia_50C_m,prop.peso_kN_m)

    # Exigir que la flecha nominal sea físicamente factible. Si no,
    # registrar que la tracción limita el diseño; sin superar la flecha.
    def ratio(H): return _valida_fuerza(L,H,prop,diseno,hip_final,hip_inicial)[0]
    r_ref=ratio(h_flecha)
    if r_ref<=1.+1e-8:
        H_fin=h_flecha
        motivo="Flecha de referencia a 50°C"
    else:
        # Búsqueda de H menor: al reducir tensión se incrementa la flecha.
        # Si el modelo carece de rango factible se informa el problema.
        candidatos=np.geomspace(max(h_flecha/500.,0.0001),h_flecha,40)
        factibles=[float(x) for x in candidatos if ratio(float(x))<=1.]
        if not factibles:
            raise ValueError("No hay diseño factible para flecha/límites; revisar hipótesis")
        H_fin=max(factibles)
        for arriba in sorted(float(x) for x in candidatos if x>H_fin):
            if ratio(arriba)>1:
                H_fin=float(brentq(lambda x:ratio(x)-1.,H_fin,arriba))
                break
        motivo="Límites de tracción; flecha mayor que referencia"
    r,H_ini= _valida_fuerza(L,H_fin,prop,diseno,hip_final,hip_inicial)
    return {
        "Claro de diseño (m)":L,
        "H50 final (kN)":H_fin,
        "H50 inicial (kN)":H_ini,
        "P50 final (m)":H_fin/prop.peso_kN_m,
        "P50 inicial (m)":H_ini/prop.peso_kN_m,
        "Flecha final 50°C (m)":_eval(
            L,H_fin,"Final",prop,
            HipotesisDisenoCFE("50°C",50.,0.,0.,prop.ruptura_kN,"Referencia"),diseno,
        )["Flecha (m)"],
        "Utilización crítica":r,
        "Criterio gobernante":motivo,
    }


def calcular_corridas_claros(
    prop,diseno,hip_final,hip_inicial,claros_regla_m,temperaturas_C,
    extras=(),
):
    """Calcula P propios para cada claro regla, sin tablas ENEE.

    Cada claro utiliza la misma regla CFE de flecha de diseño escalada
    proporcionalmente L² al caso de diseño, sometida a los límites de
    tracción. Esta extrapolación es hipótesis explícita del modelo,
    NO una regla publicada por CFE ni reproducción SAGSEC.
    """
    base=calcular_referencia_diseno(prop,diseno,hip_final,hip_inicial)
    filas=[];referencias=[]
    for luz in claros_regla_m:
        L=float(luz)
        if L<=0:raise ValueError("Claro regla no positivo")
        flecha_estim=diseno.flecha_final_referencia_50C_m*(L/diseno.claro_diseno_m)**2
        di=DisenoCFE(
            claro_diseno_m=L,
            flecha_final_referencia_50C_m=flecha_estim,
            epsilon_permanente=diseno.epsilon_permanente,
            temperatura_referencia_C=diseno.temperatura_referencia_C,
            densidad_hielo_kg_m3=diseno.densidad_hielo_kg_m3,
            Cd=diseno.Cd,rho_kg_m3=diseno.rho_kg_m3,
        )
        ref=calcular_referencia_diseno(prop,di,hip_final,hip_inicial)
        referencias.append(ref)
        casos=[
            HipotesisDisenoCFE("Térmica",float(t),0.,0.,prop.ruptura_kN,"Corrida")
            for t in temperaturas_C
        ]+list(extras)
        for estado,h50 in (("Inicial",ref["H50 inicial (kN)"]),
                           ("Final",ref["H50 final (kN)"])):
            for caso in casos:
                res=_eval(L,h50,estado,prop,caso,di)
                filas.append({
                    "Condición":estado,
                    "Claro regla (m)":L,
                    "Caso":caso.nombre,
                    "Temperatura (°C)":caso.temperatura_C,
                    "Viento (km/h)":caso.viento_kmh,
                    "Hielo (mm)":caso.hielo_mm,
                    "P50 (m)":h50/prop.peso_kN_m,
                    **res,
                })
    return base,pd.DataFrame(referencias),pd.DataFrame(filas)
