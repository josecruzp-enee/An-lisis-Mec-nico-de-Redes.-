"""El Excel habitual debe entregar resultados geométricos inmediatos."""
import unittest

import numpy as np
import pandas as pd

from calculos.resumen_geometrico_regulacion import resumen_geometrico


class ResumenGeométricoTest(unittest.TestCase):
    def test_dos_vanos_del_usuario_no_requieren_hipotesis(self):
        df=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0,-44.45,-54.35],
            "Y":[0,9.89,-34.55],
        })
        r=resumen_geometrico(df)
        self.assertEqual(r["n_vanos"],2)
        self.assertEqual(len(r["tramos"]), 2)
        self.assertAlmostEqual(float(r["tramos"]["Luz horizontal (m)"].iloc[0]), 45.53, delta=.03)
        self.assertNotIn("vano_regulador_m", r)
        self.assertAlmostEqual(r["longitud_total_m"],91.06,delta=.05)
        self.assertEqual(len(r["tramos"]),2)
        self.assertFalse(r["nivelado_confirmado"])

    def test_equal_height_is_explicit(self):
        df=pd.DataFrame({
            "Punto":["A","B","C"],
            "X":[0,40,80],"Y":[0,0,0],
            "Altitud":[1,1,1],"Altura_Amarre_m":[10,10,10]
        })
        r=resumen_geometrico(df)
        self.assertTrue(r["nivelado_confirmado"])
        self.assertTrue((r["tramos"]["Luz horizontal (m)"] == 40).all())

    def test_different_height_not_treated_as_level(self):
        df=pd.DataFrame({
            "Punto":["A","B","C"],
            "X":[0,40,80],"Y":[0,0,0],
            "Altitud":[1,2,1],"Altura_Amarre_m":[10,10,10]
        })
        r=resumen_geometrico(df)
        self.assertFalse(r["nivelado_confirmado"])


if __name__=="__main__":
    unittest.main()
