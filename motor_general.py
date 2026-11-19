"""Motor general: único punto de coordinación de los módulos de ingeniería.

La interfaz llama a este coordinador. Ningún módulo importa internamente
el código del otro: los resultados se intercambian desde aquí.
"""
from __future__ import annotations


def ejecutar_modulo(nombre: str, *args, **kwargs):
    """Despacha los cálculos conservando la API original de cada módulo."""
    if nombre == "estructuras":
        from Analisis_mecanico_estructuras.motor import ejecutar_todo as ejecutar
    elif nombre == "conductores":
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_analisis_integral_de_conductores import ejecutar_analisis_integral as ejecutar
    elif nombre == "cfe":
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano as ejecutar
    else:
        raise ValueError(f"Módulo desconocido: {nombre!r}")
    return ejecutar(*args, **kwargs)


def ejecutar_todo(*args, **kwargs):
    """Compatibilidad de la interfaz: verificación preliminar de estructuras."""
    return ejecutar_modulo("estructuras", *args, **kwargs)
