"""Suite consolidada: arquitectura e integridad de módulos."""
from __future__ import annotations


# === Casos conservados de tests/test_arquitectura_modular.py ===
"""Contrato arquitectónico: los módulos se ejecutan desde motor_general.

No deben importarse entre sí, ni conservarse rutas de analisis/ y
salidas/ globales ya migradas. Evita que el proyecto vuelva a dispersarse.
"""
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
        for ruta in ("analisis", "salidas", "calculos",
                     "entradas/importar_red.py", "entradas/importar_hipotesis_red.py",
                     "entradas/norma_postes.py"):
            self.assertFalse((ROOT / ruta).exists(), ruta)

    def test_salidas_y_entradas_por_modulo(self):
        for modulo in (M1, M2):
            self.assertTrue((modulo / "entradas").is_dir())
            self.assertTrue((modulo / "salidas").is_dir())
        self.assertTrue((M1 / "salidas/PDF/generar_pdf_corrida_cfe.py").is_file())
        self.assertTrue((M2 / "motor.py").is_file())
        self.assertTrue((ROOT / "motor_general.py").is_file())

    def test_calculos_de_red_pertenecen_al_modulo_1(self):
        self.assertFalse((ROOT / "calculos").exists())
        for nombre in ("modelo_red", "ensamblador_global",
                       "hipotesis_red", "barrido_global"):
            with self.subTest(nombre=nombre):
                self.assertTrue((M1 / "calculos" / f"{nombre}.py").is_file())

    def test_entradas_raiz_sin_catalogos_ni_interfaces_heredadas(self):
        esperados = {
            "__init__.py", "io_excel.py", "validacion_entrada.py",
        }
        encontrados = {p.name for p in (ROOT / "entradas").glob("*.py")}
        self.assertEqual(encontrados, esperados)
        for nombre in ("importar_red.py", "importar_hipotesis_red.py"):
            self.assertTrue((M1 / "entradas" / nombre).is_file())
        self.assertTrue((M1 / "interfaz/mostrar_barrido_3d.py").is_file())
        self.assertTrue((M1 / "interfaz/mostrar_red_global.py").is_file())
        self.assertTrue((M1 / "entradas/catalogos/cfe_limitantes_estructuras_120kmh.csv").is_file())
        self.assertTrue((M1 / "entradas/catalogos/cfe_limitantes_estructuras_H_120kmh.csv").is_file())
        self.assertTrue((M2 / "entradas/catalogos_estructuras.py").is_file())
        self.assertTrue((ROOT / "comun/catalogos_conductores.py").is_file())

    def test_catalogo_compartido_identico(self):
        from comun.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR as comun
        from Analisis_mecanico_conductores.conductores.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR as modulo1
        from comun.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR as antiguo
        self.assertIs(comun, modulo1)
        self.assertIs(comun, antiguo)

    def test_entradas_no_dependen_de_interfaz_ni_motor_general(self):
        """La lectura del Módulo 1 es reutilizable sin Streamlit."""
        for archivo in (M1 / "entradas").rglob("*.py"):
            arbol = ast.parse(archivo.read_text(encoding="utf-8-sig"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.ImportFrom):
                    nombre = nodo.module or ""
                    self.assertFalse(
                        nombre.startswith("Analisis_mecanico_conductores.interfaz")
                        or nombre == "motor_general",
                        f"{archivo}: dependencia de capa superior {nombre}",
                    )
                elif isinstance(nodo, ast.Import):
                    for alias in nodo.names:
                        self.assertFalse(
                            alias.name.startswith("Analisis_mecanico_conductores.interfaz")
                            or alias.name == "motor_general",
                            f"{archivo}: dependencia de capa superior {alias.name}",
                        )
        self.assertTrue((M1 / "entradas/hipotesis_tendido.py").is_file())

    def test_motor_general_no_acepta_modulos_desconocidos(self):
        from motor_general import ejecutar_modulo
        with self.assertRaises(ValueError):
            ejecutar_modulo("módulo-inexistente")


# === Casos conservados de tests/test_compatibilidad_modulos_depurados.py ===
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
            "comun.catalogos_conductores", "Analisis_mecanico_estructuras.entradas.norma_postes",
            "entradas.validacion_entrada",
        ):
            with self.subTest(modulo=nombre):
                self.assertIsNotNone(import_module(nombre))


# === Casos conservados de tests/test_migracion_modulo2_equivalencia.py ===
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
