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
08 Decisión estructural FINAL
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
    if df is None or df.empty:
        raise ValueError("df de entrada vacío")

    for c in ("Punto", "X", "Y", "Poste", "Espacio Retenida"):
        if c not in df.columns:
            raise ValueError(f"El Excel debe incluir columna '{c}'.")

    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    df_tramos = calcular_tramos(puntos, etiquetas)
    df_def = calcular_deflexiones(puntos, etiquetas)

    # deflex_real = |180 - ang|
    if not df_def.empty and "Deflexión (°)" in df_def.columns:
        deflex_real = []
        for a in df_def["Deflexión (°)"].tolist():
            try:
                deflex_real.append(abs(180.0 - float(a)))
            except Exception:
                deflex_real.append(0.0)

        df_def["Deflexión (°)"] = [round(d, 1) for d in deflex_real]

        estructuras, retenidas = [], []
        for d in deflex_real:
            est, ret = clasificar_por_angulo(float(d))
            estructuras.append(est)
            retenidas.append(ret)

        df_def["Estructura"] = estructuras
        df_def["Retenidas"] = retenidas

    # resumen base: remates en extremos
    resumen = df[["Punto", "Poste", "Espacio Retenida"]].copy()
    resumen["Deflexión (°)"] = "-"
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = 1

    # insertar info interna desde df_def
    if not df_def.empty and "Punto" in df_def.columns:
        mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
        for i in range(1, len(resumen) - 1):
            p = str(resumen.loc[i, "Punto"])
            if p in mapa.index:
                resumen.loc[i, "Deflexión (°)"] = mapa.loc[p, "Deflexión (°)"]
                resumen.loc[i, "Estructura"] = mapa.loc[p, "Estructura"]
                resumen.loc[i, "Retenidas"] = int(mapa.loc[p, "Retenidas"])

    total_m = float(df_tramos["Distancia (m)"].sum()) if "Distancia (m)" in df_tramos.columns else 0.0

    return {
        "tramos": df_tramos,
        "deflexiones": df_def,
        "resumen": resumen,
        "total_m": total_m,
    }


# =============================================================================
# FASE 02 – CARGAS POR TRAMO (robusto a viento=0)
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
    """
    Wrapper robusto: permite v_viento_ms <= 0 (caso sin viento),
    evitando que cargas_tramo.py reviente.
    """
    vv = float(v_viento_ms or 0.0)
    if vv <= 0.0:
        vv = 0.0  # caso válido: sin viento

    return calcular_cargas_por_tramo(
        df_tramos=df_tramos,
        calibre=calibre,
        n_fases=int(n_fases),
        v_viento_ms=vv,
        azimut_viento_deg=float(az_viento_deg or 0.0),
        diametro_conductor_m=float(diametro_m),
        Cd=float(Cd),
        rho=float(rho),
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

    geo: Dict[str, Any] = ejecutar_fase_geometria(df)

    # 02) Cargas por tramo
    geo["cargas_tramo"] = ejecutar_cargas_tramo(
        geo["tramos"],
        calibre=str(calibre),
        n_fases=int(n_fases),
        v_viento_ms=float(v_viento_ms or 0.0),
        az_viento_deg=float(az_viento_deg or 0.0),
        diametro_m=float(diametro_m),
        Cd=float(Cd),
        rho=float(rho),
    )

    # 03) Fuerzas en nodos
    geo["fuerzas_nodo"] = calcular_fuerzas_en_nodos(
        df_tramos=geo["cargas_tramo"],
        df_resumen=geo["resumen"],
        usar_col_w="w_viento_eff (kN/m)",
        azimut_viento_deg=float(az_viento_deg or 0.0),
    )

    # 07) Momento (referencial)
    geo["momento_poste"] = calcular_momento_poste(
        df_fuerzas_nodo=geo["fuerzas_nodo"],
        df_resumen=geo["resumen"],
    )

    # ---- DF maestro para retenidas / equilibrio / cimentación
    df_nodos = geo["resumen"][["Punto", "Poste", "Espacio Retenida", "Retenidas"]].merge(
        geo["fuerzas_nodo"],
        on="Punto",
        how="left",
    )

    # altura típica de amarre (m)
    df_nodos["h_amarre (m)"] = df_nodos["Poste"].apply(lambda p: float(h_amarre_tipica_m(str(p))))

    # 04) Retenidas (solo donde aplica por geometría + espacio)
    aplica = (
        (df_nodos["Retenidas"].astype(int) > 0) &
        (df_nodos["Espacio Retenida"].astype(str).str.strip().str.upper().isin(["SI", "S", "TRUE", "1"]))
    )
    df_nodos_aplica = df_nodos.loc[aplica].copy()

    geo["retenidas"] = calcular_retenidas(
        df_nodos_aplica,
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

    # 08) Decisión estructural FINAL
    geo["decision"] = decidir_soporte(
        df_resumen=geo["resumen"],
        df_equilibrio=geo["equilibrio"],
        df_cimentacion=geo["cimentacion"],
    )

    # 09) Perfil longitudinal (si hay Altitud)
    geo["perfil"] = analizar_perfil(
        df,
        tipo_poste=str(df["Poste"].iloc[0]) if "Poste" in df.columns and len(df) else "",
        calibre=str(calibre),
        fraccion_trabajo=0.20,
        modo_sag="CATENARIA",
        offset_amarre_desde_punta_m=0.10,
        despeje_min_m=0.0,
    )

    return geo
