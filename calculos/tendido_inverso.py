"""Diseño inverso del tendido de UN vano fijo, con BVP no lineal 3D.

Basado en el procedimiento de hipótesis climáticas, ecuación de estado y
tabla de tendido descritos en:
  - Luis María Checa, Líneas de Transporte de Energía, 3ª ed., cap. 4.
  - Cálculo mecánica de conductores aéreos, páginas 2-6 del resumen ISEP.

La ecuación cúbica y el vano crítico del resumen son APROXIMACIONES para
la catenaria parabólica; NO sustituyen este BVP en desniveles y viento.

Objetivo: elegir la mayor tensión horizontal H de referencia al tendido,
dentro de un intervalo de búsqueda SUMINISTRADO, que satisfaga las
tensiones máximas de TODAS las hipótesis explícitamente declaradas.
Maximizar H es un objetivo de diseño elegido (reduce flecha); NO
equivale automáticamente a un óptimo global multivariable.

Restricciones de aplicación:
- un único vano con extremos fijos;
- parámetros mecánicos y límites con fuente; ley EA lineal;
- hipótesis especificadas; no se adivinan estados climáticos normativos;
- H->Tmax debe comprobarse monótona en el intervalo; si no, SE RECHAZA;
- sin topografía, creep histórico, hielo ni cargas extraordinarias.
No hay certificación estructural ni continuidad entre suspensiones.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math

from scipy.optimize import brentq

from .cable_no_lineal import resolver_cable_no_lineal
from .barrido_no_lineal_3d import _extremo_minimo
from .validacion_mecanica import finito, vector3


@dataclass(frozen=True)
class HipotesisTendido:
    nombre: str
    temperatura_C: float
    viento_ms: float
    azimut_viento_deg: float
    tension_limite_kN: float
    fuente_limite: str
    criterio_diseno: str

    def __post_init__(self):
        if not self.nombre.strip() or not self.fuente_limite.strip() or not self.criterio_diseno.strip():
            raise ValueError("Cada hipótesis requiere nombre, fuente y criterio de diseño")
        finito(self.temperatura_C, "temperatura hipótesis")
        finito(self.viento_ms, "velocidad viento", 0)
        finito(self.azimut_viento_deg, "azimut")
        finito(self.tension_limite_kN, "límite de tensión", 0, True)


@dataclass
class ResultadoTendido:
    H_tendido_kN: float
    hipotesis: list[dict]
    tabla_tendido: list[dict]
    caso_gobernante: str
    razon_maxima: float
    cota_superior_activa: bool
    evaluaciones_bvp: int
    estado: str


def dimensionar_tension_tendido(
    inicio, fin, *, hipotesis, temperaturas_tabla_C,
    temperatura_tendido_C, peso_kN_m, diametro_m, EA_kN,
    alpha_por_C, fuente_material,
    H_min_kN, H_max_kN,
    Cd=1.2, rho_kg_m3=1.225,
    muestras_monotonia=9, tolerancia_ratio=1e-4,
    tolerancia_bvp=1e-5,
):
    """Determina tensión H de tendido dentro de intervalo explícito.

    Nunca usa porcentajes implícitos de carga de ruptura.
    Los resultados se devuelven por estado y tabla de tendido SIN viento
    para cada temperatura solicitada, con tensión y fuerzas en extremos.
    """
    a=vector3(inicio, "amarre inicial")
    b=vector3(fin, "amarre final")
    if float(((b-a)**2).sum()) <= 0:
        raise ValueError("Vano de longitud nula")
    if not fuente_material or not str(fuente_material).strip():
        raise ValueError("Propiedades mecánicas sin fuente técnica")
    if not hipotesis:
        raise ValueError("Debe definirse al menos una hipótesis")
    hip=[
        h if isinstance(h, HipotesisTendido) else HipotesisTendido(**h)
        for h in hipotesis
    ]
    if len({h.nombre for h in hip}) != len(hip):
        raise ValueError("Nombres de hipótesis duplicados")
    temps=[finito(x, "temperatura tabla") for x in temperaturas_tabla_C]
    if not temps:
        raise ValueError("Sin temperaturas para tabla de tendido")
    t0=finito(temperatura_tendido_C, "temperatura tendido")
    Hmin=finito(H_min_kN, "H mínimo", 0, True)
    Hmax=finito(H_max_kN, "H máximo", Hmin, True)
    finito(peso_kN_m, "peso", 0, True)
    finito(diametro_m, "diámetro", 0, True)
    finito(EA_kN, "EA", 0, True)
    finito(alpha_por_C, "dilatación")
    finito(Cd, "Cd", 0, True)
    finito(rho_kg_m3, "densidad del aire", 0, True)
    tol=finito(tolerancia_ratio, "tolerancia ratio", 0, True)
    if isinstance(muestras_monotonia,bool) or not isinstance(muestras_monotonia,int) or muestras_monotonia<5:
        raise ValueError("Se requieren al menos 5 muestras de monotonía")

    @lru_cache(maxsize=None)
    def evaluar(H, t, v, az):
        return resolver_cable_no_lineal(
            a,b,peso_kN_m=peso_kN_m,diametro_m=diametro_m,
            EA_kN=EA_kN,alpha_por_C=alpha_por_C,
            H_tendido_kN=float(H),temperatura_tendido_C=t0,
            temperatura_estado_C=float(t),
            velocidad_viento_ms=float(v),azimut_viento_deg=float(az),
            rho_kg_m3=rho_kg_m3,Cd=Cd,tolerancia=tolerancia_bvp,
        )

    def ratios(H):
        return [
            evaluar(H,h.temperatura_C,h.viento_ms,h.azimut_viento_deg)
            .tension_maxima_kN/h.tension_limite_kN for h in hip
        ]

    # No se presume monotonicidad del modelo: comprobarla con muestras
    # y negarse a certificar si aparecen ramas no monótonas.
    import numpy as np
    hs=np.linspace(Hmin,Hmax,muestras_monotonia)
    ratios_muestra=np.asarray([ratios(float(H)) for H in hs])
    if not np.isfinite(ratios_muestra).all():
        raise ValueError("Relaciones de tensión no finitas")
    if (np.diff(ratios_muestra,axis=0)<-max(tol,1e-5)).any():
        raise ValueError(
            "Tensión máxima no monótona en el intervalo; "
            "subdividir el dominio y revisar hipótesis"
        )
    maximos=ratios_muestra.max(axis=1)
    if maximos[0] > 1+tol:
        raise ValueError(
            "No existe tensión de tendido factible desde el límite inferior "
            f"H={Hmin:g} kN para las hipótesis suministradas"
        )
    if maximos[-1]<=1:
        Hopt=float(Hmax)
        cota_activa=True
    else:
        # Envelope contínuo de hipótesis: max(T_i(H)/lim_i)-1.
        # Al ser creciente en cada rama comprobada, su primera
        # intersección determina el máximo H factible del intervalo.
        Hopt=float(brentq(lambda H:max(ratios(float(H)))-1,
                          Hmin,Hmax,xtol=1e-7,rtol=1e-9,maxiter=120))
        cota_activa=False

    detalle=[]
    for h in hip:
        cable=evaluar(Hopt,h.temperatura_C,h.viento_ms,h.azimut_viento_deg)
        razon=cable.tension_maxima_kN/h.tension_limite_kN
        detalle.append({
            "Hipótesis":h.nombre,
            "Temperatura (°C)":h.temperatura_C,
            "Viento (m/s)":h.viento_ms,
            "Azimut viento (°)":h.azimut_viento_deg,
            "T máxima (kN)":cable.tension_maxima_kN,
            "Límite de diseño (kN)":h.tension_limite_kN,
            "Relación T/límite":razon,
            "Fuente límite":h.fuente_limite,
            "Criterio":h.criterio_diseno,
            "Estado":("EXCEDE LÍMITE" if razon>1+tol
                      else "DENTRO DEL LÍMITE DE ESTA HIPÓTESIS"),
        })
    peor=max(detalle,key=lambda d:d["Relación T/límite"])
    if peor["Relación T/límite"]>1+tol:
        raise ValueError("La tensión final no satisface las hipótesis")

    tabla=[]
    for temp in temps:
        cable=evaluar(Hopt,temp,0.,0.)
        # Flecha vertical de la curva BVP respecto a la cuerda,
        # no aproximación parabólica f=qL²/(8H).
        delta=b-a
        dx2=float(delta[:2]@delta[:2])
        if dx2<=0:
            raise ValueError("La tabla requiere luz horizontal no nula")
        def elevacion_relativa(u):
            p=cable.puntos(u)
            fraccion=float((p[:2]-a[:2])@delta[:2]/dx2)
            return float(p[2]-(a[2]+fraccion*delta[2]))
        min_altitud,_=_extremo_minimo(cable,elevacion_relativa)
        flecha=max(0.,-float(min_altitud))
        tabla.append({
            "Temperatura (°C)":temp,
            "Flecha vertical sobre cuerda (m)":flecha,
            "H de referencia (kN)":Hopt,
            "T extremo A (kN)":float(np.linalg.norm(cable.fuerza_a)),
            "T extremo B (kN)":float(np.linalg.norm(cable.fuerza_b)),
            "T máxima (kN)":cable.tension_maxima_kN,
            "Longitud deformada (m)":cable.longitud_deformada_m,
            "Residual equilibrio (kN)":cable.residual_equilibrio_kN,
            "Estado":"TABLA SIN VIENTO; NO CERTIFICACIÓN",
        })
    return ResultadoTendido(
        H_tendido_kN=Hopt,hipotesis=detalle,tabla_tendido=tabla,
        caso_gobernante=peor["Hipótesis"],
        razon_maxima=float(peor["Relación T/límite"]),
        cota_superior_activa=cota_activa,
        evaluaciones_bvp=evaluar.cache_info().misses,
        estado=("LÍMITE DE BÚSQUEDA ACTIVO; ESTADOS VERIFICADOS"
                if cota_activa else
                "HIPÓTESIS DE TENSIÓN SATISFECHAS; RESTO DE DISEÑO PENDIENTE"),
    )
