"""El resumen de calidad no oculta fallos ni mezcla casos."""
import unittest
import pandas as pd
from calculos.resumen_calidad_bvp import resumen_calidad_bvp


class CalidadBVPTest(unittest.TestCase):
    def test_caso_critico_por_indicador(self):
        t=pd.DataFrame({
            "Vano":["AB","BC"],
            "Caso":["calor","viento"],
            "Residual equilibrio (kN)":[1e-6,2e-6],
            "Residual contorno (m)":[1e-8,5e-9],
            "Residual compatibilidad (m)":[2e-6,1e-6],
            "Error poligonal longitud (m)":[1e-4,2e-4],
            "Residual BVP RMS máximo":[3e-6,5e-6],
        })
        r=resumen_calidad_bvp(t).set_index("Indicador")
        self.assertEqual(r.loc["Residual contorno (m)","Caso crítico del indicador"],"calor")
        self.assertEqual(r.loc["Residual equilibrio (kN)","Caso crítico del indicador"],"viento")
        self.assertEqual(r.loc["Error poligonal longitud (m)","Vano"],"BC")

    def test_residual_no_finito_es_error(self):
        t=pd.DataFrame({
            "Vano":["AB"],"Caso":["C1"],
            **{k:[0.] for k in (
                "Residual equilibrio (kN)",
                "Residual contorno (m)",
                "Residual compatibilidad (m)",
                "Error poligonal longitud (m)",
                "Residual BVP RMS máximo",
            )}
        })
        t.loc[0,"Residual equilibrio (kN)"]=float("nan")
        with self.assertRaisesRegex(ValueError,"Residual inválido"):
            resumen_calidad_bvp(t)


if __name__=="__main__":
    unittest.main()
