"""Fuerzas de los cables sobre todos los apoyos desde estados CFE calculados.

Reutiliza reacciones vectoriales EXACTAS de resolver_catenaria.fuerzas.
La presión CFE por claro y la carga de hielo son idénticas a las empleadas
por el generador de perfiles y el motor. NO adiciona peso de postes ni
viento sobre estructuras y NO certifica su resistencia.

NOTA: CFE usa viento transversal LOCAL para cada vano. La suma vectorial
representa esa envolvente local, no un evento de viento geográfico uniforme.
"""
from __future__ import annotations
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import calcular_flecha_y_desviacion_3d
from Analisis_mecanico_conductores.salidas.PDF.graficos_catenarias_cfe import _carga


CASOS = (
    ("H1", "Inicial", 0., 0., 0.),
    ("H2", "Final", 16., 0., 0.),
    ("H3", "Final", 0., 0., 0.),
    ("H4", "Final", -10., 109., None),
    ("H5", "Final", 0., 120., 0.),
)


def calcular_fuerzas_por_apoyo(tabla, puntos, propiedades, clima):
    """Retorna (detalle por vano extremo, suma por apoyo, envolvente por apoyo).

    Las reacciones están en kN y describen fuerza del cable SOBRE el apoyo.
    H1..H5 son hipótesis de diseño; los estados térmicos adicionales se
    conservan en las tablas del motor, pero aquí no se mezclan con H1..H5.
    """
    if not isinstance(puntos, pd.DataFrame) or len(puntos)<2:
        raise ValueError("La tabla de apoyos completa es obligatoria")
    required={"Punto","X","Y","Altitud","Altura_Amarre_m"}
    if not required.issubset(puntos):
        raise ValueError(f"Faltan columnas de apoyos: {sorted(required-set(puntos))}")
    pts=puntos.reset_index(drop=True)
    nombres=pts["Punto"].astype(str).str.strip().tolist()
    if len(set(nombres))!=len(nombres):
        raise ValueError("Identificadores de apoyos repetidos")
    xy=pts[["X","Y"]].to_numpy(float)
    alt=pts["Altitud"].to_numpy(float)+pts["Altura_Amarre_m"].to_numpy(float)
    xyz=np.column_stack([xy,alt])
    if not np.isfinite(xyz).all():
        raise ValueError("Coordenadas de amarre no finitas")
    vano_ids=[f"{a} → {b}" for a,b in zip(nombres[:-1],nombres[1:])]
    datos=tabla.copy()
    if set(datos["Vano"].astype(str))!=set(vano_ids):
        raise ValueError("Las etiquetas de vanos no coinciden con los apoyos")
    # Las cinco hipótesis se emparejan por condición, temperatura, viento,
    # hielo y, para escenarios de viento, por la etiqueta documentada.
    filas=[]
    for caso,cond,t,v,h in CASOS:
        sub=datos[(datos["Condición"]==cond)&
                  np.isclose(datos["Temperatura (°C)"].astype(float),t)&
                  np.isclose(datos["Viento (km/h)"].astype(float),v)]
        if h is None:
            hielo=float(clima.get("hielo_mm",0.))
        else:
            hielo=h
        sub=sub[np.isclose(sub["Hielo (mm)"].astype(float),hielo)]
        if v>0:
            palabra="reducido" if caso=="H4" else "máximo"
            sub=sub[sub["Hipótesis"].astype(str).str.contains(palabra,case=False,regex=False)]
        else:
            sub=sub[sub["Hipótesis"].astype(str)=="Tabla térmica"]
        if len(sub)!=len(vano_ids) or sub["Vano"].duplicated().any():
            raise ValueError(f"{caso}: debe existir un resultado por vano")
        for i,vano in enumerate(vano_ids):
            row=sub.loc[sub["Vano"]==vano].iloc[0]
            q=_carga(xyz,i,row,propiedades[cond],clima)
            cable=resolver_catenaria(xyz[i],xyz[i+1],q,float(row["H (kN)"]))
            total=max(float(cable.tension(0)),float(cable.tension(cable.luz)))
            if abs(total-float(row["T máx. (kN)"]))>2e-4:
                raise ValueError(f"{caso} {vano}: tensión de extremos no coincide")
            flecha,lateral=calcular_flecha_y_desviacion_3d(cable,xyz[i],xyz[i+1])
            if abs(flecha-float(row["Flecha (m)"]))>2e-4 or abs(lateral-float(row["Lateral (m)"]))>2e-4:
                raise ValueError(f"{caso} {vano}: geometría de catenaria no coincide")
            fa,fb=cable.fuerzas
            for k,force in ((i,fa),(i+1,fb)):
                force=np.asarray(force,dtype=float)
                filas.append({
                    "Hipótesis":caso,"Condición":cond,
                    "Apoyo":nombres[k],"Vano":vano,
                    "Sección":str(row.get("Sección","S1")),
                    "Fx (kN)":float(force[0]),"Fy (kN)":float(force[1]),
                    "Fz (kN)":float(force[2]),
                    "F resultante (kN)":float(np.linalg.norm(force)),
                })
    detalle=pd.DataFrame(filas)
    suma=(detalle.groupby(["Hipótesis","Condición","Apoyo"],sort=False,as_index=False)
          [["Fx (kN)","Fy (kN)","Fz (kN)"]].sum())
    suma["F resultante (kN)"]=np.linalg.norm(
        suma[["Fx (kN)","Fy (kN)","Fz (kN)"]].to_numpy(float),axis=1
    )
    envolvente=(suma.loc[suma.groupby("Apoyo",sort=False)["F resultante (kN)"].idxmax()]
                .reset_index(drop=True))
    return detalle,suma,envolvente


