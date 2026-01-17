import streamlit as st
from datetime import date

from analisis.catalogos import CONDUCTORES_ACSR  # ya lo tienes


def ui_datos_proyecto():
    st.header("Datos del Proyecto")

    c1, c2 = st.columns(2)
    with c1:
        nombre = st.text_input("Nombre del proyecto", value="Proyecto prueba")
        lugar = st.text_input("Lugar / Municipio", value="Honduras")
        cliente = st.text_input("Cliente (opcional)", value="")
    with c2:
        fecha = st.date_input("Fecha", value=date.today())
        responsable = st.text_input("Responsable (opcional)", value="")

    st.subheader("Parámetros eléctricos y mecánicos")

    c3, c4, c5 = st.columns(3)
    with c3:
        calibre = st.selectbox("Conductor", options=list(CONDUCTORES_ACSR.keys()), index=2)  # 2/0 ACSR por ejemplo
        n_fases = st.selectbox("Fases", options=[1, 2, 3], index=2)

    with c4:
        v_viento_ms = st.number_input("Velocidad de viento (m/s)", min_value=0.0, value=30.0, step=0.5)
        az_viento_deg = st.number_input("Dirección del viento (°)", min_value=0.0, max_value=360.0, value=0.0, step=5.0)

    with c5:
        diametro_m = st.number_input("Diámetro conductor (m)", min_value=0.0001, value=0.0100, step=0.0001, format="%.4f")
        Cd = st.number_input("Cd", min_value=0.1, value=1.20, step=0.05)
        rho = st.number_input("ρ aire (kg/m³)", min_value=0.5, value=1.225, step=0.01)

    proyecto = {
        "nombre": nombre,
        "lugar": lugar,
        "cliente": cliente,
        "fecha": str(fecha),
        "responsable": responsable,
        "calibre": calibre,
        "n_fases": int(n_fases),
        "v_viento_ms": float(v_viento_ms),
        "az_viento_deg": float(az_viento_deg),
        "diametro_m": float(diametro_m),
        "Cd": float(Cd),
        "rho": float(rho),
    }

    st.info(
        f"**Resumen:** {proyecto['nombre']} | {proyecto['lugar']} | "
        f"{proyecto['calibre']} | {proyecto['n_fases']} fases | "
        f"Viento {proyecto['v_viento_ms']} m/s a {proyecto['az_viento_deg']}°"
    )

    return proyecto
