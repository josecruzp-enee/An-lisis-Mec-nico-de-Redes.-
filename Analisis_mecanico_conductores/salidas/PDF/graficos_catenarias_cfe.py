"""Perfiles verificables desde resultados del motor CFE, sin parábolas.

Para cada fila se utiliza exactamente la H calculada y la misma carga
transversal del motor de vanos amarrados. La reconstrucción geométrica
se comprueba contra las flechas y desviaciones registradas antes de graficar.
No se supone terreno continuo ni se certifican libramientos.
"""
from __future__ import annotations

from io import BytesIO
from math import pi

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import (
    calcular_flecha_y_desviacion_3d,
)
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    calcular_cargas_transversales_por_vano,
)


def _escenarios(tabla, nombre):
    """Elegir condiciones representativas sin interpolar estados faltantes."""
    d = tabla[tabla["Vano"].astype(str) == nombre]
    def buscar(estado, temp=None, viento=None, hielo=None, texto=None):
        s = d[d["Condición"] == estado]
        if texto is not None:
            s = s[s["Hipótesis"].astype(str).str.contains(texto, case=False, regex=False)]
        if temp is not None:
            s = s[np.isclose(s["Temperatura (°C)"], temp)]
        if viento is not None:
            s = s[np.isclose(s["Viento (km/h)"], viento)]
        if hielo is not None:
            s = s[np.isclose(s["Hielo (mm)"], hielo)]
        return s.iloc[0] if not s.empty else None
    opciones = [
        ("H1 inicial, 0°C, calma", buscar("Inicial",0.,0.,0.), "#353535", "-"),
        ("H2 final, 16°C, calma", buscar("Final",16.,0.,0.), "#2355a4", "--"),
        ("H3 final, 0°C, calma", buscar("Final",0.,0.,0.), "#0e8060", "-."),
        ("H4 final, -10°C, hielo", buscar("Final",texto="viento reducido"), "#a03d2b", ":"),
        ("H5 final, viento máximo", buscar("Final",texto="viento máximo"), "#8a579c", "-"),
        ("Flecha térmica: final 50°C", buscar("Final",50.,0.,0.), "#d3780a", "--"),
    ]
    return [(label, r, color, estilo) for label,r,color,estilo in opciones if r is not None]


def _carga(xyz, i, row, propiedades, clima):
    peso = float(propiedades["peso_kN_m"])
    diametro = float(propiedades["diametro_m"])
    hielo_mm = float(row["Hielo (mm)"])
    if hielo_mm < 0:
        raise ValueError("Hielo negativo al generar perfil")
    if hielo_mm:
        radio = diametro/2
        espesor = hielo_mm/1000.
        densidad_hielo = float(clima.get("densidad_hielo_kg_m3",913.))
        peso += pi*((radio+espesor)**2-radio**2)*densidad_hielo*9.80665/1000.
        diametro += 2*espesor
    cargas, _ = calcular_cargas_transversales_por_vano(
        xyz, peso, diametro, float(row["Viento (km/h)"])/3.6,
        float(clima.get("Cd",1.)),float(clima.get("rho_kg_m3",1.225)),
        modelo_presion_cfe=bool(clima.get("modelo_presion_cfe",False)),
    )
    return cargas[i][1]


