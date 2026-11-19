"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_interfaz_red_calculo.py ===
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


# === Casos conservados de tests/test_interfaz_red_global.py ===
"""La plantilla publicada por Streamlit debe importar sin pérdidas."""
from io import BytesIO
import unittest

from Analisis_mecanico_conductores.interfaz.mostrar_red_global import _plantilla
from Analisis_mecanico_conductores.entradas.importar_red import leer_red_excel


class InterfazRedTest(unittest.TestCase):
    def test_plantilla_contiene_suspension_y_dos_vanos(self):
        red=leer_red_excel(BytesIO(_plantilla()))
        self.assertEqual(len(red.apoyos),3)
        self.assertEqual(len(red.vanos),2)
        self.assertEqual(len(red.secciones()),1)
        self.assertEqual(red.vanos["V1"].conexion_destino,"SUSPENSION")
        self.assertEqual(red.vanos["V2"].conexion_origen,"SUSPENSION")


# === Casos conservados de tests/test_importar_red.py ===
"""Contrato de entrada Excel explícito para redes con varios vanos."""
from io import BytesIO
import unittest
import pandas as pd

from Analisis_mecanico_conductores.entradas.importar_red import leer_red_excel


def libro(continuo=True):
    puntos=pd.DataFrame({
        "Punto":["P1","P2","P3"],
        "X":[0.,40.,80.], "Y":[0.,0.,0.],
        "Altitud":[0.,2.,6.],"Poste":["PC-40"]*3,
        "Fijacion":["FIJO"]*3,
    })
    vanos=pd.DataFrame({
        "Vano":["V1","V2"],"Inicio":["P1","P2"],"Fin":["P2","P3"],
        "Circuito":["C1","C1"],
        "Seccion":["S1","S1" if continuo else "S2"],
        "Conductor":["2/0 ACSR"]*2,
        "Conexion_Inicio":["ANCLAJE","SUSPENSION" if continuo else "ANCLAJE"],
        "Conexion_Fin":["SUSPENSION" if continuo else "ANCLAJE","ANCLAJE"],
        "Altura_Inicio_m":[9.5,9.5],"Altura_Fin_m":[9.5,9.5],
    })
    salida=BytesIO()
    with pd.ExcelWriter(salida,engine="openpyxl") as w:
        puntos.to_excel(w,sheet_name="Puntos",index=False)
        vanos.to_excel(w,sheet_name="Vanos",index=False)
    salida.seek(0)
    return salida


class ImportacionRedTest(unittest.TestCase):
    def test_seccion_montana_con_suspension(self):
        red=leer_red_excel(libro())
        self.assertEqual(len(red.apoyos),3)
        self.assertEqual(len(red.vanos),2)
        self.assertEqual(len(red.secciones()),1)
        self.assertEqual(red.apoyos["P3"].base_m[2],6.)

    def test_dos_secciones_independientes(self):
        red=leer_red_excel(libro(continuo=False))
        self.assertEqual(len(red.secciones()),2)

    def test_no_infiere_apoyo_fijo_si_falta_fijacion(self):
        puntos=pd.DataFrame({
            "Punto":["P1","P2"],"X":[0.,40.],"Y":[0.,0.],
            "Altitud":[0.,0.],"Poste":["PC-40","PC-40"],
        })
        vanos=pd.DataFrame({
            "Vano":["V1"],"Inicio":["P1"],"Fin":["P2"],
            "Circuito":["C1"],"Seccion":["S1"],"Conductor":["2/0 ACSR"],
            "Conexion_Inicio":["ANCLAJE"],"Conexion_Fin":["ANCLAJE"],
            "Altura_Inicio_m":[9.5],"Altura_Fin_m":[9.5],
        })
        archivo=BytesIO()
        with pd.ExcelWriter(archivo,engine="openpyxl") as escritor:
            puntos.to_excel(escritor,sheet_name="Puntos",index=False)
            vanos.to_excel(escritor,sheet_name="Vanos",index=False)
        archivo.seek(0)
        with self.assertRaisesRegex(ValueError,"Fijacion explícita"):
            leer_red_excel(archivo)

    def test_hoja_ausente_no_autocompleta_conexiones(self):
        datos=BytesIO()
        pd.DataFrame({
            "Punto":["P1","P2"],"X":[0,50],"Y":[0,0]
        }).to_excel(datos,index=False)
        datos.seek(0)
        with self.assertRaisesRegex(ValueError,"hojas"):
            leer_red_excel(datos)
