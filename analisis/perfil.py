"""Perfil longitudinal exacto sin viento, con terreno lineal entre apoyos.

API heredada conservada. Para viento, temperatura y puntos de amarre 3D usar
motor_integral. El despeje a terreno lineal no comprueba obstáculos no medidos.
"""
from __future__ import annotations
import numpy as np
from .catenaria import resolver_catenaria
from .geometria_amarres import alturas_amarre, longitudes_poste
from .mecanica import peso_lineal_kN_m, tension_trabajo_kN
from .validacion_mecanica import finito, validar_puntos

OFFSET_AMARRE_DESDE_PUNTA_M_DEFAULT = .10
DESPEJE_MIN_M_DEFAULT = None


def altura_poste_por_df(df,tipo_poste,default_m=float('nan')):
    """Compatibilidad: devuelve longitud total por punto, nunca altura expuesta."""
    return longitudes_poste(df,tipo_poste)


def altura_amarre_abs(df,terreno,h_poste,*,offset_desde_punta_m=.10):
    """Cota de amarre; exige altura medida o empotramiento explícito."""
    datos = df.copy()
    datos['Altura_Poste_m'] = h_poste
    h = alturas_amarre(datos,offset_m=offset_desde_punta_m)
    if h is None:
        raise ValueError('Falta Altura_Amarre_m o Empotramiento_m')
    return np.asarray(terreno)+h


def sag_parabolica_m(L,wv_kN_m,H_kN):
    """Aproximación auxiliar w L²/(8H), no sustituye al cable exacto."""
    finito(L,'L',0); finito(wv_kN_m,'peso',0); finito(H_kN,'H',0,True)
    return wv_kN_m*L**2/(8*H_kN)


def sag_catenaria_m(Lh,wv_kN_m,H_kN):
    """Flecha nivelada exacta; 2a sinh²(L/4a) evita cancelación numérica."""
    sag_parabolica_m(Lh,wv_kN_m,H_kN)
    if Lh == 0 or wv_kN_m == 0:
        return 0.0
    cable = resolver_catenaria([0,0,0],[Lh,0,0],[0,0,-wv_kN_m],H_kN)
    return float(-cable.puntos(Lh/2)[2])


def tension_soporte_catenaria_kN(Lh,wv_kN_m,H_kN):
    """Tensión total en apoyo nivelado; con carga nula sigue siendo H."""
    sag_parabolica_m(Lh,wv_kN_m,H_kN)
    if Lh == 0 or wv_kN_m == 0:
        return H_kN
    return float(resolver_catenaria([0,0,0],[Lh,0,0],[0,0,-wv_kN_m],H_kN).tension(0))


def evaluar_despeje_por_vano(chain0,L,g0,g1,y0,y1,sag_f,npts=80):
    """API auxiliar parabólica. Mínimo analítico, independiente de la malla."""
    finito(L,'L',0,True)
    finito(sag_f,'flecha',0)
    if npts < 2:
        raise ValueError('npts debe ser al menos 2')
    r = np.linspace(0,1,int(npts))
    terreno = g0+(g1-g0)*r
    conductor = y0+(y1-y0)*r-4*sag_f*r*(1-r)
    pendiente = (y1-g1)-(y0-g0)
    rc = np.clip((4*sag_f-pendiente)/(8*sag_f),0,1) if sag_f else float(pendiente < 0)
    minimo = y0-g0+pendiente*rc-4*sag_f*rc*(1-rc)
    return chain0+L*r,terreno,conductor,float(minimo)


def _vano_exacto(L,g0,g1,y0,y1,H,w):
    """Perfil, flecha respecto a cuerda y mínimo de despeje analítico."""
    cable = resolver_catenaria([0,0,y0],[L,0,y1],[0,0,-w],H)
    x = np.linspace(0,L,90)
    terreno = g0+(g1-g0)*x/L
    yc = cable.puntos(x)[:,2]
    xmin = cable.minimo_lineal([0,0,1],(g1-g0)/L)
    despeje = cable.puntos(xmin)[2]-(g0+(g1-g0)*xmin/L)
    xf = cable.minimo_lineal([0,0,1],(y1-y0)/L)
    flecha = y0+(y1-y0)*xf/L-cable.puntos(xf)[2]
    return x,terreno,yc,float(despeje),float(flecha),float(cable.tension(0)),float(cable.tension(L))


