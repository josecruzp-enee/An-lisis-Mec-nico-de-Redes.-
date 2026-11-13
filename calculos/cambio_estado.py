"""Compatibilidad de longitud sin tensión; elasticidad lineal y expansión térmica.

Cada vano fijo conserva su longitud natural. Una sección deslizante ideal
puede conservar la suma; NO representa cadenas de suspensión de longitud finita.
La fluencia entra como deformación permanente suministrada, no como predicción.
"""
from __future__ import annotations
import numpy as np
from .catenaria import resolver_catenaria
from .validacion_mecanica import finito

# Cuadratura Gauss-Legendre de orden fijo, contrastada con orden 128 en pruebas.
_ABSCISAS, _PESOS = np.polynomial.legendre.leggauss(64)


def longitud_natural(cable, EA_kN: float) -> float:
    """Integra ds/(1+T/EA) para recuperar la longitud descargada en m."""
    EA = finito(EA_kN, 'EA_kN', 0, True)
    x = (_ABSCISAS+1)*cable.luz/2
    tangente = np.cosh((x-cable.xc)/cable.a)
    return float(cable.luz/2 * np.dot(_PESOS, tangente/(1+cable.tension(x)/EA)))


def resolver_cambio_estado(vanos, H_inicial_kN, EA_kN, alpha_por_C,
                           delta_temperatura_C, deformacion_permanente=0.0,
                           tolerancia_m=1e-8, max_iter=200):
    """Resuelve una H común por bisección con intervalo físico comprobado.

    vanos: lista de (inicio, fin, q_inicial, q_final). Varios vanos sólo
    corresponden a apoyos ideales deslizantes con H común y carga compatible.
    Devuelve H, residual en m, iteraciones y longitud natural objetivo.
    """
    if not vanos:
        raise ValueError('Sección vacía')
    finito(H_inicial_kN, 'H inicial', 0, True)
    finito(EA_kN, 'EA', 0, True)
    finito(tolerancia_m, 'tolerancia', 0, True)
    alpha = finito(alpha_por_C, 'alpha', 0)
    dt = finito(delta_temperatura_C, 'delta temperatura')
    creep = finito(deformacion_permanente, 'deformación permanente', 0)
    factor = finito(1+alpha*dt+creep, 'factor térmico', 0, True)
    inicial = sum(longitud_natural(resolver_catenaria(a,b,q0,H_inicial_kN), EA_kN)
                  for a,b,q0,q1 in vanos)
    objetivo = inicial*factor

    def residuo(H):
        """Error de compatibilidad de toda la sección en metros."""
        return sum(longitud_natural(resolver_catenaria(a,b,q1,H), EA_kN)
                   for a,b,q0,q1 in vanos)-objetivo

    bajo, alto = _acotar_raiz(residuo, H_inicial_kN)
    for i in range(max_iter):
        H = (bajo+alto)/2
        error = residuo(H)
        if abs(error) <= tolerancia_m:
            return {'H_kN': H, 'residual_m': error, 'iteraciones': i+1,
                    'longitud_natural_objetivo_m': objetivo}
        if error > 0:
            bajo = H
        else:
            alto = H
    raise ValueError('Cambio de estado sin convergencia; no se emite resultado')


def _acotar_raiz(residuo, H):
    """Busca cambio de signo; no silencia desbordamientos ni raíces ausentes."""
    bajo = alto = float(H)
    for _ in range(80):
        if residuo(bajo) >= 0:
            break
        bajo /= 2
    else:
        raise ValueError('No se pudo acotar H inferior')
    for _ in range(80):
        if residuo(alto) <= 0:
            return bajo, alto
        alto *= 2
    raise ValueError('No se pudo acotar H superior')


def vano_regulador(longitudes):
    """sqrt(sum(L³)/sum(L)); sólo auxiliar para vanos aproximadamente nivelados."""
    luces = [finito(v, 'luz', 0, True) for v in longitudes]
    if not luces:
        raise ValueError('Sin vanos')
    return float(np.sqrt(sum(x**3 for x in luces)/sum(luces)))
