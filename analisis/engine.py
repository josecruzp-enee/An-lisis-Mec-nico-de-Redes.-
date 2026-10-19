# analisis/engine.py
# -*- coding: utf-8 -*-
"""Adaptador Excel: conserva geometría, tablas y gráficos, exige datos mecánicos.

Para proyecto 3D multicaso con alternativas usar motor_integral.py.
La ruta Excel no dimensiona retenidas ni aprueba postes con datos incompletos.
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
from .geometria import calcular_tramos, calcular_deflexiones, clasificar_por_angulo
from .cargas_tramo import calcular_cargas_por_tramo
from .perfil import analizar_perfil


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
    resumen["Deflexión (°)"] = float("nan")
    resumen["Estructura"] = "Remate"
    resumen["Retenidas"] = pd.Series(pd.NA,index=resumen.index,dtype="Int64")

    if df_def is None or df_def.empty or "Punto" not in df_def.columns:
        return resumen

    # puntos internos toman df_def
    mapa = df_def.set_index("Punto")[["Deflexión (°)", "Estructura", "Retenidas"]]
    for i in range(1, len(resumen) - 1):
        p = str(resumen.loc[i, "Punto"])
        if p in mapa.index:
            resumen.loc[i, "Deflexión (°)"] = mapa.loc[p, "Deflexión (°)"]
            resumen.loc[i, "Estructura"] = mapa.loc[p, "Estructura"]
            resumen.loc[i, "Retenidas"] = pd.NA  # Se diseña por equilibrio, no por ángulo.

    return resumen


def ejecutar_fase_geometria(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    _validar_entrada(df)
    from .validacion_mecanica import validar_puntos
    validar_puntos(df)
    df = df.reset_index(drop=True)

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




def ejecutar_cargas_tramo(df_tramos, *, calibre, n_fases, v_viento_ms,
                          az_viento_deg, diametro_m, Cd, rho):
    """Adaptador público conservado para consumidores anteriores."""
    return calcular_cargas_por_tramo(df_tramos, calibre=calibre, n_fases=n_fases,
        v_viento_ms=v_viento_ms, azimut_viento_deg=az_viento_deg,
        diametro_conductor_m=diametro_m, Cd=Cd, rho=rho)


def _fuerzas_desde_amarres(df, calibre, n_fases, H, viento, azimut, diametro, Cd, rho,
                           EA, alpha, temperatura, temperatura_tendido):
    """Adapta el Excel heredado a fuerzas 3D exactas cuando existen datos suficientes."""
    from .geometria_amarres import alturas_amarre
    from .modelos_datos import Conductor, EstadoClimatico, Nodo, Vano
    from .motor_integral import _evaluar_estado
    from .mecanica import peso_lineal_kN_m
    h = alturas_amarre(df)
    if H is None or h is None or 'Altitud' not in df:
        return None
    conductor = Conductor(calibre,peso_lineal_kN_m(calibre),diametro,H,temperatura_tendido,
                          'Catálogo heredado; H explícita del usuario',EA,alpha)
    estado = EstadoClimatico('Caso Excel',temperatura,viento,azimut,'Entrada del usuario',Cd,rho)
    nodos = {str(r.Punto):Nodo(str(r.Punto),(r.X,r.Y,r.Altitud)) for r in df.itertuples()}
    nombres = list(nodos)
    vanos = {str(i):Vano(str(i),nombres[i],nombres[i+1],(0,0,h[i]),(0,0,h[i+1]),calibre,n_fases)
             for i in range(len(df)-1)}
    acciones,_,_ = _evaluar_estado(nodos,{calibre:conductor},vanos,estado)
    filas = [{'Punto':n,**dict(zip(('Fx (kN)','Fy (kN)','Fz (kN)',
               'Mx (kN·m)','My (kN·m)','Mz (kN·m)'),v))} for n,v in acciones.items()]
    resultado = pd.DataFrame(filas)
    resultado['H (kN)'] = (resultado['Fx (kN)']**2+resultado['Fy (kN)']**2)**.5
    return resultado


def ejecutar_todo(df, *, calibre, n_fases, v_viento_ms, az_viento_deg, diametro_m,
                  Cd=1.2, rho=1.225, H_tendido_kN=None, EA_kN=None, alpha_por_C=None,
                  temperatura_C=20., temperatura_tendido_C=20., despeje_min_m=None):
    """Entrada Excel compatible; no diseña retenidas ni capacidades sin sus datos.

    Para alternativas, estados múltiples, anclajes y rigidez use el proyecto
    integral JSON. Las tablas faltantes conservan un motivo NO VERIFICABLE.
    """
    df = df.copy().reset_index(drop=True)
    df['Punto'] = df['Punto'].astype(str).str.strip()
    geo = ejecutar_fase_geometria(df)
    geo['cargas_tramo'] = ejecutar_cargas_tramo(geo['tramos'],calibre=calibre,n_fases=n_fases,
        v_viento_ms=v_viento_ms,az_viento_deg=az_viento_deg,diametro_m=diametro_m,Cd=Cd,rho=rho)
    fuerzas = _fuerzas_desde_amarres(df,calibre,n_fases,H_tendido_kN,v_viento_ms,
        az_viento_deg,diametro_m,Cd,rho,EA_kN,alpha_por_C,temperatura_C,temperatura_tendido_C)
    motivo = ('Faltan capacidades de poste, rigidez, geometría de anclajes y estudio geotécnico'
              if fuerzas is not None else 'Faltan H de tendido, Altitud o altura real de amarre')
    geo['fuerzas_nodo'] = fuerzas if fuerzas is not None else pd.DataFrame({
        'Punto':df['Punto'],'Estado':'NO VERIFICABLE','Motivo':motivo})
    geo['decision'] = pd.DataFrame({'Punto':df['Punto'],'Poste':df['Poste'],
        'Solución':'NO VERIFICABLE','Motivo':motivo})
    for nombre in ('nodos','retenidas','equilibrio','cimentacion','momento_poste'):
        geo[nombre] = pd.DataFrame({'Punto':df['Punto'],'Estado':'NO VERIFICABLE','Motivo':motivo})
    # El perfil heredado es válido sólo en el estado de tendido sin viento/hielo.
    geo['perfil'] = analizar_perfil(df,'',calibre,H_kN=H_tendido_kN,
        despeje_min_m=despeje_min_m) if v_viento_ms == 0 and temperatura_C == temperatura_tendido_C else None
    geo['advertencias'] = [motivo,'Retenidas: cantidad y posición requieren diseño mecánico.',
        'Perfil Excel limitado al tendido sin viento; usar JSON para estados termomecánicos.']
    geo['trazabilidad'] = {'modelo':'Excel compatible, vanos retenidos, fuerzas 3D',
        'H_tendido_kN':H_tendido_kN,'EA_kN':EA_kN,'alpha_por_C':alpha_por_C,
        'temperatura_C':temperatura_C,'temperatura_tendido_C':temperatura_tendido_C,
        'despeje_min_m':despeje_min_m,'calibre':calibre,'n_fases':n_fases,
        'viento_ms':v_viento_ms,'azimut_deg':az_viento_deg,'Cd':Cd,'rho':rho,
        'version_motor':'0.2.0-candidato','catalogo':'catalogos.py heredado; procedencia por revisar'}
    return geo
