# analisis/engine.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import pandas as pd

from .geometria import calcular_tramos, calcular_deflexiones, clasificar_por_angulo
from .cargas_tramo import calcular_cargas_por_tramo
from .fuerzas_nodo import calcular_fuerzas_en_nodos
from .decision_soporte import decidir_soporte
from .momento_poste import calcular_momento_poste
from .perfil import analizar_perfil



def ejecutar_fase_geometria(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    df_tramos = calcular_tramos(puntos, etiquetas)
    df_def = calcular_deflexiones(puntos, etiquetas)

    # ------------------------------------------------------------
    # deflex_real = |180 - ang|
    # ------------------------------------------------------------
    if not df_def.empty and "Deflexión (°)" in df_def.columns:
        deflex_real_list = []
        for ang in df_def["Deflexión (°)"].tolist():
            try:
                a = float(ang)
                deflex_real = abs(180.0 - a)
            except Exception:
                deflex_real = 0.0
            deflex_real_list.append(deflex_real)

        # Guardar la deflexión real (reemplaza la anterior)
        df_def["Deflexión (°)"] = df_def["Deflexión (°)"].round(2)


        # Clasificar con deflexión real
        estructuras, retenidas = [], []
        for d in deflex_real_list:
            est, ret = clasificar_por_angulo(float(d))
            estructuras.append(est)
            retenidas.append(ret)

        df_def["Estructura"] = estructuras
        df_def["Retenidas"] = retenidas

    # ------------------------------------------------------------
    # Resumen base (remates en extremos)
    # ------------------------------------------------------------
    resumen = df[["Punto", "Poste", "Espacio Retenida"]].copy()
    resumen["Deflexión (°)"] = "-"
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = 1

    # ------------------------------------------------------------
    # Insertar info de puntos internos desde df_def ya corregido
    # ------------------------------------------------------------
    if not df_def.empty:
        mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
        for i in range(1, len(resumen) - 1):
            p = resumen.loc[i, "Punto"]
            if p in mapa.index:
                resumen.loc[i, "Deflexión (°)"] = float(mapa.loc[p, "Deflexión (°)"])
                resumen.loc[i, "Estructura"] = str(mapa.loc[p, "Estructura"])
                resumen.loc[i, "Retenidas"] = int(mapa.loc[p, "Retenidas"])

    return {
        "tramos": df_tramos,
        "deflexiones": df_def,
        "resumen": resumen,
        "total_m": float(df_tramos["Distancia (m)"].sum()) if "Distancia (m)" in df_tramos.columns else 0.0,
    }


def ejecutar_cargas_tramo(
    df_tramos: pd.DataFrame,
    *,
    calibre: str,
    n_fases: int,
    v_viento_ms: float,
    az_viento_deg: float,
    diametro_m: float,
    Cd: float = 1.2,
    rho: float = 1.225,
) -> pd.DataFrame:
    return calcular_cargas_por_tramo(
        df_tramos=df_tramos,
        calibre=calibre,
        n_fases=int(n_fases),
        v_viento_ms=float(v_viento_ms),
        azimut_viento_deg=float(az_viento_deg),
        diametro_conductor_m=float(diametro_m),
        Cd=float(Cd),
        rho=float(rho),
    )


def ejecutar_todo(
    df: pd.DataFrame,
    *,
    calibre: str,
    n_fases: int,
    v_viento_ms: float,
    az_viento_deg: float,
    diametro_m: float,
    Cd: float = 1.2,
    rho: float = 1.225,
) -> Dict[str, Any]:
    geo = ejecutar_fase_geometria(df)

    df_cargas = ejecutar_cargas_tramo(
        geo["tramos"],
        calibre=calibre,
        n_fases=n_fases,
        v_viento_ms=v_viento_ms,
        az_viento_deg=az_viento_deg,
        diametro_m=diametro_m,
        Cd=Cd,
        rho=rho,
    )
    geo["cargas_tramo"] = df_cargas

    # 3) Fuerzas por nodo (poste) usando suma vectorial por azimut
    geo["fuerzas_nodo"] = calcular_fuerzas_en_nodos(
        df_tramos=df_cargas,
        df_resumen=geo["resumen"],
        usar_col_w="w_resultante (kN/m)",
    )

    # 3.1) Momento por poste (se calcula y se guarda, pero NO se usa para decisión FASE 1)
    geo["momento_poste"] = calcular_momento_poste(
        df_fuerzas_nodo=geo["fuerzas_nodo"],
        df_resumen=geo["resumen"],
    )

    # 4) Decisión soporte (poste / retenida / autosoportado)
    geo["decision"] = decidir_soporte(
        df_resumen=geo["resumen"],
        df_fuerzas_nodo=geo["fuerzas_nodo"],
    )

    # 5) Perfil longitudinal (solo si Excel trae Altitud)
    geo["perfil"] = analizar_perfil(
        df,
        tipo_poste=str(df["Poste"].iloc[0]) if "Poste" in df.columns and len(df) else "",
        calibre=calibre,
        fraccion_trabajo=0.20,
        modo_sag="CATENARIA",
        offset_amarre_desde_punta_m=0.10,
        despeje_min_m=0.0,
    )

    return geo
