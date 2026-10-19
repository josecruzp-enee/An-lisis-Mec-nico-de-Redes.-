"""Alturas reales: diferencia longitud total, empotramiento y altura expuesta."""
import numpy as np
from .norma_postes import altura_poste_m


def alturas_amarre(df, tipo_poste='', offset_m=.10):
    """Usa altura explícita o longitud menos empotramiento y offset documentados.

    No inventa empotramiento. La columna Altura_Amarre_m es sobre terreno.
    Devuelve None si faltan datos para el conjunto; entradas inválidas fallan.
    """
    if 'Altura_Amarre_m' in df:
        h = df['Altura_Amarre_m'].to_numpy(dtype=float)
    elif 'Empotramiento_m' in df:
        total = longitudes_poste(df,tipo_poste)
        enterrado = df['Empotramiento_m'].to_numpy(dtype=float)
        if not np.isfinite(enterrado).all() or (enterrado < 0).any():
            raise ValueError('Empotramiento debe ser finito y no negativo')
        h = total-enterrado-float(offset_m)
    else:
        return None
    if not np.isfinite(h).all() or (h <= 0).any():
        raise ValueError('Altura de amarre debe ser finita y positiva')
    return h


def longitudes_poste(df,tipo_poste=''):
    """Longitud total por fila; poste desconocido no recibe una altura ficticia."""
    if 'Altura_Poste_m' in df:
        return df['Altura_Poste_m'].to_numpy(dtype=float)
    tipos = df['Poste'].tolist() if 'Poste' in df else [tipo_poste]*len(df)
    return np.array([altura_poste_m(p,default_m=float('nan')) for p in tipos])
