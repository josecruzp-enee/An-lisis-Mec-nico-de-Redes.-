"""Evalúa alternativas por estado; nunca propone autosoportado por falta de espacio."""
from __future__ import annotations
import numpy as np
from .estados_limite import Estado, Verificacion, estado_conjunto, verificar_capacidad
from .resistencia_postes import verificar_poste
from .anclajes import verificar_anclaje
from .retenidas_espaciales import resolver_poste_retenidas


REQUISITOS_CIMENTACION = ('lateral','momento','compresion','extraccion','deslizamiento',
                          'rotacion','desplazamiento','resistencia_estructural')


def verificar_fundacion(acciones, ficha, caso, metodo):
    """Comparaciones parciales; interacción suelo–estructura requiere modelo específico."""
    fx,fy,fz,mx,my,mz = acciones
    demandas = {'lateral':(np.hypot(fx,fy),'kN'),'momento':(np.hypot(mx,my),'kN·m'),
                'compresion':(max(-fz,0),'kN'),'extraccion':(max(fz,0),'kN')}
    salida = []
    for nombre in REQUISITOS_CIMENTACION:
        d,u = demandas.get(nombre,(None,''))
        cap = ficha.get(nombre,{})
        valido = cap.get('tipo') in ('admisible','diseno') and cap.get('metodo') == metodo
        salida.append(verificar_capacidad('cimentacion_'+nombre,d,
                      cap.get('valor') if valido else None,u,cap.get('fuente',''),caso))
    return salida


def evaluar_alternativa(alternativa, acciones, caso, metodo):
    """Retorna verificaciones y residual; una solución incompleta queda bloqueada."""
    retenidas = alternativa.get('retenidas',[])
    K = alternativa.get('rigidez_6x6')
    verificaciones, equilibrio = [], None
    if retenidas and not alternativa.get('espacio_retenidas',False):
        verificaciones.append(Verificacion('espacio',Estado.NO_CUMPLE,caso=caso,
                                           motivo='Anclajes incompatibles con espacio disponible'))
    if K is not None and alternativa.get('fuente_rigidez'):
        equilibrio = resolver_poste_retenidas(K,acciones,retenidas)
    elif retenidas:
        verificaciones.append(Verificacion('reparto_retenidas',Estado.NO_VERIFICABLE,
                              caso=caso,motivo='Falta rigidez del poste y su fuente'))
    esfuerzos = equilibrio['acciones_poste'] if equilibrio is not None else acciones
    u = equilibrio['desplazamiento'] if equilibrio is not None else None
    verificaciones += verificar_poste(esfuerzos,alternativa.get('capacidades_poste',{}),u,caso,metodo)
    verificaciones += verificar_fundacion(esfuerzos,alternativa.get('cimentacion',{}),caso,metodo)
    for i,retenida in enumerate(retenidas):
        T = equilibrio['tensiones_kN'][i] if equilibrio is not None else None
        for v in verificar_anclaje(T,retenida.get('capacidades',{}),caso,metodo):
            verificaciones.append(Verificacion(**{**v.como_dict(),'nombre':f'retenida_{i+1}_{v.nombre}'}))
    return {'nombre':alternativa['nombre'],'caso':caso,'estado':estado_conjunto(verificaciones),
            'verificaciones':verificaciones,'equilibrio':equilibrio,
            'costo_total':alternativa.get('costo_total'),
            'fuente_costo':alternativa.get('fuente_costo','')}


def seleccionar_alternativa(resultados):
    """Exige cumplimiento en TODOS los casos y costos completos para optimizar."""
    grupos = {}
    for r in resultados:
        grupos.setdefault(r['nombre'],[]).append(r)
    casos = {r['caso'] for r in resultados}
    viables = [g for g in grupos.values() if {r['caso'] for r in g} == casos
               and len(g) == len(casos) and all(r['estado']==Estado.CUMPLE for r in g)]
    if not viables:
        return {'seleccion':None,'motivo':'Ninguna alternativa verificable cumple todos los casos'}
    costos = [g[0].get('costo_total') for g in viables]
    if any(c is None or not np.isfinite(c) or c < 0 for c in costos) or any(not g[0]['fuente_costo'] for g in viables):
        return {'seleccion':None,'viables':[g[0]['nombre'] for g in viables],
                'motivo':'Faltan costos totales trazables; no se elige la más económica'}
    elegida = min(viables,key=lambda g:g[0]['costo_total'])[0]
    return {'seleccion':elegida['nombre'],'motivo':'Menor costo entre alternativas verificadas'}
