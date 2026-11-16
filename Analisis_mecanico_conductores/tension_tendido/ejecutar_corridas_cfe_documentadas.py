"""Hipótesis de CFE DCCIAMBT y cálculo por vanos reales.

Fuentes: CFE DCCIAMBT (2014), 05 00 02/05 00 03 y 07 FT 01.
NO se usan los valores P, tensiones ni flechas de tablas ENEE como entrada.
Los límites porcentuales se aplican a tensión MÁXIMA del conductor
(apoyos), no a un valor de referencia H.

Esta primera validación calcula referencias inicial y final SEPARADAS con
las respectivas hipótesis y módulos. NO las presenta como una evolución
física única entre tendido y servicio: esa transformación requiere
modelo de deformación permanente documentado. No se inventa creep.
"""
from __future__ import annotations

import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, EstadoReferenciaCFE, HipotesisDisenoCFE,
    calcular_parametro_cfe_desde_limites, calcular_tablas_inicial_final,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import vano_regulador


CFE_FUENTE = (
    "CFE DCCIAMBT (2014), secciones 05 00 02, 05 00 03 y 07 FT 01; "
    "límites del diseño básico de estructuras"
)


def construir_hipotesis_cfe(
    ruptura_kN, *, viento_max_kmh, viento_reducido_kmh, hielo_mm,
):
    """Devuelve hipótesis por condición, exclusivamente documentadas.

    Viento reducido y hielo han de declararse para el caso de estudio.
    La tabla porcentual es CFE DCCIAMBT; no proviene de Checa.
    """
    rotura=float(ruptura_kN)
    v_max=float(viento_max_kmh)
    v_red=float(viento_reducido_kmh)
    hielo=float(hielo_mm)
    if rotura<=0 or v_max<=0 or v_red<0 or hielo<0:
        raise ValueError(
            "La ruptura y el viento máximo deben ser positivos. "
            "El viento reducido y el hielo admiten cero si así "
            "lo establece el caso de estudio; no admiten negativos."
        )
    if v_red>v_max:
        raise ValueError("Viento reducido no puede exceder viento máximo")
    condicion_frio = (
        "CFE final -10°C viento reducido + hielo (45% RTS)"
        if hielo > 0 else
        "CFE final -10°C viento reducido SIN hielo (45% RTS)"
    )
    inicial=[
        HipotesisDisenoCFE("CFE inicial 0°C sin viento (33% RTS)",
                           0.,0.,0.,rotura*.33,CFE_FUENTE),
    ]
    final=[
        HipotesisDisenoCFE("CFE final 16°C sin viento (20% RTS)",
                           16.,0.,0.,rotura*.20,CFE_FUENTE),
        HipotesisDisenoCFE("CFE final 0°C sin viento (25% RTS)",
                           0.,0.,0.,rotura*.25,CFE_FUENTE),
        HipotesisDisenoCFE(condicion_frio,
                           -10.,v_red,hielo,rotura*.45,CFE_FUENTE),
        HipotesisDisenoCFE("CFE final 0°C viento máximo (45% RTS)",
                           0.,v_max,0.,rotura*.45,CFE_FUENTE),
    ]
    return inicial,final


def ejecutar_corridas_cfe_por_vano(
    puntos, ficha_inicial, ficha_final, *, viento_max_kmh,
    viento_reducido_kmh, hielo_mm, temperaturas_C,
    Cd=1.0, rho_kg_m3=1.225,
):
    """Calcula condiciones de referencia y tablas por vano real.

    CFE emplea Cd=1 para cables; densidad de aire es entrada explícita.
    P=H50/peso es SALIDA del optimizador, no una tensión prescrita.

    IMPORTANTE: las referencias inicial y final todavía no se relacionan
    por creep; no equiparar automáticamente al procedimiento SAGSEC.
    """
    campos=("peso_kN_m","diametro_m","ruptura_kN")
    for campo in campos:
        if abs(float(ficha_inicial[campo])-float(ficha_final[campo]))>1e-10:
            raise ValueError("Fichas inicial y final de conductores diferentes")
    propiedades=PropiedadesConductorCFE(
        peso_kN_m=float(ficha_inicial["peso_kN_m"]),
        diametro_m=float(ficha_inicial["diametro_m"]),
        EA_inicial_kN=float(ficha_inicial["EA_kN"]),
        EA_final_kN=float(ficha_final["EA_kN"]),
        alpha_inicial_por_C=float(ficha_inicial["alpha_por_C"]),
        alpha_final_por_C=float(ficha_final["alpha_por_C"]),
        ruptura_kN=float(ficha_inicial["ruptura_kN"]),
        fuente=str(ficha_inicial["fuente"])+" | "+str(ficha_final["fuente"]),
    )
    propiedades.validar()
    ini,fin=construir_hipotesis_cfe(
        propiedades.ruptura_kN,viento_max_kmh=viento_max_kmh,
        viento_reducido_kmh=viento_reducido_kmh,hielo_mm=hielo_mm,
    )
    xyz,luces=_geometria(puntos)
    # Claro regla informativo: equivalente convencional de una sección
    # con suspensión deslizante ideal y vanos aproximadamente nivelados.
    # El motor actual mantiene amarres fijos; NO emplear este claro como
    # condición de contorno ni confundirlo con el claro de diseño ENEE.
    claro_regla_m=vano_regulador(luces)
    desnivel_max_m=max(abs(float(xyz[i+1,2]-xyz[i,2])) for i in range(len(luces)))
    referencia_inicial=calcular_parametro_cfe_desde_limites(
        xyz,propiedades,ini,condicion="Inicial",Cd=Cd,rho_kg_m3=rho_kg_m3,
    )
    referencia_final=calcular_parametro_cfe_desde_limites(
        xyz,propiedades,fin,condicion="Final",Cd=Cd,rho_kg_m3=rho_kg_m3,
    )
    if referencia_inicial["cota_busqueda_activa"] or referencia_final["cota_busqueda_activa"]:
        raise ValueError(
            "Se alcanzó el límite superior sin hipótesis gobernante. "
            "No se asignará un parámetro P arbitrario."
        )
    estados_extra=[
        ("CFE viento reducido + hielo" if hielo_mm > 0 else
         "CFE viento reducido SIN hielo",-10.,float(viento_reducido_kmh),float(hielo_mm)),
        ("CFE viento máximo",0.,float(viento_max_kmh),0.),
    ]
    tabla=calcular_tablas_inicial_final(
        puntos,propiedades,
        EstadoReferenciaCFE(referencia_inicial["parametro_P_m"],CFE_FUENTE),
        EstadoReferenciaCFE(referencia_final["parametro_P_m"],CFE_FUENTE),
        temperaturas_C,estados_climaticos=estados_extra,
        Cd=Cd,rho_kg_m3=rho_kg_m3,
    )
    resumen=pd.DataFrame([
        {"Condición":"Inicial — referencia independiente",
         "Hipótesis aplicadas":"; ".join(h.nombre for h in ini),**referencia_inicial},
        {"Condición":"Final — referencia independiente (NO creep)",
         "Hipótesis aplicadas":"; ".join(h.nombre for h in fin),**referencia_final},
    ])
    resumen["Claro regla convencional orientativo (m)"]=claro_regla_m
    resumen["Número de vanos"]=len(luces)
    resumen["Desnivel máximo entre apoyos (m)"]=desnivel_max_m
    resumen["Advertencia"]=(
        "Claros reales: motor de amarres fijos por vano. "
        "Claro regla: solo informativo, no usado en el cálculo. "
        "Referencias inicial/final independientes, sin creep validado."
    )
    return resumen,tabla
