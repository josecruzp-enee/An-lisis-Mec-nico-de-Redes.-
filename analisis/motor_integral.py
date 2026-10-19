"""Orquestación reproducible de geometría 3D, estados, acciones y alternativas.

Entrada JSON documentada en docs/CONTRATOS.md. Cada vano representa un cable
retenido en sus extremos; secciones con suspensión móvil no se aproximan como
vanos fijos. Se rechazan hasta disponer de un modelo de suspensión específico.
"""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import numpy as np
import pandas as pd
from .modelos_datos import Conductor, EstadoClimatico, Nodo, Vano, Combinacion
from .catenaria import resolver_catenaria
from .cambio_estado import resolver_cambio_estado
from .cargas_espaciales import carga_conductor, resultante_acciones
from .alternativas_estructurales import evaluar_alternativa, seleccionar_alternativa
from .estados_limite import verificar_capacidad
from .validacion_mecanica import finito, vector3

VERSION_MOTOR = '0.2.0-candidato'


def _indice(registros, clase):
    """Construye objetos validados y rechaza identificadores duplicados."""
    objetos = [clase(**r) for r in registros]
    indice = {r.nombre:r for r in objetos}
    if not objetos or len(indice) != len(objetos):
        raise ValueError(f'{clase.__name__}: lista vacía o nombres duplicados')
    return indice


def _validar_proyecto(datos):
    """Contratos explícitos; no adivina conductor, nodo, fuente ni combinación."""
    if datos.get('modelo_secciones') != 'vanos_retenidos':
        raise ValueError('Se requiere modelo_secciones=vanos_retenidos; suspensión móvil no implementada')
    nodos = _indice(datos['nodos'],Nodo)
    conductores = _indice(datos['conductores'],Conductor)
    vanos = _indice(datos['vanos'],Vano)
    estados = _indice(datos['estados'],EstadoClimatico)
    combinaciones = _indice(datos['combinaciones'],Combinacion)
    for v in vanos.values():
        if v.inicio not in nodos or v.fin not in nodos or v.conductor not in conductores:
            raise ValueError(f'{v.nombre}: referencia a nodo/conductor inexistente')
    for registro in datos.get('acciones_adicionales',[]):
        if registro['nodo'] not in nodos or registro['estado'] not in estados:
            raise ValueError('Acción adicional con nodo/estado inexistente')
    for nodo, alternativas in datos.get('alternativas',{}).items():
        if nodo not in nodos or len({a['nombre'] for a in alternativas}) != len(alternativas):
            raise ValueError('Nodo de alternativa inexistente o nombres duplicados')
        for alternativa in alternativas:
            if alternativa.get('costo_total') is not None:
                finito(alternativa['costo_total'],'costo total',0)
    if any(c.estado not in estados for c in combinaciones.values()):
        raise ValueError('Combinación con estado inexistente')
    return nodos,conductores,vanos,estados,combinaciones


def _resolver_vano(vano,nodos,conductor,estado):
    """Tendido sin viento/hielo explícito, seguido de compatibilidad termomecánica."""
    a = np.array(nodos[vano.inicio].base_m)+vano.amarre_inicio_m
    b = np.array(nodos[vano.fin].base_m)+vano.amarre_fin_m
    q0 = np.array([0,0,-conductor.peso_kN_m])
    q1 = carga_conductor(conductor,estado,a,b)
    dt = estado.temperatura_C-conductor.temperatura_tendido_C
    cambio = {'H_kN':conductor.H_tendido_kN,'residual_m':0.,'iteraciones':0}
    if dt != 0 or not np.array_equal(q0,q1) or estado.deformacion_permanente != 0:
        if conductor.EA_kN is None or conductor.alpha_por_C is None:
            raise ValueError(f'{vano.nombre}: faltan EA/alpha específicos para cambio de estado')
        cambio = resolver_cambio_estado([(a,b,q0,q1)],conductor.H_tendido_kN,
                  conductor.EA_kN,conductor.alpha_por_C,dt,estado.deformacion_permanente)
    return resolver_catenaria(a,b,q1,cambio['H_kN']),cambio


