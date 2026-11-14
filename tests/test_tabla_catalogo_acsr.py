"""Catálogo exportable sin asignar propiedades de Nexans a Viakon."""
import unittest

from entradas.tabla_catalogo_acsr import tabla_catalogo_acsr
from entradas.catalogo_viakon_acsr import CONDUCTORES_VIAKON_ACSR


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


if __name__=="__main__":
    unittest.main()
