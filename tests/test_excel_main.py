"""Regresión de importación Excel en main."""
from io import BytesIO
import unittest
import pandas as pd
from analisis.io_excel import leer_puntos_excel


class TestExcelMain(unittest.TestCase):
    def leer(self, **extras):
        datos = {"Punto": ["P-01", "P-02"], "X": [400000, 400050],
                 "Y": [1750000, 1750050], **extras}
        buf = BytesIO()
        pd.DataFrame(datos).to_excel(buf, index=False)
        buf.seek(0)
        return leer_puntos_excel(buf)

    def test_faltante_no_significa_si(self):
        self.assertEqual(self.leer()["Espacio Retenida"].tolist(),
                         ["NO VERIFICABLE", "NO VERIFICABLE"])

    def test_celda_vacia(self):
        self.assertEqual(self.leer(**{"Espacio Retenida":["SI", None]})
                         ["Espacio Retenida"].tolist(), ["SI", "NO VERIFICABLE"])

    def test_altitud(self):
        self.assertEqual(self.leer(**{"Altitud (m)": [10, 11]})["Altitud"].tolist(),
                         [10.0, 11.0])

    def test_errata(self):
        with self.assertRaisesRegex(ValueError, "valor no reconocido"):
            self.leer(**{"Espacio Retenida":["SI", "SII"]})

    def test_duplicado(self):
        with self.assertRaisesRegex(ValueError, "identificadores únicos"):
            self.leer(Punto=["P-01", "P-01"])

    def test_vano_nulo(self):
        with self.assertRaisesRegex(ValueError, "longitud cero"):
            self.leer(X=[400000, 400000], Y=[1750000, 1750000])


if __name__ == "__main__":
    unittest.main()
