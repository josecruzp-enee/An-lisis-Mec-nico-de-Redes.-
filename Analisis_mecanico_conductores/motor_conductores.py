"""Único orquestador de ejecución ordinaria del Módulo 1.

Las cinco hipótesis CFE son restricciones del MISMO cálculo de conductor,
no cinco motores. Se reutilizan las implementaciones matemáticas existentes;
esta capa no modifica la catenaria, las propiedades ni los solvers.

IMPORTANTE: inicial/final se calculan con las propiedades originales
CFE pero usan una UNICA longitud natural de referencia por vano a 50 C.
Se supone creep adicional cero. No se afirma modelar la evolución real.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    ejecutar_corridas_cfe_por_vano,
)


@dataclass(frozen=True)
class DiagnosticoMaterial:
    """Distingue compatibilidad numérica de evolución material demostrada."""

    cinco_hipotesis_cfe: bool
    presion_cfe_por_claro: bool
    compatibilidad_estados_m: float
    igualdad_extrema_reportada: bool
    diferencia_extrema_kN: float
    deformacion_aparente_maxima: float
    creep_constitutivo_validado: bool
    estado: str


def _diagnosticar(resumen: pd.DataFrame, tabla: pd.DataFrame, *, presion_cfe: bool) -> DiagnosticoMaterial:
    if len(resumen) != 2 or tabla.empty:
        raise ValueError("El motor no devolvió ambas referencias y resultados por vano")
    if "Condición" not in tabla or set(tabla["Condición"]) != {"Inicial", "Final"}:
        raise ValueError("No están presentes las tablas inicial y final")
    for campo in ("Residual (m)", "T máx. (kN)", "H (kN)"):
        if campo not in tabla:
            raise ValueError(f"Salida física incompleta: {campo}")
    resid = pd.to_numeric(tabla["Residual (m)"], errors="raise").to_numpy(dtype=float)
    tens = pd.to_numeric(tabla["T máx. (kN)"], errors="raise").to_numpy(dtype=float)
    hs = pd.to_numeric(tabla["H (kN)"], errors="raise").to_numpy(dtype=float)
    if not (np.isfinite(resid).all() and np.isfinite(tens).all() and np.isfinite(hs).all()):
        raise ValueError("Salida mecánica con magnitudes no finitas")
    if (tens <= 0).any() or (hs <= 0).any():
        raise ValueError("Tracciones o parámetros H no positivos")
    residual_max = float(np.max(np.abs(resid)))
    if residual_max > 1e-7:
        raise ValueError(f"Compatibilidad de vanos fuera de tolerancia: {residual_max:g} m")

    def unico(campo):
        if campo not in resumen:
            raise ValueError(f"Falta diagnóstico de referencia: {campo}")
        valores = resumen[campo]
        if valores.isna().any():
            raise ValueError(f"Diagnóstico incompleto: {campo}")
        return valores.iloc[0]

    cumple = bool(unico("Igualdad extrema publicada verificada"))
    dif = float(unico("Diferencia real de acoplamiento H4 (kN)"))
    aparente = float(unico("Deformación aparente inicial→final máxima |ΔL0/L0|"))
    if not (np.isfinite(dif) and np.isfinite(aparente)):
        raise ValueError("Diagnóstico inicial/final no finito")
    # La igualdad de tracción en un estado no prueba una ley de creep.
    return DiagnosticoMaterial(
        cinco_hipotesis_cfe=True,
        presion_cfe_por_claro=bool(presion_cfe),
        compatibilidad_estados_m=residual_max,
        igualdad_extrema_reportada=cumple,
        diferencia_extrema_kN=dif,
        deformacion_aparente_maxima=aparente,
        creep_constitutivo_validado=False,
        estado=(
            "Longitud natural inicial/final comun por vano a 50 C; "
            "creep adicional = 0; la evolucion constitutiva real no se modela"
        ),
    )



def dividir_secciones_por_remates(puntos: pd.DataFrame):
    """Separa secciones mecánicas: remate en los dos extremos de cada una.

    La columna Remate acepta SI/NO, REMATE/PASO y booleanos. Si se omite,
    se supone únicamente remate en el primer y último apoyo (compatibilidad
    con estudios de una sola sección). Los remates interiores son explícitos.
    Un poste compartido aparece en ambas secciones, sin transferencia de
    longitud de conductor entre ellas.
    """
    if not isinstance(puntos, pd.DataFrame) or len(puntos) < 2:
        raise ValueError("La línea requiere dos o más apoyos")
    if "Punto" not in puntos:
        raise ValueError("Falta la columna Punto")
    if puntos["Punto"].duplicated().any():
        raise ValueError("Identificadores de apoyos duplicados")
    if "Remate" in puntos:
        import pandas as pd
        estados = []
        for i, value in enumerate(puntos["Remate"]):
            if pd.isna(value) or str(value).strip() == "":
                if i in (0, len(puntos)-1):
                    estados.append(True)
                    continue
                raise ValueError(
                    f"Remate sin declarar en {puntos.iloc[i]['Punto']}; "
                    "usar SI o NO"
                )
            valor = str(value).strip().upper()
            if valor in ("SI", "SÍ", "REMATE", "ANCLAJE", "TRUE", "1", "1.0"):
                estados.append(True)
            elif valor in ("NO", "PASO", "SUSPENSION", "SUSPENSIÓN",
                           "FALSE", "0", "0.0"):
                estados.append(False)
            else:
                raise ValueError(
                    f"Remate inválido en {puntos.iloc[i]['Punto']}: {value!r}"
                )
        if not estados[0] or not estados[-1]:
            raise ValueError("El primer y último apoyo deben ser remates")
    else:
        estados = [True] + [False] * (len(puntos)-2) + [True]
    cortes = [i for i, remate in enumerate(estados) if remate]
    return [
        (f"S{indice + 1}", puntos.iloc[inicio:fin + 1].copy().reset_index(drop=True))
        for indice, (inicio, fin) in enumerate(zip(cortes[:-1], cortes[1:]))
    ]


def ejecutar_motor_conductores(
    puntos,
    ficha_inicial,
    ficha_final,
    *,
    viento_max_kmh,
    viento_reducido_kmh,
    hielo_mm,
    temperaturas_C,
    Cd=1.0,
    rho_kg_m3=1.225,
    incluir_ensayo_viento_16C=False,
    densidad_hielo_kg_m3=913.0,
    modelo_presion_cfe=True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Una corrida ordinaria, con el contrato público histórico (resumen, tabla).

    Obliga a declarar el viento tabulado CFE por claro en el flujo principal.
    No impide utilizar los solvers legados en ensayos y comparaciones
    independientes, pero estos no son otra ruta de producción de diseño.
    """
    if not modelo_presion_cfe:
        raise ValueError(
            "El motor único CFE exige presiones tabuladas por claro; "
            "las evaluaciones generales se reservan a ensayos separados"
        )
    resumenes, tablas = [], []
    secciones = dividir_secciones_por_remates(puntos)
    for seccion, puntos_seccion in secciones:
        # Cada sección se instala ENTRE SUS PROPIOS remates; no existe
        # deslizamiento de material a través de un remate intermedio.
        try:
            resumen, tabla = ejecutar_corridas_cfe_por_vano(
                puntos_seccion, ficha_inicial, ficha_final,
                viento_max_kmh=viento_max_kmh,
                viento_reducido_kmh=viento_reducido_kmh,
                hielo_mm=hielo_mm,
                temperaturas_C=temperaturas_C,
                Cd=Cd, rho_kg_m3=rho_kg_m3,
                incluir_ensayo_viento_16C=incluir_ensayo_viento_16C,
                densidad_hielo_kg_m3=densidad_hielo_kg_m3,
                modelo_presion_cfe=True,
                longitud_comun_sin_creep=True,
            )
        except (ValueError, ArithmeticError) as exc:
            raise ValueError(
                f"{seccion} ({puntos_seccion.iloc[0]['Punto']} → "
                f"{puntos_seccion.iloc[-1]['Punto']}): {exc}"
            ) from exc
        diagnostico = _diagnosticar(resumen, tabla, presion_cfe=True)
        resumen = resumen.copy()
        tabla = tabla.copy()
        resumen["Sección"] = seccion
        tabla["Sección"] = seccion
        resumen["Remate inicial"] = str(puntos_seccion.iloc[0]["Punto"])
        resumen["Remate final"] = str(puntos_seccion.iloc[-1]["Punto"])
        resumen["Motor Módulo 1"] = "Motor único — cinco restricciones CFE"
        resumen["Evolución material validada"] = diagnostico.creep_constitutivo_validado
        resumen["Creep adicional"] = 0.0
        resumen["Compatibilidad longitudinal inicial/final"] = "Igualdad exacta de L0 por vano a 50 C"
        resumen["Estado de consistencia material"] = diagnostico.estado
        resumenes.append(resumen)
        tablas.append(tabla)
    return (
        pd.concat(resumenes, ignore_index=True),
        pd.concat(tablas, ignore_index=True),
    )
