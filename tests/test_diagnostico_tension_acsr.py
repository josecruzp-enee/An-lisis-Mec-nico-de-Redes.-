"""Control de tensión máxima y ruptura, sin aprobar estados con T<RBS."""
import unittest
import pandas as pd

from calculos.diagnostico_tension_acsr import (
    diagnosticar_tensiones, resumen_tensiones,
)


class DiagnosticoTensionesTest(unittest.TestCase):
    def test_conserva_caso_y_muestra_exceso_nominal(self):
        v=pd.DataFrame({
            "Vano":["AB","AB","BC"],
            "Caso":["calor","viento fuerte","viento fuerte"],
            "T máxima (kN)":[5.0,30.0,10.0],
        })
        diag=diagnosticar_tensiones(v,"2/0 ACSR — QUAIL")
        self.assertEqual(len(diag),3)
        self.assertAlmostEqual(
            diag["Carga nominal ruptura (kN)"].iloc[0],
            2398*9.80665/1000,
        )
        self.assertTrue("ALCANZA O SUPERA" in diag.iloc[1]["Estado de ruptura nominal"])
        self.assertTrue("NO ES CUMPLIMIENTO" in diag.iloc[0]["Estado de ruptura nominal"])
        res=resumen_tensiones(diag).set_index("Vano")
        self.assertEqual(res.loc["AB","Caso crítico"],"viento fuerte")

    def test_valores_no_validos_son_error(self):
        v=pd.DataFrame({"Vano":["AB"],"Caso":["C1"],"T máxima (kN)":[float("nan")]})
        with self.assertRaises(ValueError):
            diagnosticar_tensiones(v,"2/0 ACSR — QUAIL")


if __name__=="__main__":
    unittest.main()
