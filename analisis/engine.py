# analisis/engine.py
# -*- coding: utf-8 -*-
"""
ORDEN LÓGICO DEL ENGINE

01 Geometría
02 Cargas por tramo
03 Fuerzas en nodos
04 Retenidas (demanda)
05 Equilibrio poste–retenida
06 Cimentación
07 Momento (referencial)
08 Decisión estructural (final)
09 Perfil longitudinal
"""

from __future__ import annotations
from typing import Dict, Any
import pandas as pd

from .geometria import calcular_tramos, calcular_deflexiones, clasificar_por_angulo
from .cargas_tramo import calcular_cargas_por_tramo
from .fuerzas_nodo import calcular_fuerzas_en_nodos
from .retenidas import calcular_retenidas
from .equilibrio_poste import equilibrar_poste_retenida
from .cimentacion import evaluar_cimentacion
from .momento_poste import calcular_momento_poste
from .decision_soporte import decidir_soporte
from .perfil import analizar_perfil
from .norma_postes import h_amarre_tipica_m


# =============================================================================
# FASE 01 – GEOMETRÍA
# =============================================================================

def ejecutar_fase_geometria(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    df_tramos = calcular_tramos(puntos, etiquetas)
    df_def = calcular_deflexiones(puntos, etiquetas)

    if not df_def.empty and "Deflexión (°)" in df_def.columns:
        deflex_real = [abs(180.0 - float(a)) for a in df_def["Deflexión (°)"]]
        df_def["Deflexión (°)"] = [round(d, 1) for d in deflex_real]

        estructuras, retenidas = [], []
        for d in deflex_real:
            est, ret = clasificar_por_angulo(d)
            estructuras.append(est)
            retenidas.append(ret)

        df_def["Estructura"] = estructuras
        df_def["Retenidas"] = retenidas

    resumen = df[["Punto", "Poste", "Espacio Retenida"]].copy()
    resumen["Deflexión (°)"] = "-"
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = 1

    if not df_def.empty:
        mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
        for i in range(1, len(resumen) - 1):
            p = resumen.loc[i, "Punto"]
            if p in mapa.index:
                resumen.loc[i, "Deflexión (°)"] = mapa.loc[p, "Deflexión (°)"]
                resumen.loc[i, "Estructura"] = mapa.loc[p, "Estructura"]
                resumen.loc[i, "Retenidas"] = mapa.loc[p, "Retenidas"]

    return {
        "tramos": df_tramos,
        "deflexiones": df_def,
        "resumen": resumen,
        "total_m": float(df_tramos["Distancia (m)"].sum()) if "Distancia (m)" in df_tramos.columns else 0.0,
    }


# =============================================================================
# FASE 02 – CARGAS POR TRAMO
# =============================================================================

def ejecutar_cargas_tramo(
    df_tramos: pd.DataFrame,
    *,
    calibre: str,
    n_fases: int,
    v_viento_ms: float,
    az_viento_deg: float,
    diametro_m: float,
    Cd: float,
    rho: float,
) -> pd.DataFrame:
    return calcular_cargas_por_tramo(
        df_tramos=df_tramos,
        calibre=calibre,
        n_fases=n_fases,
        v_viento_ms=v_viento_ms,
        azimut_viento_deg=az_viento_deg,
        diametro_conductor_m=diametro_m,
        Cd=Cd,
        rho=rho,
    )


# =============================================================================
# FASE 03 – EJECUCIÓN TOTAL
# =============================================================================

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

    # 02) Cargas por tramo
    geo["cargas_tramo"] = ejecutar_cargas_tramo(
        geo["tramos"],
        calibre=calibre,
        n_fases=n_fases,
        v_viento_ms=v_viento_ms,
        az_viento_deg=az_viento_deg,
        diametro_m=diametro_m,
        Cd=Cd,
        rho=rho,
    )

    # 03) Fuerzas en nodos
    geo["fuerzas_nodo"] = calcular_fuerzas_en_nodos(
        df_tramos=geo["cargas_tramo"],
        df_resumen=geo["resumen"],
        usar_col_w="w_viento_eff (kN/m)",
        azimut_viento_deg=az_viento_deg,
    )

    # --- Preparar DF nodos para retenidas/equilibrio: agregar Poste y h_amarre
    df_nodos = geo["fuerzas_nodo"].merge(
        geo["resumen"][["Punto", "Poste", "Retenidas", "Espacio Retenida"]],
        on="Punto",
        how="left",
    )

    # altura típica de amarre por poste (m)
    df_nodos["h_amarre (m)"] = df_nodos["Poste"].apply(lambda p: float(h_amarre_tipica_m(str(p))))

    # 04) Retenidas (demanda mecánica)  ✅ USA TU MODULO ACTUAL
    # IMPORTANTE: col_H debe coincidir con tu fuerzas_nodo.
    # Por tu proyecto, normalmente es "H (kN)" (no "H_nodo (kN)").
    geo["retenidas"] = calcular_retenidas(
        df_nodos,
        col_H="H (kN)",
        cable_retenida="1/4",
        FS_retenida=2.0,
        ang_retenida_deg=45.0,
    )

    # 05) Equilibrio poste–retenida
    geo["equilibrio"] = equilibrar_poste_retenida(
        df=geo["retenidas"],
        col_H_nodo="H (kN)",
        col_T_ret="T_retenida (kN)",
        col_h_amarre="h_amarre (m)",
    )

    # 06) Cimentación
    geo["cimentacion"] = evaluar_cimentacion(
        df=geo["equilibrio"],
        col_H_poste="H_poste (kN)",
        col_h_amarre="h_amarre (m)",
        profundidad_empotramiento_m=2.0,
        capacidad_suelo_kN=50.0,
    )

    # 07) Momento (referencial, si lo quieres aparte)
    geo["momento_poste"] = calcular_momento_poste(
        df_fuerzas_nodo=geo["fuerzas_nodo"],
        df_resumen=geo["resumen"],
    )

    # 08) Decisión FINAL (con equilibrio + cimentación)
    geo["decision"] = decidir_soporte(
        df_resumen=geo["resumen"],
        df_equilibrio=geo["equilibrio"],
        df_cimentacion=geo["cimentacion"],
    )

    # 09) Perfil longitudinal
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
