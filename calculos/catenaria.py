"""Cable flexible exacto bajo carga uniforme por longitud REAL de cable.

Deducción de equilibrio d(T tangente)/ds = -q. No incluye rigidez flexional,
arrastre dependiente de la tangente ni elasticidad variable en la geometría.
La elasticidad se aplica en cambio_estado.py mediante compatibilidad integral.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .validacion_mecanica import finito, vector3


@dataclass(frozen=True)
class Catenaria:
    """Base local: e longitudinal normal a la carga; n opuesta a la carga."""
    inicio: np.ndarray
    e: np.ndarray
    n: np.ndarray
    luz: float
    desnivel: float
    H: float
    w: float
    a: float
    xc: float

    def puntos(self, x) -> np.ndarray:
        """Coordenadas globales en m; identidad hiperbólica evita cancelación."""
        x = np.asarray(x, dtype=float)
        z = 2 * self.a * np.sinh(x / (2*self.a)) * np.sinh((x/2-self.xc)/self.a)
        return self.inicio + x[..., None]*self.e + z[..., None]*self.n

    def tension(self, x):
        """Magnitud de tracción en kN en cualquier abscisa local."""
        return self.H * np.cosh((np.asarray(x)-self.xc)/self.a)

    @property
    def longitud(self) -> float:
        """Longitud exacta en m, integral del arco entre apoyos."""
        return float(2*self.a*np.sinh(self.luz/(2*self.a))*
                     np.cosh((self.luz/2-self.xc)/self.a))

    @property
    def fuerzas(self) -> tuple[np.ndarray, np.ndarray]:
        """Fuerzas del cable SOBRE los apoyos A y B en kN (no las opuestas)."""
        izquierda = self.H*(self.e + np.sinh(-self.xc/self.a)*self.n)
        derecha = -self.H*(self.e + np.sinh((self.luz-self.xc)/self.a)*self.n)
        return izquierda, derecha

    def minimo_lineal(self, vector, pendiente=0.0) -> float:
        """Abscisa que minimiza dot(posición,vector)-pendiente*x en [0,luz]."""
        v = vector3(vector, 'dirección de medición')
        coef = float(v @ self.n)
        candidatos = [0.0, self.luz]
        if coef > 0:
            x = self.xc + self.a*np.arcsinh((pendiente-v@self.e)/coef)
            candidatos.append(float(np.clip(x, 0, self.luz)))
        return min(candidatos, key=lambda x: float(self.puntos(x)@v-pendiente*x))


def resolver_catenaria(inicio, fin, carga_kN_m, H_kN) -> Catenaria:
    """Resuelve apoyos desnivelados en el plano cuerda–carga constante.

    H es la componente perpendicular a la carga resultante, no la tensión
    total ni necesariamente la horizontal global cuando hay viento.
    """
    p, b, q = (vector3(v, n) for v, n in
               [(inicio, 'inicio'), (fin, 'fin'), (carga_kN_m, 'carga')])
    H = finito(H_kN, 'H_kN', 0, True)
    w = finito(np.linalg.norm(q), 'magnitud de carga', 0, True)
    n = -q/w
    dz = float((b-p)@n)
    proyeccion = b-p-dz*n
    luz = finito(np.linalg.norm(proyeccion), 'luz perpendicular a carga', 0, True)
    a = H/w
    u = luz/(2*a)
    if u > 300:
        raise ValueError('Catenaria fuera del dominio numérico: H demasiado pequeña')
    xc = luz/2-a*np.arcsinh(dz/(2*a*np.sinh(u)))
    return Catenaria(p, proyeccion/luz, n, luz, dz, H, w, a, float(xc))
