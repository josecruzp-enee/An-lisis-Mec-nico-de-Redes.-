"""Auxiliar H*h para cargas centradas; fuerzas excéntricas requieren cargas_espaciales."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .geometria_amarres import alturas_amarre


def calcular_momento_poste(df_fuerzas_nodo,df_resumen=None,*,col_punto='Punto',
        col_H='H (kN)',col_poste='Poste',col_altura_amarre_excel='Altura_Amarre_m',
        default_h_amarre_m=None,he_offset_m=.10,incluir_fp=False):
    """Firma compatible, sin inventar alturas; exige amarre medido sobre terreno.

    default_h_amarre_m se conserva sólo por compatibilidad, no se aplica.
    El signo de H se conserva. Este auxiliar no comprueba capacidad del poste.
    """
    if df_fuerzas_nodo is None or df_fuerzas_nodo.empty:
        raise ValueError('Fuerzas vacías')
    out=df_fuerzas_nodo.copy()
    if df_resumen is not None:
        adicionales=[c for c in df_resumen.columns if c not in out.columns]
        out=out.merge(df_resumen[[col_punto]+adicionales],on=col_punto,validate='one_to_one')
    if 'h_amarre (m)' in out:
        h=out['h_amarre (m)'].to_numpy(dtype=float)
    else:
        datos=out.rename(columns={col_altura_amarre_excel:'Altura_Amarre_m',col_poste:'Poste'})
        h=alturas_amarre(datos)
    if h is None or not np.isfinite(h).all() or (h<=0).any():
        raise ValueError('Falta altura de amarre válida')
    fuerzas=out[col_H].to_numpy(dtype=float)
    if not np.isfinite(fuerzas).all():
        raise ValueError('Fuerzas no finitas')
    out['h_amarre (m)']=h
    out['M_base (kN·m)']=fuerzas*h
    if incluir_fp:
        out['He (m)']=h+he_offset_m
        if (out['He (m)']<=0).any():
            raise ValueError('Altura equivalente inválida')
        out['Fp (kN)']=out['M_base (kN·m)']/out['He (m)']
    return out
