"""Cálculo convencional de una sección de regulación multivano.

Referencia: L. M. Checa, Líneas de Transporte de Energía, 3ª ed.,
cap. 4, apartado 4.2, pp. impresas 245-247 (vano ideal de regulación).

El vano equivalente Checa sqrt(sum(a^3)/sum(a)) se informa SOLO como
referencia de la aproximación para vanos aproximadamente nivelados.

El cálculo de tensiones NO emplea ese vano para reemplazar la geometría:
aplica compatibilidad exacta de la suma de longitudes naturales mediante
catenarias de cada vano, conservando una H común convencional. La
hipótesis mecánica explícita es una sección regulada con redistribución
de cable ideal y tensiones horizontales uniformes, entre remates.

Viento: carga aerodinámica transversal máxima, perpendicular al eje
de cada vano (envolvente convencional). No representa un vector de viento
geográfico único si la traza gira. El Cd, rho, diámetro y velocidad
se usan para obtener w_v = 0.5*rho*Cd*d*V²/1000 kN/m.
No calcula cargas de viento reales sobre los postes.

No permite dictaminar seguridad estructural, libramientos, creep,
ni una sección con conductor fijado indeformablemente en cada suspensión.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado, vano_regulador
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    EvaluadorEstadosRegulacion,
    calcular_cargas_transversales_por_vano as _cargas,
)
from Analisis_mecanico_conductores.flechas.calcular_flecha_vertical_de_catenaria import (
    calcular_flecha_vertical_de_catenaria as _flecha,
)
from Analisis_mecanico_conductores.tension_tendido.construir_resultados_regulacion import (
    construir_tablas_de_hipotesis,
    construir_tabla_de_tendido,
)


@dataclass
class ResultadoRegulacion:
    H_tendido_kN: float
    vano_regulador_m: float
    longitud_tramo_m: float
    hipotesis: pd.DataFrame
    flechas: pd.DataFrame
    tabla_tendido: pd.DataFrame
    caso_gobernante: str
    relacion_maxima: float
    cota_busqueda_activa: bool
    modelo: str


def _geometria(puntos):
    if not isinstance(puntos,pd.DataFrame) or len(puntos)<2:
        raise ValueError("Se requieren dos o más postes ordenados")
    cols=("Punto","X","Y")
    if any(c not in puntos for c in cols):
        raise ValueError("Faltan identificadores o coordenadas X/Y")
    if puntos["Punto"].astype(str).duplicated().any():
        raise ValueError("Puntos duplicados")
    xy=puntos[["X","Y"]].to_numpy(dtype=float)
    if not np.isfinite(xy).all():
        raise ValueError("Coordenadas no finitas")
    # El cálculo convencional admite cota uniforme conocida y alturas
    # iguales. Si se declaran desniveles o faltan algunas cotas,
    # no los suplanta por geometría horizontal.
    if "Altitud" in puntos and puntos["Altitud"].notna().any():
        if puntos["Altitud"].isna().any():
            raise ValueError("Altitud parcial; completar cotas")
        alt=puntos["Altitud"].to_numpy(dtype=float)
        if max(alt)-min(alt)>1e-5:
            raise ValueError(
                "Esta regulación convencional requiere cotas de "
                "terreno iguales. Para desniveles usar cálculo 3D."
            )
    else:
        alt=np.zeros(len(puntos))
    if "Altura_Amarre_m" in puntos and puntos["Altura_Amarre_m"].notna().any():
        if puntos["Altura_Amarre_m"].isna().any():
            raise ValueError("Altura de amarre parcial")
        amarre=puntos["Altura_Amarre_m"].to_numpy(dtype=float)
        if (amarre<=0).any() or max(amarre)-min(amarre)>1e-5:
            raise ValueError(
                "La regulación convencional requiere amarres de "
                "igual altura. Para alturas distintas usar cálculo 3D."
            )
    else:
        amarre=np.zeros(len(puntos))
    z=alt+amarre
    xyz=np.column_stack((xy,z))
    luces=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    if (luces<=0).any():
        raise ValueError("Vano de longitud cero")
    return xyz,luces


def resolver_seccion_regulacion(
    puntos, *, hipotesis, temperaturas_tabla_C,
    peso_kN_m, diametro_m, EA_kN, alpha_por_C, fuente_material,
    temperatura_tendido_C, H_min_kN, H_max_kN,
    Cd=1.2, rho_kg_m3=1.225,
):
    """Encuentra H inicial por compatibilidad y límites en toda la sección.

    Hipótesis: columnas Hipotesis, Temperatura_C, Viento_ms,
    T_limite_kN, Fuente_limite, Criterio_diseno.
    No se requiere conocer un herraje intermedio para el método
    CONVENCIONAL de regulación; NO es cálculo de fuerzas de ese herraje.
    """
    xyz,luces=_geometria(puntos)
    if not fuente_material or not str(fuente_material).strip():
        raise ValueError("Falta fuente mecánica del conductor")
    if not isinstance(hipotesis,pd.DataFrame) or hipotesis.empty:
        raise ValueError("Sin hipótesis documentadas")
    campos=("Hipotesis","Temperatura_C","Viento_ms",
            "T_limite_kN","Fuente_limite","Criterio_diseno")
    if any(c not in hipotesis for c in campos):
        raise ValueError("Faltan hipótesis, límites o fuentes documentales")
    if hipotesis[list(campos)].isna().any().any():
        raise ValueError("Hipótesis incompletas")
    if hipotesis["Hipotesis"].astype(str).str.strip().duplicated().any():
        raise ValueError("Hipótesis duplicadas")
    peso=finito(peso_kN_m,"peso",0,True)
    d=finito(diametro_m,"diámetro",0,True)
    ea=finito(EA_kN,"EA",0,True)
    alpha=finito(alpha_por_C,"alpha")
    t0=finito(temperatura_tendido_C,"temperatura de tendido")
    hmin=finito(H_min_kN,"H mínimo",0,True)
    hmax=finito(H_max_kN,"H máximo",hmin,True)
    temps=[finito(t,"temperatura tabla") for t in temperaturas_tabla_C]
    if not temps:
        raise ValueError("Sin temperaturas de tabla")
    for _,h in hipotesis.iterrows():
        if not str(h["Fuente_limite"]).strip() or not str(h["Criterio_diseno"]).strip():
            raise ValueError("Falta fuente o criterio de un límite")
        finito(h["T_limite_kN"],"límite de tensión",0,True)
    evaluador=EvaluadorEstadosRegulacion(
        xyz,peso,d,ea,alpha,t0,Cd,rho_kg_m3
    )
    estado=evaluador.evaluar_estado

    def max_relacion(H_referencia_kN):
        """Mayor cociente tensión real/límite de todas las hipótesis."""
        return max(
            max(estado(
                float(H_referencia_kN),
                float(caso["Temperatura_C"]),float(caso["Viento_ms"])
            )[1])/float(caso["T_limite_kN"])
            for _,caso in hipotesis.iterrows()
        )

    hs=np.linspace(hmin,hmax,9)
    muestra=np.array([max_relacion(float(h)) for h in hs])
    if not np.isfinite(muestra).all():
        raise ValueError("Solución no finita")
    if (np.diff(muestra)<-1e-5).any():
        raise ValueError("Relación tensión/tendido no monótona en la búsqueda")
    if muestra[0]>1+1e-5:
        raise ValueError("No hay estado factible dentro del intervalo de H")
    activo=bool(muestra[-1]<=1)
    hopt=float(hmax if activo else brentq(
        lambda h:max_relacion(float(h))-1,hmin,hmax,
        xtol=1e-7,rtol=1e-9
    ))
    tabla_hipotesis,tabla_flechas=construir_tablas_de_hipotesis(
        puntos,xyz,luces,hipotesis,hopt,estado
    )
    peor=tabla_hipotesis.loc[tabla_hipotesis["Relación T/límite"].idxmax()]
    if peor["Relación T/límite"]>1+1e-5:
        raise ValueError("Las hipótesis de tensión no se satisfacen")
    tabla_tendido=construir_tabla_de_tendido(puntos,xyz,temps,hopt,estado)
    return ResultadoRegulacion(
        H_tendido_kN=hopt,
        vano_regulador_m=vano_regulador(luces),
        longitud_tramo_m=float(sum(luces)),
        hipotesis=tabla_hipotesis,
        flechas=tabla_flechas,
        tabla_tendido=tabla_tendido,
        caso_gobernante=peor["Hipótesis"],
        relacion_maxima=float(peor["Relación T/límite"]),
        cota_busqueda_activa=activo,
        modelo="Sección convencional de regulación: H común y redistribución ideal; cargas de viento transversales máximas por vano",
    )
