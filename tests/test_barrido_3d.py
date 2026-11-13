"""Regresiones de la catenaria 3D y barridos con datos sintéticos."""
import math
import unittest

import numpy as np

from calculos.catenaria import resolver_catenaria
from calculos.cambio_estado import resolver_cambio_estado, longitud_natural
from calculos.barrido_3d import ejecutar_barrido_3d


def ejemplo_vanos():
    return [{
        "nombre": "P1-P2", "inicio": "P1", "fin": "P2",
        "base_inicio_m": [0, 0, 100], "base_fin_m": [40, 0, 104],
        "amarre_inicio_m": [0, 0, 10], "amarre_fin_m": [0, 0, 9],
    }]


def barrido(**kwargs):
    params = dict(
        vanos=ejemplo_vanos(),
        peso_kN_m=0.0095, diametro_m=0.021,
        EA_kN=16000, alpha_por_C=1.8e-5,
        temperatura_tendido_C=20, temperaturas_C=[20],
        tensiones_iniciales_kN=[8], viento_min_ms=0,
        viento_max_ms=2, incremento_viento_ms=1,
        direcciones_viento_deg=[90], Cd=1.2, rho_kg_m3=1.225,
        cantidad_conductores=3, fuente_conductor="Datos sintéticos de ensayo",
    )
    params.update(kwargs)
    return ejecutar_barrido_3d(**params)


class TestCatenariaTridimensional(unittest.TestCase):
    def test_apoyos_desnivelados_con_y_sin_viento(self):
        for carga in ([0, 0, -.01], [0, .02, -.01]):
            c = resolver_catenaria([0, 0, 110], [40, 0, 113], carga, 8)
            np.testing.assert_allclose(c.puntos(0), [0, 0, 110], atol=1e-11)
            np.testing.assert_allclose(c.puntos(c.luz), [40, 0, 113], atol=1e-11)
            f1, f2 = c.fuerzas
            np.testing.assert_allclose(f1 + f2, np.asarray(carga) * c.longitud,
                                       rtol=1e-10, atol=1e-11)

    def test_catenaria_nivelada_con_solucion_cerrada(self):
        c = resolver_catenaria([0, 0, 10], [40, 0, 10], [0, 0, -.01], 8)
        a = 8 / .01
        esperado = a * (math.cosh(40 / (2*a)) - 1)
        self.assertAlmostEqual(10-c.puntos(20)[2], esperado, places=11)
        self.assertGreater(c.longitud, 40)

    def test_identidad_termica_y_calor(self):
        vano = ([0, 0, 10], [40, 0, 13], [0, 0, -.01], [0, 0, -.01])
        r0 = resolver_cambio_estado([vano], 8, 16000, 1.8e-5, 0)
        r1 = resolver_cambio_estado([vano], 8, 16000, 1.8e-5, 30)
        self.assertAlmostEqual(r0["H_kN"], 8, places=5)
        self.assertLess(r1["H_kN"], 8)
        self.assertLess(abs(r1["residual_m"]), 1e-8)

    def test_cuadratura_con_orden_superior(self):
        c = resolver_catenaria([0, 0, 10], [40, 0, 14], [0, 0, -.01], 8)
        x, w = np.polynomial.legendre.leggauss(128)
        x = (x+1)*c.luz/2
        ref = c.luz/2 * np.dot(w, np.cosh((x-c.xc)/c.a) /
                                (1+c.tension(x)/16000))
        self.assertAlmostEqual(longitud_natural(c,16000),ref,places=10)


class TestBarridos(unittest.TestCase):
    def test_velocidades_de_uno_en_uno(self):
        r = barrido()
        self.assertEqual(r["parametros"]["velocidades_m_s"], [0, 1, 2])
        self.assertEqual(len(r["vanos"]), 3)
        self.assertEqual(len(r["nodos"]), 6)
        self.assertLess(r["vanos"]["Residual equilibrio (kN)"].max(), 1e-7)
        self.assertLess(r["vanos"]["Residual compatibilidad (m)"].abs().max(), 1e-8)

    def test_barrido_de_tensiones_y_temperaturas(self):
        r = barrido(tensiones_iniciales_kN=[4, 6, 8],
                    temperaturas_C=[20, 40], viento_max_ms=1)
        self.assertEqual(len(r["vanos"]), 12)
        self.assertEqual(len(r["nodos"]), 24)
        self.assertTrue((r["nodos"]["Estado"] ==
                         "SOLICITACIÓN, NO VERIFICABLE").all())

    def test_viento_invertido_cambia_fuerza_transversal(self):
        r = barrido(viento_min_ms=10, viento_max_ms=10,
                    direcciones_viento_deg=[90, 270])
        vanos = r["vanos"]
        self.assertEqual(len(vanos), 2)
        a = r["nodos"].query("Punto == 'P1'").sort_values("Azimut viento (°)")
        self.assertAlmostEqual(a.iloc[0]["Fy (kN)"], -a.iloc[1]["Fy (kN)"], places=8)

    def test_faltan_propiedades_rechazar(self):
        with self.assertRaises(ValueError):
            barrido(EA_kN=None)
        with self.assertRaises(ValueError):
            barrido(fuente_conductor="")
        with self.assertRaises(ValueError):
            barrido(incremento_viento_ms=0)

    def test_amarres_invalidos_rechazar(self):
        v = ejemplo_vanos()
        v[0]["amarre_inicio_m"] = [0, 0, -2]
        with self.assertRaises(ValueError):
            barrido(vanos=v)


if __name__ == "__main__":
    unittest.main()
