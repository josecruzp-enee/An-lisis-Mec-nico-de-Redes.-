"""Pruebas de flecha y despeje de referencia con catenaria espacial."""
import unittest
import math

from calculos.barrido_3d import ejecutar_barrido_3d


class TestFlechaDespeje(unittest.TestCase):
    def test_nivelado_sin_viento_cotejo_analitico(self):
        w=.01;H=8.;L=40.;h=10.
        v=[{
            "nombre":"A-B","inicio":"A","fin":"B",
            "base_inicio_m":[0,0,0],"base_fin_m":[L,0,0],
            "amarre_inicio_m":[0,0,h],"amarre_fin_m":[0,0,h],
        }]
        r=ejecutar_barrido_3d(
            v,peso_kN_m=w,diametro_m=.02,EA_kN=16000,
            alpha_por_C=1.8e-5,temperatura_tendido_C=20,
            temperaturas_C=[20],tensiones_iniciales_kN=[H],
            viento_max_ms=0,direcciones_viento_deg=[0],
            fuente_conductor="Ensayo sintético",
        )
        fila=r["vanos"].iloc[0]
        a=H/w
        f=a*(math.cosh(L/(2*a))-1)
        self.assertAlmostEqual(fila["Flecha vertical respecto cuerda (m)"],f,places=5)
        self.assertAlmostEqual(fila["Despeje sobre terreno lineal (m)"],h-f,places=5)

    def test_desnivelado_muestra_despeje_sin_aprobar(self):
        v=[{
            "nombre":"A-B","inicio":"A","fin":"B",
            "base_inicio_m":[0,0,0],"base_fin_m":[50,0,8],
            "amarre_inicio_m":[0,0,11],"amarre_fin_m":[0,0,10],
        }]
        r=ejecutar_barrido_3d(
            v,peso_kN_m=.01,diametro_m=.02,EA_kN=16000,
            alpha_por_C=1.8e-5,temperatura_tendido_C=20,
            temperaturas_C=[20],tensiones_iniciales_kN=[5],
            viento_max_ms=10,direcciones_viento_deg=[90],
            fuente_conductor="Ensayo sintético",
        )
        self.assertTrue((r["vanos"]["Despeje sobre terreno lineal (m)"]>0).all())
        self.assertTrue((r["vanos"]["Modelo terreno"].str.contains("NO VERIFICADO")).all())


if __name__=="__main__":
    unittest.main()
