"""Validaciones de importación Excel: un faltante nunca equivale a NO."""
import unittest
from io import BytesIO

import pandas as pd

from analisis.io_excel import leer_puntos_excel, _norm_si_no


class TestEntradaExcel(unittest.TestCase):
    def importar(self, espacios=None):
        datos = {'Punto': ['P-01', 'P-02'], 'X': [400000, 400050],
                 'Y': [1750000, 1750050]}
        if espacios is not None:
            datos['Espacio Retenida'] = espacios
        archivo = BytesIO()
        pd.DataFrame(datos).to_excel(archivo, index=False)
        archivo.seek(0)
        return leer_puntos_excel(archivo)

    def test_sin_columna_es_pendiente(self):
        df = self.importar()
        self.assertEqual(df['Espacio Retenida'].tolist(),
                         ['NO VERIFICABLE', 'NO VERIFICABLE'])

    def test_celda_vacia_no_se_convierte_en_no(self):
        df = self.importar(['SI', None])
        self.assertEqual(df['Espacio Retenida'].tolist(),
                         ['SI', 'NO VERIFICABLE'])

    def test_si_y_no_explicitos(self):
        df = self.importar(['SÍ', 'N'])
        self.assertEqual(df['Espacio Retenida'].tolist(), ['SI', 'NO'])

    def test_valores_booleanos_y_pendientes(self):
        self.assertEqual(_norm_si_no(True), 'SI')
        self.assertEqual(_norm_si_no(False), 'NO')
        self.assertEqual(_norm_si_no('PENDIENTE'), 'NO VERIFICABLE')

    def test_errata_no_modifica_la_decision(self):
        with self.assertRaisesRegex(ValueError, 'valor no reconocido'):
            self.importar(['SI', 'SII'])

    def test_identificador_duplicado_se_rechaza(self):
        datos = pd.DataFrame({'Punto':['P-01','P-01'],'X':[1,2],'Y':[1,2]})
        archivo = BytesIO()
        datos.to_excel(archivo, index=False)
        archivo.seek(0)
        with self.assertRaises(ValueError):
            leer_puntos_excel(archivo)


if __name__ == '__main__':
    unittest.main()
