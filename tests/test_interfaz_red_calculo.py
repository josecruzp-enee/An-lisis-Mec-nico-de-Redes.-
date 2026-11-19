"""Contrato de la plantilla y ejecución real desde Excel de varios vanos.

Solo se evalúan extremos declarados ANCLAJE; sin suplir
propiedades en blanco ni confundir una suspensión con anclaje.
"""
import unittest
from io import BytesIO
import pandas as pd

from Analisis_mecanico_conductores.interfaz.mostrar_red_global import _plantilla_calculo
from Analisis_mecanico_conductores.entradas.importar_red import leer_red_excel
from Analisis_mecanico_conductores.entradas.importar_hipotesis_red import leer_materiales_excel, leer_estados_excel
from Analisis_mecanico_conductores.calculos.hipotesis_red import calcular_hipotesis_red


class PlantillaRedCalculableTest(unittest.TestCase):
    def _libro(self):
        xl=pd.ExcelFile(BytesIO(_plantilla_calculo()))
        return {hoja:xl.parse(hoja) for hoja in xl.sheet_names}

    def test_plantilla_no_inventa_materiales_ni_clima(self):
        h=self._libro()
        self.assertEqual(set(h),{"Puntos","Vanos","Materiales","Hipotesis"})
        self.assertTrue(h["Materiales"]["EA_kN"].isna().all())
        self.assertTrue(h["Hipotesis"]["Temperatura_C"].isna().all())
        with self.assertRaisesRegex(ValueError,"vacíos"):
            leer_materiales_excel(h["Materiales"],{"2/0 ACSR"})

    def test_plantilla_completada_ejecuta_dos_vanos_reales(self):
        h=self._libro()
        for campo,valor in {
            "Peso_kN_m":.008,"Diametro_m":.020,"EA_kN":16000.,
            "Alpha_por_C":1.91e-5,"H_tendido_kN":8.,
            "Temperatura_tendido_C":20.,
        }.items():
            h["Materiales"].loc[0,campo]=valor
        h["Materiales"]["Fuente"]="ENSAYO SINTÉTICO"
        h["Hipotesis"].loc[0,[
            "Temperatura_C","Viento_ms","Azimut_deg",
        ]]=[20.,0.,0.]
        buff=BytesIO()
        with pd.ExcelWriter(buff,engine="openpyxl") as writer:
            for n,tabla in h.items():
                tabla.to_excel(writer,index=False,sheet_name=n)
        buff.seek(0)
        red=leer_red_excel(buff)
        self.assertEqual(len(red.vanos),2)
        self.assertEqual({v.seccion_tendido for v in red.vanos.values()},
                         {"S1","S2"})
        materiales=leer_materiales_excel(h["Materiales"],{"2/0 ACSR"})
        clima=leer_estados_excel(h["Hipotesis"])
        r=calcular_hipotesis_red(red,materiales,clima)
        self.assertEqual(len(r["vanos"]),2)
        self.assertEqual(len(r["apoyos"]),3)
        self.assertTrue((r["vanos"]["T máxima (kN)"]>0).all())


if __name__=="__main__":
    unittest.main()
