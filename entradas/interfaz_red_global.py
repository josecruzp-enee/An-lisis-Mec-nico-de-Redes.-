"""Vista del MODELO global de red, independiente del cálculo preliminar.

La aplicación sólo inspecciona conectividad: no llama al solucionador global
con parámetros sintéticos ni aprueba apoyos automáticamente.
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from entradas.importar_red import leer_red_excel


def _plantilla():
    """Excel de ejemplo con conectividad física declarada explícitamente."""
    puntos=pd.DataFrame({
        "Punto":["P1","P2","P3"],
        "X":[0.,40.,75.],"Y":[0.,0.,20.],
        "Altitud":[0.,2.,5.],"Poste":["PC-40"]*3,
        "Fijacion":["FIJO"]*3,
    })
    vanos=pd.DataFrame({
        "Vano":["V1","V2"],"Inicio":["P1","P2"],
        "Fin":["P2","P3"],"Circuito":["C1","C1"],
        "Seccion":["S1","S1"],"Conductor":["2/0 ACSR"]*2,
        "Conexion_Inicio":["ANCLAJE","SUSPENSION"],
        "Conexion_Fin":["SUSPENSION","ANCLAJE"],
        "Altura_Inicio_m":[9.5,9.5],"Altura_Fin_m":[9.5,9.5],
    })
    memoria=BytesIO()
    with pd.ExcelWriter(memoria,engine="openpyxl") as writer:
        puntos.to_excel(writer,index=False,sheet_name="Puntos")
        vanos.to_excel(writer,index=False,sheet_name="Vanos")
    return memoria.getvalue()


def mostrar_modelo_red():
    st.subheader("Modelo global de la red — conectividad")
    st.info(
        "Esta vista valida la geometría y las conexiones mecánicas "
        "de cada circuito. No calcula ni aprueba estructuras todavía."
    )
    st.download_button(
        "Descargar plantilla de red mecánica",
        _plantilla(),
        file_name="plantilla_red_mecanica.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(
        "La plantilla contiene datos ficticios. Se necesitan dos hojas: "
        "Puntos (postes, XYZ y condición FIJO/MOVIL) y Vanos "
        "(circuito, sección de tendido, alturas y tipo de conexión). "
        "No se deducen suspensiones ni remates de manera automática."
    )
    archivo=st.file_uploader(
        "Cargar red con hojas Puntos y Vanos",type=["xlsx"],
        key="red_global_excel",
    )
    if archivo is None:
        return
    try:
        red=leer_red_excel(archivo)
        a,b,c=st.columns(3)
        a.metric("Apoyos",len(red.apoyos))
        b.metric("Vanos",len(red.vanos))
        c.metric("Secciones mecánicas",len(red.secciones()))
        st.markdown("#### Secciones de tendido identificadas")
        secciones = pd.DataFrame(red.secciones())
        estados = []
        for registro in red.secciones():
            tipos = set()
            for nombre in registro["Identificadores"]:
                vano = red.vanos[nombre]
                tipos.update((vano.conexion_origen, vano.conexion_destino))
            if "SUSPENSION" in tipos:
                estado = "PENDIENTE: grapa/cadena de suspensión real"
            elif "DESLIZANTE" in tipos:
                estado = "IMPLEMENTADO: guía IDEAL sin fricción"
            else:
                estado = "IMPLEMENTADO: amarres sin deslizamiento"
            estados.append(estado)
        secciones["Estado modelo mecánico"] = estados
        st.dataframe(secciones, use_container_width=True, hide_index=True)
        st.markdown("#### Conexiones por apoyo")
        filas=[]
        enlaces=red.apoyos_conectados()
        for nombre,nodo in red.apoyos.items():
            filas.append({
                "Punto":nombre,"Modelo":nodo.modelo_apoyo,
                "Fijacion":nodo.fijacion,
                "Cantidad conexiones":len(enlaces[nombre]),
                "Vanos":", ".join(v for _,v,_ in enlaces[nombre]),
            })
        st.dataframe(pd.DataFrame(filas),use_container_width=True,
                     hide_index=True)
        st.caption(
            f"Componentes conexas: {len(red.componentes_conexas())}. "
            "El ensamblador admite amarres fijos y guías DESLIZANTE "
            "ideales con continuidad de tensión y longitud natural total. "
            "Las suspensiones con grapa real siguen pendientes y NO se "
            "reemplazan por una guía sin fricción. Esta vista no ejecuta "
            "un dimensionamiento estructural."
        )
    except (ValueError,TypeError,KeyError) as exc:
        st.error(f"Red mecánica inválida: {exc}")
