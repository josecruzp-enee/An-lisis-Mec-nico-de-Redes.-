"""Regresiones independientes de viento en fuste y casos gobernantes."""
import math
import unittest

import numpy as np
import pandas as pd

from calculos.solicitaciones_poste import (
    geometria_fuste, viento_fuste, combinar_solicitaciones_postes,
)
from calculos.envolventes_3d import mayores_por_apoyo, envolventes_apoyos


class TestVientoEnPoste(unittest.TestCase):
    def test_integral_fuste_cilindrico(self):
        g={"Altura expuesta (m)":10.,"Diámetro terreno (m)":.3,
           "Diámetro punta (m)":.3}
        f=viento_fuste(g,20,0,rho_kg_m3=1.2,Cd_poste=1)
        fuerza=.5*1.2*20**2*.3*10/1000
        np.testing.assert_allclose(f,[fuerza,0,0,0,5*fuerza,0],atol=1e-12)

    def test_integral_fuste_conico_vs_integracion_numerica(self):
        g={"Altura expuesta (m)":10.,"Diámetro terreno (m)":.4,
           "Diámetro punta (m)":.2}
        result=viento_fuste(g,30,90,rho_kg_m3=1.225,Cd_poste=1.2)
        z=np.linspace(0,10,100001)
        d=.4+(.2-.4)*z/10
        q=.5*1.225*1.2*30**2*d/1000
        self.assertAlmostEqual(result[1],np.trapezoid(q,z),places=7)
        self.assertAlmostEqual(result[3],-np.trapezoid(z*q,z),places=7)

    def test_simetria_inversion_viento(self):
        g=geometria_fuste("PC-40")
        self.assertIsNotNone(g)
        self.assertAlmostEqual(g["Empotramiento (m)"],
                               .1*12.19+.6096,places=10)
        a=viento_fuste(g,25,0)
        b=viento_fuste(g,25,180)
        np.testing.assert_allclose(a,-b,atol=1e-12)

    def test_acciones_combinadas_y_envolventes(self):
        df=pd.DataFrame({
            "Punto":["P1","P1"],"Caso":["v0","v20"],
            "Viento (m/s)":[0.,20.],"Azimut viento (°)":[0.,0.],
            "Temperatura (°C)":[20.,20.],"H inicial (kN)":[6.,6.],
            "Fx (kN)":[5.,5.],"Fy (kN)":[0.,0.],"Fz (kN)":[-1.,-1.],
            "Mx (kN·m)":[0.,0.],"My (kN·m)":[45.,45.],
            "Mz (kN·m)":[0.,0.],"H resultante (kN)":[5.,5.],
        })
        postes=pd.DataFrame({"Punto":["P1"],"Poste":["PC-40"],
                             "Empotramiento_m":[1.8]})
        combinado=combinar_solicitaciones_postes(df,postes)
        self.assertEqual(combinado.iloc[0]["Fx (kN)"],5.)
        self.assertGreater(combinado.iloc[1]["Fx (kN)"],5.)
        self.assertGreater(combinado.iloc[1]["My (kN·m)"],45.)
        resumen=mayores_por_apoyo(combinado)
        self.assertEqual(resumen.iloc[0]["Caso de H máxima"],"v20")
        self.assertEqual(resumen.iloc[0]["Caso de M máxima"],"v20")
        env=envolventes_apoyos(combinado)
        self.assertEqual(len(env),8)

    def test_sin_geometria_no_aprueba(self):
        df=pd.DataFrame({
            "Punto":["P1"],"Caso":["a"],"Viento (m/s)":[20.],
            "Azimut viento (°)":[90.],"Fx (kN)":[1.],"Fy (kN)":[2.],
            "Fz (kN)":[0.],"Mx (kN·m)":[0.],"My (kN·m)":[0.],
            "Mz (kN·m)":[0.]
        })
        postes=pd.DataFrame({"Punto":["P1"],"Poste":["TIPO SIN FICHA"]})
        result=combinar_solicitaciones_postes(df,postes)
        self.assertTrue(math.isnan(result.iloc[0]["Fx (kN)"]))
        self.assertIn("INCOMPLETO",result.iloc[0]["Estado viento poste"])


if __name__=="__main__":
    unittest.main()
