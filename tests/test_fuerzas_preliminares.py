"""Pruebas de fuerzas preliminares, sin aprobación estructural."""
import math
import unittest
import pandas as pd

from calculos.fuerzas_nodo import calcular_fuerzas_en_nodos
from calculos.engine import ejecutar_todo


class TestFuerzasPreliminares(unittest.TestCase):
    def tramo(self, az=0, viento=0):
        return pd.DataFrame([{
            "Tramo": "P1 → P2", "Distancia (m)": 40.0,
            "Azimut (°)": az, "w_peso (kN/m)": .008,
            "w_viento (kN/m)": viento,
        }])

    def puntos(self):
        return pd.DataFrame({"Punto": ["P1","P2"],"Poste":["PC-40"]*2,
                             "Espacio Retenida":["SI"]*2})

    def test_peso_no_es_carga_horizontal(self):
        r = calcular_fuerzas_en_nodos(self.tramo(),self.puntos(),
                H_tendido_kN=2,n_fases=3)
        self.assertAlmostEqual(r.iloc[0]["Fx (kN)"],6)
        self.assertAlmostEqual(r.iloc[1]["Fx (kN)"],-6)
        self.assertAlmostEqual(r.iloc[0]["Fy (kN)"],0)
        self.assertAlmostEqual(r.iloc[0]["Fz (kN)"],-.16)
        self.assertAlmostEqual(r.iloc[1]["Fz (kN)"],-.16)

    def test_viento_transversal_en_ambos_apoyos(self):
        r = calcular_fuerzas_en_nodos(self.tramo(viento=.001),
                self.puntos(),H_tendido_kN=2,n_fases=3,azimut_viento_deg=90)
        self.assertAlmostEqual(r.iloc[0]["Fy (kN)"],.06)
        self.assertAlmostEqual(r.iloc[1]["Fy (kN)"],.06)

    def test_viento_paralelo_no_aplica_lateral(self):
        r = calcular_fuerzas_en_nodos(self.tramo(viento=.001),
                self.puntos(),H_tendido_kN=2,n_fases=3,azimut_viento_deg=0)
        self.assertAlmostEqual(r.iloc[0]["Fy (kN)"],0)

    def test_tension_no_puede_ser_cero(self):
        with self.assertRaises(ValueError):
            calcular_fuerzas_en_nodos(self.tramo(),self.puntos(),
                H_tendido_kN=0,n_fases=3)

    def test_engine_no_aprueba_sin_capacidades(self):
        df = pd.DataFrame({"Punto":["P1","P2"],"X":[0,40],"Y":[0,0],
                           "Altitud":[0,0],"Poste":["PC-40"]*2,
                           "Espacio Retenida":["SI"]*2})
        r = ejecutar_todo(df,calibre="2/0 ACSR",n_fases=3,v_viento_ms=0,
            az_viento_deg=0,diametro_m=.01134,H_tendido_kN=2)
        self.assertTrue((r["decision"]["Solución"]=="NO VERIFICABLE").all())
        self.assertLess(r["fuerzas_nodo"]["Fz (kN)"].max(),0)

    def test_altitud_desnivelada_se_rechaza(self):
        df = pd.DataFrame({"Punto":["P1","P2"],"X":[0,40],"Y":[0,0],
                           "Altitud":[0,3],"Poste":["PC-40"]*2,
                           "Espacio Retenida":["SI"]*2})
        with self.assertRaisesRegex(ValueError,"desnivelados"):
            ejecutar_todo(df,calibre="2/0 ACSR",n_fases=3,v_viento_ms=0,
                az_viento_deg=0,diametro_m=.01134,H_tendido_kN=2)


if __name__ == "__main__":
    unittest.main()