def grafico_red_y_fuerzas(puntos, detalle, sumas, *, hipotesis="H4"):
    """Plano general de apoyos, secciones y vectores horizontales por apoyo."""
    pts=puntos.reset_index(drop=True)
    n=pts["Punto"].astype(str).tolist()
    xx=pts["X"].to_numpy(float)
    yy=pts["Y"].to_numpy(float)
    sub=sumas[sumas["Hipótesis"]==hipotesis].set_index("Apoyo")
    if set(n)!=set(sub.index):
        raise ValueError("No existen resultantes para todos los apoyos")
    fig,ax=plt.subplots(figsize=(11.4,5.8))
    ax.plot(xx,yy,"-",lw=1.7,color="#475569",alpha=.75)
    section_map={}
    for _,r in detalle[detalle["Hipótesis"]==hipotesis].iterrows():
        section_map[str(r["Vano"])]=str(r["Sección"])
    colors=plt.rcParams["axes.prop_cycle"].by_key()["color"]
    ids=list(dict.fromkeys(section_map.values()))
    for i in range(len(n)-1):
        sec=section_map[f"{n[i]} → {n[i+1]}"]
        color=colors[ids.index(sec)%len(colors)]
        ax.plot(xx[i:i+2],yy[i:i+2],"-",color=color,lw=3,label=sec if sec not in section_map.values() else None)
        length=float(np.hypot(xx[i+1]-xx[i],yy[i+1]-yy[i]))
        ax.annotate(f"{length:.1f} m  ({sec})",
                    ((xx[i]+xx[i+1])/2,(yy[i]+yy[i+1])/2),
                    xytext=(0,-15),textcoords="offset points",ha="center",fontsize=8,
                    bbox=dict(fc="white",ec="none",alpha=.8))
    remates={n[0],n[-1]}
    if "Remate" in pts:
        remates.update(str(r["Punto"]) for _,r in pts.iterrows()
                      if str(r["Remate"]).strip().upper() in ("SI","SÍ","REMATE","1","TRUE"))
    for i,name in enumerate(n):
        remate=name in remates
        ax.scatter(xx[i],yy[i],s=85 if remate else 45,
                   marker="s" if remate else "o",
                   facecolor="white",edgecolor="#b91c1c" if remate else "#334155",
                   lw=2,zorder=4)
        ax.annotate(name+(" (R)" if remate else ""), (xx[i],yy[i]),
                    xytext=(5,12),textcoords="offset points",fontsize=9,weight="bold")
    fx=np.array([float(sub.loc[name,"Fx (kN)"]) for name in n])
    fy=np.array([float(sub.loc[name,"Fy (kN)"]) for name in n])
    mag=np.hypot(fx,fy)
    if mag.max()>1e-10:
        dx=xx.max()-xx.min()
        dy=yy.max()-yy.min()
        ext=max(dx,dy,1.)
        factor=.15*ext/mag.max()
        for i,name in enumerate(n):
            if mag[i]<=1e-10:continue
            ax.annotate("",xy=(xx[i]+fx[i]*factor,yy[i]+fy[i]*factor),
                        xytext=(xx[i],yy[i]),
                        arrowprops=dict(arrowstyle="-|>",color="#b91c1c",lw=2))
    ax.set_title(f"Red completa — fuerzas del conductor sobre apoyos, {hipotesis} (CFE local)",fontsize=12)
    ax.set_xlabel("Coordenada X (m)")
    ax.set_ylabel("Coordenada Y (m)")
    ax.set_aspect("equal",adjustable="datalim")
    ax.margins(.25)
    ax.grid(ls=":",alpha=.35)
    fig.tight_layout()
    b=BytesIO()
    fig.savefig(b,format="png",dpi=150,facecolor="white")
    plt.close(fig)
    b.seek(0)
    return b
