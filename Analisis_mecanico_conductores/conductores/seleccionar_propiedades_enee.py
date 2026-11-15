"""Selecciona una ficha ACSR ENEE y convierte sus propiedades a SI.

Fuente: ENEE, Tablas 1-17.xlsx, hoja Tabla 16. No mezcla área,
peso o ruptura de ENEE con datos Viakon: una ficha es una fuente.
K y K' se conservan en JSON, pero no se usan en el modelo elástico.
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from math import isfinite

_GRAVEDAD = 9.80665


@lru_cache(maxsize=1)
def leer_catalogo_enee():
    """Lee la Tabla 16 y devuelve el conjunto inmutable de fichas originales."""
    ruta=files("Analisis_mecanico_conductores.conductores").joinpath(
        "propiedades_mecanicas_acsr_enee.json"
    )
    datos=json.loads(ruta.read_text(encoding="utf-8"))
    return tuple(datos["conductores"])


def seleccionar_conductor_enee(calibre, nombre, estado="Final"):
    """Obtiene propiedades para regulación, en unidades del motor.

    calibre: designación ENEE, p.ej. '2/0' o '266.8 MCM'.
    nombre: ave exacta, p.ej. 'QUAIL'. Nunca elegir solo por calibre,
    porque 477 MCM y 795 MCM tienen múltiples construcciones.
    estado: 'Inicial' o 'Final'; selecciona E inicial o final.

    Devuelve área_mm2, peso_kN_m, diametro_m, ruptura_kN,
    EA_kN, alpha_por_C y trazabilidad. No devuelve límites admisibles.
    """
    if estado not in ("Inicial","Final"):
        raise ValueError("Estado elástico debe ser Inicial o Final")
    candidatos=[
        fila for fila in leer_catalogo_enee()
        if fila["nombre"].strip().upper()==str(nombre).strip().upper()
        and fila["calibre"].replace(" MCM","").strip()==str(calibre).replace(" MCM","").strip()
    ]
    if len(candidatos)!=1:
        raise ValueError(
            f"Conductor {calibre} {nombre} sin ficha única en ENEE Tabla 16"
        )
    ficha=candidatos[0]
    area=float(ficha["area_mm2"])
    modulo=float(ficha["modulo_inicial_kgf_mm2"] if estado=="Inicial"
                 else ficha["modulo_final_kgf_mm2"])
    alpha=float(ficha["dilatacion_micro_por_C"])*1e-6
    masa=float(ficha["peso_unitario_kg_m"])
    diametro=float(ficha["diametro_mm"])
    ruptura=float(ficha["ruptura_kgf"])
    if not all(isfinite(x) and x>0 for x in
               (area,modulo,alpha,masa,diametro,ruptura)):
        raise ValueError("Propiedades ENEE incompletas o no físicas")
    origen=ficha["fuente"]+f", columna {ficha['columna_excel']}, E {estado.lower()}"
    return {
        "calibre":ficha["calibre"],
        "nombre":ficha["nombre"],
        "estado_elasticidad":estado,
        "area_mm2":area,
        "E_kgf_mm2":modulo,
        "EA_kN":modulo*area*_GRAVEDAD/1000,
        "alpha_por_C":alpha,
        "peso_kg_m":masa,
        "peso_kN_m":masa*_GRAVEDAD/1000,
        "diametro_m":diametro/1000,
        "ruptura_kN":ruptura*_GRAVEDAD/1000,
        "fuente":origen,
        "uso":"Modelo elástico lineal seleccionado; sin cálculo de creep",
    }


def seleccionar_desde_clave_viakon(clave, estado="Final"):
    """Interpreta el nombre de selección anterior; no usa propiedades Viakon."""
    from .catalogo_acsr_viakon import ficha_viakon_acsr
    ficha=ficha_viakon_acsr(clave)
    return seleccionar_conductor_enee(
        ficha["calibre"],ficha["codigo"],estado
    )
