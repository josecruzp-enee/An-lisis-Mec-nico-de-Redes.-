"""Cálculo de flechas y tensiones con condiciones inicial/final (CFE 07 FT 01).

El catálogo ENEE aporta identidad y, cuando procede, propiedades de cable.
La metodología de referencia CFE diferencia E inicial/final y calcula
estados térmicos y climáticos. No se afirma equivalencia con SAGSEC/FEM.

El parámetro P=H_50/w a 50 °C se puede aportar DOCUMENTADO o determinar
desde límites de tensión y cargas climáticas explícitas. Nunca se lee
una flecha ENEE como entrada oculta.

El estado final requiere un dato físico adicional: la longitud natural
final o, equivalentemente, P_final documentado. No es correcto modelar
el creep únicamente cambiando EA; cuando P_final falta se rechaza el
cálculo final en vez de inventar elongación permanente.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from Analisis_mecanico_conductores.tension_tendido.evaluar_vanos_amarrados_independientes import (
    EvaluadorVanosAmarrados,
)
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import (
    calcular_flecha_y_desviacion_3d,
)
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito


@dataclass(frozen=True)
class PropiedadesConductorCFE:
    """Propiedades por condición, con trazabilidad documental obligatoria."""

    peso_kN_m: float
    diametro_m: float
    EA_inicial_kN: float
    EA_final_kN: float
    alpha_inicial_por_C: float
    alpha_final_por_C: float
    ruptura_kN: float
    fuente: str

    def validar(self):
        for campo in ("peso_kN_m", "diametro_m", "EA_inicial_kN",
                      "EA_final_kN", "ruptura_kN"):
            finito(getattr(self, campo), campo, 0, True)
        for campo in ("alpha_inicial_por_C", "alpha_final_por_C"):
            finito(getattr(self, campo), campo, 0)
        if not str(self.fuente).strip():
            raise ValueError("Se exige fuente de propiedades mecánicas")


@dataclass(frozen=True)
class EstadoReferenciaCFE:
    """H a 50 °C / peso = P (m); para cada condición su P físico propio."""

    parametro_P_m: float
    fuente: str

    def validar(self):
        finito(self.parametro_P_m, "Parámetro de diseño P", 0, True)
        if not str(self.fuente).strip():
            raise ValueError("Falta fuente del parámetro P")


@dataclass(frozen=True)
class HipotesisDisenoCFE:
    """Carga y límite mecánico documentados; ningún límite por defecto."""

    nombre: str
    temperatura_C: float
    viento_kmh: float
    hielo_mm: float
    limite_tension_kN: float
    fuente: str
    limite_horizontal_kN: float | None = None

    def validar(self):
        if self.limite_horizontal_kN is not None:
            finito(self.limite_horizontal_kN, "Límite horizontal", 0, True)
        finito(self.temperatura_C, "Temperatura")
        for nombre in ("viento_kmh", "hielo_mm"):
            finito(getattr(self, nombre), nombre, 0)
        finito(self.limite_tension_kN, "Límite mecánico", 0, True)
        if not self.nombre.strip() or not self.fuente.strip():
            raise ValueError("Hipótesis CFE sin nombre o fuente")


def _evaluador(xyz, propiedades, condicion, Cd, rho, longitudes_fijadas=None):
    inicial = condicion == "Inicial"
    return EvaluadorVanosAmarrados(
        xyz, propiedades.peso_kN_m, propiedades.diametro_m,
        propiedades.EA_inicial_kN if inicial else propiedades.EA_final_kN,
        propiedades.alpha_inicial_por_C if inicial else propiedades.alpha_final_por_C,
        50., Cd, rho,
        longitudes_naturales_referencia_m=longitudes_fijadas,
    )


def calcular_parametro_cfe_desde_limites(
    xyz, propiedades: PropiedadesConductorCFE, hipotesis,
    *, condicion="Inicial", H_min_kN=0.01, H_max_kN=None,
    Cd=1.2, rho_kg_m3=1.225, densidad_hielo_kg_m3=900.,
):
    """Halla máximo P50 admisible por TODAS las hipótesis y vanos fijos.

    Este optimizador constituye una solución de diseño propuesta, no una
    reproducción demostrada del algoritmo SAGSEC de CFE. Los límites de
    cada hipótesis deben derivarse del caso concreto y su documentación.
    """
    propiedades.validar()
    if condicion not in ("Inicial", "Final"):
        raise ValueError("Condición incorrecta")
    hipotesis = tuple(hipotesis)
    if not hipotesis:
        raise ValueError("Sin hipótesis de diseño")
    for h in hipotesis:
        h.validar()
    evaluador = _evaluador(xyz, propiedades, condicion, Cd, rho_kg_m3)
    minimo = finito(H_min_kN, "H mínimo", 0, True)
    maximo = finito(
        H_max_kN if H_max_kN is not None else propiedades.ruptura_kN,
        "H máximo", minimo, True,
    )

    def relacion(H):
        ratios = []
        for h in hipotesis:
            hs, tensiones, _, _, _ = evaluador.evaluar_estado_con_hielo(
                H, h.temperatura_C, h.viento_kmh / 3.6,
                h.hielo_mm, densidad_hielo_kg_m3,
            )
            ratios.append(max(tensiones) / h.limite_tension_kN)
            if h.limite_horizontal_kN is not None:
                ratios.append(max(hs) / h.limite_horizontal_kN)
        return max(ratios)

    # La tensión MÁXIMA en el apoyo no es necesariamente monótona en H:
    # cuando H es pequeña, la pendiente de la catenaria aumenta y la
    # componente tangencial puede superar el límite. La función de
    # utilización puede ser en forma de U (dos cruces con el límite).
    # Por ello NO se debe exigir monotonicidad ni usar H_min como extremo
    # necesariamente factible. Se busca el MAYOR H factible, detectando
    # los cruces a partir de un barrido mixto logarítmico y lineal.
    rejilla = np.unique(np.r_[
        np.geomspace(minimo, maximo, 96),
        np.linspace(minimo, maximo, 96),
    ])
    utilizaciones = np.array([relacion(float(h)) for h in rejilla])
    if not np.isfinite(utilizaciones).all():
        raise ValueError("Utilizaciones no finitas al dimensionar H a 50 °C")

    factibles = np.flatnonzero(utilizaciones <= 1.0)
    if len(factibles) == 0:
        raise ValueError(
            "Ninguna tensión de referencia evaluada satisface todos los "
            "límites mecánicos. Revisar conductor, vano e hipótesis."
        )
    ultimo = int(factibles[-1])
    cota_activa = ultimo == len(rejilla) - 1
    if cota_activa:
        H = float(maximo)
    else:
        # Último intervalo factible -> no factible; brentq encuentra la
        # intersección superior sin exigir monotonía global.
        H = float(brentq(
            lambda h: relacion(float(h)) - 1.0,
            float(rejilla[ultimo]), float(rejilla[ultimo + 1]),
            xtol=1e-8,
        ))
    if relacion(H) > 1.000001:
        raise ValueError("La tensión optimizada no satisface los límites")
    # Trazabilidad: identificar qué hipótesis restringió realmente H50.
    # Estos resultados son diagnósticos del optimizador, no una prueba de
    # que dicho criterio reproduzca el procedimiento histórico ENEE/SAGSEC.
    detalles = []
    for hip in hipotesis:
        hs, tensiones, _, residuales, _ = evaluador.evaluar_estado_con_hielo(
            H, hip.temperatura_C, hip.viento_kmh / 3.6,
            hip.hielo_mm, densidad_hielo_kg_m3,
        )
        tension_maxima = max(float(t) for t in tensiones)
        uso_total = tension_maxima / hip.limite_tension_kN
        uso_horizontal = (max(hs) / hip.limite_horizontal_kN
                          if hip.limite_horizontal_kN is not None else 0.)
        detalles.append((
            max(uso_total, uso_horizontal), hip, tension_maxima,
            max(abs(float(r)) for r in residuales),
        ))
    indice_critico = max(range(len(detalles)), key=lambda i: detalles[i][0])
    ratio, gobernante, tension_real, residuo_max = detalles[indice_critico]
    return {
        "condicion": condicion,
        "H_50_kN": H,
        "parametro_P_m": H / propiedades.peso_kN_m,
        "relacion_critica": ratio,
        "hipotesis_gobernante": gobernante.nombre,
        "temperatura_gobernante_C": gobernante.temperatura_C,
        "viento_gobernante_kmh": gobernante.viento_kmh,
        "hielo_gobernante_mm": gobernante.hielo_mm,
        "tension_maxima_gobernante_kN": tension_real,
        "limite_gobernante_kN": gobernante.limite_tension_kN,
        "residuo_maximo_gobernante_m": residuo_max,
        "cota_busqueda_activa": cota_activa,
        "metodo": "Optimización de límites documentados, NO SAGSEC",
    }


def calcular_tablas_inicial_final(
    puntos: pd.DataFrame, propiedades: PropiedadesConductorCFE,
    referencia_inicial: EstadoReferenciaCFE,
    referencia_final: EstadoReferenciaCFE,
    temperaturas_C, *,
    estados_climaticos=(), Cd=1.2, rho_kg_m3=1.225,
    densidad_hielo_kg_m3=900., longitudes_fijadas=None,
):
    """Genera ambas tablas por vano; también admite estados viento/hielo.

    Para un claro regla tabulado debe introducirse la luz equivalente en
    la geometría de prueba. Para un tramo real cada vano posee su propia
    longitud natural y se evalúa independientemente tras los amarres.
    """
    from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria

    propiedades.validar()
    referencia_inicial.validar()
    referencia_final.validar()
    xyz, luces = _geometria(puntos)
    filas = []
    for condicion, referencia in (("Inicial", referencia_inicial),
                                  ("Final", referencia_final)):
        longitudes = (longitudes_fijadas or {}).get(condicion)
        evaluador = _evaluador(xyz, propiedades, condicion, Cd, rho_kg_m3,
                               longitudes_fijadas=longitudes)
        H_50 = referencia.parametro_P_m * propiedades.peso_kN_m
        estados = [("Tabla térmica", float(t), 0., 0.) for t in temperaturas_C]
        estados.extend((str(x[0]), float(x[1]), float(x[2]), float(x[3]))
                       for x in estados_climaticos)
        if not estados:
            raise ValueError("Sin estados climáticos para calcular")
        for nombre, temperatura, viento_kmh, hielo_mm in estados:
            if hielo_mm > 0:
                hs, tensiones, cables, residuales, _ = evaluador.evaluar_estado_con_hielo(
                    H_50, temperatura, viento_kmh / 3.6,
                    hielo_mm, densidad_hielo_kg_m3,
                )
            else:
                hs, tensiones, cables, residuales, _ = evaluador.evaluar_estado(
                    H_50, temperatura, viento_kmh / 3.6,
                )
            for i, cable in enumerate(cables):
                flecha, lateral = calcular_flecha_y_desviacion_3d(
                    cable, xyz[i], xyz[i+1],
                )
                filas.append({
                    "Condición": condicion,
                    "Hipótesis": nombre,
                    "Temperatura (°C)": temperatura,
                    "Viento (km/h)": viento_kmh,
                    "Hielo (mm)": hielo_mm,
                    "Vano": str(puntos.iloc[i]["Punto"]) + " → " +
                            str(puntos.iloc[i+1]["Punto"]),
                    "Luz (m)": float(luces[i]),
                    "Longitud natural fijada (m)": (float(longitudes[i]) if longitudes is not None else None),
                    "P a 50 °C (m)": referencia.parametro_P_m,
                    "H (kN)": float(hs[i]),
                    "T máx. (kN)": float(tensiones[i]),
                    "Flecha (m)": float(flecha),
                    "Lateral (m)": float(lateral),
                    "Residual (m)": float(residuales[i]),
                    "Fuente referencia": referencia.fuente,
                    "Fuente conductor": propiedades.fuente,
                })
    return pd.DataFrame(filas)
