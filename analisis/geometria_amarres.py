"""Alturas de amarre: prioridad a mediciones y regla de empotramiento del proyecto.

Prioridad: Altura_Amarre_m explícita > Empotramiento_m explícito >
regla general E = 0.10*L(pies) + 2 pies.
Una altura calculada NO supone validación geotécnica o normativa.
"""
import numpy as np
from .norma_postes import altura_poste_m, empotramiento_por_regla_m


def longitudes_poste(df, tipo_poste=''):
    """Longitud total en metros; desconocidos permanecen no verificables."""
    if 'Altura_Poste_m' in df:
        valores = df['Altura_Poste_m'].to_numpy(dtype=float)
    else:
        tipos = df['Poste'].tolist() if 'Poste' in df else [tipo_poste] * len(df)
        valores = np.array([altura_poste_m(p, default_m=float('nan')) for p in tipos])
    return valores


def _enterramientos(df, longitudes):
    """Usa profundidades explícitas o regla general, rechazando datos inválidos."""
    if 'Empotramiento_m' in df:
        valores = df['Empotramiento_m'].to_numpy(dtype=float)
    else:
        valores = np.array([empotramiento_por_regla_m(L) for L in longitudes])
    if not np.isfinite(valores).all() or (valores < 0).any() or (valores >= longitudes).any():
        raise ValueError('Empotramiento debe ser finito, no negativo y menor que longitud total')
    return valores


def alturas_amarre(df, tipo_poste='', offset_m=.10):
    """Altura sobre terreno, usando la cota de amarre observada si existe.

    El offset de 0.10 m es el valor legado de interfaz y no un valor normativo.
    """
    if 'Altura_Amarre_m' in df:
        h = df['Altura_Amarre_m'].to_numpy(dtype=float)
    else:
        longitud = longitudes_poste(df, tipo_poste)
        if not np.isfinite(longitud).all() or (longitud <= 0).any():
            return None
        offset = float(offset_m)
        if not np.isfinite(offset) or offset < 0:
            raise ValueError('Offset debe ser finito y no negativo')
        h = longitud - _enterramientos(df, longitud) - offset
    if not np.isfinite(h).all() or (h <= 0).any():
        raise ValueError('Altura de amarre debe ser finita y positiva')
    return h
