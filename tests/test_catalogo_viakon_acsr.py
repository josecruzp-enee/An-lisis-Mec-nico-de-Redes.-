"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_catalogo_viakon_acsr.py ===
"""Catálogo Viakon ACSR: ave obligatoria y construcción distinguible."""
import unittest

from comun.catalogo_acsr_viakon import (
    CONDUCTORES_VIAKON_ACSR, ficha_viakon_acsr,
    propiedades_mecanicas_documentadas,
)


class CatalogoViakonTest(unittest.TestCase):
    def test_todos_llevan_calibre_y_nombre_pajarito(self):
        self.assertGreaterEqual(len(CONDUCTORES_VIAKON_ACSR), 15)
        for nombre, ficha in CONDUCTORES_VIAKON_ACSR.items():
            self.assertIn(" — ", nombre)
            self.assertTrue(nombre.endswith(ficha["nombre_pajarito"]))
            self.assertIn(ficha["calibre"].replace(".0",""), nombre)
            self.assertGreater(ficha["peso_kg_m"],0)
            self.assertGreater(ficha["diametro_m"],0)
            self.assertGreater(ficha["TR_kgf"],0)
            self.assertGreater(ficha["hilos_aluminio"],0)
            self.assertGreater(ficha["hilos_acero"],0)
            self.assertTrue(ficha["fuente"].startswith("https://"))

    def test_quail_es_2_0_y_no_se_confunde_con_otros(self):
        ficha=ficha_viakon_acsr("2/0 ACSR — QUAIL")
        self.assertEqual(ficha["codigo"],"QUAIL")
        self.assertAlmostEqual(ficha["diametro_mm"],11.34)
        self.assertAlmostEqual(ficha["peso_kg_km"],272.0)
        self.assertEqual(ficha["TR_kgf"],2398)

    def test_calibre_266_8_tiene_tres_aves_y_construcciones(self):
        aves={
            f["codigo"] for f in CONDUCTORES_VIAKON_ACSR.values()
            if f["calibre"]=="266.8"
        }
        self.assertEqual(aves,{"OWL","WAXWING","PARTRIDGE"})
        penguin=ficha_viakon_acsr("4/0 ACSR — PENGUIN")
        self.assertEqual((penguin["hilos_aluminio"],penguin["hilos_acero"]),(6,1))

    def test_no_se_inventan_ea_ni_dilatacion(self):
        for nombre in CONDUCTORES_VIAKON_ACSR:
            p=propiedades_mecanicas_documentadas(nombre)
            self.assertFalse(p["completo"])
            self.assertEqual(set(p["faltantes"]),{"EA_kN","alpha_por_C"})

    def test_copia_independiente(self):
        a=ficha_viakon_acsr("2/0 ACSR — QUAIL")
        a["peso_kg_km"]=0
        self.assertEqual(
            ficha_viakon_acsr("2/0 ACSR — QUAIL")["peso_kg_km"],272.0
        )


# === Casos conservados de tests/test_catalogos_unificados.py ===
"""Los análisis consumen un catálogo ACSR Viakon compartido."""
import unittest

from comun.catalogos_conductores import CONDUCTORES_ACSR as raiz
from comun.catalogo_acsr_viakon import ficha_viakon_acsr


class CatalogosConsistentesTest(unittest.TestCase):
    def test_alias_historicos_identifican_la_misma_ave_y_masa(self):
        casos={
            "2 ACSR":"2 ACSR — SPARROW",
            "1/0 ACSR":"1/0 ACSR — RAVEN",
            "2/0 ACSR":"2/0 ACSR — QUAIL",
            "3/0 ACSR":"3/0 ACSR — PIGEON",
            "4/0 ACSR":"4/0 ACSR — PENGUIN",
            "266.8 MCM":"266.8 MCM — OWL",
            "336.4 MCM":"336.4 MCM — LINNET",
            "477 MCM":"477 MCM — HAWK",
            "795 MCM":"795 MCM — DRAKE",
        }
        self.assertEqual(set(raiz),set(casos))
        for alias,pajarito in casos.items():
            f=ficha_viakon_acsr(pajarito)
            for catalogo in (raiz,):
                self.assertEqual(catalogo[alias]["codigo"],f["codigo"])
                self.assertEqual(catalogo[alias]["TR_kgf"],f["TR_kgf"])
                self.assertAlmostEqual(catalogo[alias]["peso_kg_m"],f["peso_kg_m"])
                self.assertAlmostEqual(catalogo[alias]["diametro_m"],f["diametro_m"])

    def test_cambios_de_alias_no_modifican_ficha_oficial(self):
        alias=raiz["2/0 ACSR"]
        original=alias["peso_kg_m"]
        alias["peso_kg_m"]=0
        try:
            self.assertAlmostEqual(
                ficha_viakon_acsr("2/0 ACSR — QUAIL")["peso_kg_m"],
                original,
            )
        finally:
            alias["peso_kg_m"]=original


