"""Las envolventes preservan caso y unidad para el nuevo BVP."""
import unittest
import pandas as pd
from calculos.envolventes_3d import envolventes_vanos


class EnvolventesBVPTest(unittest.TestCase):
    def test_tension_maxima_interior_flecha_y_despeje(self):
        v=pd.DataFrame({
            "Vano":["A-B"]*3,
            "Caso":["C1","C2","C3"],
            "T extremo A (kN)":[8,9,10],
            "T extremo B (kN)":[9,10,10],
            "H resuelta (kN)":[7,8,9],
            "T máxima (kN)":[12,11,10],
            "Flecha vertical respecto cuerda (m)":[.3,.5,.4],
            "Despeje sobre terreno lineal (m)":[9,8,7],
            "Viento (m/s)":[0,10,20],
            "Azimut viento (°)":[0,90,180],
            "Temperatura (°C)":[20,30,40],
            "H inicial (kN)":[7,7,7],
        })
        resultado=envolventes_vanos(v).set_index("Magnitud")
        self.assertEqual(resultado.loc["T máxima (kN)","Caso gobernante"],"C1")
        self.assertEqual(resultado.loc["Flecha vertical respecto cuerda (m)","Caso gobernante"],"C2")
        self.assertEqual(resultado.loc["Despeje sobre terreno lineal (m)","Caso gobernante"],"C3")
        self.assertEqual(resultado.loc["Despeje sobre terreno lineal (m)","Unidad"],"m")
        self.assertIn("NO VERIFICADO",resultado.loc["Despeje sobre terreno lineal (m)","Estado"])


if __name__=="__main__":
    unittest.main()
