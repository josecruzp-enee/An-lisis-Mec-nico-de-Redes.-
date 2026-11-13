"""Integración de entrada Excel con el barrido espacial."""
import unittest
import pandas as pd
from entradas.interfaz_barrido_3d import _vanos_desde_excel, _numeros


class TestInterfaz3D(unittest.TestCase):
    def test_desnivel_y_amarres_por_punto(self):
        df = pd.DataFrame({
            "Punto": ["P1", "P2", "P3"],
            "X": [0.,40.,40.], "Y": [0.,0.,40.],
            "Altitud": [0.,2.,5.],
            "Altura_Amarre_m": [9.5,9.2,9.0],
        })
        vanos = _vanos_desde_excel(df)
        self.assertEqual(len(vanos),2)
        self.assertEqual(vanos[0]["base_fin_m"][2],2)
        self.assertEqual(vanos[0]["amarre_fin_m"][2],9.2)
        self.assertEqual(vanos[1]["amarre_fin_m"][2],9.0)

    def test_faltantes_rechazados(self):
        df = pd.DataFrame({"Punto":["P1","P2"],"X":[0,40],"Y":[0,0]})
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            _vanos_desde_excel(df)

    def test_listas_parametricas(self):
        self.assertEqual(_numeros("4, 6, 8","H",positivos=True),[4.,6.,8.])
        with self.assertRaises(ValueError):
            _numeros("0, 6","H",positivos=True)


if __name__ == "__main__":
    unittest.main()
