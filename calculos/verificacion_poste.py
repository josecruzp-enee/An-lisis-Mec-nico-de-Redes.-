"""Diagrama de solicitaciones de poste en secciones sobre el terreno.

El modelo suma las acciones de cables aplicadas a sus amarres y el arrastre
distribuido del fuste cónico. Entrega Vx,Vy,N,Mx,My,Mz en cada sección.
No asigna propiedades resistentes al material, ni trata el fuste como macizo.

Convención: acciones EXTERNAS sobre el segmento SUPERIOR al corte. La
resultante interna resistente es la opuesta a esta acción externa.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from calculos.solicitaciones_poste import geometria_fuste
from calculos.validacion_mecanica import finito


def _cargas_fuste_sobre_corte(geometria, z_m, v_ms, azimut_deg,
                             rho_kg_m3, Cd):
    """Integra q(t)=p[D0+(D1-D0)t/h] desde z hasta h analíticamente."""
    h = geometria["Altura expuesta (m)"]
    d0 = geometria["Diámetro terreno (m)"]
    d1 = geometria["Diámetro punta (m)"]
    pendiente = (d1-d0)/h
    dz = h-z_m
    diam_corte = d0+pendiente*z_m
    fuerza = .5*rho_kg_m3*Cd*v_ms**2/1000 * (
        diam_corte*dz + .5*pendiente*dz**2
    )
    momento = .5*rho_kg_m3*Cd*v_ms**2/1000 * (
        diam_corte*dz**2/2 + pendiente*dz**3/3
    )
    theta = math.radians(azimut_deg)
    return np.array([
        fuerza*math.cos(theta), fuerza*math.sin(theta), 0.,
        -momento*math.sin(theta), momento*math.cos(theta), 0.,
    ])


def calcular_secciones_poste(nodos_conductores, postes, *,
                            cantidad_secciones=21,
                            rho_kg_m3=1.225, Cd_poste=1.2):
    """Calcula acciones de cada estado a lo largo del fuste.

    Entrada 'nodos_conductores': resultantes de cables por caso en terreno
    (sin viento del poste). Se admite una altura común por nodo para los
    conductores agrupados. Fases con amarres distintos requieren registros
    separados antes de usar este análisis.
    """
    if isinstance(cantidad_secciones, bool) or int(cantidad_secciones) != cantidad_secciones or cantidad_secciones < 2:
        raise ValueError("Se requieren por lo menos dos secciones")
    if int(cantidad_secciones)>201:
        raise ValueError("Máximo 201 secciones por poste")
    rho = finito(rho_kg_m3, "densidad aire", 0, True)
    cd = finito(Cd_poste, "Cd poste", 0, True)
    if nodos_conductores is None or nodos_conductores.empty:
        raise ValueError("Sin acciones de conductor")
    if postes["Punto"].astype(str).duplicated().any():
        raise ValueError("Puntos duplicados en tabla de postes")
    if "Altura_Amarre_m" not in postes:
        raise ValueError("Falta altura real de amarre")

    lookup = postes.set_index(postes["Punto"].astype(str),drop=False)
    filas=[]
    for _, caso in nodos_conductores.iterrows():
        nombre = str(caso["Punto"])
        if nombre not in lookup.index:
            raise ValueError(f"Poste {nombre} sin geometría")
        poste=lookup.loc[nombre]
        empotramiento=poste.get("Empotramiento_m",None)
        geo=geometria_fuste(poste["Poste"],empotramiento)
        if geo is None:
            # Sin dimensiones no se pueden generar esfuerzos distribuidos.
            filas.append({"Punto":nombre,"Caso":caso["Caso"],
                          "Estado sección":"NO VERIFICABLE: geometría de poste ausente"})
            continue
        amarre=finito(poste["Altura_Amarre_m"], "altura amarre",0,True)
        h=geo["Altura expuesta (m)"]
        if amarre>h+1e-8:
            raise ValueError(
                f"{nombre}: amarre {amarre:g} m supera altura expuesta {h:g} m "
                f"(empotramiento {geo['Empotramiento (m)']:g} m). "
                "Revise cotas del Excel y geometría del poste."
            )
        v=finito(caso["Viento (m/s)"],"viento",0)
        az=finito(caso["Azimut viento (°)"],"azimut viento")
        f_cable=np.array([float(caso[k]) for k in (
            "Fx (kN)","Fy (kN)","Fz (kN)"
        )])
        mz_cable=finito(caso["Mz (kN·m)"],"torsión")
        if not np.isfinite(f_cable).all():
            raise ValueError("Fuerzas del conductor no finitas")
        # M de cable en el origen es (r x F). Resta r_corte x F
        # para obtener el momento referido a la sección.
        m_cable_base=np.array([float(caso[k]) for k in (
            "Mx (kN·m)","My (kN·m)","Mz (kN·m)"
        )])
        if not np.isfinite(m_cable_base).all():
            raise ValueError("Momentos de conductor no finitos")
        for z in np.linspace(0,h,int(cantidad_secciones)):
            # Los cables por debajo del corte no pertenecen al cuerpo superior.
            cable_activo = z<=amarre+1e-10
            F = f_cable.copy() if cable_activo else np.zeros(3)
            M = (m_cable_base - np.cross(np.array([0.,0.,z]), f_cable)
                 if cable_activo else np.zeros(3))
            viento=_cargas_fuste_sobre_corte(geo,float(z),v,az,rho,cd)
            F += viento[:3]
            M += viento[3:]
            d=geo["Diámetro terreno (m)"] + (
                geo["Diámetro punta (m)"] - geo["Diámetro terreno (m)"]
            )*z/h
            filas.append({
                "Punto":nombre,"Caso":caso["Caso"],
                "Altura corte (m)":float(z),
                "Diámetro exterior (m)":float(d),
                "Fx (kN)":float(F[0]),"Fy (kN)":float(F[1]),
                "N axial (kN)":float(F[2]),
                "V transversal (kN)":float(np.hypot(F[0],F[1])),
                "Mx (kN·m)":float(M[0]),"My (kN·m)":float(M[1]),
                "Mz (kN·m)":float(M[2]),
                "M flector (kN·m)":float(np.hypot(M[0],M[1])),
                "Origen empotramiento":geo["Origen empotramiento"],
                "Estado sección":"SOLICITACIÓN, RESISTENCIA NO VERIFICABLE",
            })
    return pd.DataFrame(filas)


def secciones_gobernantes(secciones):
    """Extrae demanda máxima por poste conservando el caso y altura críticos."""
    if secciones is None or secciones.empty:
        raise ValueError("No existen secciones")
    completas=secciones.loc[
        secciones["Estado sección"]=="SOLICITACIÓN, RESISTENCIA NO VERIFICABLE"
    ]
    filas=[]
    for punto,g in completas.groupby("Punto",sort=False):
        for componente in ("M flector (kN·m)","V transversal (kN)",
                           "N axial (kN)","Mz (kN·m)"):
            r=g.loc[g[componente].abs().idxmax()]
            filas.append({
                "Punto":punto,"Magnitud":componente,
                "Demanda":float(r[componente]),
                "Altura crítica (m)":float(r["Altura corte (m)"]),
                "Caso gobernante":r["Caso"],
                "Estado":"RESISTENCIA NO VERIFICABLE",
            })
    return pd.DataFrame(filas)
