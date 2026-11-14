"""La plantilla publicada por Streamlit debe importar sin pérdidas."""
from io import BytesIO
import unittest

from entradas.interfaz_red_global import _plantilla
from entradas.importar_red import leer_red_excel


class InterfazRedTest(unittest.TestCase):
    def test_plantilla_contiene_suspension_y_dos_vanos(self):
        red=leer_red_excel(BytesIO(_plantilla()))
        self.assertEqual(len(red.apoyos),3)
        self.assertEqual(len(red.vanos),2)
        self.assertEqual(len(red.secciones()),1)
        self.assertEqual(red.vanos["V1"].conexion_destino,"SUSPENSION")
        self.assertEqual(red.vanos["V2"].conexion_origen,"SUSPENSION")


if __name__=="__main__":
    unittest.main()
