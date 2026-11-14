"""Tabla auditable del catálogo ACSR para la interfaz y exportación CSV.

Separar datos Viakon (nominales) y Nexans (solo referencia comparativa).
No se infieren resistencias admisibles ni se exportan como 'certificadas'
propiedades de otro fabricante.
"""
from __future__ import annotations

import pandas as pd

from entradas.catalogo_viakon_acsr import CONDUCTORES_VIAKON_ACSR
from entradas.referencias_mecanicas_acsr import referencia_mecanica_nexans


def tabla_catalogo_acsr():
    filas=[]
    for nombre, f in CONDUCTORES_VIAKON_ACSR.items():
        r=referencia_mecanica_nexans(nombre)
        filas.append({
            "Conductor":nombre,
            "Código de ave":f["codigo"],
            "Calibre":f["calibre"],
            "Construcción Al/Acero":r["configuracion"],
            "Área aluminio nominal (mm²)":f["area_nominal_mm2"],
            "Diámetro total (mm)":f["diametro_mm"],
            "Peso aproximado (kg/km)":f["peso_kg_km"],
            "Carga ruptura nominal (kgf)":f["TR_kgf"],
            "Carga ruptura nominal (kN)":f["carga_rotura_kN"],
            "Resistencia CD 20°C (ohm/km)":f["resistencia_dc_20_ohm_km"],
            "Referencia E final Nexans (GPa)":r["E_final_GPa"],
            "Referencia EA final Nexans (kN)":r["EA_final_referencia_kN"],
            "Referencia alpha final Nexans (1/°C)":r["alpha_final_referencia_por_C"],
            "Propiedades E/alpha certificadas Viakon": "NO DISPONIBLES",
            "Fuente nominal":f["fuente"],
            "Fuente referencia":r["fuente"],
            "Estado":"REFERENCIAS NEXANS NO APTAS PARA CERTIFICAR VIakON",
        })
    return pd.DataFrame(filas)
