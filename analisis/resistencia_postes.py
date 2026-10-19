"""Verificación estructural por componentes; ninguna ruptura se toma como admisible.

Convención global: Z positivo hacia arriba. Fz negativo comprime el poste;
Fz positivo lo tracciona. Las capacidades están en kN, kN·m, m o rad.
Los datos proceden de fichas o criterios suministrados por el diseñador; no
se calculan capacidades de concreto/madera/metal/PRFV a partir de la ruptura.
"""
from __future__ import annotations

import numpy as np

from .estados_limite import Estado, Verificacion, verificar_capacidad

REQUISITOS_POSTE = (
    'flexion_x', 'flexion_y', 'cortante', 'axial', 'torsion',
    'flexocompresion', 'desplazamiento', 'rotacion',
    'estabilidad', 'resistencia_local',
)
UNIDADES = {
    'flexion_x': 'kN·m', 'flexion_y': 'kN·m',
    'cortante': 'kN', 'axial': 'kN', 'torsion': 'kN·m',
    'desplazamiento': 'm', 'rotacion': 'rad',
    'traccion_axial': 'kN',
}


def _vector_finito(valores, dimension, nombre):
    """Rechaza acciones incompletas, NaN e infinitos antes de comparar."""
    vector = np.asarray(valores, dtype=float)
    if vector.shape != (dimension,) or not np.isfinite(vector).all():
        raise ValueError(f'{nombre}: se requieren {dimension} valores finitos')
    return vector


def demandas_poste(acciones, desplazamiento=None):
    """Obtiene demandas físicas por eje y distingue compresión de tracción.

    Se conserva 'axial' como magnitud de COMPRESIÓN para compatibilidad con
    fichas anteriores. La tracción se comprueba aparte sólo cuando existe.
    """
    fx, fy, fz, mx, my, mz = _vector_finito(acciones, 6, 'acciones')
    demandas = {
        'flexion_x': abs(mx), 'flexion_y': abs(my),
        'cortante': float(np.hypot(fx, fy)),
        'axial': max(-fz, 0.0),
        'torsion': abs(mz),
    }
    if fz > 0:
        demandas['traccion_axial'] = float(fz)
    if desplazamiento is not None:
        u = _vector_finito(desplazamiento, 6, 'desplazamiento')
        demandas['desplazamiento'] = float(np.linalg.norm(u[:3]))
        demandas['rotacion'] = float(np.linalg.norm(u[3:]))
    return demandas


def _comparar(nombre, demanda, capacidades, caso, metodo):
    """Permite sólo capacidad admisible/de diseño con unidad y método correctos."""
    ficha = capacidades.get(nombre, {})
    if not isinstance(ficha, dict):
        ficha = {}
    unidad = UNIDADES[nombre]
    compatible = (ficha.get('tipo') in ('admisible', 'diseno')
                  and ficha.get('metodo') == metodo
                  and ficha.get('unidad', unidad) == unidad)
    valor = ficha.get('valor') if compatible else None
    fuente = ficha.get('fuente', '')
    return verificar_capacidad(nombre, demanda, valor, unidad, fuente, caso)


def _interaccion(demandas, capacidades, caso, metodo):
    """Suma lineal sólo con regla y capacidades documentadas compatibles."""
    regla = capacidades.get('flexocompresion', {})
    if not isinstance(regla, dict) or regla.get('modelo') != 'suma_lineal':
        return Verificacion(
            'flexocompresion', Estado.NO_VERIFICABLE, caso=caso,
            motivo='Falta modelo de interacción documentado')
    if not regla.get('fuente') or regla.get('metodo', metodo) != metodo:
        return Verificacion(
            'flexocompresion', Estado.NO_VERIFICABLE, caso=caso,
            motivo='Regla de interacción sin fuente o método compatible')
    nombres = ('axial', 'flexion_x', 'flexion_y')
    parciales = [_comparar(n, demandas[n], capacidades, caso, metodo)
                 for n in nombres]
    if any(v.utilizacion is None for v in parciales):
        return Verificacion(
            'flexocompresion', Estado.NO_VERIFICABLE, caso=caso,
            motivo='Faltan resistencias admisibles para la interacción')
    return verificar_capacidad('flexocompresion',
                              sum(v.utilizacion for v in parciales),
                              1.0, '1', regla['fuente'], caso)


def verificar_poste(acciones, capacidades, desplazamiento=None,
                   caso='', metodo='servicio'):
    """Devuelve todas las verificaciones sin aprobar requisitos desconocidos."""
    if not isinstance(capacidades, dict):
        raise ValueError('Las capacidades del poste deben ser un diccionario')
    demandas = demandas_poste(acciones, desplazamiento)
    resultados = [
        _comparar(nombre, demanda, capacidades, caso, metodo)
        for nombre, demanda in demandas.items()
    ]
    resultados.append(_interaccion(demandas, capacidades, caso, metodo))
    presentes = {v.nombre for v in resultados}
    for nombre in REQUISITOS_POSTE:
        if nombre not in presentes:
            resultados.append(Verificacion(
                nombre, Estado.NO_VERIFICABLE, caso=caso,
                motivo='Requiere modelo específico del poste y material'))
    return resultados
