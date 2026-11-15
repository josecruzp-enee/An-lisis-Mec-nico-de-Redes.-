"""Interfaz separada: diseño inverso de tendido para UN vano anclado.

Nunca ejecuta silenciosamente sobre múltiples vanos ni establece
límites normativos por defecto. Las filas de hipótesis climáticas se
suministran explícitamente y tienen fuente documental.
"""
from __future__ import annotations

from io import BytesIO
import math

import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.conductores.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR
from Analisis_mecanico_conductores.conductores.referencias_mecanicas_acsr_nexans import referencia_mecanica_nexans
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_inversa_de_un_vano import HipotesisTendido, dimensionar_tension_tendido


COLUMNAS_HIPOTESIS = (
    "Hipotesis", "Temperatura_C", "Viento_ms", "Azimut_deg",
    "T_limite_kN", "Fuente_limite", "Criterio_diseno",
)


def leer_hipotesis_tabla(tabla):
    if not isinstance(tabla,pd.DataFrame) or tabla.empty:
        raise ValueError("Hoja Hipotesis vacía")
    falta=[c for c in COLUMNAS_HIPOTESIS if c not in tabla]
    if falta:
        raise ValueError("Hoja Hipotesis: faltan "+", ".join(falta))
    if tabla[list(COLUMNAS_HIPOTESIS)].isna().any().any():
        raise ValueError("Hoja Hipotesis: campos incompletos")
    return [
        HipotesisTendido(
            nombre=str(r["Hipotesis"]).strip(),
            temperatura_C=float(r["Temperatura_C"]),
            viento_ms=float(r["Viento_ms"]),
            azimut_viento_deg=float(r["Azimut_deg"]),
            tension_limite_kN=float(r["T_limite_kN"]),
            fuente_limite=str(r["Fuente_limite"]).strip(),
            criterio_diseno=str(r["Criterio_diseno"]).strip(),
        ) for _,r in tabla.iterrows()
    ]


def plantilla_tendido():
    """Excel sin límites de diseño ficticios: celdas en blanco."""
    puntos=pd.DataFrame({
        "Punto":["A","B"],"X":[0.,80.],"Y":[0.,0.],
        "Altitud":[0.,6.],"Altura_Amarre_m":[10.,10.],
    })
    hip=pd.DataFrame([
        {"Hipotesis":"Estado_1","Temperatura_C":None,
         "Viento_ms":None,"Azimut_deg":None,
         "T_limite_kN":None,"Fuente_limite":"",
         "Criterio_diseno":""},
        {"Hipotesis":"Estado_2","Temperatura_C":None,
         "Viento_ms":None,"Azimut_deg":None,
         "T_limite_kN":None,"Fuente_limite":"",
         "Criterio_diseno":""},
    ],columns=COLUMNAS_HIPOTESIS)
    salida=BytesIO()
    with pd.ExcelWriter(salida,engine="openpyxl") as writer:
        puntos.to_excel(writer,sheet_name="Puntos",index=False)
        hip.to_excel(writer,sheet_name="Hipotesis",index=False)
    return salida.getvalue()