def _fila_perfil(etiquetas,i,L,modo,w,H,f,ta,tb,despeje,limite):
    """Conserva columnas heredadas y distingue los dos apoyos desnivelados."""
    cumple = 'NO VERIFICABLE' if limite is None else ('SI' if despeje >= limite else 'NO')
    return {'Tramo':f'{etiquetas[i]} → {etiquetas[i+1]}','Longitud (m)':L,
            'Modo sag':modo,'wv (kN/m)':w,'H (kN)':H,'Ts (kN)':max(ta,tb),
            'Ts A (kN)':ta,'Ts B (kN)':tb,'Sag f (m)':f,
            'Despeje mín (m)':despeje,'Cumple despeje':cumple}


def analizar_perfil(df,tipo_poste,calibre,*,fraccion_trabajo=None,modo_sag='CATENARIA',
                     offset_amarre_desde_punta_m=.10,despeje_min_m=None,H_kN=None):
    """Sin cota/amarre/tensión retorna None; jamás interpreta faltantes como cumplimiento."""
    if 'Altitud' not in df:
        return None
    validar_puntos(df)
    h = alturas_amarre(df,tipo_poste,offset_amarre_desde_punta_m)
    if h is None or (H_kN is None and fraccion_trabajo is None):
        return None
    H = H_kN if H_kN is not None else tension_trabajo_kN(calibre,fraccion_trabajo)
    finito(H,'H',0,True)
    if despeje_min_m is not None:
        finito(despeje_min_m,'despeje mínimo',0,True)
    modo = str(modo_sag).strip().upper()
    if modo not in ('CATENARIA','PARABOLA'):
        raise ValueError('Modo de flecha desconocido')
    terreno = df['Altitud'].to_numpy(dtype=float)
    if not np.isfinite(terreno).all():
        raise ValueError('Altitudes no finitas')
    return _construir_perfil(df,terreno,h,H,peso_lineal_kN_m(calibre),modo,despeje_min_m,
                            {'tipo_poste':tipo_poste,'calibre':calibre,'H_kN':H,
                             'fraccion_trabajo':fraccion_trabajo,'modo_sag':modo,
                             'despeje_min_m':despeje_min_m,'alcance':'Sin viento; terreno lineal'})


def _construir_perfil(df,terreno,h,H,w,modo,limite,meta):
    """Ensambla vanos independientes y arrays usados por los gráficos existentes."""
    xy = df[['X','Y']].to_numpy(dtype=float)
    luces = np.linalg.norm(np.diff(xy,axis=0),axis=1)
    chain = np.r_[0,np.cumsum(luces)]
    amarre = terreno+h
    perfiles,filas = [],[]
    for i,L in enumerate(luces):
        g0,g1,y0,y1 = terreno[i],terreno[i+1],amarre[i],amarre[i+1]
        x,g,y,cl,f,ta,tb = _vano_exacto(L,g0,g1,y0,y1,H,w)
        if modo == 'PARABOLA':
            f = sag_parabolica_m(L,w,H)
            x,g,y,cl = evaluar_despeje_por_vano(0,L,g0,g1,y0,y1,f,90)
            pendiente = (y1-y0)/L
            ta,tb = H*np.sqrt(1+(pendiente-4*f/L)**2),H*np.sqrt(1+(pendiente+4*f/L)**2)
        perfiles.append((chain[i]+x,g,y))
        filas.append(_fila_perfil(df['Punto'].tolist(),i,L,modo,w,H,f,ta,tb,cl,limite))
    return {'total_m':float(chain[-1]),'chain_nodes':chain,'terreno':terreno,'amarre':amarre,
            'X_prof':np.concatenate([p[0] for p in perfiles]),
            'G_prof':np.concatenate([p[1] for p in perfiles]),
            'Y_prof':np.concatenate([p[2] for p in perfiles]),'tabla_vanos':filas,'meta':meta}
