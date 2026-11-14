"""El motor preliminar y el módulo 01 comparten fichas ACSR Viakon."""
import unittest

from entradas.catalogos import CONDUCTORES_ACSR as raiz
from analisis.catalogos import CONDUCTORES_ACSR as historico
from entradas.catalogo_viakon_acsr import ficha_viakon_acsr


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
        self.assertEqual(set(historico),set(casos))
        for alias,pajarito in casos.items():
            f=ficha_viakon_acsr(pajarito)
            for catalogo in (raiz,historico):
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


if __name__=="__main__":
    unittest.main()
