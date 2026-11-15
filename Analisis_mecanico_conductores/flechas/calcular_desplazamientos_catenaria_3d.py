"""Flecha vertical y desviación transversal de una catenaria 3D.

Referencia geométrica: la CUERDA que une los dos amarres, no la cota
del apoyo inicial ni un plano horizontal. Se usa la catenaria exacta ya
calculada; no se resuelve un segundo modelo de tensiones.

Con amarres nivelados coincide con la definición de flecha convencional.
Para desniveles evita atribuir a la flecha la diferencia entre cotas.
No calcula despejes contra terreno ni obstáculos.
"""
from __future__ import annotations

import numpy as np


def _separacion_cuerda(cable, a, b, x, direccion):
    """Proyección firmada cable-cuerda en la abscisa local x."""
    t=float(x)/float(cable.luz)
    cuerda=a+t*(b-a)
    return float(np.dot(cable.puntos(float(x))-cuerda,direccion))


def calcular_flecha_y_desviacion_3d(cable, inicio_m, fin_m):
    """Retorna (flecha vertical, desviación lateral máxima), ambas en m.

    Flecha: máximo descenso vertical respecto a la recta de amarres.
    Lateral: máximo desplazamiento transversal respecto a la misma cuerda,
    normal a la proyección horizontal del vano. Son magnitudes geométricas
    distintas del punto más bajo de la catenaria.
    """
    a=np.asarray(inicio_m,dtype=float)
    b=np.asarray(fin_m,dtype=float)
    delta=b-a
    proy=delta[:2]
    luz_planta=float(np.linalg.norm(proy))
    if luz_planta<=0 or cable.luz<=0:
        raise ValueError("Se requiere luz horizontal positiva para medir flecha")
    vertical=np.array([0.,0.,1.])
    # El extremo de descenso está donde z(x)-z_cuerda(x) es mínimo.
    x_min=cable.minimo_lineal(
        vertical,pendiente=float(delta[2])/float(cable.luz)
    )
    flecha=max(0.,-_separacion_cuerda(cable,a,b,x_min,vertical))

    normal=np.array([-proy[1],proy[0],0.])/luz_planta
    # Buscar los dos signos: la carga puede actuar sobre cualquier costado.
    pendiente=float(np.dot(delta,normal))/float(cable.luz)
    x_neg=cable.minimo_lineal(normal,pendiente=pendiente)
    x_pos=cable.minimo_lineal(-normal,pendiente=-pendiente)
    lateral=max(
        abs(_separacion_cuerda(cable,a,b,x_neg,normal)),
        abs(_separacion_cuerda(cable,a,b,x_pos,normal)),
    )
    return flecha,lateral
