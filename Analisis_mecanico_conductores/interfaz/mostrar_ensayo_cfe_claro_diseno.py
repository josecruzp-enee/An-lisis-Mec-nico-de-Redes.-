"""UI de investigación CFE 2014: diseño y tablas por claro regla.

No usa las tablas ENEE como entradas. No sustituye memoria de cálculo
de la Etapa 1 ni certifica equivalencia SAGSEC. Temperatura/viento/hielo
se informan explícitamente y los límites son porcentajes CFE 05 00 02.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee, seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE,HipotesisDisenoCFE,
)
from Analisis_mecanico_conductores.tension_tendido.cfe_claro_diseno_y_claros_regla import (
    DisenoCFE, calcular_corridas_claros,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    _geometria,
)


def mostrar_ensayo_cfe_diseno(puntos):
    st.subheader("CFE — claro de diseño, condiciones inicial/final y claros regla")
    st.warning(
        "Investigación: el cálculo de referencia se realiza desde el claro "
        "de diseño; la condición inicial deriva de la final por compatibilidad "
        "de longitudes. La deformación permanente requiere evidencia y no "
        "puede inferirse solo de EA. No reproduce todavía SAGSEC ni certifica "
        "cumplimiento ENEE. No carga tablas de flechas ENEE."
    )
    opciones=[(p["calibre"],p["nombre"]) for p in leer_catalogo_enee()]
    with st.form("ensayo_cfe_diseno"):
        seleccionado=st.selectbox(
            "Conductor ENEE",opciones,
            format_func=lambda x:f"{x[0]} — {x[1]}",
        )
        c1,c2=st.columns(2)
        with c1:
            claro=st.number_input(
                "Claro de diseño (m)",min_value=1.,value=100.,step=1.,
                help="No es el claro regla. Debe justificarse por estructuras, despejes y cálculo CFE.",
            )
            flecha=st.number_input(
                "Flecha de referencia a 50°C, condición FINAL (m)",
                min_value=.01,value=1.50,step=.05,
                help="CFE emplea 1.5 m como punto de partida en casos específicos; no universal.",
            )
            epsilon=st.number_input(
                "Deformación permanente final ε (adimensional)",min_value=0.,
                max_value=.1,value=0.,format="%.6f",
                help="0 = ensayo SIN CREEP, NO resultado final histórico de CFE.",
            )
            temp_min=st.number_input("Temperatura mínima (°C)",value=-10.)
            temp_max=st.number_input("Temperatura máxima (°C)",value=50.)
            temp_paso=st.number_input("Paso (°C)",min_value=1.,value=5.)
        with c2:
            viento_max=st.number_input(
                "Viento máximo (km/h)",min_value=0.,value=120.,
            )
            viento_reducido=st.number_input(
                "Viento reducido (km/h)",min_value=0.,value=109.,
            )
            hielo=st.number_input(
                "Hielo radial a −10°C (mm)",min_value=0.,value=0.,step=.5,
                help="Dato climático explícito: 0 no representa una hipótesis con hielo.",
            )
            usar_claros=st.checkbox(
                "Usar longitudes de los vanos cargados como claros de ensayo",value=True,
            )
            claros_texto=st.text_input(
                "Claros regla adicionales (m), separados por coma",
                value="30,40,50,60,70,80,90,100",
            )
            Cd=st.number_input(
                "Coeficiente aerodinámico de ensayo Cd",min_value=.1,value=1.,
            )
            rho=st.number_input(
                "Densidad de aire (kg/m³)",min_value=.1,value=1.225,
            )
        enviar=st.form_submit_button("Calcular desde claro de diseño")
    if not enviar:return
    try:
        if temp_max<temp_min:
            raise ValueError("Temperatura máxima debe ser >= mínima")
        ini=seleccionar_conductor_enee(*seleccionado,"Inicial")
        fin=seleccionar_conductor_enee(*seleccionado,"Final")
        p=PropiedadesConductorCFE(
            float(ini["peso_kN_m"]),float(ini["diametro_m"]),
            float(ini["EA_kN"]),float(fin["EA_kN"]),
            float(ini["alpha_por_C"]),float(fin["alpha_por_C"]),
            float(ini["ruptura_kN"]),str(ini["fuente"])+" | "+str(fin["fuente"]),
        )
        xyz,luces=_geometria(puntos)
        if np.ptp(xyz[:,2])>1e-5:
            raise ValueError(
                "La comparación CFE por claro regla requiere apoyos nivelados; "
                "el motor 3D previo sigue disponible para desniveles."
            )
        d=DisenoCFE(
            claro_diseno_m=float(claro),
            flecha_final_referencia_50C_m=float(flecha),
            epsilon_permanente=float(epsilon),
            Cd=float(Cd),rho_kg_m3=float(rho),
        )
        fuente="CFE DCCIAMBT 2014, 05 00 02, límites de diseño básico"
        # 20%,25%,45% (final) y 33% (inicial) de ruptura.
        hip_fin=[
            HipotesisDisenoCFE("Final 16°C",16.,0.,0.,.20*p.ruptura_kN,fuente),
            HipotesisDisenoCFE("Final 0°C",0.,0.,0.,.25*p.ruptura_kN,fuente),
            HipotesisDisenoCFE("TH1 -10°C", -10.,viento_reducido,hielo,.45*p.ruptura_kN,fuente),
            HipotesisDisenoCFE("TH2 0°C",0.,viento_max,0.,.45*p.ruptura_kN,fuente),
        ]
        hip_ini=[
            HipotesisDisenoCFE("Inicial 0°C",0.,0.,0.,.33*p.ruptura_kN,fuente),
        ]
        claros=[float(v.strip()) for v in claros_texto.split(",") if v.strip()]
        if usar_claros:claros.extend(float(x) for x in luces)
        claros=sorted(set(claros))
        if not claros:
            raise ValueError("Ingresá al menos un claro regla")
        temperaturas=np.arange(temp_min,temp_max+temp_paso*.5,temp_paso)
        extras=[
            HipotesisDisenoCFE("TH1", -10.,viento_reducido,hielo,p.ruptura_kN,fuente),
            HipotesisDisenoCFE("TH2",0.,viento_max,0.,p.ruptura_kN,fuente),
        ]
        ref,referencias,tabla=calcular_corridas_claros(
            p,d,hip_fin,hip_ini,claros,temperaturas,extras,
        )
        st.subheader("Referencia física del claro de diseño")
        st.dataframe(pd.DataFrame([ref]),hide_index=True,use_container_width=True)
        st.subheader("P y H calculados por cada claro regla")
        st.dataframe(referencias,hide_index=True,use_container_width=True)
        st.subheader("Condición inicial y final por temperatura y claro")
        st.dataframe(tabla,hide_index=True,use_container_width=True)
        st.download_button(
            "Exportar tabla calculada CSV",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            file_name="cfe_diseno_y_claros_regla.csv",mime="text/csv",
        )
        if hielo==0:
            st.error(
                "TH1 se calculó sin hielo porque se introdujo 0 mm. "
                "No usar esta corrida para validar contra ENEE."
            )
        if epsilon==0:
            st.info(
                "Condición final sin deformación permanente: "
                "modelo termoelástico de ensayo, no predicción del creep."
            )
        st.caption(
            "La extrapolación de flecha de diseño a otros claros regla "
            "es una hipótesis del motor, no una ecuación atribuible a SAGSEC. "
            "Las tablas ENEE se compararán externamente, sin alimentar el modelo."
        )
    except (ValueError,KeyError,TypeError,ArithmeticError,OverflowError) as exc:
        st.error(f"No fue posible completar el cálculo: {exc}")
