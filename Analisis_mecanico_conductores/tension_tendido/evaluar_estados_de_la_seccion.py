"""Evaluación termomecánica de una sección de regulación convencional.

Cada estado usa una tensión H horizontal común para toda la sección
idealmente regulada. La tensión de referencia corresponde a tendido sin
viento a temperatura de tendido; cada otro estado conserva la suma de
longitudes naturales mediante el motor de cambio de estado.

Solo admite la geometría nivelada comprobada por el coordinador.
No representa fricción real en suspensión ni capacidad de los postes.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito


def calcular_cargas_transversales_por_vano(xyz_m, peso_kN_m, diametro_m,
                                          velocidad_ms, Cd, rho_kg_m3, *, modelo_presion_cfe=False):
    """Devuelve pares (carga inicial, carga final) en kN/m y viento en kN/m.

    El viento se aplica normal a cada vano: envolvente convencional local,
    NO una dirección de viento geográfica común para toda la traza.
    """
    velocidad=finito(velocidad_ms,"viento",0)
    if modelo_presion_cfe:
        from Analisis_mecanico_conductores.hipotesis_climaticas.presiones_cfe_por_claro import presion_cfe_por_claro
    else:
        viento=.5*finito(rho_kg_m3,"rho",0,True)*finito(Cd,"Cd",0,True)*diametro_m*velocidad**2/1000
    cargas=[]
    vientos=[]
    for inicio,fin in zip(xyz_m[:-1],xyz_m[1:]):
        direccion=fin[:2]-inicio[:2]
        claro=float(np.linalg.norm(direccion))
        perpendicular=np.array([-direccion[1],direccion[0],0.])/claro
        if modelo_presion_cfe:
            viento=presion_cfe_por_claro(claro,velocidad*3.6)*diametro_m/1000.
        vientos.append(viento)
        cargas.append((
            np.array([0.,0.,-peso_kN_m]),
            np.array([viento*perpendicular[0],viento*perpendicular[1],-peso_kN_m]),
        ))
    return cargas,max(vientos) if vientos else 0.


class EvaluadorEstadosRegulacion:
    """Calcula estados (H, tensiones extremas, catenarias, residual, viento).

    Parámetros
    ----------
    puntos_xyz_m: amarres ordenados, en metros; mismo nivel de elevación.
    peso_kN_m, diametro_m, EA_kN: parámetros SI expresados en esas unidades.
    alpha_por_C: dilatación lineal 1/°C.
    temperatura_tendido_C: estado de referencia, sin viento.
    Cd, rho_kg_m3: parámetros explícitos de presión dinámica.
    """

    def __init__(self, puntos_xyz_m, peso_kN_m, diametro_m, EA_kN,
                 alpha_por_C, temperatura_tendido_C, Cd, rho_kg_m3):
        self.xyz=puntos_xyz_m
        self.peso=peso_kN_m
        self.diametro=diametro_m
        self.ea=EA_kN
        self.alpha=alpha_por_C
        self.temperatura_tendido=temperatura_tendido_C
        self.cd=Cd
        self.rho=rho_kg_m3

    @lru_cache(maxsize=None)
    def evaluar_estado(self, H_referencia_kN, temperatura_C, velocidad_ms):
        """Resuelve una hipótesis conservando longitud natural (retorno documentado)."""
        cargas,viento=calcular_cargas_transversales_por_vano(
            self.xyz,self.peso,self.diametro,velocidad_ms,self.cd,self.rho
        )
        parejas=[
            (a,b,q0,q1)
            for (a,b),(q0,q1) in zip(zip(self.xyz[:-1],self.xyz[1:]),cargas)
        ]
        delta=float(temperatura_C)-self.temperatura_tendido
        if delta==0 and velocidad_ms==0:
            H_estado=H_referencia_kN
            residual=0.
        else:
            res=resolver_cambio_estado(
                parejas,H_referencia_kN,self.ea,self.alpha,delta,
                tolerancia_m=1e-8
            )
            H_estado=res["H_kN"]
            residual=res["residual_m"]
        cables=[
            resolver_catenaria(a,b,q1,H_estado)
            for a,b,q0,q1 in parejas
        ]
        tensiones=[
            max(float(c.tension(0)),float(c.tension(c.luz)))
            for c in cables
        ]
        return H_estado,tensiones,cables,residual,viento
