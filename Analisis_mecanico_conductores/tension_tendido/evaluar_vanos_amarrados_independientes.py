"""Cambio de estado de distribución con conductor fijado en cada espiga.

Se supone que durante instalación los vanos se tensaron con un valor
H_referencia COMÚN (dato de procedimiento, no consecuencia de las espigas).
Tras el amarre NO se redistribuye material entre vanos: cada uno conserva
su propia longitud natural descargada al variar clima y temperatura.

No infiere H inicial del Excel. El dimensionamiento por límites documentados
está en calcular_tension_y_flechas_de_seccion.py, separado de esta clase.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    calcular_cargas_transversales_por_vano,
)
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito


class EvaluadorVanosAmarrados:
    """Estados independientes para una misma condición inicial de tendido."""

    modelo_vanos_fijos = True

    def __init__(self, puntos_xyz_m, peso_kN_m, diametro_m, EA_kN,
                 alpha_por_C, temperatura_tendido_C, Cd, rho_kg_m3):
        self.xyz=np.asarray(puntos_xyz_m,dtype=float)
        self.peso=finito(peso_kN_m,"peso",0,True)
        self.diametro=finito(diametro_m,"diámetro",0,True)
        self.ea=finito(EA_kN,"EA",0,True)
        self.alpha=finito(alpha_por_C,"alpha")
        self.temperatura_tendido=finito(temperatura_tendido_C,"temperatura de tendido")
        self.cd=finito(Cd,"Cd",0,True)
        self.rho=finito(rho_kg_m3,"densidad aire",0,True)
        if self.xyz.ndim != 2 or self.xyz.shape[1] != 3 or len(self.xyz)<2:
            raise ValueError("Se necesitan dos o más amarres XYZ")
        if not np.isfinite(self.xyz).all():
            raise ValueError("Coordenadas XYZ no finitas")

    @lru_cache(maxsize=512)
    def evaluar_estado(self, H_referencia_kN, temperatura_C, velocidad_ms):
        """Retorna H_i, tensiones_i, cables_i, residuales_i, viento.

        Los valores H_i y residuales_i son listas alineadas con los vanos.
        Esta salida difiere intencionalmente del evaluador de regulación
        ideal, que devuelve H y residual únicos para toda la sección.
        """
        h0=finito(H_referencia_kN,"H inicial",0,True)
        t=finito(temperatura_C,"temperatura")
        v=finito(velocidad_ms,"velocidad",0)
        cargas,viento=calcular_cargas_transversales_por_vano(
            self.xyz,self.peso,self.diametro,v,self.cd,self.rho
        )
        h_vanos=[]
        tensiones=[]
        cables=[]
        residuales=[]
        delta=t-self.temperatura_tendido
        for (a,b),(q0,q1) in zip(zip(self.xyz[:-1],self.xyz[1:]),cargas):
            if delta==0 and v==0:
                h_estado=h0
                residual=0.
            else:
                res=resolver_cambio_estado(
                    [(a,b,q0,q1)],h0,self.ea,self.alpha,delta,
                    tolerancia_m=1e-8,
                )
                h_estado=float(res["H_kN"])
                residual=float(res["residual_m"])
            cable=resolver_catenaria(a,b,q1,h_estado)
            h_vanos.append(h_estado)
            tensiones.append(max(float(cable.tension(0)),float(cable.tension(cable.luz))))
            cables.append(cable)
            residuales.append(residual)
        return h_vanos,tensiones,cables,residuales,viento

    def evaluar_estado_con_hielo(self,H_referencia_kN,temperatura_C,
                                 velocidad_ms,hielo_mm,densidad_hielo_kg_m3):
        """Adiciona hielo por vano sin mezclar longitudes naturales."""
        from math import pi
        espesor=finito(hielo_mm,"espesor hielo",0)
        if espesor==0:
            return self.evaluar_estado(H_referencia_kN,temperatura_C,velocidad_ms)
        densidad=finito(densidad_hielo_kg_m3,"densidad hielo",0,True)
        r=self.diametro/2
        extra=pi*((r+espesor/1000)**2-r**2)*densidad*9.80665/1000
        cargas,viento=calcular_cargas_transversales_por_vano(
            self.xyz,self.peso+extra,self.diametro+2*espesor/1000,
            velocidad_ms,self.cd,self.rho,
        )
        q0=np.array([0.,0.,-self.peso])
        hs=[]; tensiones=[]; cables=[]; residuales=[]
        delta=float(temperatura_C)-self.temperatura_tendido
        for (a,b),(_base,q1) in zip(zip(self.xyz[:-1],self.xyz[1:]),cargas):
            res=resolver_cambio_estado(
                [(a,b,q0,q1)],H_referencia_kN,self.ea,self.alpha,delta,
                tolerancia_m=1e-8,
            )
            h=float(res["H_kN"])
            cable=resolver_catenaria(a,b,q1,h)
            hs.append(h)
            tensiones.append(max(float(cable.tension(0)),float(cable.tension(cable.luz))))
            cables.append(cable)
            residuales.append(float(res["residual_m"]))
        return hs,tensiones,cables,residuales,viento
