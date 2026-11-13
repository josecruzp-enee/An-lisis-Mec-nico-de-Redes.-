"""Catenaria exacta en un plano vertical, con amarres a distinta cota.

Modelo por conductor: cable flexible, peso uniforme por longitud REAL,
componente horizontal de tensión impuesta y sin viento/hielo.
No modela elasticidad, temperatura, ni restricciones de suspensión móvil.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class ResultadoCatenaria:
    origen: np.ndarray
    direccion: np.ndarray
    longitud_horizontal: float
    z_inicial: float
    H_kN: float
    peso_kN_m: float
    a: float
    xc: float

    def altura(self, x):
        x = np.asarray(x, dtype=float)
        return self.z_inicial + 2 * self.a * np.sinh(
            x / (2 * self.a)) * np.sinh((x / 2 - self.xc) / self.a)

    @property
    def longitud_real(self):
        L = self.longitud_horizontal
        return float(2 * self.a * np.sinh(L / (2 * self.a)) *
                     np.cosh((L / 2 - self.xc) / self.a))

    @property
    def fuerzas_extremos(self):
        """Fuerzas del cable SOBRE A y B; Z positivo hacia arriba."""
        L = self.longitud_horizontal
        vertical_a = self.H_kN * np.sinh(-self.xc / self.a)
        vertical_b = -self.H_kN * np.sinh((L - self.xc) / self.a)
        horizontal = self.H_kN * self.direccion
        return (
            np.array([*horizontal, vertical_a]),
            np.array([*-horizontal, vertical_b]),
        )

    def tension_extremo(self, x):
        return float(self.H_kN * np.cosh((x - self.xc) / self.a))

    def minimo_terreno_lineal(self, z_terreno_a, z_terreno_b):
        """Mínimo analítico de distancia vertical a terreno interpolado."""
        L = self.longitud_horizontal
        pendiente = (z_terreno_b - z_terreno_a) / L
        x = float(np.clip(self.xc + self.a * np.arcsinh(pendiente), 0, L))
        terreno = z_terreno_a + pendiente * x
        return x, float(self.altura(x) - terreno)

    def flecha_respecto_cuerda(self, z_final):
        L = self.longitud_horizontal
        pendiente = (z_final - self.z_inicial) / L
        x = float(np.clip(self.xc + self.a * np.arcsinh(pendiente), 0, L))
        cuerda = self.z_inicial + pendiente * x
        return float(cuerda - self.altura(x))


def resolver_catenaria_desnivel(a_xyz, b_xyz, peso_kN_m, H_kN):
    """Resuelve la curva con desnivel e impide geometrías o datos inválidos."""
    p = np.asarray(a_xyz, dtype=float)
    q = np.asarray(b_xyz, dtype=float)
    if p.shape != (3,) or q.shape != (3,) or not np.isfinite([*p, *q]).all():
        raise ValueError("Amarres deben tener coordenadas XYZ finitas")
    w = float(peso_kN_m)
    H = float(H_kN)
    if not math.isfinite(w) or w <= 0 or not math.isfinite(H) or H <= 0:
        raise ValueError("Se requieren peso y tensión positivos y finitos")
    vector = q[:2] - p[:2]
    L = float(np.linalg.norm(vector))
    if L <= 0:
        raise ValueError("Vano con distancia horizontal nula")
    a = H / w
    u = L / (2 * a)
    if u > 300:
        raise ValueError("H demasiado pequeña para resolver catenaria")
    desnivel = float(q[2] - p[2])
    xc = L / 2 - a * np.arcsinh(desnivel / (2 * a * np.sinh(u)))
    return ResultadoCatenaria(p, vector / L, L, float(p[2]),
                             H, w, a, float(xc))
