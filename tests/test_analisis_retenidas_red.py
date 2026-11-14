"""Contratos y resultados de retenidas XYZ sobre múltiples estados."""
import unittest
import pandas as pd

from calculos.analisis_retenidas_red import (
    leer_configuraciones_retenidas, evaluar_retenidas_en_barrido,
)


class RetenidasRedTest(unittest.TestCase):
    def setUp(self):
        self.tabla=pd.DataFrame({
            "Punto":["P1"],"Retenida":["R1"],
            "Amarre_X_m":[0],"Amarre_Y_m":[0],"Amarre_Z_m":[9],
            "Anclaje_X_m":[-12],"Anclaje_Y_m":[0],"Anclaje_Z_m":[0],
        })
        self.casos=pd.DataFrame({
            "Punto":["P1","P1"],"Caso":["C1","C2"],
            "Fx (kN)":[10,20],"Fy (kN)":[0,0],"Fz (kN)":[-1,-1],
            "Mx (kN·m)":[0,0],"My (kN·m)":[90,180],
            "Mz (kN·m)":[0,0],
        })

    def test_distintas_demandas_no_se_mezclan(self):
        grupos=leer_configuraciones_retenidas(self.tabla)
        estados,detalles=evaluar_retenidas_en_barrido(self.casos,grupos)
        self.assertEqual(len(estados),2)
        self.assertEqual(len(detalles),2)
        self.assertTrue((estados["Equilibrio momento"]=="FACTIBLE").all())
        a,b=detalles["Tensión solicitada (kN)"].tolist()
        self.assertAlmostEqual(b/a,2,places=6)

    def test_no_inventa_limite_de_ruptura(self):
        grupos=leer_configuraciones_retenidas(self.tabla)
        estados,_=evaluar_retenidas_en_barrido(self.casos,grupos)
        self.assertFalse(estados["Capacidades documentadas"].any())
        self.assertTrue(estados["Estado"].str.contains("NO VERIFICABLE").all())

    def test_retenida_sin_poste_no_se_descarta_silenciosamente(self):
        datos=self.tabla.copy()
        datos.loc[0,"Punto"]="P9"
        with self.assertRaisesRegex(ValueError,"no calculados"):
            evaluar_retenidas_en_barrido(
                self.casos,leer_configuraciones_retenidas(datos)
            )


if __name__=="__main__":
    unittest.main()
