"""Topología explícita de red mecánica, sin inferir anclajes por ángulo.

Un nodo identifica un APOYO físico. Cada arista representa una SECCIÓN DE
CONDUCTOR conectada entre amarres del apoyo. Los tipos de conexión son
propiedades de cada extremo, no del poste completo: un apoyo puede retener un
circuito y suspender otro. No se supone continuidad donde no esté declarada.

Esta capa no calcula fuerzas: valida una red para el solucionador global.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import math

import numpy as np

TIPOS_CONEXION = frozenset({"ANCLAJE", "SUSPENSION", "FIJA", "DESLIZANTE"})


def _xyz(valor, nombre):
    try:
        resultado = np.asarray(valor, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{nombre}: coordenadas no numéricas") from exc
    if resultado.shape != (3,) or not np.isfinite(resultado).all():
        raise ValueError(f"{nombre}: se necesitan tres coordenadas XYZ finitas")
    return tuple(float(x) for x in resultado)


@dataclass(frozen=True)
class NodoRed:
    nombre: str
    base_m: tuple[float, float, float]
    modelo_apoyo: str
    # Modelo mecánico explícito, no resistencia catalogada.
    # FIJO: apoyo inmóvil; MOVIL: debe aportarse ley fuerza-desplazamiento.
    fijacion: str = "FIJO"

    def __post_init__(self):
        if not str(self.nombre).strip():
            raise ValueError("Identificador de apoyo vacío")
        object.__setattr__(self, "base_m", _xyz(self.base_m, self.nombre))
        if self.fijacion not in ("FIJO", "MOVIL"):
            raise ValueError(f"{self.nombre}: fijación no reconocida")
        if not str(self.modelo_apoyo).strip():
            raise ValueError(f"{self.nombre}: modelo_apoyo vacío")


@dataclass(frozen=True)
class VanoRed:
    nombre: str
    origen: str
    destino: str
    circuito: str
    conductor: str
    amarre_origen_m: tuple[float, float, float]
    amarre_destino_m: tuple[float, float, float]
    conexion_origen: str
    conexion_destino: str
    # Sección física de cable continuo (igual identificador entre varios vanos).
    seccion_tendido: str

    def __post_init__(self):
        for nombre in ("nombre", "origen", "destino", "circuito",
                       "conductor", "seccion_tendido"):
            if not str(getattr(self,nombre)).strip():
                raise ValueError(f"Vano con {nombre} vacío")
        if self.origen == self.destino:
            raise ValueError(f"{self.nombre}: vano sobre el mismo apoyo")
        for k in ("amarre_origen_m", "amarre_destino_m"):
            objeto = _xyz(getattr(self,k), f"{self.nombre}/{k}")
            if objeto[2] <= 0:
                raise ValueError(f"{self.nombre}: altura de amarre no positiva")
            object.__setattr__(self,k,objeto)
        for k in ("conexion_origen","conexion_destino"):
            if getattr(self,k) not in TIPOS_CONEXION:
                raise ValueError(f"{self.nombre}: conexión {k} inválida")


@dataclass
class RedMecanica:
    apoyos: dict[str,NodoRed]
    vanos: dict[str,VanoRed]

    @classmethod
    def desde_registros(cls, apoyos, vanos):
        n = [a if isinstance(a,NodoRed) else NodoRed(**a) for a in apoyos]
        e = [v if isinstance(v,VanoRed) else VanoRed(**v) for v in vanos]
        if not n or not e:
            raise ValueError("La red necesita apoyos y vanos")
        if len({a.nombre for a in n}) != len(n):
            raise ValueError("Apoyos con nombres duplicados")
        if len({v.nombre for v in e}) != len(e):
            raise ValueError("Vanos con nombres duplicados")
        red=cls({a.nombre:a for a in n},{v.nombre:v for v in e})
        red.validar()
        return red

    def validar(self):
        incidencias=defaultdict(list)
        for vano in self.vanos.values():
            if vano.origen not in self.apoyos or vano.destino not in self.apoyos:
                raise ValueError(f"{vano.nombre}: apoyo inexistente")
            p=np.asarray(self.apoyos[vano.origen].base_m)+vano.amarre_origen_m
            q=np.asarray(self.apoyos[vano.destino].base_m)+vano.amarre_destino_m
            if np.linalg.norm(q-p)<1e-8:
                raise ValueError(f"{vano.nombre}: amarres coincidentes")
            incidencias[(vano.origen,vano.circuito,vano.seccion_tendido)].append(
                (vano.nombre,vano.conexion_origen,vano.conductor)
            )
            incidencias[(vano.destino,vano.circuito,vano.seccion_tendido)].append(
                (vano.nombre,vano.conexion_destino,vano.conductor)
            )
        for (apoyo,circuito,seccion),lista in incidencias.items():
            # Continuidad física interna: un apoyo de suspensión une DOS
            # tramos del MISMO cable y circuito. Aristas sueltas no implican
            # continuidad mecánica automáticamente.
            deslizantes=[x for x in lista if x[1] in ("SUSPENSION","DESLIZANTE")]
            ancladas=[x for x in lista if x[1] in ("ANCLAJE","FIJA")]
            if deslizantes:
                if len(deslizantes)!=2 or ancladas or len(lista)!=2:
                    raise ValueError(
                        f"{apoyo}/{circuito}/{seccion}: suspensión debe unir "
                        "exactamente dos vanos de la sección y circuito"
                    )
                if deslizantes[0][2]!=deslizantes[1][2]:
                    raise ValueError(f"{apoyo}: conductor discontinuo en suspensión")
            if len(lista)>2:
                raise ValueError(
                    f"{apoyo}/{circuito}/{seccion}: derivación mecánica no "
                    "definida; separar secciones o declarar dispositivo específico"
                )
        # Una sección de tendido sin dispositivos intermedios especiales es
        # una cadena conectada con exactamente dos anclajes en sus extremos.
        # Un ramal, ciclo o doble anclaje interior se modela por otras
        # secciones explícitas, nunca se oculta en un vano regulador.
        for clave,vlist in self._agrupar_secciones().items():
            vecinos=defaultdict(set)
            conexiones=defaultdict(list)
            for v in vlist:
                vecinos[v.origen].add(v.destino)
                vecinos[v.destino].add(v.origen)
                conexiones[v.origen].append(v.conexion_origen)
                conexiones[v.destino].append(v.conexion_destino)
            extremos=[n for n,tipos in conexiones.items() if len(tipos)==1]
            if len(extremos)!=2 or any(len(tipos)>2 for tipos in conexiones.values()):
                raise ValueError(
                    f"Sección {clave}: no es una cadena entre dos anclajes"
                )
            if any(conexiones[n][0] not in ("ANCLAJE","FIJA") for n in extremos):
                raise ValueError(
                    f"Sección {clave}: cada extremo debe estar anclado"
                )
            if any(
                any(t in ("ANCLAJE","FIJA") for t in conexiones[n])
                for n in conexiones if n not in extremos
            ):
                raise ValueError(
                    f"Sección {clave}: anclaje interno; divida la sección"
                )
            vistos=set()
            cola=deque([extremos[0]])
            while cola:
                actual=cola.popleft()
                if actual in vistos:
                    continue
                vistos.add(actual)
                cola.extend(vecinos[actual]-vistos)
            if len(vistos)!=len(conexiones):
                raise ValueError(
                    f"Sección {clave}: vanos desconectados"
                )

    def _agrupar_secciones(self):
        grupos=defaultdict(list)
        for v in self.vanos.values():
            grupos[(v.circuito,v.seccion_tendido)].append(v)
        return dict(grupos)

    def secciones(self):
        """Reducción topológica, NO fórmula de vano regulador."""
        salida=[]
        for (circuito,seccion), vanos in self._agrupar_secciones().items():
            nodos=set()
            longitud=0.
            for vano in vanos:
                nodos.update((vano.origen,vano.destino))
                p=np.array(self.apoyos[vano.origen].base_m)+vano.amarre_origen_m
                q=np.array(self.apoyos[vano.destino].base_m)+vano.amarre_destino_m
                longitud+=float(np.linalg.norm(q-p))
            salida.append({
                "Circuito":circuito,"Sección":seccion,
                "Vanos":len(vanos),"Apoyos":len(nodos),
                "Longitud cuerda 3D (m)":longitud,
                "Identificadores":tuple(v.nombre for v in vanos),
            })
        return salida

    def apoyos_conectados(self):
        enlaces=defaultdict(list)
        for v in self.vanos.values():
            enlaces[v.origen].append((v.destino,v.nombre,v.circuito))
            enlaces[v.destino].append((v.origen,v.nombre,v.circuito))
        return {p:tuple(enlaces[p]) for p in self.apoyos}

    def componentes_conexas(self):
        conexiones=self.apoyos_conectados()
        por_ver=set()
        salida=[]
        for nodo in self.apoyos:
            if nodo in por_ver:
                continue
            cola=deque([nodo])
            componente=set()
            while cola:
                n=cola.popleft()
                if n in componente:
                    continue
                componente.add(n)
                cola.extend(other for other,*_ in conexiones[n])
            por_ver|=componente
            salida.append(tuple(sorted(componente)))
        return salida
