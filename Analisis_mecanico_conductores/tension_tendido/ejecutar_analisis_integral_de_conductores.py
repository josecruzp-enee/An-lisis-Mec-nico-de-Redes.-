"""Punto único de ejecución de la Etapa 1 (no duplica ecuaciones).

Recibe la ficha mecánica SI de una única fuente y las hipótesis ya
documentadas. Ejecuta tensión de tendido, estados, flechas, tabla de
tendido y barrido climático en una sola llamada al motor canónico.
"""
from __future__ import annotations

import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    resolver_seccion_regulacion,
)
from Analisis_mecanico_conductores.verificaciones.perfil_limites_tension_checa import (
    construir_hipotesis_checa_acsr,
)
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito


def ejecutar_analisis_integral(
    puntos, *, propiedades, temperatura_tendido_C=20.,
    perfil_tension="Checa", hipotesis_manuales=None,
    configuracion_barrido=None, Cd=1.2, rho=1.225,
):
    """Ejecuta análisis integral de una sección nivelada entre remates.

    propiedades: dict con peso_kN_m, diametro_m, EA_kN, alpha_por_C,
    ruptura_kN y fuente; todos de una ficha técnica consistente.
    perfil_tension: 'Checa' (TCD/THF de referencia) o 'Manual' (requiere
    hipótesis completas con fuente). Sin hipótesis normativas de
    viento/hielo y sin capacidades de estructuras.
    Devuelve ResultadoRegulacion con tablas y barrido opcional.
    """
    campos=("peso_kN_m","diametro_m","EA_kN","alpha_por_C","ruptura_kN","fuente")
    faltantes=[campo for campo in campos if campo not in propiedades]
    if faltantes:
        raise ValueError("Ficha de conductor incompleta: "+", ".join(faltantes))
    rotura=finito(propiedades["ruptura_kN"],"ruptura del conductor",0,True)
    perfil=str(perfil_tension).strip().upper()
    if perfil in ("CHECA","CHECA TCD/THF","CHECA_TCD_THF"):
        hip=construir_hipotesis_checa_acsr(rotura)
    elif perfil=="MANUAL":
        if not isinstance(hipotesis_manuales,pd.DataFrame) or hipotesis_manuales.empty:
            raise ValueError("El perfil Manual requiere hipótesis documentadas")
        hip=hipotesis_manuales.copy()
    else:
        raise ValueError("Perfil_Tension debe ser Checa o Manual")
    if "T_limite_kN" not in hip:
        raise ValueError("Hipotesis requiere T_limite_kN documentada")
    for _,caso in hip.iterrows():
        limite=finito(caso["T_limite_kN"],"límite de tensión",0,True)
        if limite>=rotura:
            raise ValueError("El límite declarado alcanza la ruptura nominal")
    return resolver_seccion_regulacion(
        puntos,hipotesis=hip,
        temperaturas_tabla_C=[0,10,20,30,40,50],
        peso_kN_m=finito(propiedades["peso_kN_m"],"peso",0,True),
        diametro_m=finito(propiedades["diametro_m"],"diámetro",0,True),
        EA_kN=finito(propiedades["EA_kN"],"EA",0,True),
        alpha_por_C=finito(propiedades["alpha_por_C"],"dilatación"),
        fuente_material=str(propiedades["fuente"]),
        temperatura_tendido_C=finito(temperatura_tendido_C,"temperatura de tendido"),
        H_min_kN=.05*rotura,H_max_kN=.95*rotura,
        Cd=Cd,rho_kg_m3=rho,
        configuracion_barrido=configuracion_barrido,
    )
