"""Verificación independiente de cada eslabón de una retenida.

Las capacidades de suelo/extracción deben proceder de un estudio específico
para el ancla y su dirección de carga. No se infieren de su diámetro.
"""
from .estados_limite import verificar_capacidad

COMPONENTES = ('cable','fijacion','herrajes','varilla','ancla','suelo')


def verificar_anclaje(tension_kN, capacidades, caso='', metodo='servicio'):
    """Exige capacidades admisibles/de diseño y procedencia de seis componentes."""
    salida = []
    for nombre in COMPONENTES:
        ficha = capacidades.get(nombre,{})
        compatible = ficha.get('tipo') in ('admisible','diseno') and ficha.get('metodo') == metodo
        salida.append(verificar_capacidad(nombre,tension_kN,
                      ficha.get('valor') if compatible else None,'kN',ficha.get('fuente',''),caso))
    return salida
