"""Pruebas de selección ENEE y conversión de unidades; sin límites ficticios."""
import unittest
from io import BytesIO

import pandas as pd

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    leer_catalogo_enee, seleccionar_desde_clave_viakon, seleccionar_conductor_enee
)
from Analisis_mecanico_conductores.entradas.leer_datos_y_calcular_regulacion import (
    ejecutar_regulacion_fase1, plantilla_regulacion
)


class PropiedadesENEETest(unittest.TestCase):
    def test_once_conductores_y_seleccion_por_ave(self):
        self.assertEqual(len(leer_catalogo_enee()),11)
        ficha=seleccionar_conductor_enee("2/0","QUAIL","Inicial")
        self.assertEqual(ficha["nombre"],"QUAIL")
        self.assertAlmostEqual(ficha["area_mm2"],78.64)
        self.assertAlmostEqual(ficha["EA_kN"],8000*78.64*9.80665/1000)
        self.assertAlmostEqual(ficha["peso_kN_m"],.2721*9.80665/1000)
        self.assertAlmostEqual(ficha["alpha_por_C"],19.21e-6)
        self.assertAlmostEqual(ficha["ruptura_kN"],2425*9.80665/1000)

    def test_modulo_inicial_distinto_de_final(self):
        inicial=seleccionar_desde_clave_viakon("2/0 ACSR — QUAIL","Inicial")
        final=seleccionar_desde_clave_viakon("2/0 ACSR — QUAIL","Final")
        self.assertAlmostEqual(inicial["EA_kN"]/final["EA_kN"],8000/6500)
        self.assertEqual(final["E_kgf_mm2"],6500)
        self.assertEqual(final["diametro_m"],.01134)
        self.assertIn("Tabla 16",final["fuente"])

    def test_construcciones_no_se_confunden(self):
        a=seleccionar_conductor_enee("477","HAWK")
        b=seleccionar_conductor_enee("477","FLICKER")
        self.assertNotEqual(a["EA_kN"],b["EA_kN"])
        with self.assertRaisesRegex(ValueError,"sin ficha"):
            seleccionar_conductor_enee("266.8","OWL")
        with self.assertRaisesRegex(ValueError,"Inicial o Final"):
            seleccionar_conductor_enee("2/0","QUAIL","inventado")

    def test_plantilla_excel_precarga_enee_sin_limites(self):
        hojas=pd.read_excel(BytesIO(plantilla_regulacion()),sheet_name=None)
        mat=hojas["Materiales"].iloc[0]
        self.assertEqual(mat["Fuente_Propiedades"],"ENEE")
        self.assertEqual(mat["Estado_Elasticidad"],"Final")
        self.assertTrue(pd.isna(mat["EA_kN"]))
        self.assertTrue(hojas["Hipotesis"]["T_limite_kN"].isna().all())

    def test_regulacion_excel_con_enee_y_sin_EA_manual(self):
        hojas=pd.read_excel(BytesIO(plantilla_regulacion()),sheet_name=None)
        hojas["Materiales"].loc[0,"Temperatura_tendido_C"]=20.
        casos=[(-10.,0.,7.),(20.,15.,9.)]
        for indice,(temp,viento,limite) in enumerate(casos):
            hojas["Hipotesis"].loc[indice,"Temperatura_C"]=temp
            hojas["Hipotesis"].loc[indice,"Viento_ms"]=viento
            hojas["Hipotesis"].loc[indice,"T_limite_kN"]=limite
        hojas["Hipotesis"]["Fuente_limite"]="Solo prueba sintética"
        hojas["Hipotesis"]["Criterio_diseno"]="No constituye criterio de diseño"
        buffer=BytesIO()
        with pd.ExcelWriter(buffer,engine="openpyxl") as wr:
            for nombre,tabla in hojas.items():
                tabla.to_excel(wr,sheet_name=nombre,index=False)
        buffer.seek(0)
        resultado=ejecutar_regulacion_fase1(
            buffer,hojas["Puntos"],"2/0 ACSR"
        )
        self.assertGreater(resultado.H_tendido_kN,0)
        self.assertEqual(len(resultado.tabla_tendido),10)
        self.assertLessEqual(resultado.relacion_maxima,1.00001)


if __name__=="__main__":
    unittest.main()
