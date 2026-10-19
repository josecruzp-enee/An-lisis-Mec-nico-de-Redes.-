"""Contratos independientes de Streamlit. Unidades SI con fuerzas en kN.

Las fuentes son identificadores aportados por el responsable; el programa no
certifica que un texto de procedencia corresponda a una norma vigente.
"""
from __future__ import annotations
from dataclasses import dataclass
from .validacion_mecanica import finito, vector3


@dataclass(frozen=True)
class Conductor:
    """Propiedades específicas del cable; EA no se infiere de otro ACSR."""
    nombre: str
    peso_kN_m: float
    diametro_m: float
    H_tendido_kN: float
    temperatura_tendido_C: float
    fuente: str
    EA_kN: float | None = None
    alpha_por_C: float | None = None
    RTS_kN: float | None = None
    tension_admisible_kN: float | None = None
    fuente_admisible: str = ''

    def __post_init__(self):
        for nombre in ('peso_kN_m','diametro_m','H_tendido_kN'):
            finito(getattr(self, nombre), nombre, 0, True)
        finito(self.temperatura_tendido_C, 'temperatura de tendido')
        for nombre in ('EA_kN','RTS_kN','tension_admisible_kN'):
            if getattr(self,nombre) is not None:
                finito(getattr(self,nombre), nombre, 0, True)
        if self.alpha_por_C is not None:
            finito(self.alpha_por_C, 'alpha', 0)
        if not self.fuente.strip():
            raise ValueError('Identifique la fuente de los datos del conductor')


@dataclass(frozen=True)
class EstadoClimatico:
    """Condición física sin factores normativos implícitos; viento HACIA azimut."""
    nombre: str
    temperatura_C: float
    viento_ms: float
    azimut_deg: float
    fuente: str
    Cd: float = 1.2
    rho_kg_m3: float = 1.225
    hielo_m: float = 0.0
    densidad_hielo_kg_m3: float | None = None
    deformacion_permanente: float = 0.0

    def __post_init__(self):
        for nombre in ('viento_ms','hielo_m','deformacion_permanente'):
            finito(getattr(self,nombre), nombre, 0)
        for nombre in ('Cd','rho_kg_m3'):
            finito(getattr(self,nombre), nombre, 0, True)
        finito(self.temperatura_C, 'temperatura')
        finito(self.azimut_deg, 'azimut')
        if self.hielo_m:
            if self.densidad_hielo_kg_m3 is None:
                raise ValueError('El hielo requiere densidad explícita')
            finito(self.densidad_hielo_kg_m3, 'densidad hielo', 0, True)
        if not self.nombre.strip() or not self.fuente.strip():
            raise ValueError('Estado climático sin nombre o fuente')


@dataclass(frozen=True)
class Nodo:
    """Base UTM y cota de terreno en metros; nunca se inventa la altitud."""
    nombre: str
    base_m: tuple[float, float, float]

    def __post_init__(self):
        vector3(self.base_m, 'base del nodo')
        if not self.nombre.strip():
            raise ValueError('Nodo sin identificador')


@dataclass(frozen=True)
class Vano:
    """Un cable o grupo co-localizado; offsets de amarre respecto a cada base."""
    nombre: str
    inicio: str
    fin: str
    amarre_inicio_m: tuple[float,float,float]
    amarre_fin_m: tuple[float,float,float]
    conductor: str
    cantidad: int = 1

    def __post_init__(self):
        vector3(self.amarre_inicio_m, 'amarre inicial')
        vector3(self.amarre_fin_m, 'amarre final')
        if self.amarre_inicio_m[2] <= 0 or self.amarre_fin_m[2] <= 0:
            raise ValueError('Los amarres deben quedar sobre terreno')
        if isinstance(self.cantidad, bool) or not isinstance(self.cantidad, int) or self.cantidad < 1:
            raise ValueError('cantidad de conductores debe ser entero positivo')
        if self.inicio == self.fin or not self.nombre.strip():
            raise ValueError('Vano inválido')


@dataclass(frozen=True)
class Combinacion:
    """Factores explícitos sobre acciones ya resueltas; no altera el estado del cable."""
    nombre: str
    estado: str
    fuente: str
    metodo: str = 'servicio'
    factor_conductor: float = 1.0
    factor_adicional: float = 1.0

    def __post_init__(self):
        finito(self.factor_conductor, 'factor conductor', 0)
        finito(self.factor_adicional, 'factor adicional', 0)
        if self.metodo not in ('servicio','resistencia','especial'):
            raise ValueError('Método de combinación desconocido')
        if not self.nombre.strip() or not self.fuente.strip():
            raise ValueError('Combinación sin nombre/fuente')
