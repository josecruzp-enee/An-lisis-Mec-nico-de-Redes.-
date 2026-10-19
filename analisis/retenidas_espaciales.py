"""Poste elástico de seis grados de libertad y cables sólo a tracción.

K del poste debe proceder de un modelo estructural documentado. Desplazamientos
pequeños del poste: u_amarre = u_base + rotación × r. No modela P-delta ni
fisuración del poste; la aceptación exige comprobar esos límites por separado.
"""
from __future__ import annotations
import numpy as np
from .validacion_mecanica import finito, vector3


def matriz_amarre(posicion):
    """Transformación cinemática 3×6, conjugada con fuerzas y momentos."""
    x,y,z = vector3(posicion,'amarre')
    cruz = np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.column_stack((np.eye(3),-cruz))


def preparar_retenida(datos):
    """Coordenadas locales reales, rigidez EA/L y pretensión explícita."""
    r = vector3(datos['amarre_m'],'amarre retenida')
    ancla = vector3(datos['ancla_m'],'ancla retenida')
    L = finito(np.linalg.norm(ancla-r),'longitud retenida',0,True)
    EA = finito(datos['EA_kN'],'EA retenida',0,True)
    pret = finito(datos.get('pretension_kN',0),'pretensión',0)
    return r, ancla, EA, L/(1+pret/EA)


def _respuesta_cable(preparada, desplazamiento):
    """Fuerza y tangente geométrica consistentes; el cable flojo aporta cero."""
    r, ancla, EA, L0 = preparada
    B = matriz_amarre(r)
    v = r+B@desplazamiento-ancla
    L = finito(np.linalg.norm(v),'longitud deformada',0,True)
    n = v/L
    tension = max(EA*(L/L0-1),0.0)
    tangente = np.zeros((3,3))
    if tension > 0:
        tangente = EA/L0*np.outer(n,n)+tension/L*(np.eye(3)-np.outer(n,n))
    return B.T@(tension*n), B.T@tangente@B, tension, -tension*n


def _respuesta_sistema(K, cables, u):
    """Fuerza interna y rigidez tangente del conjunto poste–retenidas."""
    interna, tangente = K@u, K.copy()
    for cable in cables:
        f, k, _, _ = _respuesta_cable(cable,u)
        interna += f
        tangente += k
    return interna, tangente


def resolver_poste_retenidas(K, acciones, retenidas, tolerancia=1e-8, max_iter=100):
    """Newton amortiguado con cable unilateral; no reparte cargas por cantidad.

    K: matriz 6×6 simétrica definida positiva, coherente con m, rad, kN, kN·m.
    acciones: [Fx,Fy,Fz,Mx,My,Mz]. El residual se devuelve para auditoría.
    """
    K = np.asarray(K,dtype=float)
    carga = np.asarray(acciones,dtype=float)
    if K.shape != (6,6) or not np.isfinite(K).all() or not np.allclose(K,K.T):
        raise ValueError('Rigidez del poste inválida')
    if carga.shape != (6,) or not np.isfinite(carga).all():
        raise ValueError('Acciones requieren seis componentes finitas')
    if np.linalg.eigvalsh(K).min() <= 0:
        raise ValueError('Rigidez singular/inestable: no se puede repartir cargas')
    cables = [preparar_retenida(r) for r in retenidas]
    u = np.zeros(6)
    for i in range(max_iter):
        interna, tangente = _respuesta_sistema(K,cables,u)
        residual = interna-carga
        if np.linalg.norm(residual,np.inf) <= tolerancia:
            return _resultado(K,cables,u,residual,i)
        paso = np.linalg.solve(tangente,-residual)
        u = _amortiguar(K,cables,u,paso,carga,np.linalg.norm(residual))
    raise ValueError('Equilibrio poste–retenidas sin convergencia')


def _amortiguar(K,cables,u,paso,carga,norma):
    """Reduce el paso para cruzar de forma estable entre cable tenso y flojo."""
    for j in range(30):
        candidato = u+paso*(.5**j)
        f,_ = _respuesta_sistema(K,cables,candidato)
        if np.linalg.norm(f-carga) < norma:
            return candidato
    raise ValueError('Equilibrio: no se encontró un paso descendente')


def _resultado(K,cables,u,residual,iteraciones):
    """Conserva tracciones, compresión inducida y momentos residuales."""
    respuestas = [_respuesta_cable(c,u) for c in cables]
    return {'desplazamiento':u,'acciones_poste':K@u,'residual':residual,
            'iteraciones':iteraciones,'tensiones_kN':[r[2] for r in respuestas],
            'fuerzas_retenidas_kN':[r[3] for r in respuestas]}