# === Casos conservados de tests/test_tabla_catalogo_acsr.py ===
"""Catálogo exportable sin asignar propiedades de Nexans a Viakon."""
import unittest

from Analisis_mecanico_conductores.conductores.mostrar_tabla_catalogo_acsr import tabla_catalogo_acsr
from comun.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR


class TablaCatalogoACSRTest(unittest.TestCase):
    def test_todas_las_aves_y_fuentes_separadas(self):
        tabla=tabla_catalogo_acsr()
        self.assertEqual(len(tabla),len(CONDUCTORES_VIAKON_ACSR))
        self.assertGreaterEqual(len(tabla),24)
        self.assertFalse(tabla["Conductor"].duplicated().any())
        self.assertTrue(tabla["Conductor"].str.contains(" — ").all())
        self.assertTrue((tabla["Propiedades E/alpha certificadas Viakon"]
                         =="NO DISPONIBLES").all())
        self.assertTrue(tabla["Fuente nominal"].str.contains("viakon.com").all())
        self.assertTrue(tabla["Fuente referencia"].str.contains("nexans.com.br").all())

    def test_numeros_referencia_son_positivos_y_sin_confundir_fuentes(self):
        tabla=tabla_catalogo_acsr()
        self.assertTrue((tabla["Referencia EA final Nexans (kN)"]>0).all())
        self.assertTrue((tabla["Carga ruptura nominal (kN)"]>0).all())
        self.assertTrue(tabla["Estado"].str.contains("NO APTAS").all())


# === Casos conservados de tests/test_referencias_mecanicas_acsr.py ===
"""Referencias mecánicas ACSR Nexans: unidades y trazabilidad."""
import unittest
import math

from comun.catalogo_acsr_viakon import ficha_viakon_acsr
from Analisis_mecanico_conductores.conductores.referencias_mecanicas_acsr_nexans import (
    referencia_mecanica_nexans, NEXANS_ACSR_FINAL,
)


class ReferenciaMecanicaTest(unittest.TestCase):
    def test_pajarito_y_construccion_quail(self):
        r=referencia_mecanica_nexans("2/0 ACSR — QUAIL")
        self.assertEqual(r["codigo"],"QUAIL")
        self.assertEqual(r["configuracion"],"6/1")
        self.assertAlmostEqual(r["E_final_GPa"],8156*0.00980665)
        self.assertAlmostEqual(r["alpha_final_referencia_por_C"],19.1e-6)
        self.assertFalse(r["apto_para_diseno"])

    def test_area_total_incluye_acero_y_ea_kN(self):
        r=referencia_mecanica_nexans("2/0 ACSR — QUAIL")
        area_total=7*math.pi/4*3.78**2
        self.assertAlmostEqual(r["area_total_mm2"],area_total)
        self.assertAlmostEqual(
            r["EA_final_referencia_kN"],
            area_total*8156*9.80665/1000,
        )
        self.assertGreater(r["area_total_mm2"],r["area_aluminio_mm2"])

    def test_owl_y_waxwing_tienen_diferentes_propiedades(self):
        owl=referencia_mecanica_nexans("266.8 MCM — OWL")
        wax=referencia_mecanica_nexans("266.8 MCM — WAXWING")
        self.assertEqual(owl["configuracion"],"6/7")
        self.assertEqual(wax["configuracion"],"18/1")
        self.assertNotEqual(owl["EA_final_referencia_kN"],
                            wax["EA_final_referencia_kN"])

    def test_no_muta_la_ficha_viakon(self):
        nombre="477 MCM — HAWK"
        r=referencia_mecanica_nexans(nombre)
        ficha=ficha_viakon_acsr(nombre)
        self.assertIsNone(ficha["EA_kN"])
        self.assertIsNone(ficha["alpha_por_C"])
        self.assertIn("Nexans",r["origen"])

    def test_no_inventa_construcciones_fuera_fuente(self):
        self.assertNotIn((9,9),NEXANS_ACSR_FINAL)