def _fila_vano(vano,cable,cambio,conductor,estado,nodos):
    """Resultados sin redondear; componentes de tracción y residual de equilibrio."""
    fa,fb = cable.fuerzas
    Tmin,Tmax = float(cable.tension(0)),float(cable.tension(cable.luz))
    xz = cable.minimo_lineal([0,0,1])
    xm = cable.xc+cable.a*np.arcsinh(cable.desnivel/cable.luz)
    xm = float(np.clip(xm,0,cable.luz))
    cuerda = cable.inicio+xm*cable.e+xm*cable.desnivel/cable.luz*cable.n
    diferencia = cuerda-cable.puntos(xm)
    residual = fa+fb+cable.w*cable.longitud*cable.n
    g0,g1 = nodos[vano.inicio].base_m[2],nodos[vano.fin].base_m[2]
    xcl = cable.minimo_lineal([0,0,1],(g1-g0)/cable.luz)
    despeje = cable.puntos(xcl)[2]-g0-(g1-g0)*xcl/cable.luz
    return {'Vano':vano.nombre,'Estado':estado.nombre,'H_perpendicular (kN)':cable.H,
            'T_A (kN)':Tmin,'T_B (kN)':Tmax,'Longitud real (m)':cable.longitud,
            'Flecha vertical cuerda (m)':float(diferencia[2]),
            'Desplazamiento lateral (m)':float(np.linalg.norm(diferencia[:2])),
            'Cota mínima (m)':float(cable.puntos(xz)[2]),
            'Despeje terreno lineal (m)':float(despeje),
            'Utilización RTS (%)':100*max(Tmin,Tmax)/conductor.RTS_kN if conductor.RTS_kN else None,
            'Residual equilibrio (kN)':float(np.linalg.norm(residual)),
            'Residual compatibilidad (m)':cambio['residual_m'],
            'Iteraciones':cambio['iteraciones'],'Fuente conductor':conductor.fuente,
            'Fuente estado':estado.fuente}


def _acciones_adicionales(datos,nodo,estado):
    """Equipos, poste, construcción y mantenimiento como acciones 3D trazables."""
    salida = []
    for r in datos.get('acciones_adicionales',[]):
        if r['nodo'] == nodo and r['estado'] == estado:
            if not r.get('fuente'):
                raise ValueError('Acción adicional sin fuente')
            salida.append((r['posicion_m'],r['fuerza_kN'],r.get('momento_kNm',[0,0,0])))
    return resultante_acciones(salida)


def _evaluar_estado(nodos,conductores,vanos,estado):
    """Acumula cable por cable en su altura y excentricidad real."""
    acciones = {n:[] for n in nodos}
    filas,verificaciones = [],[]
    for vano in vanos.values():
        conductor = conductores[vano.conductor]
        cable,cambio = _resolver_vano(vano,nodos,conductor,estado)
        fa,fb = cable.fuerzas
        acciones[vano.inicio].append((vano.amarre_inicio_m,vano.cantidad*fa,[0,0,0]))
        acciones[vano.fin].append((vano.amarre_fin_m,vano.cantidad*fb,[0,0,0]))
        filas.append(_fila_vano(vano,cable,cambio,conductor,estado,nodos))
        verificaciones.append(verificar_capacidad(vano.nombre,max(np.linalg.norm(fa),np.linalg.norm(fb)),
                conductor.tension_admisible_kN,'kN',conductor.fuente_admisible,estado.nombre))
    return {n:resultante_acciones(a) for n,a in acciones.items()},filas,verificaciones


def _evaluar_combinaciones(datos,nodos,combinaciones,por_estado):
    """Aplica factores homogéneos a fuerzas Y momentos, conservando signos."""
    filas,alternativas = [],[]
    for combinacion in combinaciones.values():
        for nodo in nodos:
            adicional = _acciones_adicionales(datos,nodo,combinacion.estado)
            carga = (por_estado[combinacion.estado][nodo]*combinacion.factor_conductor+
                     adicional*combinacion.factor_adicional)
            filas.append(dict(Punto=nodo,Caso=combinacion.nombre,
                         **dict(zip(('Fx','Fy','Fz','Mx','My','Mz'),carga))))
            for alt in datos.get('alternativas',{}).get(nodo,[]):
                r = evaluar_alternativa(alt,carga,combinacion.nombre,combinacion.metodo)
                r['nodo'] = nodo
                alternativas.append(r)
    return filas,alternativas


