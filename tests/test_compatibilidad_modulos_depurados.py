"""Control de integridad de implementaciones canónicas tras la depuración.

Las rutas históricas sin consumidores fueron retiradas. La prueba
confirma que permanecen las fuentes necesarias para los cálculos.
"""
from importlib import import_module
import unittest


CALCULOS = (
    "cargas_tramo", "cimentacion", "decision_soporte",
    "equilibrio_poste", "geometria", "mecanica",
    "momento_poste", "perfil", "retenidas", "unidades", "viento",
)


class TestModulosCanonicos(unittest.TestCase):
    def test_implementaciones_estructurales_presentes(self):
        for nombre in CALCULOS:
            with self.subTest(modulo=nombre):
                modulo = import_module(f"Analisis_mecanico_estructuras.calculos.{nombre}")
                elementos = [
                    valor for valor in vars(modulo).values()
                    if getattr(valor, "__module__", None) == modulo.__name__
                ]
                self.assertTrue(elementos)

    def test_entradas_y_salidas_canonicas(self):
        for nombre in (
            "entradas.catalogos", "Analisis_mecanico_estructuras.entradas.norma_postes",
            "entradas.validacion_entrada",
        ):
            with self.subTest(modulo=nombre):
                self.assertIsNotNone(import_module(nombre))


if __name__ == "__main__":
    unittest.main()
