"""Vista del MODELO global de red, independiente del cálculo preliminar.

La aplicación sólo inspecciona conectividad: no llama al solucionador global
con parámetros sintéticos ni aprueba apoyos automáticamente.
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from entradas.importar_red import leer_red_excel
from entradas.importar_hipotesis_red import (
    COLUMNAS_MATERIALES, COLUMNAS_ESTADOS,
    leer_materiales_excel, leer_estados_excel,
)
from calculos.hipotesis_red import calcular_hipotesis_red


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
    materiales=pd.DataFrame([{
        "Conductor":"2/0 ACSR",
        "Peso_kN_m":None,"Diametro_m":None,"EA_kN":None,
        "Alpha_por_C":None,"H_tendido_kN":None,
        "Temperatura_tendido_C":None,"Fuente":"",
    }],columns=COLUMNAS_MATERIALES)
    hipotesis=pd.DataFrame([{
        "Hipotesis":"Estado_1","Temperatura_C":None,
        "Viento_ms":None,"Azimut_deg":None,
    }],columns=COLUMNAS_ESTADOS)
    memoria=BytesIO()
    with pd.ExcelWriter(memoria,engine="openpyxl") as writer:
        puntos.to_excel(writer,index=False,sheet_name="Puntos")
        vanos.to_excel(writer,index=False,sheet_name="Vanos")
        materiales.to_excel(writer,index=False,sheet_name="Materiales")
        hipotesis.to_excel(writer,index=False,sheet_name="Hipotesis")
    return memoria.getvalue()


def _plantilla_calculo():
    """Caso de cálculo de dos vanos realmente anclados, sin suspensiones."""
    libro=pd.ExcelFile(BytesIO(_plantilla()))
    puntos=libro.parse("Puntos")
    vanos=libro.parse("Vanos")
    vanos["Seccion"]=["S1","S2"]
    vanos["Conexion_Inicio"]=["ANCLAJE","ANCLAJE"]
    vanos["Conexion_Fin"]=["ANCLAJE","ANCLAJE"]
    salida=BytesIO()
    with pd.ExcelWriter(salida,engine="openpyxl") as writer:
        puntos.to_excel(writer,index=False,sheet_name="Puntos")
        vanos.to_excel(writer,index=False,sheet_name="Vanos")
        libro.parse("Materiales").to_excel(writer,index=False,sheet_name="Materiales")
        libro.parse("Hipotesis").to_excel(writer,index=False,sheet_name="Hipotesis")
    return salida.getvalue()


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
    st.download_button(
        "Descargar plantilla para cálculo de dos vanos anclados",
        _plantilla_calculo(),
        file_name="plantilla_calculo_red.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(
        "La primera plantilla conserva una SUSPENSIÓN real para "
        "validar conectividad (su cálculo está pendiente). La segunda "
        "representa DOS secciones ancladas calculables. Ambas traen "
        "Puntos, Vanos, Materiales e Hipotesis; los valores de diseño "
        "quedan vacíos para que no se inventen. "
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
        st.markdown("#### Calcular hipótesis mecánicas de la red")
        st.caption(
            "Usa las hojas Materiales e Hipotesis del mismo Excel. "
            "Solo admite apoyos FIJO, amarres ANCLAJE/FIJA y guías "
            "DESLIZANTE ideales. No sustituye grapas de suspensión reales."
        )
        if st.button("Calcular tensiones y flechas por vano",key="calcular_red_bvp"):
            try:
                archivo.seek(0)
                libro=pd.ExcelFile(archivo)
                if "Materiales" not in libro.sheet_names or "Hipotesis" not in libro.sheet_names:
                    raise ValueError(
                        "Faltan las hojas Materiales e Hipotesis. "
                        "Descargá la plantilla actualizada."
                    )
                if any(n.fijacion!="FIJO" for n in red.apoyos.values()):
                    raise ValueError(
                        "La pantalla de cálculo solo admite apoyos FIJO. "
                        "Los apoyos MOVIL requieren rigideces documentadas."
                    )
                materiales=leer_materiales_excel(
                    libro.parse("Materiales"),
                    {v.conductor for v in red.vanos.values()},
                )
                climas=leer_estados_excel(libro.parse("Hipotesis"))
                with st.spinner("Resolviendo los estados mecánicos BVP..."):
                    calculo=calcular_hipotesis_red(red,materiales,climas)
                st.caption(calculo["estado"])
                for nombre,tabla in (
                    ("Resultados por vano",calculo["vanos"]),
                    ("Fuerzas por apoyo",calculo["apoyos"]),
                    ("Casos gobernantes",calculo["tensiones_gobernantes"]),
                    ("Guías deslizantes",calculo["secciones_deslizantes"]),
                ):
                    st.markdown("##### "+nombre)
                    if tabla.empty:
                        st.caption("No hay registros de este tipo.")
                        continue
                    st.dataframe(tabla,use_container_width=True,hide_index=True)
                    st.download_button(
                        "Exportar "+nombre+" CSV",
                        tabla.to_csv(index=False).encode("utf-8-sig"),
                        file_name=(
                            "red_"+nombre.lower().replace(" ","_")+".csv"
                        ),
                        mime="text/csv",
                        key="descarga_"+nombre,
                    )
            except (ValueError,TypeError,KeyError,OverflowError) as e:
                st.error(f"No se emitieron resultados: {e}")
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
