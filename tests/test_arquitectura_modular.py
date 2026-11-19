"""Contrato arquitectónico: los módulos se ejecutan desde motor_general.

No deben importarse entre sí, ni conservarse rutas de analisis/ y
salidas/ globales ya migradas. Evita que el proyecto vuelva a dispersarse.
"""
from __future__ import annotations
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / "Analisis_mecanico_conductores"
M2 = ROOT / "Analisis_mecanico_estructuras"


class TestArquitecturaModular(unittest.TestCase):
    def test_paquetes_independientes(self):
        for origen, destino in ((M1, "Analisis_mecanico_estructuras"),
                                (M2, "Analisis_mecanico_conductores")):
            for archivo in origen.rglob("*.py"):
                with self.subTest(archivo=archivo.relative_to(ROOT)):
                    nodo = ast.parse(archivo.read_text(encoding="utf-8-sig"))
                    for parte in ast.walk(nodo):
                        if isinstance(parte, ast.ImportFrom):
                            nombre = parte.module or ""
                            self.assertFalse(nombre == destino or nombre.startswith(destino+"."),
                                             f"{archivo}: importación cruzada {nombre}")
                        elif isinstance(parte, ast.Import):
                            for alias in parte.names:
                                self.assertFalse(alias.name == destino or alias.name.startswith(destino+"."),
                                                 f"{archivo}: importación cruzada {alias.name}")

    def test_sin_carpetas_historicas(self):
        for ruta in ("analisis", "salidas", "calculos/engine.py",
                     "calculos/fuerzas_nodo.py", "entradas/norma_postes.py"):
            self.assertFalse((ROOT / ruta).exists(), ruta)

    def test_salidas_y_entradas_por_modulo(self):
        for modulo in (M1, M2):
            self.assertTrue((modulo / "entradas").is_dir())
            self.assertTrue((modulo / "salidas").is_dir())
        self.assertTrue((M1 / "salidas/PDF/generar_pdf_corrida_cfe.py").is_file())
        self.assertTrue((M2 / "motor.py").is_file())
        self.assertTrue((ROOT / "motor_general.py").is_file())

    def test_catalogo_compartido_identico(self):
        from comun.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR as comun
        from Analisis_mecanico_conductores.conductores.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR as modulo1
        from entradas.catalogo_viakon_acsr import CONDUCTORES_VIAKON_ACSR as antiguo
        self.assertIs(comun, modulo1)
        self.assertIs(comun, antiguo)

    def test_motor_general_no_acepta_modulos_desconocidos(self):
        from motor_general import ejecutar_modulo
        with self.assertRaises(ValueError):
            ejecutar_modulo("módulo-inexistente")


if __name__ == "__main__":
    unittest.main()
