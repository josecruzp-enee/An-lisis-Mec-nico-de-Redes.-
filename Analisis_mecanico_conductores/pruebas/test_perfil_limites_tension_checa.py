"""Pruebas del perfil Checa ACSR; criterio de referencia, NO norma ENEE."""
import unittest
from io import BytesIO

import pandas as pd

from Analisis_mecanico_conductores.verificaciones.perfil_limites_tension_checa import (
    construir_hipotesis_checa_acsr,
)
from Analisis_mecanico_conductores.entradas.leer_datos_y_calcular_regulacion import (
    plantilla_regulacion,ejecutar_regulacion_fase1,
)


class PerfilTensionChecaTest(unittest.TestCase):
    def test_limites_y_condiciones_Checa(self):
        hip=construir_hipotesis_checa_acsr(20.)
        self.assertEqual(len(hip),2)
        self.assertEqual(hip["Temperatura_C"].tolist(),[15.,-5.])
        self.assertEqual(hip["Viento_ms"].tolist(),[0.,0.])
        self.assertAlmostEqual(hip.loc[0,"T_limite_kN"],4.)
        self.assertAlmostEqual(hip.loc[1,"T_limite_kN"],4.5)
        self.assertTrue(hip["Fuente_limite"].str.contains("Checa").all())
        self.assertTrue(hip["Fuente_limite"].str.contains("NO norma ENEE").all())

    def test_rechaza_ruptura_invalida(self):
        for valor in (0.,-1.,float("nan"),float("inf")):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    construir_hipotesis_checa_acsr(valor)

    def test_excel_activa_perfil_y_calcula_sin_limites_manuales(self):
        hojas=pd.read_excel(BytesIO(plantilla_regulacion()),sheet_name=None)
        materiales=hojas["Materiales"]
        materiales.loc[0,"Temperatura_tendido_C"]=20.
        materiales.loc[0,"Perfil_Tension"]="Checa"
        self.assertTrue(hojas["Hipotesis"]["T_limite_kN"].isna().all())
        salida=BytesIO()
        with pd.ExcelWriter(salida,engine="openpyxl") as wr:
            for nombre,tabla in hojas.items():
                tabla.to_excel(wr,sheet_name=nombre,index=False)
        salida.seek(0)
        res=ejecutar_regulacion_fase1(salida,hojas["Puntos"],"2/0 ACSR")
        self.assertEqual(res.hipotesis["Hipótesis"].tolist(),["TCD — Checa","THF — Checa"])
        rotura_kN=2425*9.80665/1000
        self.assertAlmostEqual(res.hipotesis.iloc[0]["Límite (kN)"],.20*rotura_kN)
        self.assertAlmostEqual(res.hipotesis.iloc[1]["Límite (kN)"],.225*rotura_kN)
        self.assertLessEqual(res.relacion_maxima,1.00001)


if __name__=="__main__":
    unittest.main()
