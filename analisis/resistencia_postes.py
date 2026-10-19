"""Comprobaciones contra resistencias documentadas, sin convertir ruptura en servicio.

Este módulo no deduce resistencia de concreto, madera, acero o PRFV de una
única carga de ensayo. Las capacidades se introducen por material y método.
"""
from __future__ import annotations
import numpy as np
from .estados_limite import Verificacion, Estado, verificar_capacidad

REQUISITOS_POSTE = ('flexion_x','flexion_y','cortante','axial','torsion',
                    'flexocompresion','desplazamiento','rotacion',
                    'estabilidad','resistencia_local')


def verificar_poste(acciones, capacidades, desplazamiento=None, caso='', metodo='servicio'):
    """Comprueba demandas por eje; faltantes de interacción/estabilidad bloquean."""
    fx,fy,fz,mx,my,mz = acciones
    demandas = {'flexion_x':(abs(mx),'kN·m'),'flexion_y':(abs(my),'kN·m'),
                'cortante':(float(np.hypot(fx,fy)),'kN'),'axial':(abs(fz),'kN'),
                'torsion':(abs(mz),'kN·m')}
    if desplazamiento is not None:
        demandas['desplazamiento'] = (float(np.linalg.norm(desplazamiento[:3])),'m')
        demandas['rotacion'] = (float(np.linalg.norm(desplazamiento[3:])),'rad')
    resultados = [_comparar(n,d,u,capacidades,caso,metodo) for n,(d,u) in demandas.items()]
    resultados.append(_interaccion(demandas,capacidades,caso,metodo))
    presentes = {v.nombre for v in resultados}
    for nombre in REQUISITOS_POSTE:
        if nombre not in presentes:
            resultados.append(Verificacion(nombre,Estado.NO_VERIFICABLE,caso=caso,
                               motivo='Requiere modelo específico del poste/material'))
    return resultados


def _comparar(nombre,demanda,unidad,capacidades,caso,metodo):
    """Rechaza resistencias últimas sin reducción y métodos incompatibles."""
    ficha = capacidades.get(nombre,{})
    compatible = ficha.get('tipo') in ('admisible','diseno') and ficha.get('metodo') == metodo
    valor = ficha.get('valor') if compatible else None
    return verificar_capacidad(nombre,demanda,valor,unidad,ficha.get('fuente',''),caso)


def _interaccion(demandas,capacidades,caso,metodo):
    """Interacción lineal sólo si se suministra expresamente ese criterio."""
    regla = capacidades.get('flexocompresion',{})
    if regla.get('modelo') != 'suma_lineal' or not regla.get('fuente'):
        return Verificacion('flexocompresion',Estado.NO_VERIFICABLE,caso=caso,
                            motivo='Falta superficie de interacción del fabricante/diseño')
    verificaciones = [_comparar(n,*demandas[n],capacidades,caso,metodo)
                      for n in ('axial','flexion_x','flexion_y')]
    if any(v.utilizacion is None for v in verificaciones):
        return Verificacion('flexocompresion',Estado.NO_VERIFICABLE,caso=caso)
    return verificar_capacidad('flexocompresion',sum(v.utilizacion for v in verificaciones),
                               1.0,'1',regla['fuente'],caso)
