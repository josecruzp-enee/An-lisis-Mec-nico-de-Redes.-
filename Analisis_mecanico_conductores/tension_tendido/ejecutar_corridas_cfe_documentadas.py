"""Hipótesis de CFE DCCIAMBT y cálculo por vanos reales.

Fuentes: CFE DCCIAMBT (2014), 05 00 02/05 00 03 y 07 FT 01.
NO se usan los valores P, tensiones ni flechas de tablas ENEE como entrada.
Los límites porcentuales se aplican a tensión MÁXIMA del conductor
(apoyos), no a un valor de referencia H.

La referencia final se dimensiona por hipótesis explícitas; la inicial
se acopla a la tensión del estado final a -10 °C siguiendo CFE 07 FT 01.
No se predice creep ni se afirma equivalencia exacta con SAGSEC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, EstadoReferenciaCFE, HipotesisDisenoCFE,
    _evaluador,
    calcular_parametro_cfe_desde_limites, calcular_tablas_inicial_final,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import vano_regulador


# TENSIONES HORIZONTALES máximas de diseño de CFE 07 FT 10–14
# (cabeceras, para estructuras tipo y viento regional de 120 km/h).
# NO son porcentajes de la resistencia de rotura.
CFE_TH_KN = {
    "RAVEN": (6.495, 5.618),
    "PIGEON": (8.824, 7.513),
    "PARTRIDGE": (9.028, 7.451),
    "LINNET": (8.904, 7.297),
    "HAWK": (8.122, 6.637),
}

CFE_FUENTE = (
    "CFE DCCIAMBT (2014), secciones 05 00 02, 05 00 03 y 07 FT 01; "
    "límites del diseño básico de estructuras"
)


# Propiedades originales de CFE 07 FT 01, hoja 6/6.
# Peso: daN/m; E: miles de N/mm²; ruptura: daN;
# alfa en tabla: valores equivalentes a 1e-6/°C.
CFE_FT01_CONDUCTORES = {
    "RAVEN": (10.11, .2120, 62.4378, 71.2209, 78.0468,
              18.57, 18.95, 1947.74),
    "PIGEON": (12.75, .3377, 99.3038, 71.2209, 78.0468,
               18.57, 18.95, 2938.28),
    "PARTRIDGE": (16.30, .5349, 156.8655, 57.4318, 75.0125,
                  17.53, 18.82, 5022.34),
    "LINNET": (18.29, .6766, 198.3854, 57.4318, 75.0125,
               17.53, 18.82, 6299.26),
    "HAWK": (21.77, .9570, 280.8395, 57.4318, 75.0125,
             17.53, 18.82, 8654.98),
}


def seleccionar_propiedades_cfe_07_ft_01(nombre):
    """Ficha SI de CFE 07 FT 01. No intercambiar con ENEE Tabla 16."""
    clave = str(nombre).strip().upper()
    if clave not in CFE_FT01_CONDUCTORES:
        raise ValueError(f"No existe ficha CFE 07 FT 01 para {nombre}")
    diam_mm, peso_dan_m, area_mm2, ei, ef, ai, af, rotura_dan = (
        CFE_FT01_CONDUCTORES[clave]
    )
    fuente = f"CFE 07 FT 01 hoja 6/6; ACSR {clave}"
    base = {
        "nombre": clave,
        "peso_kN_m": peso_dan_m * 10. / 1000.,
        "diametro_m": diam_mm / 1000.,
        "ruptura_kN": rotura_dan * 10. / 1000.,
    }
    inicial = dict(base, EA_kN=ei * area_mm2,
                   alpha_por_C=ai * 1e-6, fuente=fuente+" inicial")
    final = dict(base, EA_kN=ef * area_mm2,
                 alpha_por_C=af * 1e-6, fuente=fuente+" final")
    return inicial, final


def construir_hipotesis_cfe(
    ruptura_kN, *, viento_max_kmh, viento_reducido_kmh, hielo_mm,
    nombre_conductor=None,
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
    # Los TH publicados corresponden a VR=120 km/h. No extrapolarlos
    # automáticamente a otras regiones de viento o configuraciones.
    th = (CFE_TH_KN.get(str(nombre_conductor).strip().upper())
          if abs(v_max - 120.) < 1e-9 else None)
    # Los límites TH1/TH2 de la cabecera CFE son HORIZONTALES;
    # el 45 % RTS es un límite de tensión TOTAL del conductor.
    # Se verifican AMBOS de forma independiente, sin tomar un min
    # entre magnitudes físicas distintas.
    limite_extremo_frio = rotura*.45
    limite_viento_max = rotura*.45
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
                           -10.,v_red,hielo,limite_extremo_frio,CFE_FUENTE,
                           limite_horizontal_kN=th[0] if th else None),
        HipotesisDisenoCFE("CFE final 0°C viento máximo (45% RTS)",
                           0.,v_max,0.,limite_viento_max,CFE_FUENTE,
                           limite_horizontal_kN=th[1] if th else None),
    ]
    return inicial,final



def obtener_referencia_inicial_desde_extremo(
    xyz, propiedades, referencia_final, hipotesis_final,
    *, puntos, ficha_inicial, longitudes_final,
    Cd=1.0, rho_kg_m3=1.225, densidad_hielo_kg_m3=900.,
):
    """Acoplamiento de referencia inicial/final sobre el MISMO esquema multivano.

    Se iguala la tensión máxima de la condición extrema -10 °C, después
    de distribuir y fijar las longitudes naturales de cada condición.
    Esta igualdad de referencia no es una ley constitutiva de creep.
    """
    from functools import lru_cache
    extremo=next(
        (h for h in hipotesis_final
         if h.temperatura_C == -10. and "reducido" in h.nombre.lower()),
        None,
    )
    if extremo is None:
        raise ValueError("No se dispone de la hipótesis final extrema a -10 °C")

    h_final=float(referencia_final["H_50_kN"])
    ev_final=_evaluador(
        xyz,propiedades,"Final",Cd,rho_kg_m3,
        longitudes_fijadas=longitudes_final,
    )
    _,tf,_,_,_=ev_final.evaluar_estado_con_hielo(
        h_final,extremo.temperatura_C,extremo.viento_kmh/3.6,
        extremo.hielo_mm,densidad_hielo_kg_m3,
    )
    objetivo=max(map(float,tf))
    @lru_cache(maxsize=96)
    def evaluar(h):
        longs,continuidad=_longitudes_de_tendido_continuo(
            puntos,xyz,ficha_inicial,float(h),Cd=Cd,rho_kg_m3=rho_kg_m3,
        )
        ev=_evaluador(xyz,propiedades,"Inicial",Cd,rho_kg_m3,
                      longitudes_fijadas=longs)
        _,tensiones,_,residuales,_=ev.evaluar_estado_con_hielo(
            float(h),extremo.temperatura_C,extremo.viento_kmh/3.6,
            extremo.hielo_mm,densidad_hielo_kg_m3,
        )
        return (max(map(float,tensiones))-objetivo,
                longs,continuidad,max(map(float,tensiones)),
                max(abs(float(x)) for x in residuales))

    # Buscar una raíz cerca de la referencia final sin asumir monotonicidad
    # global ni permitir un estado que supere la resistencia a rotura.
    semilla=float(referencia_final["H_50_kN"])
    minimo=max(0.05,semilla*0.60)
    maximo=min(propiedades.ruptura_kN*0.95,semilla*1.55)
    muestras=np.unique(np.r_[
        np.linspace(minimo,maximo,13),semilla,
    ])
    valores=[evaluar(float(h))[0] for h in muestras]
    intervalos=[]
    for i in range(len(muestras)-1):
        if valores[i]*valores[i+1]<=0.:
            intervalos.append((float(muestras[i]),float(muestras[i+1])))
    if not intervalos:
        raise ValueError(
            "El acoplamiento inicial/final multivano no tiene raíz "
            "identificada en el intervalo físico explorado; "
            "no se sustituye por el ajuste de vanos fijos."
        )
    a,b=min(intervalos,key=lambda x:abs((x[0]+x[1])/2-semilla))
    h_inicial=float(a if a==b else brentq(
        lambda h:evaluar(float(h))[0],a,b,xtol=1e-8,rtol=1e-10,
    ))
    error,longitudes,continuidad,tension,residuo=evaluar(h_inicial)
    if abs(error)>max(1e-5,objetivo*1e-6):
        raise ValueError("Acoplamiento de tensiones extremas fuera de tolerancia")
    if continuidad>1e-4 or residuo>1e-7:
        raise ValueError("La referencia inicial incumple equilibrio/compatibilidad")
    return {
        "condicion":"Inicial",
        "H_50_kN":h_inicial,
        "parametro_P_m":h_inicial/propiedades.peso_kN_m,
        "relacion_critica":tension/extremo.limite_tension_kN,
        "hipotesis_gobernante":extremo.nombre,
        "temperatura_gobernante_C":extremo.temperatura_C,
        "viento_gobernante_kmh":extremo.viento_kmh,
        "hielo_gobernante_mm":extremo.hielo_mm,
        "tension_maxima_gobernante_kN":tension,
        "limite_gobernante_kN":extremo.limite_tension_kN,
        "residuo_maximo_gobernante_m":abs(error),
        "cota_busqueda_activa":False,
        "metodo":"Acoplamiento de tensión extrema sobre multivano fijado; NO creep",
    },longitudes,continuidad


def _longitudes_de_tendido_continuo(puntos, xyz, ficha, H_50_kN,
                                     *, Cd, rho_kg_m3):
    """Etapa 1: continuidad ideal a 50 C sin viento, antes de fijar."""
    from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural
    from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
    if len(xyz) == 2:
        cable=resolver_catenaria(xyz[0],xyz[1],
                                [0.,0.,-float(ficha["peso_kN_m"])],float(H_50_kN))
        return [longitud_natural(cable,float(ficha["EA_kN"]))],0.
    from Analisis_mecanico_conductores.tension_tendido.comparar_multivano_deslizante_cfe import (
        construir_red_deslizante_de_puntos,
    )
    from Analisis_mecanico_conductores.tension_tendido.resolver_seccion_deslizante_ideal import (
        resolver_seccion_deslizante,
    )
    # La geometría ya fue validada por _geometria. Se crea una representación
    # equivalente sin inventar un desnivel: z_amarre permanece idéntico.
    geom=puntos[["Punto","X","Y"]].copy()
    geom["Altitud"]=xyz[:,2]-10.
    geom["Altura_Amarre_m"]=10.
    red=construir_red_deslizante_de_puntos(geom,str(ficha["nombre"]).upper())
    nombre=str(ficha["nombre"]).upper()
    materiales={nombre:{
        "peso_kN_m":float(ficha["peso_kN_m"]),
        "diametro_m":float(ficha["diametro_m"]),
        "EA_kN":float(ficha["EA_kN"]),
        "alpha_por_C":float(ficha["alpha_por_C"]),
        "H_tendido_kN":float(H_50_kN),
        "temperatura_tendido_C":50.,
        "fuente":str(ficha["fuente"]),
    }}
    res=resolver_seccion_deslizante(
        red,materiales=materiales,circuito="C1",seccion="S1",
        temperatura_C=50.,viento_ms=0.,azimut_deg=90.,
        Cd=float(Cd),rho_kg_m3=float(rho_kg_m3),
    )
    orden=[str(puntos.iloc[i]["Punto"])+" → "+str(puntos.iloc[i+1]["Punto"])
           for i in range(len(puntos)-1)]
    longitudes=[float(res.longitudes_naturales_referencia_m[k]) for k in orden]
    if abs(sum(longitudes)-res.longitud_natural_total_m)>1e-7:
        raise ValueError("El tendido continuo no conserva longitud total")
    return longitudes,float(res.residual_max_kN)


def _ajustar_referencia_final_multivano(puntos,xyz,ficha,propiedades,
                                        hipotesis,referencia,*,Cd,rho_kg_m3):
    """Reoptimiza H50 sobre tendido continuo y vanos fijados, no vanos aislados.

    El valor anterior sirve solo de semilla. Busca una raiz de utilizacion
    total igual a 1 en el borde superior de un intervalo factible.
    """
    from functools import lru_cache
    @lru_cache(maxsize=192)
    def evaluar(H):
        longitudes,continuidad=_longitudes_de_tendido_continuo(
            puntos,xyz,ficha,float(H),Cd=Cd,rho_kg_m3=rho_kg_m3)
        ev=_evaluador(xyz,propiedades,"Final",Cd,rho_kg_m3,
                      longitudes_fijadas=longitudes)
        detalles=[]
        for caso in hipotesis:
            hs,ts,_,residuales,_=ev.evaluar_estado_con_hielo(
                float(H),caso.temperatura_C,caso.viento_kmh/3.6,
                caso.hielo_mm,900.)
            uso_t=max(map(float,ts))/caso.limite_tension_kN
            uso_h=(max(map(float,hs))/caso.limite_horizontal_kN
                   if caso.limite_horizontal_kN is not None else 0.)
            detalles.append((max(uso_t,uso_h),caso,max(map(float,ts)),
                             max(abs(float(r)) for r in residuales)))
        ratio,caso,tension,residual=max(detalles,key=lambda item:item[0])
        return ratio,longitudes,continuidad,caso,tension,residual

    semilla=float(referencia["H_50_kN"])
    u0=evaluar(semilla)[0]
    # Recorrer el intervalo superior desde una semilla cercana; la
    # utilizacion puede tener forma de U, por lo que no se presume
    # monotonia desde H=0.
    if u0>1.:
        alto=semilla
        bajo=None
        for paso in range(1,91):
            candidato=semilla*(0.97**paso)
            if candidato<=0.01: break
            if evaluar(candidato)[0]<=1.:
                bajo=candidato
                break
            alto=candidato
        if bajo is None:
            raise ValueError(
                "No se encontro tension factible para tendido continuo "
                "seguido de fijacion; revisar geometria y restricciones."
            )
        H=float(brentq(lambda h:evaluar(float(h))[0]-1.,
                        bajo,alto,xtol=1e-7,rtol=1e-9))
    else:
        H=semilla
        # La referencia anterior no necesariamente es el borde superior
        # factible despues de la redistribucion del material.
        for paso in range(1,61):
            candidato=semilla*(1.02**paso)
            if candidato>=propiedades.ruptura_kN: break
            if evaluar(candidato)[0]>1.:
                H=float(brentq(lambda h:evaluar(float(h))[0]-1.,
                              H,candidato,xtol=1e-7,rtol=1e-9))
                break
            H=candidato
    ratio,longitudes,continuidad,caso,tension,residual=evaluar(H)
    if ratio>1.+1e-6:
        raise ValueError("Tendido continuo: la referencia optimizada incumple")
    nueva=dict(referencia)
    nueva.update({
        "H_50_kN":H,
        "parametro_P_m":H/propiedades.peso_kN_m,
        "relacion_critica":ratio,
        "hipotesis_gobernante":caso.nombre,
        "temperatura_gobernante_C":caso.temperatura_C,
        "viento_gobernante_kmh":caso.viento_kmh,
        "hielo_gobernante_mm":caso.hielo_mm,
        "tension_maxima_gobernante_kN":tension,
        "limite_gobernante_kN":caso.limite_tension_kN,
        "residuo_maximo_gobernante_m":residual,
        "metodo":"Tendido continuo, fijacion por vano y limites climaticos",
    })
    return nueva,longitudes,continuidad


def ejecutar_corridas_cfe_por_vano(
    puntos, ficha_inicial, ficha_final, *, viento_max_kmh,
    viento_reducido_kmh, hielo_mm, temperaturas_C,
    Cd=1.0, rho_kg_m3=1.225, incluir_ensayo_viento_16C=False,
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
        nombre_conductor=ficha_inicial.get("nombre"),
    )
    xyz,luces=_geometria(puntos)
    # Claro regla informativo: equivalente convencional de una sección
    # en regulación con deslizamiento ideal y vanos aproximadamente nivelados.
    # El motor actual mantiene amarres fijos; NO emplear este claro como
    # condición de contorno ni confundirlo con el claro de diseño ENEE.
    claro_regla_m=vano_regulador(luces)
    desnivel_max_m=max(abs(float(xyz[i+1,2]-xyz[i,2])) for i in range(len(luces)))
    referencia_final=calcular_parametro_cfe_desde_limites(
        xyz,propiedades,fin,condicion="Final",Cd=Cd,rho_kg_m3=rho_kg_m3,
    )
    referencia_final, longitudes_final, residual_final = _ajustar_referencia_final_multivano(
        puntos,xyz,ficha_final,propiedades,fin,referencia_final,
        Cd=Cd,rho_kg_m3=rho_kg_m3,
    )
    referencia_inicial, longitudes_inicial, residual_inicial = obtener_referencia_inicial_desde_extremo(
        xyz,propiedades,referencia_final,fin,
        puntos=puntos,ficha_inicial=ficha_inicial,
        longitudes_final=longitudes_final,
        Cd=Cd,rho_kg_m3=rho_kg_m3,
    )
    # Verificar además el límite propio del estado inicial a 0 °C:
    # el acoplamiento con el extremo final no da permiso para superarlo.
    evaluador_inicial = _evaluador(
        xyz,propiedades,"Inicial",Cd,rho_kg_m3,
        longitudes_fijadas=longitudes_inicial,
    )
    for caso in ini:
        hs, ts, _, _, _ = evaluador_inicial.evaluar_estado_con_hielo(
            referencia_inicial["H_50_kN"],caso.temperatura_C,
            caso.viento_kmh/3.6,caso.hielo_mm,900.,
        )
        if (max(ts) > caso.limite_tension_kN*(1+1e-6) or
            (caso.limite_horizontal_kN is not None and
             max(hs) > caso.limite_horizontal_kN*(1+1e-6))):
            raise ValueError(
                "La condición inicial acoplada excede el límite de "
                f"{caso.nombre}. No se puede emitir diseño factible."
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
    # Estado opcional que se muestra SOLO en la interfaz de verificación.
    # Preserva la salida pública existente del calculador y sus pruebas.
    if incluir_ensayo_viento_16C:
        estados_extra.append(
            ("Exploratorio 16°C viento máximo",16.,float(viento_max_kmh),0.),
        )
    # Etapa 1: resolver la sección continua y obtener longitudes descargadas
    # para cada vano. Etapa 2: fijarlas antes de los cambios climáticos.
    # Las referencias inicial/final CFE son condiciones constitutivas
    # distintas; no se atribuye la diferencia a creep no caracterizado.
    longitudes_fijadas={}
    residuales_continuidad={}
    longitudes_fijadas["Final"]=longitudes_final
    residuales_continuidad["Final"]=residual_final
    longitudes_fijadas["Inicial"]=longitudes_inicial
    residuales_continuidad["Inicial"]=residual_inicial
    # Los limites se verifican de NUEVO tras redistribuir material:
    # la factibilidad del modelo de amarres fijos anterior no se hereda.
    for condicion,casos,referencia in (
        ("Inicial",ini,referencia_inicial),
        ("Final",fin,referencia_final),
    ):
        evaluador=_evaluador(
            xyz,propiedades,condicion,Cd,rho_kg_m3,
            longitudes_fijadas=longitudes_fijadas[condicion],
        )
        for caso in casos:
            hs,ts,_,residuales,_=evaluador.evaluar_estado_con_hielo(
                referencia["H_50_kN"],caso.temperatura_C,
                caso.viento_kmh/3.6,caso.hielo_mm,900.,
            )
            uso_t=max(ts)/caso.limite_tension_kN
            uso_h=(max(hs)/caso.limite_horizontal_kN
                   if caso.limite_horizontal_kN is not None else 0.)
            if max(uso_t,uso_h)>1.+1e-6:
                raise ValueError(
                    "El tendido continuo seguido de fijacion incumple "
                    f"{caso.nombre}: utilizacion={max(uso_t,uso_h):.4f}. "
                    "La referencia optimizada para amarres fijos no es "
                    "factible tras redistribucion de longitudes."
                )
            if max(abs(float(r)) for r in residuales)>1e-7:
                raise ValueError("Compatibilidad fuera de tolerancia tras fijacion")
    tabla=calcular_tablas_inicial_final(
        puntos,propiedades,
        EstadoReferenciaCFE(referencia_inicial["parametro_P_m"],CFE_FUENTE),
        EstadoReferenciaCFE(referencia_final["parametro_P_m"],CFE_FUENTE),
        temperaturas_C,estados_climaticos=estados_extra,
        Cd=Cd,rho_kg_m3=rho_kg_m3,
        longitudes_fijadas=longitudes_fijadas,
    )
    resumen=pd.DataFrame([
        {"Condición":"Inicial — vinculada por tensión extrema final",
         "Hipótesis aplicadas":"; ".join(h.nombre for h in ini),**referencia_inicial},
        {"Condición":"Final — referencia climática (sin creep validado)",
         "Hipótesis aplicadas":"; ".join(h.nombre for h in fin),**referencia_final},
    ])
    resumen["Claro regla convencional orientativo (m)"]=claro_regla_m
    resumen["Número de vanos"]=len(luces)
    # Diagnóstico, NO ley de creep: diferencias geométricas/constitutivas
    # implícitas entre referencias calculadas por separado.
    deformaciones_aparentes=[
        (lf/li-1.) for li,lf in zip(longitudes_inicial,longitudes_final)
    ]
    resumen["Deformación aparente inicial→final máxima |ΔL0/L0|"]=[
        float(max(abs(v) for v in deformaciones_aparentes))]*2
    resumen["Modelo de deformación permanente"]=[
        "NO suministrado: referencias acopladas por tensión, no por creep"
    ]*2
    resumen["Longitud natural total fijada (m)"]=[
        sum(longitudes_fijadas["Inicial"]),sum(longitudes_fijadas["Final"])]
    resumen["Residual continuidad tendido (kN)"]=[
        residuales_continuidad["Inicial"],residuales_continuidad["Final"]]
    resumen["Desnivel máximo entre apoyos (m)"]=desnivel_max_m
    resumen["Advertencia"]=(
        "Tendido continuo de guias ideales a 50 C, seguido de longitudes "
        "individuales fijadas para cambios de estado. "
        "Claro regla: informativo. Sin creep validado."
    )
    return resumen,tabla
