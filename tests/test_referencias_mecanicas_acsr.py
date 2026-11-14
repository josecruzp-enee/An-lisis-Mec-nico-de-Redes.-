"""Referencias mecánicas ACSR Nexans: unidades y trazabilidad."""
import unittest
import math

from entradas.catalogo_viakon_acsr import ficha_viakon_acsr
from entradas.referencias_mecanicas_acsr import (
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


if __name__=="__main__":
    unittest.main()
