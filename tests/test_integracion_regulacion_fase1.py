"""Prueba extremo a extremo del Excel convencional con tres postes.

Los valores mecánicos y límites son SINTÉTICOS para las pruebas.
Las hojas Materiales e Hipotesis no contienen H prescrita.
"""
import unittest
from io import BytesIO

import pandas as pd

from entradas.io_excel import leer_puntos_excel
from Analisis_mecanico_conductores.entradas.leer_datos_y_calcular_regulacion import (
    plantilla_regulacion, ejecutar_regulacion_fase1
)


def _libro_completo():
    xl=pd.ExcelFile(BytesIO(plantilla_regulacion()))
    hojas={n:xl.parse(n) for n in xl.sheet_names}
    for campo,valor in {
        "EA_kN":15000.,"Alpha_por_C":1.91e-5,
        "Temperatura_tendido_C":20.,
    }.items():
        hojas["Materiales"].loc[0,campo]=valor
    hojas["Materiales"]["Fuente"]="ENSAYO SINTÉTICO"
    for idx,(temp,viento,limite) in enumerate([(-10.,0.,7.),(20.,15.,9.)]):
        for col,val in {
            "Temperatura_C":temp,"Viento_ms":viento,
            "T_limite_kN":limite,
        }.items():
            hojas["Hipotesis"].loc[idx,col]=val
    hojas["Hipotesis"]["Fuente_limite"]="Hipótesis sintéticas de ensayo"
    hojas["Hipotesis"]["Criterio_diseno"]="No es límite normativo real"
    memoria=BytesIO()
    with pd.ExcelWriter(memoria,engine="openpyxl") as wr:
        for nombre,tabla in hojas.items():
            tabla.to_excel(wr,index=False,sheet_name=nombre)
    memoria.seek(0)
    return memoria


class IntegracionRegulacionFase1Test(unittest.TestCase):
    def test_plantilla_no_tiene_H_ni_limites_inventados(self):
        hojas=pd.read_excel(BytesIO(plantilla_regulacion()),sheet_name=None)
        self.assertEqual(set(hojas),{"Puntos","Materiales","Hipotesis"})
        self.assertNotIn("H_tendido_kN",hojas["Materiales"].columns)
        self.assertTrue(hojas["Hipotesis"]["T_limite_kN"].isna().all())
        self.assertEqual(len(hojas["Puntos"]),3)

    def test_tres_postes_generan_H_flechas_y_tabla(self):
        f=_libro_completo()
        puntos=leer_puntos_excel(pd.read_excel(f,sheet_name="Puntos"))
        f.seek(0)
        res=ejecutar_regulacion_fase1(f,puntos,"2/0 ACSR")
        self.assertAlmostEqual(res.vano_regulador_m,45.53,places=6)
        self.assertEqual(len(res.flechas),4)
        self.assertEqual(len(res.tabla_tendido),10)
        self.assertGreater(res.H_tendido_kN,0)
        self.assertLessEqual(res.relacion_maxima,1.00001)

    def test_falta_hoja_mecanica_se_rechaza_sin_solicitar_H(self):
        tabla=pd.DataFrame({
            "Punto":["P1","P2","P3"],"X":[0.,45.53,91.06],
            "Y":[0.,0.,0.],"Poste":["PC-40"]*3,
        })
        salida=BytesIO()
        with pd.ExcelWriter(salida,engine="openpyxl") as w:
            tabla.to_excel(w,index=False,sheet_name="Puntos")
        salida.seek(0)
        with self.assertRaisesRegex(ValueError,"Materiales"):
            ejecutar_regulacion_fase1(salida,tabla,"2/0 ACSR")

    def test_rechazar_retencion_intermedia_declarada(self):
        f=_libro_completo()
        hojas=pd.read_excel(f,sheet_name=None)
        hojas["Vanos"]=pd.DataFrame([
            {"Seccion":"S1","Conexion_Inicio":"ANCLAJE",
             "Conexion_Fin":"ANCLAJE"},
            {"Seccion":"S1","Conexion_Inicio":"SUSPENSION",
             "Conexion_Fin":"ANCLAJE"},
        ])
        f=BytesIO()
        with pd.ExcelWriter(f,engine="openpyxl") as writer:
            for n,tabla in hojas.items():
                tabla.to_excel(writer,sheet_name=n,index=False)
        f.seek(0)
        with self.assertRaisesRegex(ValueError,"retención intermedia"):
            ejecutar_regulacion_fase1(f,hojas["Puntos"],"2/0 ACSR")


if __name__=="__main__":
    unittest.main()
