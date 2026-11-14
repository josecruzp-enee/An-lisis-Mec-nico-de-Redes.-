"""Estudio de equilibrio estático de retenidas con geometría XYZ explícita.

Fase de factibilidad de configuración, NO cálculo final de retenidas ni
aprobación de postes. El problema físico queda definido por:
    M_externa + sum(T_i * (r_i x u_i)) = M_residual
    F_externa + sum(T_i * u_i) = F_transmitida_a_la_base

donde T_i >= 0. El mínimo cuadrático acotado evalúa si las direcciones
disponibles pueden equilibrar el MOMENTO pedido. La distribución de T_i
NO constituye una solución única de pretensiones ni compatibilidad
elástica. El análisis definitivo exige rigideces, pretensiones,
alargamiento, desplazamientos, rigidez del poste y anclajes.

No se atribuyen resistencias a cables, dispositivos ni suelos.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import lsq_linear

from .validacion_mecanica import finito, vector3


@dataclass(frozen=True)
class RetenidaXYZ:
    nombre: str
    amarre_m: tuple[float, float, float]
    anclaje_m: tuple[float, float, float]
    tension_limite_kN: float | None = None
    fuente_limite: str = ""

    def __post_init__(self):
        if not str(self.nombre).strip():
            raise ValueError("La retenida requiere un identificador")
        a = vector3(self.amarre_m, f"{self.nombre}/amarre")
        b = vector3(self.anclaje_m, f"{self.nombre}/anclaje")
        if a[2] <= 0:
            raise ValueError(f"{self.nombre}: el amarre debe situarse sobre el terreno")
        if b[2] >= a[2]:
            raise ValueError(f"{self.nombre}: el anclaje debe quedar por debajo del amarre")
        if float(np.linalg.norm(b-a)) <= 0:
            raise ValueError(f"{self.nombre}: longitud nula")
        if self.tension_limite_kN is not None:
            finito(self.tension_limite_kN, "tensión límite", 0, True)
            if not self.fuente_limite.strip():
                raise ValueError(f"{self.nombre}: capacidad sin fuente")


@dataclass
class EstudioRetenidas:
    tensiones_kN: dict[str, float]
    fuerzas_retenidas_kN: dict[str, np.ndarray]
    momentos_retenidas_kNm: dict[str, np.ndarray]
    fuerza_resultante_base_kN: np.ndarray
    momento_residual_base_kNm: np.ndarray
    residual_momento_kNm: float
    equilibrio_momentos: bool
    capacidades_documentadas: bool
    estado: str


def estudiar_equilibrio_retenidas(
    fuerza_externa_kN, momento_externo_kNm, retenidas, *,
    tolerancia_momento_kNm=1e-4,
):
    """Busca tensiones no negativas compatibles con equilibrio de momentos.

    Se analiza el par de fuerzas en el poste alrededor de la sección
    de terreno (origen XYZ). Reacción de base no es "cero":
    se reporta la fuerza que seguirá transmitiéndose al terreno.

    Sin capacidades documentadas NO existen valores ficticios de rotura.
    La existencia de una solución de mínimos cuadrados NO valida anclajes,
    compatibilidad de alargamiento ni resistencia del poste.
    """
    F = vector3(fuerza_externa_kN, "fuerza externa")
    M = vector3(momento_externo_kNm, "momento externo")
    tol = finito(tolerancia_momento_kNm, "tolerancia momento", 0, True)
    if not retenidas:
        raise ValueError("Se requiere al menos una retenida con geometría definida")
    elementos = [
        x if isinstance(x, RetenidaXYZ) else RetenidaXYZ(**x)
        for x in retenidas
    ]
    nombres = [x.nombre for x in elementos]
    if len(nombres) != len(set(nombres)):
        raise ValueError("Identificadores de retenida duplicados")

    direcciones = []
    brazos = []
    topes = []
    for guy in elementos:
        a = vector3(guy.amarre_m, guy.nombre+"/amarre")
        b = vector3(guy.anclaje_m, guy.nombre+"/anclaje")
        direccion = (b-a) / np.linalg.norm(b-a)
        direcciones.append(direccion)
        brazos.append(np.cross(a, direccion))
        topes.append(
            np.inf if guy.tension_limite_kN is None
            else float(guy.tension_limite_kN)
        )
    matriz_momentos = np.column_stack(brazos)
    # Se evita imponer arbitrariamente equilibrio de fuerza nula:
    # el poste y su fundación reciben las fuerzas remanentes.
    solucion = lsq_linear(
        matriz_momentos, -M,
        bounds=(np.zeros(len(elementos)), np.asarray(topes)),
        tol=1e-12, max_iter=1000,
    )
    if not solucion.success:
        raise ValueError("No convergió el problema estático de retenidas")
    tensiones = np.asarray(solucion.x, dtype=float)
    momento_residual = M + matriz_momentos @ tensiones
    fuerza_base = F + np.column_stack(direcciones) @ tensiones
    residual = float(np.linalg.norm(momento_residual))
    puede_equilibrar = residual <= tol
    capacidades = all(x.tension_limite_kN is not None for x in elementos)
    if not puede_equilibrar:
        estado = "CONFIGURACIÓN INSUFICIENTE: MOMENTO SIN EQUILIBRAR"
    else:
        estado = (
            "FACTIBILIDAD ESTÁTICA: NO VERIFICABLE ESTRUCTURALMENTE"
        )
    return EstudioRetenidas(
        tensiones_kN=dict(zip(nombres, map(float, tensiones))),
        fuerzas_retenidas_kN={
            g.nombre: float(tensiones[i]) * direcciones[i]
            for i, g in enumerate(elementos)
        },
        momentos_retenidas_kNm={
            g.nombre: float(tensiones[i]) * brazos[i]
            for i, g in enumerate(elementos)
        },
        fuerza_resultante_base_kN=fuerza_base,
        momento_residual_base_kNm=momento_residual,
        residual_momento_kNm=residual,
        equilibrio_momentos=puede_equilibrar,
        capacidades_documentadas=capacidades,
        estado=estado,
    )
