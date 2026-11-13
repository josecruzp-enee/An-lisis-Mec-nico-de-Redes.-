"""Interfaz Streamlit del barrido termo-mecánico 3D (versión experimental).

Los datos de material faltantes se solicitan; nunca se inventan.
Los resultados son solicitaciones, NO verificaciones estructurales.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from entradas.io_excel import leer_puntos_excel
from entradas.catalogos import CONDUCTORES_ACSR
from calculos.barrido_3d import ejecutar_barrido_3d


def _numeros(texto, campo, positivos=False):
    """Convierte una lista de valores sin completar silenciosamente faltantes."""
    valores = []
    for parte in texto.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        valor = float(parte)
        if not math.isfinite(valor) or (positivos and valor <= 0):
            raise ValueError(f"{campo}: valores no válidos")
        valores.append(valor)
    if not valores:
        raise ValueError(f"{campo}: introduzca al menos un valor")
    return valores


def _vanos_desde_excel(df):
    """Los amarres se expresan como desplazamientos XYZ relativos al terreno."""
    requeridas = ("Punto", "X", "Y", "Altitud", "Altura_Amarre_m")
    faltan = [c for c in requeridas if c not in df.columns]
    if faltan:
        raise ValueError("Faltan columnas para análisis 3D: " + ", ".join(faltan))
    if df[list(requeridas)].isna().any().any():
        raise ValueError("Hay cotas o alturas de amarre vacías")
    h = df["Altura_Amarre_m"].astype(float)
    if (h <= 0).any() or not h.map(math.isfinite).all():
        raise ValueError("Altura_Amarre_m debe ser positiva y finita")
    resultado = []
    for i in range(len(df)-1):
        a, b = df.iloc[i], df.iloc[i+1]
        resultado.append({
            "nombre": f"{a['Punto']} → {b['Punto']}",
            "inicio": str(a["Punto"]), "fin": str(b["Punto"]),
            "base_inicio_m": [float(a["X"]), float(a["Y"]), float(a["Altitud"])],
            "base_fin_m": [float(b["X"]), float(b["Y"]), float(b["Altitud"])],
            "amarre_inicio_m": [0, 0, float(a["Altura_Amarre_m"])],
            "amarre_fin_m": [0, 0, float(b["Altura_Amarre_m"])],
        })
    return resultado


def mostrar_barrido_3d():
    """Vista independiente del motor existente de Streamlit."""
    st.subheader("Análisis termomecánico 3D — experimental")
    st.warning(
        "Catenaria espacial y compatibilidad termoelástica con carga vectorial "
        "uniforme por longitud real. El viento se proyecta según el eje del vano, "
        "no según la tangente local de la curva. No verifica postes, retenidas, "
        "suelo, distancias de seguridad ni cumplimiento normativo."
    )

    archivo = st.file_uploader("Puntos XYZ y altura de amarre (.xlsx)", type=["xlsx"],
                               key="archivo_barrido_3d")
    st.caption(
        "Excel: Punto, X, Y, Altitud (cota de terreno), Altura_Amarre_m "
        "(altura sobre terreno). Los vanos son los pares consecutivos. "
        "Se suponen amarres fijos, no suspensión móvil."
    )
    with st.form("config_barrido_3d"):
        c1, c2, c3 = st.columns(3)
        with c1:
            calibre = st.selectbox("Conductor", list(CONDUCTORES_ACSR),
                                   index=list(CONDUCTORES_ACSR).index("2/0 ACSR"))
            cantidad = st.number_input("Conductores idénticos por vano",
                                       min_value=1, max_value=12, value=3, step=1)
            ea_texto = st.text_input("EA axial (kN) — ficha técnica", value="")
            alfa_texto = st.text_input("Dilatación térmica α (1/°C) — ficha", value="")
            fuente = st.text_input("Fuente verificable de EA y α", value="")
        with c2:
            t0 = st.number_input("Temperatura inicial de tendido (°C)",
                                 value=20.0, step=1.0)
            temperaturas = st.text_input("Temperaturas a resolver (°C)",
                                         value="20, 40")
            tensiones = st.text_input("Tensiones iniciales por conductor (kN)",
                                      value="4, 6, 8")
            rumbos = st.text_input("Viento HACIA azimut (°; 0=Este, 90=Norte)",
                                   value="0, 180")
        with c3:
            vmin = st.number_input("Viento inicial (m/s)", min_value=0.0, value=0.0)
            vmax = st.number_input("Viento final (m/s)", min_value=0.0, value=10.0)
            paso = st.number_input("Incremento viento (m/s)", min_value=0.1,
                                    value=1.0, step=0.1)
            cd = st.number_input("Coeficiente Cd", min_value=0.01, value=1.2)
            rho = st.number_input("Densidad aire (kg/m³)", min_value=0.1, value=1.225)
        enviar = st.form_submit_button("Calcular barrido 3D", type="primary")

    if not enviar:
        return
    if archivo is None:
        st.error("Seleccione un Excel antes de calcular")
        return

    try:
        if not ea_texto.strip() or not alfa_texto.strip() or not fuente.strip():
            raise ValueError("EA, α y su fuente son obligatorios; no usar valores supuestos")
        ea, alfa = float(ea_texto), float(alfa_texto)
        temperaturas_lista = _numeros(temperaturas, "temperaturas")
        tensiones_lista = _numeros(tensiones, "tensiones", positivos=True)
        rumbos_lista = _numeros(rumbos, "direcciones")
        n_v = round((vmax-vmin)/paso)+1
        if vmax < vmin:
            raise ValueError("El viento final debe ser mayor o igual al inicial")
        n_casos = n_v*len(temperaturas_lista)*len(tensiones_lista)*len(rumbos_lista)
        if n_casos > 500:
            raise ValueError(
                f"{n_casos} combinaciones exceden el límite interactivo de 500. "
                "Divida el ensayo en intervalos para evitar tiempos excesivos."
            )

        df = leer_puntos_excel(archivo)
        vanos = _vanos_desde_excel(df)
        ficha = CONDUCTORES_ACSR[calibre]
        resultado = ejecutar_barrido_3d(
            vanos,
            peso_kN_m=ficha["peso_kg_m"] * 9.80665 / 1000,
            diametro_m=ficha["diametro_m"],
            EA_kN=ea, alpha_por_C=alfa,
            temperatura_tendido_C=t0,
            temperaturas_C=temperaturas_lista,
            tensiones_iniciales_kN=tensiones_lista,
            viento_min_ms=vmin, viento_max_ms=vmax,
            incremento_viento_ms=paso, direcciones_viento_deg=rumbos_lista,
            Cd=cd, rho_kg_m3=rho,
            cantidad_conductores=int(cantidad), fuente_conductor=fuente,
        )
        st.success(
            f"Estados resueltos: {len(resultado['vanos'])} por vano; "
            f"acciones acumuladas: {len(resultado['nodos'])} por apoyo."
        )
        a, b = st.tabs(["Tensiones y equilibrio por vano", "Fuerzas y momentos por apoyo"])
        with a:
            st.dataframe(resultado["vanos"], use_container_width=True)
            st.download_button("Exportar tensiones CSV",
                resultado["vanos"].to_csv(index=False).encode("utf-8-sig"),
                "tensiones_barrido_3d.csv", mime="text/csv")
        with b:
            st.dataframe(resultado["nodos"], use_container_width=True)
            st.download_button("Exportar acciones CSV",
                resultado["nodos"].to_csv(index=False).encode("utf-8-sig"),
                "acciones_barrido_3d.csv", mime="text/csv")
        st.caption(
            "Estado de todas las acciones: NO VERIFICABLE para aprobación de estructura. "
            "No deben interpretarse como combinaciones normativas."
        )
    except (ValueError, TypeError, OverflowError, KeyError, ZeroDivisionError) as exc:
        st.error(f"No se ejecutó el barrido: {exc}")
