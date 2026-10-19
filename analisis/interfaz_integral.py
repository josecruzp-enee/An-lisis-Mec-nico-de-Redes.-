"""Controles Streamlit aislados del motor científico."""
import json
from pathlib import Path
import streamlit as st
from .motor_integral import ejecutar_proyecto_integral
from .memoria_calculo import exportar_json, exportar_excel_memoria, exportar_pdf_memoria


def controles_tendido():
    """No activa tensión, elasticidad ni libramiento por defecto."""
    with st.sidebar.expander('Tendido y perfil: datos explícitos'):
        tension = st.number_input('H de tendido por conductor (kN); 0 = sin dato',min_value=0.,value=0.)
        EA = st.number_input('Rigidez axial EA (kN); 0 = sin dato',min_value=0.,value=0.)
        alpha = st.number_input('Expansión térmica (1/°C); 0 = sin dato',min_value=0.,value=0.,format='%.8f')
        t0 = st.number_input('Temperatura de tendido (°C)',value=20.)
        t1 = st.number_input('Temperatura de evaluación (°C)',value=20.)
        limite = st.number_input('Despeje exigido (m); 0 = sin criterio',min_value=0.,value=0.)
        st.caption('H corresponde al tendido sin viento/hielo. EA y alpha deben ser del cable específico.')
    return dict(H_tendido_kN=tension or None,EA_kN=EA or None,alpha_por_C=alpha or None,
                temperatura_C=t1,temperatura_tendido_C=t0,despeje_min_m=limite or None)


def descargas(resultados,entrada=None):
    """Genera archivos sólo por solicitud, evitando recalcular PDFs en cada rerun."""
    with st.expander('Memoria y exportación reproducible'):
        if st.button('Preparar PDF, Excel y JSON'):
            st.download_button('Descargar JSON',exportar_json(resultados),'memoria_calculo.json','application/json')
            st.download_button('Descargar Excel',exportar_excel_memoria(resultados,entrada),
                               'memoria_calculo.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            st.download_button('Descargar PDF',exportar_pdf_memoria(resultados),'memoria_calculo.pdf','application/pdf')


def mostrar_proyecto_integral():
    """Carga configuración auditable y muestra fallas de validación sin aprobación parcial."""
    st.title('Proyecto integral: estados, acciones 3D y alternativas')
    st.warning('Versión candidata. Las verificaciones de material/suelo no implementadas quedan NO VERIFICABLE.')
    ejemplo = Path(__file__).resolve().parents[1]/'ejemplos/piloto_477_sintetico.json'
    st.download_button('Ejemplo sintético para aprender el formato',ejemplo.read_bytes(),ejemplo.name,'application/json')
    archivo = st.file_uploader('Proyecto JSON (ver docs/CONTRATOS.md)',type=['json'])
    if archivo is None:
        return
    try:
        resultado = ejecutar_proyecto_integral(json.load(archivo))
        for nombre in ('vanos_estados','acciones_nodos','envolventes','verificaciones_conductor','verificaciones','decision'):
            st.subheader(nombre.replace('_',' ').capitalize())
            st.dataframe(resultado[nombre],width="stretch")
        descargas(resultado)
    except (ValueError,KeyError,TypeError) as error:
        st.error(f'Proyecto no calculable: {error}')