def mostrar_tendido_inverso():
    st.subheader("Módulo 01 — Determinación de tensión de tendido")
    st.caption(
        "Cálculo inverso BVP de un vano con amarres fijos. "
        "Se requieren límites de diseño documentados en todas las "
        "hipótesis climáticas. No representa una sección en suspensión."
    )
    st.download_button(
        "Descargar plantilla de vano e hipótesis (Excel)",
        plantilla_tendido(),file_name="plantilla_tendido_inverso.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    archivo=st.file_uploader(
        "Excel de un vano: hojas Puntos e Hipotesis",
        type=["xlsx"],key="archivo_tendido_inverso"
    )
    aves=list(CONDUCTORES_VIAKON_ACSR)
    with st.form("config_tendido_inverso"):
        ave=st.selectbox("Conductor ACSR (calibre y pajarito)",aves,
             index=aves.index("2/0 ACSR — QUAIL") if "2/0 ACSR — QUAIL" in aves else 0)
        origen=st.radio("Origen propiedades termoelásticas",[
            "Datos documentados del conductor",
            "Referencia Nexans comparativa (NO apto para diseño)",
        ])
        c1,c2,c3=st.columns(3)
        with c1:
            temp_tendido=st.number_input("Temperatura de tendido (°C)",value=20.)
            Hmin=st.number_input("H mínima de búsqueda (kN)",min_value=.01,value=1.)
        with c2:
            Hmax=st.number_input("H máxima de búsqueda (kN)",min_value=.02,value=6.)
            EA=st.text_input("EA (kN), si dispone de ficha",value="")
        with c3:
            alpha=st.text_input("Dilatación α (1/°C), si dispone de ficha",value="")
            fuente=st.text_input("Documento/edición del material",value="")
        temperaturas=st.text_input("Temperaturas para tabla (°C)",value="0,10,20,30,40")
        enviar=st.form_submit_button("Determinar tensión y generar tabla")
    if not enviar:
        return
    if archivo is None:
        st.error("Cargá la plantilla Excel completada.")
        return
    try:
        libro=pd.ExcelFile(BytesIO(archivo.getvalue()))
        if not {"Puntos","Hipotesis"}.issubset(libro.sheet_names):
            raise ValueError("El libro requiere hojas Puntos e Hipotesis")
        puntos=pd.read_excel(libro,sheet_name="Puntos")
        if len(puntos)!=2:
            raise ValueError(
                "Esta pantalla solo admite dos puntos de UN vano fijo. "
                "No transforma silenciosamente una red en vanos independientes."
            )
        campos=["Punto","X","Y","Altitud","Altura_Amarre_m"]
        if any(c not in puntos for c in campos) or puntos[campos].isna().any().any():
            raise ValueError("Puntos: se requieren identificador, XYZ y altura de amarre")
        coordenadas=[]
        for _,p in puntos.iterrows():
            z=float(p["Altitud"])+float(p["Altura_Amarre_m"])
            if not math.isfinite(z) or float(p["Altura_Amarre_m"])<=0:
                raise ValueError("Altura de amarre inválida")
            coordenadas.append((float(p["X"]),float(p["Y"]),z))
        hipotesis=leer_hipotesis_tabla(pd.read_excel(libro,sheet_name="Hipotesis"))
        ficha=CONDUCTORES_VIAKON_ACSR[ave]
        if origen.startswith("Referencia"):
            comparativa=referencia_mecanica_nexans(ave)
            rigidez=comparativa["EA_final_referencia_kN"]
            dilatacion=comparativa["alpha_final_referencia_por_C"]
            fuente_material=comparativa["fuente"]
            st.warning(
                "ESTUDIO DE SENSIBILIDAD: módulo final Nexans por construcción "
                "equivalente, no propiedades certificadas del ACSR Viakon. "
                "No utilices este resultado para aprobar un tendido real."
            )
        else:
            if not EA.strip() or not alpha.strip() or not fuente.strip():
                raise ValueError("Ingresá EA, dilatación y fuente documentada")
            rigidez=float(EA)
            dilatacion=float(alpha)
            fuente_material=fuente
        if Hmax>=float(ficha["carga_rotura_kN"]):
            raise ValueError(
                "H máxima de búsqueda alcanza la ruptura nominal del "
                "conductor. Elegí un intervalo físicamente válido."
            )
        temp_lista=[float(x.strip()) for x in temperaturas.split(",") if x.strip()]
        res=dimensionar_tension_tendido(
            *coordenadas,hipotesis=hipotesis,
            temperaturas_tabla_C=temp_lista,
            temperatura_tendido_C=temp_tendido,
            peso_kN_m=ficha["peso_kg_m"]*9.80665/1000,
            diametro_m=ficha["diametro_m"],
            EA_kN=rigidez,alpha_por_C=dilatacion,
            fuente_material=fuente_material,
            H_min_kN=Hmin,H_max_kN=Hmax,
        )
        st.metric("Tensión horizontal de referencia",f"{res.H_tendido_kN:.4f} kN")
        st.caption(
            f"Hipótesis gobernante: {res.caso_gobernante}; "
            f"relación máxima T/límite: {res.razon_maxima:.5f}. "
            f"{res.estado}. BVP evaluados: {res.evaluaciones_bvp}"
        )
        for nombre, registros in (("Hipótesis climáticas",res.hipotesis),
                                  ("Tabla de tendido",res.tabla_tendido)):
            tabla=pd.DataFrame(registros)
            st.markdown("#### "+nombre)
            st.dataframe(tabla,use_container_width=True,hide_index=True)
            st.download_button(
                "Exportar "+nombre+" CSV",
                tabla.to_csv(index=False).encode("utf-8-sig"),
                file_name=("hipotesis_tendido.csv" if "Hipótesis" in nombre
                           else "tabla_tendido.csv"),
                mime="text/csv",
            )
        st.warning(
            "Los límites suministrados no se han validado como norma hondureña. "
            "Faltan comprobaciones de creep, vibración, topografía y "
            "compatibilidad entre vanos; resultado de alcance limitado."
        )
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        st.error(str(exc))