def ejecutar_proyecto_integral(datos):
    """API pública: devuelve tablas, verificaciones, decisiones y entrada reproducible."""
    nodos,conductores,vanos,estados,combinaciones = _validar_proyecto(datos)
    por_estado,filas_vanos,verificaciones = {},[],[]
    for estado in estados.values():
        fuerzas,filas,checks = _evaluar_estado(nodos,conductores,vanos,estado)
        por_estado[estado.nombre] = fuerzas
        filas_vanos.extend(filas)
        verificaciones.extend(checks)
    filas_nodos,alternativas = _evaluar_combinaciones(datos,nodos,combinaciones,por_estado)
    decisiones = [{'Punto':n,**seleccionar_alternativa([r for r in alternativas if r['nodo']==n])}
                  for n in nodos]
    verificaciones_alt = [{**v.como_dict(),'nodo':r['nodo'],'alternativa':r['nombre']}
                         for r in alternativas for v in r['verificaciones']]
    return {'vanos_estados':pd.DataFrame(filas_vanos),'acciones_nodos':pd.DataFrame(filas_nodos),
            'verificaciones_conductor':pd.DataFrame([v.como_dict() for v in verificaciones]),
            'verificaciones':pd.DataFrame(verificaciones_alt),'decision':pd.DataFrame(decisiones),
            'alternativas':alternativas,'envolventes':_envolventes(filas_nodos),
            'envolventes_conductor':_envolventes_conductor(filas_vanos),
            'trazabilidad':_trazabilidad(datos),'entrada':datos}


def _envolventes(filas):
    """Máximos absolutos con signo y caso gobernante; nunca mezcla un vector ficticio."""
    tabla = pd.DataFrame(filas)
    salida = []
    for nodo,g in tabla.groupby('Punto'):
        for componente in ('Fx','Fy','Fz','Mx','My','Mz'):
            fila = g.loc[g[componente].abs().idxmax()]
            salida.append({'Punto':nodo,'Componente':componente,'Valor':fila[componente],
                           'Caso gobernante':fila['Caso'],'Unidad':'kN' if componente[0]=='F' else 'kN·m'})
    return pd.DataFrame(salida)


def _trazabilidad(datos):
    """Huella de entrada y versiones; ecuaciones deducidas, sin citas inventadas."""
    canon = json.dumps(datos,sort_keys=True,ensure_ascii=False,allow_nan=False)
    return {'version_motor':VERSION_MOTOR,'sha256_entrada':hashlib.sha256(canon.encode()).hexdigest(),
            'sistema':'X Este, Y Norte, Z arriba; m, kN, kN·m, °C',
            'modelo':'Catenaria bajo q uniforme por longitud real; vanos retenidos',
            'ecuaciones':'docs/ECUACIONES.md','catalogo':'Datos explícitos del proyecto JSON',
            'alcance':'Candidato de cálculo. Verificaciones específicas de material/suelo pendientes.'}


def _envolventes_conductor(filas):
    """Estados gobernantes de tensión, flecha y despeje; conserva valores sin redondear."""
    tabla = pd.DataFrame(filas)
    salida = []
    for vano,g in tabla.groupby('Vano'):
        g = g.copy()
        g['T máxima (kN)'] = g[['T_A (kN)','T_B (kN)']].max(axis=1)
        for nombre,minimizar in [('T máxima (kN)',False),('Flecha vertical cuerda (m)',False),
                                 ('Despeje terreno lineal (m)',True)]:
            indice = g[nombre].idxmin() if minimizar else g[nombre].idxmax()
            fila = g.loc[indice]
            salida.append({'Vano':vano,'Magnitud':nombre,'Valor':fila[nombre],
                           'Estado gobernante':fila['Estado']})
    return pd.DataFrame(salida)
