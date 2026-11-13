"""Acciones 3D, arrastre transversal e hielo explícito; X=Este,Y=Norte,Z=arriba."""
from __future__ import annotations
import numpy as np
from .validacion_mecanica import vector3


def carga_conductor(conductor, estado, inicio, fin):
    """Carga kN/m real en el plano normal al eje horizontal del vano.

    Hipótesis: cilindro con velocidad normal V*sin(theta), arrastre proporcional
    a V_normal² y sentido transversal. No es presión normativa ENEE/NESC.
    """
    d = vector3(fin,'fin')-vector3(inicio,'inicio')
    horizontal = np.linalg.norm(d[:2])
    if horizontal <= 0:
        raise ValueError('Vano vertical no admitido')
    normal = np.array([-d[1], d[0], 0.0])/horizontal
    theta = np.deg2rad(estado.azimut_deg)
    viento = estado.viento_ms*np.array([np.cos(theta), np.sin(theta), 0.0])
    vn = float(viento@normal)
    diametro = conductor.diametro_m+2*estado.hielo_m
    arrastre = .5*estado.rho_kg_m3*estado.Cd*diametro*vn*abs(vn)/1000
    peso_hielo = 0.0
    if estado.hielo_m:
        area = np.pi/4*(diametro**2-conductor.diametro_m**2)
        peso_hielo = area*estado.densidad_hielo_kg_m3*9.80665/1000
    return arrastre*normal + np.array([0,0,-conductor.peso_kN_m-peso_hielo])


def resultante_acciones(acciones):
    """Suma (r[m], F[kN], M[kN·m]) respecto a la base del poste."""
    fuerza, momento = np.zeros(3), np.zeros(3)
    for posicion, carga, par in acciones:
        r, f, m = (vector3(v,n) for v,n in
                   [(posicion,'posición'),(carga,'fuerza'),(par,'momento')])
        fuerza += f
        momento += np.cross(r,f)+m
    return np.r_[fuerza,momento]
