"""Regresión documentada CFE 05 00 03: viento por claro."""
import unittest
import numpy as np

from Analisis_mecanico_conductores.hipotesis_climaticas.presiones_cfe_por_claro import presion_cfe_por_claro
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import calcular_cargas_transversales_por_vano


class TestPresionesCfePorClaro(unittest.TestCase):
    def test_tabla_interpolada_109m(self):
        self.assertAlmostEqual(presion_cfe_por_claro(109,120),382.4)
        self.assertAlmostEqual(presion_cfe_por_claro(109,109),70.)
        self.assertEqual(presion_cfe_por_claro(109,0),0.)

    def test_viento_cfe_sin_doblar_cd(self):
        xyz=np.array([[0.,0.,0.],[109.,0.,0.]])
        for v,p in ((120.,382.4),(109.,70.)):
            cargas,viento=calcular_cargas_transversales_por_vano(
                xyz,0.002120,0.01011,v/3.6,1.,1.225,modelo_presion_cfe=True)
            self.assertAlmostEqual(viento*1000,p*0.01011,places=9)
            self.assertAlmostEqual(cargas[0][1][2],-0.002120,places=12)
        _,dinamico=calcular_cargas_transversales_por_vano(
            xyz,0.002120,0.01011,120/3.6,1.,1.225)
        self.assertGreater(dinamico,viento)

    def test_no_extrapolar_fuera_de_tabla(self):
        with self.assertRaises(ValueError):
            presion_cfe_por_claro(109,115)
        with self.assertRaises(ValueError):
            presion_cfe_por_claro(400,120)


if __name__=="__main__":
    unittest.main()
