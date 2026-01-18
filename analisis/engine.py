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
from .norma_postes import h_amarre_norma_m
from .geometria import calcular_tramos, calcular_deflexiones, clasificar_por_angulo
from .cargas_tramo import calcular_cargas_por_tramo
from .fuerzas_nodo import calcular_fuerzas_en_nodos
from .retenidas import calcular_retenidas, ParamsRetenida
from .equilibrio_poste import equilibrar_poste_retenida
from .cimentacion import evaluar_cimentacion
from .momento_poste import calcular_momento_poste
from .decision_soporte import decidir_soporte
from .perfil import analizar_perfil
from .norma_postes import h_amarre_tipica_m


# =============================================================================
# Utilidades cortas
# =============================================================================

def _si_no(v) -> bool:
    return str(v).strip().upper() in ("SI", "S", "TRUE", "1")


def _validar_entrada(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        raise ValueError("df de entrada vacío")

    for c in ("Punto", "X", "Y", "Poste", "Espacio Retenida"):
        if c not in df.columns:
            raise ValueError(f"El Excel debe incluir columna '{c}'.")


# =============================================================================
# FASE 01 – GEOMETRÍA
# =============================================================================

def _calcular_deflexion_real(df_def: pd.DataFrame) -> pd.DataFrame:
    if df_def is None or df_def.empty or "Deflexión (°)" not in df_def.columns:
        return df_def

    deflex_real = []
    for a in df_def["Deflexión (°)"].tolist():
        try:
            deflex_real.append(abs(180.0 - float(a)))
        except Exception:
            deflex_real.append(0.0)

    out = df_def.copy()
    out["Deflexión (°)"] = [round(d, 1) for d in deflex_real]

    estructuras, retenidas = [], []
    for d in deflex_real:
        est, ret = clasificar_por_angulo(float(d))
        estructuras.append(est)
        retenidas.append(ret)

    out["Estructura"] = estructuras
    out["Retenidas"] = retenidas
    return out


def _armar_resumen(df: pd.DataFrame, df_def: pd.DataFrame) -> pd.DataFrame:
    # remates en extremos
    resumen = df[["Punto", "Poste", "Espacio Retenida"]].copy()
    resumen["Deflexión (°)"] = "-"
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = 1

    if df_def is None or df_def.empty or "Punto" not in df_def.columns:
        return resumen

    # puntos internos toman df_def
    mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
    for i in range(1, len(resumen) - 1):
        p = str(resumen.loc[i, "Punto"])
        if p in mapa.index:
            resumen.loc[i, "Deflexión (°)"] = mapa.loc[p, "Deflexión (°)"]
            resumen.loc[i, "Estructura"] = mapa.loc[p, "Estructura"]
            resumen.loc[i, "Retenidas"] = int(mapa.loc[p, "Retenidas"])

    return resumen


def ejecutar_fase_geometria(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    _validar_entrada(df)

    puntos = list(zip(df["X"].tolist(), df["Y"].tolist()))
    etiquetas = df["Punto"].tolist()

    df_tramos = calcular_tramos(puntos, etiquetas)
    df_def = calcular_deflexiones(puntos, etiquetas)
    df_def = _calcular_deflexion_real(df_def)

    resumen = _armar_resumen(df, df_def)

    total_m = float(df_tramos["Distancia (m)"].sum()) if "Distancia (m)" in df_tramos.columns else 0.0

    return {
        "tramos": df_tramos,
        "deflexiones": df_def,
        "resumen": resumen,
        "total_m": total_m,
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
    """
    Aquí NO debe tronar si el viento es 0.
    El modelo físico permite caso sin viento.
    """
    vv = float(v_viento_ms or 0.0)
    az = float(az_viento_deg or 0.0)

    return calcular_cargas_por_tramo(
        df_tramos=df_tramos,
        calibre=str(calibre),
        n_fases=int(n_fases),
        v_viento_ms=vv,
        azimut_viento_deg=az,
        diametro_conductor_m=float(diametro_m),
        Cd=float(Cd),
        rho=float(rho),
    )


# =============================================================================
# FASE 03/04 – MAESTRO POR NODO + RETENIDAS
# =============================================================================

def _armar_df_nodos(resumen: pd.DataFrame, fuerzas: pd.DataFrame) -> pd.DataFrame:
    df_nodos = resumen[["Punto", "Poste", "Espacio Retenida", "Retenidas"]].merge(
        fuerzas,
        on="Punto",
        how="left",
    )
    df_nodos["h_amarre (m)"] = df_nodos["Poste"].apply(lambda p: float(h_amarre_tipica_m(str(p))))

    # columna booleana (contrato explícito)
    df_nodos["Retenidas_aplican"] = (
        (df_nodos["Retenidas"].astype(int) > 0) &
        (df_nodos["Espacio Retenida"].apply(_si_no))
    )
    return df_nodos


from .mecanica import retenida_recomendada

def _calcular_retenidas(df_nodos: pd.DataFrame, calibre: str) -> pd.DataFrame:
    return calcular_retenidas(
        df_nodos,
        col_punto="Punto",
        col_H="H (kN)",
        aplicar_si_col="Retenidas_aplican",
        aplicar_si_val=None,  # booleano
        params=ParamsRetenida(
            cable_retenida=retenida_recomendada(calibre),  # <- automático
            FS_retenida=2.0,
            ang_retenida_deg=45.0,
        ),
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

    # ============================================================
    # 01) Geometría base
    # ============================================================
    geo: Dict[str, Any] = ejecutar_fase_geometria(df)

    # ============================================================
    # 02) Cargas por tramo (peso + viento)
    # ============================================================
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

    # ============================================================
    # 03) Fuerzas en nodos (planta)
    # ============================================================
    geo["fuerzas_nodo"] = calcular_fuerzas_en_nodos(
        df_tramos=geo["cargas_tramo"],
        df_resumen=geo["resumen"],
        usar_col_w="w_viento_eff (kN/m)",
        azimut_viento_deg=float(az_viento_deg or 0.0),
    )

    # ============================================================
    # 04) DataFrame maestro por nodo
    # ============================================================
    geo["nodos"] = _armar_df_nodos(
        geo["resumen"],
        geo["fuerzas_nodo"],
    )

    # ============================================================
    # 05) Retenidas (demanda mecánica)
    # ============================================================
    geo["retenidas"] = _calcular_retenidas(geo["nodos"], calibre)
    df_ret = geo["retenidas"].copy()

    # --- asegurar Poste y h_amarre por punto (SIN constantes)
    if "Poste" not in df_ret.columns and "Poste" in geo["resumen"].columns:
        df_ret = df_ret.merge(
            geo["resumen"][["Punto", "Poste"]],
            on="Punto",
            how="left",
        )

    if "h_amarre (m)" not in df_ret.columns or df_ret["h_amarre (m)"].isna().any():
        df_ret["h_amarre (m)"] = df_ret["Poste"].apply(
            lambda p: h_amarre_tipica_m(str(p))
        )

    geo["retenidas"] = df_ret

    # ============================================================
    # 06) Equilibrio poste – retenida
    # ============================================================
    geo["equilibrio"] = equilibrar_poste_retenida(
        df=geo["retenidas"],
        col_H_nodo="H_sin_retenida (kN)",
        col_T_ret="T_retenida (kN)",
        col_h_amarre="h_amarre (m)",
    )

    # ============================================================
    # 07) Cimentación (referencial)
    # ============================================================
    geo["cimentacion"] = evaluar_cimentacion(
        df=geo["equilibrio"],
        col_H_poste="H_poste (kN)",
        col_h_amarre="h_amarre (m)",
        profundidad_empotramiento_m=2.0,
        capacidad_suelo_kN=50.0,
    )

    # ============================================================
    # 08) Momento en el poste (USANDO H_poste REAL)
    # ============================================================
    geo["momento_poste"] = calcular_momento_poste(
        df_fuerzas_nodo=geo["equilibrio"],
        df_resumen=geo["resumen"],
        col_H="H_poste (kN)",
        col_poste="Poste",
        col_h_amarre="h_amarre (m)",
    )

    # ============================================================
    # 09) Decisión estructural FINAL
    # ============================================================
    geo["decision"] = decidir_soporte(
        df_resumen=geo["resumen"],
        df_equilibrio=geo["equilibrio"],
        df_cimentacion=geo["cimentacion"],
    )

    # ============================================================
    # 10) Perfil longitudinal (si hay Altitud)
    # ============================================================
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
