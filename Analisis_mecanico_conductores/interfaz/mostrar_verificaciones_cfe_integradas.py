"""Evaluación integrada posterior al solver CFE de vanos individuales.

Solo usa magnitudes calculadas. Las tablas CFE son referencias mexicanas
específicas, nunca capacidades sustitutas para estructuras ENEE.
"""
from __future__ import annotations
import math
import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.verificaciones.verificar_restricciones_documentadas_cfe import (
    verificar_tabla_estructura, verificar_fases, verificar_vertical_superficie,
    verificar_horizontal_construccion, verificar_traccion,
    ALTURAS_MINIMAS_MT_M, SEPARACION_HORIZONTAL_CONSTRUCCIONES_M,
)


def evaluar_corrida_documentada(tabla, puntos, *, estructura, conductor,
                                clase_kV, tipo_superficie=None,
                                separacion_fases_m=None, distancia_construccion_m=None,
                                ambiente="normal", hielo=False):
    """Cruza tabla climática por vano con comprobaciones documentales.

    Si no existen cota de terreno, amarre, separación real de fases u
    obstáculos, la verificación correspondiente es NO VERIFICABLE.
    """
    if tabla.empty:
        raise ValueError("No existen corridas para verificar")
    vanos = list(zip(puntos["Punto"].astype(str).iloc[:-1],
                     puntos["Punto"].astype(str).iloc[1:]))
    area = {"RAVEN":62.4378,"PIGEON":99.3038,
            "PARTRIDGE":156.8655,"LINNET":198.3854,
            "HAWK":280.8395}.get(conductor.upper())
    if area is None:
        raise ValueError("Conductor sin área CFE documentada")
    hay_terreno = ("Altitud" in puntos and "Altura_Amarre_m" in puntos
                   and puntos["Altitud"].notna().all()
                   and puntos["Altura_Amarre_m"].notna().all())
    if hay_terreno:
        terreno = puntos["Altitud"].astype(float).to_numpy()
        amarres = puntos["Altura_Amarre_m"].astype(float).to_numpy()
        plano = bool(max(terreno)-min(terreno) < 1e-7)
    else:
        plano = False
    # Ángulos geométricos reales entre tramos: 0° significa alineamiento.
    coordenadas=puntos[["X","Y"]].to_numpy(dtype=float)
    angulos_apoyo=[0.]*len(puntos)
    for j in range(1,len(puntos)-1):
        ax=float(coordenadas[j,0]-coordenadas[j-1,0])
        ay=float(coordenadas[j,1]-coordenadas[j-1,1])
        bx=float(coordenadas[j+1,0]-coordenadas[j,0])
        by=float(coordenadas[j+1,1]-coordenadas[j,1])
        if math.hypot(ax,ay)<=0 or math.hypot(bx,by)<=0:
            raise ValueError("Vano de longitud cero en geometría de apoyos")
        angulos_apoyo[j]=math.degrees(math.atan2(
            abs(ax*by-ay*bx),ax*bx+ay*by,
        ))
    resultados=[]
    for i,(p,q) in enumerate(vanos):
        clave=f"{p} → {q}"
        grupo=tabla.loc[tabla["Vano"]==clave]
        final50=grupo.loc[(grupo["Condición"]=="Final")
                         & (grupo["Hipótesis"]=="Tabla térmica")
                         & ((grupo["Temperatura (°C)"]-50.).abs()<1e-7)]
        tension_ini=grupo.loc[(grupo["Condición"]=="Inicial")
                             & (grupo["Hipótesis"]=="Tabla térmica")
                             & ((grupo["Temperatura (°C)"]).abs()<1e-7)]
        final16=grupo.loc[(grupo["Condición"]=="Final")
                         & (grupo["Hipótesis"]=="Tabla térmica")
                         & ((grupo["Temperatura (°C)"]-16.).abs()<1e-7)]
        luz=float(grupo["Luz (m)"].iloc[0])
        luz_real=math.hypot(
            float(coordenadas[i+1,0]-coordenadas[i,0]),
            float(coordenadas[i+1,1]-coordenadas[i,1]),
        )
        if abs(luz-luz_real)>max(0.01,1e-6*luz_real):
            raise ValueError(
                f"{clave}: la luz de los resultados ({luz:.3f}m) no coincide "
                f"con la geometría ({luz_real:.3f}m)."
            )
        angulo_mayor=max(angulos_apoyo[i],angulos_apoyo[i+1])
        desnivel=(abs(float((terreno[i+1]+amarres[i+1])-
                             (terreno[i]+amarres[i])))
                 if hay_terreno else None)
        tb=verificar_tabla_estructura(
            luz,estructura,f"ACSR {conductor.upper()} "+
            {"RAVEN":"1/0","PIGEON":"3/0","PARTRIDGE":"266.8",
             "LINNET":"336.4","HAWK":"477"}[conductor.upper()],
            clase_kV,ambiente,hielo=hielo,
            angulo_grados=angulo_mayor,desnivel_m=desnivel,
        )
        f50=float(final50["Flecha (m)"].iloc[0]) if len(final50)==1 else None
        fases=verificar_fases(clase_kV,f50,area,separacion_fases_m) if f50 is not None else {"estado":"NO VERIFICABLE"}
        if f50 is not None and plano and abs(float(amarres[i]-amarres[i+1]))<1e-7:
            zmin=float(terreno[i]+amarres[i])-f50
            altura=verificar_vertical_superficie(
                zmin,float(terreno[i]),tipo_superficie,
            )
        else:
            altura={"estado":"NO VERIFICABLE",
                    "motivo":"Requiere terreno plano, amarres a igual cota y cotas completas"}
        viento16=grupo.loc[(grupo["Condición"]=="Final")
                         &(grupo["Hipótesis"]=="Exploratorio 16°C viento máximo")
                         &((grupo["Temperatura (°C)"]-16.).abs()<1e-7)]
        if distancia_construccion_m is not None and len(viento16)==1:
            desplazamiento=float(viento16["Lateral (m)"].iloc[0])
            # Comprobación conservadora: se resta el desplazamiento
            # absoluto aunque el viento real aleje el cable del edificio.
            horizontal=verificar_horizontal_construccion(
                clase_kV,distancia_construccion_m,desplazamiento
            )
            if horizontal["estado"] in ("CUMPLE","NO CUMPLE"):
                horizontal["estado"] += " (ENSAYO VIENTO DECLARADO, NO CFE 02 00 04)"
        else:
            horizontal={"estado":"NO VERIFICABLE",
                        "motivo":"Se requiere distancia a construcción y corrida 16°C con viento"}
        # Comprobaciones de tracción disponibles: usar T resultante,
        # no componente H; no declarar completa si falta un caso.
        por_caso={
            "final_16C_sin_viento":("Final","Tabla térmica",16.),
            "final_0C_sin_viento":("Final","Tabla térmica",0.),
            "inicial_0C_sin_viento":("Inicial","Tabla térmica",0.),
            "final_menos10C_viento_reducido_hielo":("Final","CFE viento reducido + hielo",-10.),
            "final_0C_viento_maximo":("Final","CFE viento máximo",0.),
        }
        tensiones={}
        for estado,(cond,nom,temp) in por_caso.items():
            coincidencias=grupo.loc[(grupo["Condición"]==cond)
                                   &(grupo["Hipótesis"]==nom)
                                   &((grupo["Temperatura (°C)"]-temp).abs()<1e-7)]
            if len(coincidencias)==1:
                tensiones[estado]=float(coincidencias["T máx. (kN)"].iloc[0])*1000.
        rotura_N={"RAVEN":19477.4,"PIGEON":29382.8,"PARTRIDGE":50223.4,
                  "LINNET":62992.6,"HAWK":86549.8}[conductor.upper()]
        traccion=verificar_traccion(rotura_N,tensiones)
        fallo_t = any(x["estado"]=="NO CUMPLE" for x in traccion.values())
        parcial_t = any(x["estado"]=="NO VERIFICABLE" for x in traccion.values())
        criterios_tb=tb.get("criterios",{})
        excedidos=[k for k,v in criterios_tb.items() if not v["cumple"]]
        resultados.append({
            "Vano":clave,"Luz (m)":luz,
            "Deflexión máx. en apoyos (°)":angulo_mayor,
            "Desnivel entre amarres (m)":desnivel,
            "P final 50°C (m)":float(final50["P a 50 °C (m)"].iloc[0]) if len(final50)==1 else None,
            "Flecha final 50°C (m)":f50,
            "T final 0°C (kN)":float(grupo.loc[(grupo["Condición"]=="Final") &
                (grupo["Hipótesis"]=="Tabla térmica") &
                (grupo["Temperatura (°C)"].abs()<1e-7),
                "T máx. (kN)"].iloc[0]) if len(grupo.loc[(grupo["Condición"]=="Final") &
                (grupo["Hipótesis"]=="Tabla térmica") &
                (grupo["Temperatura (°C)"].abs()<1e-7)])==1 else None,
            "Tracción CFE":("NO CUMPLE" if fallo_t else
                             "NO VERIFICABLE" if parcial_t else "CUMPLE"),
            "Tabla estructura CFE":tb["estado"],
            "Limitantes excedidas CFE":", ".join(excedidos),
            "Libramiento vertical":altura["estado"],
            "Separación entre fases":fases["estado"],
            "Libramiento horizontal edificio":horizontal["estado"],
            "Fuente tabla":f"CFE {estructura}, p. {tb.get('pagina_pdf','sin fila')}",
        })
    return pd.DataFrame(resultados)


