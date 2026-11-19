"""Regresión del coordinador: reproducir exactamente el Módulo 2 sin alteraciones."""
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal

from Analisis_mecanico_estructuras.motor import ejecutar_todo as nuevo
from motor_general import ejecutar_todo as coordinado
from Analisis_mecanico_estructuras.calculos.geometria import calcular_tramos as geometria_nueva
from Analisis_mecanico_estructuras.entradas.norma_postes import obtener_ficha_poste as ficha_nueva


class TestMigracionSinAlterarResultados(unittest.TestCase):
    @staticmethod
    def datos():
        return pd.DataFrame({
            "Punto": ["P1", "P2", "P3"],
            "X": [0.0, 40.0, 100.0], "Y": [0.0, 0.0, 0.0],
            "Altitud": [0.0, 0.0, 0.0],
            "Poste": ["PC-40"] * 3, "Espacio Retenida": ["SI"] * 3,
        })

    @staticmethod
    def kwargs():
        return dict(calibre="2/0 ACSR", n_fases=3, v_viento_ms=12.0,
                    az_viento_deg=90.0, diametro_m=0.01134, H_tendido_kN=2.0)

    def test_motor_estructuras_equivalente(self):
        b = nuevo(self.datos(), **self.kwargs())
        c = coordinado(self.datos(), **self.kwargs())
        self.assertEqual(b.keys(), c.keys())
        for nombre in b:
            with self.subTest(nombre=nombre):
                y, z = b[nombre], c[nombre]
                if isinstance(y, pd.DataFrame):
                    assert_frame_equal(y, z, check_exact=True)
                else:
                    self.assertEqual(y, z)

    def test_geometria_equivalente(self):
        puntos = [(0,0), (40,0), (100,0)]
        ids = ["P1", "P2", "P3"]
        tabla = geometria_nueva(puntos, ids)
        self.assertEqual(len(tabla), 2)
        self.assertAlmostEqual(float(tabla["Distancia (m)"].sum()), 100.0)

    def test_fichas_equivalentes(self):
        for poste in ["PC-40", "PC-35", "CLASE 3"]:
            with self.subTest(poste=poste):
                self.assertNotEqual(ficha_nueva(poste)["fuente"], "NO_ENCONTRADO")


if __name__ == "__main__":
    unittest.main()