def graficar_perfiles_cfe(tabla: pd.DataFrame, xyz, propiedades: dict,
                          clima: dict | None = None):
    """Devuelve lista (nombre_vano, PNG BytesIO) para cada vano real.

    Exige que geometría y propiedades sean las mismas que las de la corrida.
    En caso de discrepancia física lanza ValueError, no crea una figura falsa.
    """
    xyz = np.asarray(xyz,dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < 2:
        raise ValueError("Los perfiles requieren puntos de amarre XYZ completos")
    if not np.isfinite(xyz).all():
        raise ValueError("Coordenadas XYZ no finitas")
    nombres = list(dict.fromkeys(tabla["Vano"].astype(str)))
    if len(nombres) != len(xyz)-1:
        raise ValueError("La cantidad de vanos no coincide con la geometría")
    clima = clima or {}
    salidas = []
    for i,nombre in enumerate(nombres):
        ini,fin = xyz[i],xyz[i+1]
        vector = fin-ini
        horizontal = float(np.linalg.norm(vector[:2]))
        if horizontal<=0:
            raise ValueError("Vano sin proyección horizontal")
        tangente = vector[:2]/horizontal
        normal = np.array([-tangente[1],tangente[0]])
        fig,(ax,planta) = plt.subplots(
            2,1,figsize=(10.3,5.4),gridspec_kw={"height_ratios":[2.5,1.]},
        )
        opciones = _escenarios(tabla,nombre)
        if not opciones:
            plt.close(fig)
            raise ValueError(f"Sin estados representativos en {nombre}")
        perfil_min = min(ini[2],fin[2])
        perfil_max = max(ini[2],fin[2])
        lateral_min,lateral_max=0.,0.
        for etiqueta,row,color,estilo in opciones:
            estado = str(row["Condición"])
            prop = propiedades[estado]
            q = _carga(xyz,i,row,prop,clima)
            cable = resolver_catenaria(ini,fin,q,float(row["H (kN)"]))
            flecha,lateral = calcular_flecha_y_desviacion_3d(cable,ini,fin)
            if abs(flecha-float(row["Flecha (m)"]))>2e-4 or abs(lateral-float(row["Lateral (m)"]))>2e-4:
                plt.close(fig)
                raise ValueError(
                    f"{nombre}: perfil incompatible con los resultados "
                    f"({etiqueta}; flecha {flecha:.6f} m, lateral {lateral:.6f} m)"
                )
            x=np.linspace(0.,cable.luz,241)
            pos=cable.puntos(x)
            recorrido=(pos[:,:2]-ini[:2])@tangente
            lado=(pos[:,:2]-ini[:2])@normal
            perfil_min=min(perfil_min,float(np.min(pos[:,2])))
            perfil_max=max(perfil_max,float(np.max(pos[:,2])))
            lateral_min=min(lateral_min,float(np.min(lado)))
            lateral_max=max(lateral_max,float(np.max(lado)))
            ax.plot(recorrido,pos[:,2],color=color,ls=estilo,lw=1.7,
                    label=(f"{etiqueta} · f={flecha:.3f} m · "
                           f"T={float(row['T máx. (kN)']):.3f} kN"))
            # Valor legible SOBRE la curva, en el punto de mayor flecha
            # vertical relativo a la cuerda, calculado desde la geometría
            # de la catenaria (sin supuesto parabólico).
            cuerda_z=ini[2]+(fin[2]-ini[2])*(recorrido/horizontal)
            pos_crit=int(np.argmax(cuerda_z-pos[:,2]))
            ax.plot(recorrido[pos_crit],pos[pos_crit,2],"o",color=color,ms=3.5)
            # Evitar seis etiquetas superpuestas: sobre la curva se
            # destacan H4 (carga crítica) y 50 °C final (flecha térmica);
            # los seis valores siguen completos en la leyenda.
            if etiqueta.startswith("H4") or etiqueta.startswith("Flecha térmica"):
                ax.annotate(f"f={flecha:.2f} m",
                            (recorrido[pos_crit],pos[pos_crit,2]),
                            xytext=(9, -12 if etiqueta.startswith("H4") else -19),
                            textcoords="offset points",fontsize=8,color=color,
                            fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.18",
                                      facecolor="white",edgecolor="none",alpha=.9))
            planta.plot(recorrido,lado,color=color,ls=estilo,lw=1.4)
        # Sólo apoyos reales: no inventar terreno ni despejes.
        ax.plot([0,horizontal],[ini[2],fin[2]],color="#777777",lw=.8,ls=":",
                label="Cuerda entre amarres")
        ax.scatter([0,horizontal],[ini[2],fin[2]],marker="s",color="black",s=23,zorder=4)
        ax.annotate("Apoyo A",(0,ini[2]),xytext=(5,9),
                    textcoords="offset points",fontsize=8)
        ax.annotate("Apoyo B",(horizontal,fin[2]),xytext=(-52,9),
                    textcoords="offset points",fontsize=8)
        span=max(.1,perfil_max-perfil_min)
        ax.set_ylim(perfil_min-.20*span,perfil_max+.25*span)
        ax.set_xlim(-horizontal*.02,horizontal*1.02)
        ax.set_title(f"{nombre} · luz horizontal {horizontal:.2f} m",fontsize=10)
        ax.set_ylabel("Cota del conductor (m)",fontsize=9)
        ax.grid(alpha=.22)
        ax.legend(loc="upper center",bbox_to_anchor=(.5,-.06),ncol=2,fontsize=7,
                  frameon=False)
        planta.axhline(0,ls=":",lw=.8,color="#777777")
        planta.scatter([0,horizontal],[0,0],color="black",s=17)
        planta.set_xlim(-horizontal*.02,horizontal*1.02)
        escala=max(.05,abs(lateral_min),abs(lateral_max))
        planta.set_ylim(-1.35*escala,1.35*escala)
        planta.set_xlabel("Distancia horizontal acumulada (m)",fontsize=9)
        planta.set_ylabel("Desvío lateral (m)",fontsize=9)
        planta.grid(alpha=.22)
        planta.set_title("Vista en planta · viento transversal local",fontsize=9)
        fig.subplots_adjust(top=.94,bottom=.10,hspace=.66,left=.09,right=.98)
        buffer=BytesIO()
        fig.savefig(buffer,format="png",dpi=160,facecolor="white")
        plt.close(fig)
        buffer.seek(0)
        salidas.append((nombre,buffer))
    return salidas
