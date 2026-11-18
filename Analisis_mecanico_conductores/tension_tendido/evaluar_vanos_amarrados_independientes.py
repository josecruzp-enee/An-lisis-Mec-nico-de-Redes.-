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
from scipy.optimize import brentq

import numpy as np

from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado, longitud_natural, _acotar_raiz
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    calcular_cargas_transversales_por_vano,
)
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito


class EvaluadorVanosAmarrados:
    """Estados independientes para una misma condición inicial de tendido."""

    modelo_vanos_fijos = True

    def __init__(self, puntos_xyz_m, peso_kN_m, diametro_m, EA_kN,
                 alpha_por_C, temperatura_tendido_C, Cd, rho_kg_m3,
                 longitudes_naturales_referencia_m=None, modelo_presion_cfe=False):
        self.xyz=np.asarray(puntos_xyz_m,dtype=float)
        self.peso=finito(peso_kN_m,"peso",0,True)
        self.diametro=finito(diametro_m,"diámetro",0,True)
        self.ea=finito(EA_kN,"EA",0,True)
        self.alpha=finito(alpha_por_C,"alpha")
        self.temperatura_tendido=finito(temperatura_tendido_C,"temperatura de tendido")
        self.cd=finito(Cd,"Cd",0,True)
        self.rho=finito(rho_kg_m3,"densidad aire",0,True)
        self.modelo_presion_cfe=bool(modelo_presion_cfe)
        if self.xyz.ndim != 2 or self.xyz.shape[1] != 3 or len(self.xyz)<2:
            raise ValueError("Se necesitan dos o más amarres XYZ")
        if not np.isfinite(self.xyz).all():
            raise ValueError("Coordenadas XYZ no finitas")
        self.longitudes_fijadas = None
        if longitudes_naturales_referencia_m is not None:
            valores=np.asarray(longitudes_naturales_referencia_m,dtype=float)
            if (valores.shape != (len(self.xyz)-1,) or
                not np.isfinite(valores).all() or (valores <= 0).any()):
                raise ValueError("Longitudes naturales fijadas inválidas")
            self.longitudes_fijadas=tuple(map(float,valores))

    def _resolver_por_longitud(self,a,b,q,objetivo,H_semilla):
        """Resuelve un vano fijo a partir de la longitud natural heredada."""
        def residuo(h):
            return longitud_natural(resolver_catenaria(a,b,q,float(h)),self.ea)-objetivo
        bajo,alto=_acotar_raiz(residuo,H_semilla)
        h=float(brentq(residuo,bajo,alto,xtol=5e-13,rtol=1e-14))
        error=float(residuo(h))
        if abs(error)>max(1e-8,1e-10*objetivo):
            raise ValueError("Longitud natural fijada: compatibilidad no convergente")
        return h,error

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
            self.xyz,self.peso,self.diametro,v,self.cd,self.rho,
            modelo_presion_cfe=self.modelo_presion_cfe,
        )
        h_vanos=[]
        tensiones=[]
        cables=[]
        residuales=[]
        delta=t-self.temperatura_tendido
        for idx,((a,b),(q0,q1)) in enumerate(zip(zip(self.xyz[:-1],self.xyz[1:]),cargas)):
            if self.longitudes_fijadas is not None:
                objetivo=self.longitudes_fijadas[idx]*(1+self.alpha*delta)
                h_estado,residual=self._resolver_por_longitud(a,b,q1,objetivo,h0)
            elif delta==0 and v==0:
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
            modelo_presion_cfe=self.modelo_presion_cfe,
        )
        q0=np.array([0.,0.,-self.peso])
        hs=[]; tensiones=[]; cables=[]; residuales=[]
        delta=float(temperatura_C)-self.temperatura_tendido
        for idx,((a,b),(_base,q1)) in enumerate(zip(zip(self.xyz[:-1],self.xyz[1:]),cargas)):
            if self.longitudes_fijadas is not None:
                objetivo=self.longitudes_fijadas[idx]*(1+self.alpha*delta)
                h,error=self._resolver_por_longitud(a,b,q1,objetivo,H_referencia_kN)
                cable=resolver_catenaria(a,b,q1,h)
                hs.append(h)
                tensiones.append(max(float(cable.tension(0)),float(cable.tension(cable.luz))))
                cables.append(cable)
                residuales.append(error)
                continue
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
