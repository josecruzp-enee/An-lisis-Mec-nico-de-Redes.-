"""Catálogo Viakon ACSR: ave obligatoria y construcción distinguible."""
import unittest

from entradas.catalogo_viakon_acsr import (
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


if __name__=="__main__":
    unittest.main()
