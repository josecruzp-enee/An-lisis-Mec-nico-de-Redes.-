"""Regresión de alturas: no confundir longitud total con altura sobre terreno."""
import math
import unittest

from analisis.norma_postes import (
    altura_expuesta_poste_m,
    altura_amarre_poste_m,
    h_amarre_norma_m,
    h_amarre_tipica_m,
)


class TestAlturasPostes(unittest.TestCase):
    """Casos geométricos, no aprobación normativa de una profundidad concreta."""

    def test_longitud_total_menos_enterramiento(self):
        # Ejemplo geométrico: profundidad 1.8 m, NO criterio normativo ENEE.
        for nombre, longitud in (
            ("PC-30", 9.15),
            ("PC-35", 10.67),
            ("PC-40", 12.19),
        ):
            with self.subTest(poste=nombre):
                self.assertAlmostEqual(
                    altura_expuesta_poste_m(nombre, 1.8), longitud - 1.8)
                self.assertAlmostEqual(
                    altura_amarre_poste_m(nombre, 1.8, 0.10),
                    longitud - 1.8 - 0.10)

    def test_amarre_por_uso_descontando_enterramiento(self):
        # Offset heredado de catálogo, pendiente de validación documental.
        self.assertAlmostEqual(
            h_amarre_norma_m("PC-40", uso="primario", empotramiento_m=1.8),
            12.19 - 1.8 - 2.0)

    def test_sin_empotramiento_no_inventa_altura(self):
        self.assertTrue(math.isnan(h_amarre_norma_m("PC-40")))
        self.assertTrue(math.isnan(h_amarre_tipica_m("PC-40")))

    def test_datos_invalidos_se_rechazan(self):
        for enterrado in (-1, float("nan"), float("inf"), 12.19):
            with self.subTest(enterrado=enterrado):
                with self.assertRaises(ValueError):
                    altura_expuesta_poste_m("PC-40", enterrado)
        with self.assertRaises(ValueError):
            altura_amarre_poste_m("PC-40", 1.8, 11)
        with self.assertRaises(ValueError):
            altura_expuesta_poste_m("DESCONOCIDO", 1.8)

    def test_longitud_explicita(self):
        self.assertAlmostEqual(
            altura_amarre_poste_m("PERSONALIZADO", 2, 0.5,
                                 longitud_total_m=13),
            10.5)


if __name__ == "__main__":
    unittest.main()
