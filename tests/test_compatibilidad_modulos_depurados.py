"""Regresión de rutas históricas tras consolidar copias exactas.

El motor conserva una única implementación, pero los imports públicos
deben continuar entregando las mismas funciones y clases.
"""
import importlib
import unittest


MODULOS = (
    "cargas_tramo", "cimentacion", "decision_soporte",
    "equilibrio_poste", "geometria", "mecanica",
    "momento_poste", "perfil", "retenidas", "unidades", "viento",
)


class TestCompatibilidadModulosDepurados(unittest.TestCase):
    def test_importaciones_historicas_conservan_funciones(self):
        for nombre in MODULOS:
            with self.subTest(modulo=nombre):
                original = importlib.import_module(f"analisis.calculos.{nombre}")
                puente = importlib.import_module(f"calculos.{nombre}")
                nombres = [
                    n for n, valor in vars(original).items()
                    if not n.startswith("_") and getattr(valor, "__module__", "")
                    == original.__name__
                ]
                self.assertTrue(nombres, f"Sin elementos propios: {nombre}")
                for simbolo in nombres:
                    self.assertIs(getattr(puente, simbolo), getattr(original, simbolo))

    def test_simbolos_privados_tambien_accesibles(self):
        for nombre in MODULOS:
            with self.subTest(modulo=nombre):
                original = importlib.import_module(f"analisis.calculos.{nombre}")
                puente = importlib.import_module(f"calculos.{nombre}")
                for simbolo in vars(original):
                    if simbolo.startswith("_") and not simbolo.startswith("__"):
                        self.assertIs(getattr(puente, simbolo), getattr(original, simbolo))


if __name__ == "__main__":
    unittest.main()