def mostrar_verificacion_integrada(tabla, puntos, conductor, *, hielo_mm=0.):
    """Panel opcional, no sustituye cálculo principal ni certificados ENEE."""
    st.subheader("Verificaciones documentadas del cálculo por vano")
    st.warning("Las capacidades de estructuras CFE NO sustituyen las de ENEE en Honduras.")
    c1,c2,c3=st.columns(3)
    with c1:
        clase=st.selectbox("Clase de tabla CFE (kV)",[13,23,33],index=0,
                          help="13 kV corresponde a la familia de tablas; no cambia la tensión nominal del proyecto.")
    with c2:
        estructura=st.selectbox("Estructura CFE comparativa",
                               ["TS3N","PS3N","TD3N","PD3N","VD3N"],
                               help="Referencia funcional, NO selección automática de estructura ENEE.")
    with c3:
        ambiente=st.selectbox("Ambiente CFE",["normal","contaminacion"])
    categoria=st.selectbox("Categoría de superficie",
                           ["Sin definir"]+list(ALTURAS_MINIMAS_MT_M),
                           help="Necesaria para libramiento vertical normativo.")
    separacion=st.number_input("Separación mínima real entre fases (m; 0 = no disponible)",
                               value=0.,min_value=0.,step=.1)
    obstaculo=st.number_input("Distancia horizontal MÍNIMA en reposo para todos los vanos (m; 0 = sin dato)",
                              value=0.,min_value=0.,step=.1)
    comprobacion=evaluar_corrida_documentada(
        tabla,puntos,estructura=estructura,conductor=conductor,
        clase_kV=clase,tipo_superficie=None if categoria=="Sin definir" else categoria,
        separacion_fases_m=separacion if separacion>0 else None,
        distancia_construccion_m=obstaculo if obstaculo>0 else None,
        ambiente=ambiente,hielo=hielo_mm>0,
    )
    st.dataframe(comprobacion,hide_index=True,use_container_width=True)
    st.download_button("Descargar verificación conjunta CSV",
                       comprobacion.to_csv(index=False).encode("utf-8-sig"),
                       "verificacion_integral_cfe_por_vano.csv","text/csv",
                       key="descarga_verificacion_cfe_integral")
    st.caption("Horizontal: usa desplazamiento numérico a 16°C con viento máximo declarado; "
               "es un ensayo conservador, NO la condición de presión específica CFE 02 00 04.")
    return comprobacion
