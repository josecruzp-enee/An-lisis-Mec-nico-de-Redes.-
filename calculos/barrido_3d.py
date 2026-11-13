"""Estudio paramétrico 3D de vanos con amarres fijos.

Usa catenaria exacta para una carga vectorial UNIFORME por longitud real;
resuelve compatibilidad termoelástica para cada estado y cada vano.
Modelo aerodinámico: arrastre normal al eje horizontal del vano, todavía
no dependiente de la tangente local del cable. No constituye aprobación de obra.

Coordenadas: X Este, Y Norte, Z arriba; m, kN, kN/m, °C.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

from .catenaria import resolver_catenaria
from .cambio_estado import resolver_cambio_estado
from .validacion_mecanica import finito, vector3


def _carga_viento(p, q, peso_kN_m, diametro_m, velocidad_ms,
                  azimut_deg, Cd, rho):
    """Carga por longitud de cable real; viento proyectado normal al vano."""
    eje = (q - p)[:2]
    longitud = float(np.linalg.norm(eje))
    if longitud == 0:
        raise ValueError("Vano horizontal nulo")
    normal = np.array([-eje[1], eje[0]]) / longitud
    rumbo = math.radians(azimut_deg)
    viento = velocidad_ms * np.array([math.cos(rumbo), math.sin(rumbo)])
    vn = float(np.dot(viento, normal))
    arrastre = 0.5 * rho * Cd * diametro_m * vn * abs(vn) / 1000
    return np.r_[arrastre * normal, -peso_kN_m]


def _verificar_vanos(vanos):
    if not vanos:
        raise ValueError("Se necesita al menos un vano")
    salida = []
    nombres = set()
    for v in vanos:
        for campo in ("nombre", "inicio", "fin", "base_inicio_m", "base_fin_m",
                      "amarre_inicio_m", "amarre_fin_m"):
            if campo not in v:
                raise ValueError(f"Vano sin {campo}")
        if v["nombre"] in nombres or v["inicio"] == v["fin"]:
            raise ValueError("Vanos duplicados o extremos iguales")
        nombres.add(v["nombre"])
        base_a = vector3(v["base_inicio_m"], "base inicio")
        base_b = vector3(v["base_fin_m"], "base fin")
        amarre_a = vector3(v["amarre_inicio_m"], "amarre inicio")
        amarre_b = vector3(v["amarre_fin_m"], "amarre fin")
        if amarre_a[2] <= 0 or amarre_b[2] <= 0:
            raise ValueError("Amarres deben situarse sobre el terreno")
        a, b = base_a + amarre_a, base_b + amarre_b
        if np.linalg.norm((b-a)[:2]) == 0:
            raise ValueError("Vano con longitud horizontal nula")
        salida.append((v, a, b, amarre_a, amarre_b))
    return salida


def _secuencia_viento(inicio, fin, incremento):
    if any(isinstance(x, bool) for x in (inicio, fin, incremento)):
        raise ValueError("Velocidad e incremento deben ser números")
    a, b, paso = (finito(x, "velocidad", 0, True) if i == 2
                  else finito(x, "velocidad", 0) for i, x in
                  enumerate((inicio, fin, incremento)))
    if b < a:
        raise ValueError("Velocidad máxima menor que mínima")
    cantidad = round((b - a) / paso)
    if not math.isclose(a + cantidad * paso, b, abs_tol=1e-9):
        raise ValueError("El rango de viento no es divisible por el incremento")
    if cantidad > 1000:
        raise ValueError("Demasiadas velocidades; máximo 1001")
    return [a + i * paso for i in range(cantidad + 1)]


def ejecutar_barrido_3d(
    vanos, *, peso_kN_m, diametro_m, EA_kN, alpha_por_C,
    temperatura_tendido_C, temperaturas_C, tensiones_iniciales_kN,
    viento_max_ms, viento_min_ms=0, incremento_viento_ms=1,
    direcciones_viento_deg=(0,), Cd=1.2, rho_kg_m3=1.225,
    cantidad_conductores=1, fuente_conductor=""
):
    """Calcula todos los estados, sin reemplazar capacidades faltantes.

    Cada vano se supone retenido entre extremos fijos. H inicial definida
    para condición sin viento a la temperatura de tendido.
    No se simulan apoyos con suspensión longitudinal deslizante.
    """
    geometria = _verificar_vanos(vanos)
    w = finito(peso_kN_m, "peso", 0, True)
    d = finito(diametro_m, "diámetro", 0, True)
    EA = finito(EA_kN, "EA", 0, True)
    alpha = finito(alpha_por_C, "alpha", 0)
    t0 = finito(temperatura_tendido_C, "temperatura de tendido")
    cd = finito(Cd, "Cd", 0, True)
    rho = finito(rho_kg_m3, "densidad aire", 0, True)
    if not isinstance(cantidad_conductores, int) or isinstance(cantidad_conductores, bool) or cantidad_conductores < 1:
        raise ValueError("Cantidad de conductores debe ser entero positivo")
    if not isinstance(fuente_conductor, str) or not fuente_conductor.strip():
        raise ValueError("Indicar fuente de peso, diámetro, EA y alpha del conductor")
    if not temperaturas_C or not tensiones_iniciales_kN or not direcciones_viento_deg:
        raise ValueError("Listas de temperaturas, tensiones y direcciones no pueden estar vacías")
    temperaturas = [finito(t, "temperatura") for t in temperaturas_C]
    tensiones = [finito(h, "H inicial", 0, True) for h in tensiones_iniciales_kN]
    rumbos = [finito(az, "azimut viento") % 360 for az in direcciones_viento_deg]
    velocidades = _secuencia_viento(viento_min_ms, viento_max_ms, incremento_viento_ms)

    filas_vanos, filas_nodos = [], []
    for h0 in tensiones:
        for temperatura in temperaturas:
            for rumbo in rumbos:
                for v_ms in velocidades:
                    cargas = defaultdict(lambda: np.zeros(6))
                    caso = f"H0={h0:g};T={temperatura:g};V={v_ms:g};Az={rumbo:g}"
                    for vano, a, b, ra, rb in geometria:
                        q0 = np.array([0.0, 0.0, -w])
                        q1 = _carga_viento(a, b, w, d, v_ms, rumbo, cd, rho)
                        cambio = resolver_cambio_estado(
                            [(a, b, q0, q1)], h0, EA, alpha, temperatura-t0
                        )
                        cable = resolver_catenaria(a, b, q1, cambio["H_kN"])
                        fa, fb = cable.fuerzas
                        residual = fa + fb - q1 * cable.longitud
                        err = float(np.linalg.norm(residual))
                        if not np.isfinite(err) or err > 1e-7:
                            raise ValueError(f"{caso}/{vano['nombre']}: desequilibrio {err} kN")
                        for nombre, r, fuerza in (
                            (vano["inicio"], ra, fa), (vano["fin"], rb, fb)
                        ):
                            f = cantidad_conductores * fuerza
                            cargas[nombre][:3] += f
                            cargas[nombre][3:] += np.cross(r, f)
                        # Flecha respecto a cuerda en abscisa local de la catenaria.
                        # Mínimo vertical de (z_cable - z_cuerda) por cálculo
                        # analítico del extremo de la curva, no por muestreo.
                        pendiente_cuerda = float((b[2]-a[2])/cable.luz)
                        x_flecha = cable.minimo_lineal(
                            [0, 0, 1], pendiente=pendiente_cuerda
                        )
                        flecha_vertical = float(
                            a[2] + pendiente_cuerda*x_flecha
                            - cable.puntos(x_flecha)[2]
                        )

                        # Despeje geométrico respecto a interpolación lineal del
                        # TERRENO ENTRE DOS APOYOS. No representa montículos,
                        # barrancos no lineales, edificaciones o vegetación.
                        dxy = b[:2]-a[:2]
                        dxy2 = float(dxy@dxy)
                        terreno_a = float(
                            np.asarray(vano["base_inicio_m"], dtype=float)[2]
                        )
                        terreno_b = float(
                            np.asarray(vano["base_fin_m"], dtype=float)[2]
                        )
                        grado = (terreno_b-terreno_a)*dxy/dxy2
                        direccion_despeje = np.array(
                            [-grado[0], -grado[1], 1.]
                        )
                        x_despeje = cable.minimo_lineal(direccion_despeje)
                        punto_despeje = cable.puntos(x_despeje)
                        progresiva = float(
                            ((punto_despeje[:2]-a[:2])@dxy)/dxy2
                        )
                        terreno_interpolado = (
                            terreno_a+(terreno_b-terreno_a)*progresiva
                        )
                        despeje_geom = float(
                            punto_despeje[2]-terreno_interpolado
                        )
                        filas_vanos.append({
                            "Caso": caso, "Vano": vano["nombre"],
                            "Flecha vertical respecto cuerda (m)": flecha_vertical,
                            "Despeje sobre terreno lineal (m)": despeje_geom,
                            "Modelo terreno": "INTERPOLACIÓN ENTRE APOYOS; NO VERIFICADO",
                            "Temperatura (°C)": temperatura,
                            "Viento (m/s)": v_ms, "Azimut viento (°)": rumbo,
                            "H inicial (kN)": h0,
                            "H resuelta (kN)": cambio["H_kN"],
                            "T extremo A (kN)": float(cable.tension(0)),
                            "T extremo B (kN)": float(cable.tension(cable.luz)),
                            "Longitud cable (m)": cable.longitud,
                            "Residual equilibrio (kN)": err,
                            "Residual compatibilidad (m)": cambio["residual_m"],
                            "Iteraciones": cambio["iteraciones"],
                            "Fuente conductor": fuente_conductor,
                        })
                    for nodo, f in cargas.items():
                        fx, fy, fz, mx, my, mz = map(float, f)
                        filas_nodos.append({
                            "Caso": caso, "Punto": nodo,
                            "Temperatura (°C)": temperatura,
                            "Viento (m/s)": v_ms, "Azimut viento (°)": rumbo,
                            "H inicial (kN)": h0,
                            "Fx (kN)": fx, "Fy (kN)": fy, "Fz (kN)": fz,
                            "Mx (kN·m)": mx, "My (kN·m)": my, "Mz (kN·m)": mz,
                            "H resultante (kN)": math.hypot(fx, fy),
                            "Estado": "SOLICITACIÓN, NO VERIFICABLE",
                        })
    return {
        "vanos": pd.DataFrame(filas_vanos),
        "nodos": pd.DataFrame(filas_nodos),
        "parametros": {
            "velocidades_m_s": velocidades, "tensiones_iniciales_kN": tensiones,
            "temperaturas_C": temperaturas, "direcciones_viento_deg": rumbos,
            "modelo": "Catenaria 3D, q vectorial uniforme y compatibilidad termoelástica",
            "alcance": "Sin arrastre local dependiente de la tangente ni capacidades estructurales",
        },
    }
