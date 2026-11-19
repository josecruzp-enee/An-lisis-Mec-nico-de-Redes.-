"""Contrato de hoja de hipótesis y plantilla del tendido inverso."""
import unittest
from io import BytesIO
import pandas as pd

from Analisis_mecanico_conductores.interfaz.mostrar_tendido_inverso_un_vano import (
    plantilla_tendido, leer_hipotesis_tabla,
    COLUMNAS_HIPOTESIS,
)


class InterfazTendidoInversoTest(unittest.TestCase):
    def test_plantilla_sin_limites_ficticios(self):
        libro=pd.ExcelFile(BytesIO(plantilla_tendido()))
        self.assertEqual(set(libro.sheet_names),{"Puntos","Hipotesis"})
        p=pd.read_excel(libro,sheet_name="Puntos")
        h=pd.read_excel(libro,sheet_name="Hipotesis")
        self.assertEqual(len(p),2)
        self.assertTrue(h["T_limite_kN"].isna().all())
        self.assertEqual(set(COLUMNAS_HIPOTESIS),set(h.columns))
        with self.assertRaisesRegex(ValueError,"incompletos"):
            leer_hipotesis_tabla(h)

    def test_hipotesis_documentada_convertida(self):
        tabla=pd.DataFrame([{
            "Hipotesis":"Frío",
            "Temperatura_C":-10,
            "Viento_ms":0,
            "Azimut_deg":90,
            "T_limite_kN":9.,
            "Fuente_limite":"Documento de diseño verificado",
            "Criterio_diseno":"Estado de frío",
        }])
        r=leer_hipotesis_tabla(tabla)
        self.assertEqual(len(r),1)
        self.assertEqual(r[0].nombre,"Frío")
        self.assertEqual(r[0].tension_limite_kN,9.)


if __name__=="__main__":
    unittest.main()
