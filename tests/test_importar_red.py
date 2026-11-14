"""Contrato de entrada Excel explícito para redes con varios vanos."""
from io import BytesIO
import unittest
import pandas as pd

from entradas.importar_red import leer_red_excel


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


if __name__=="__main__":
    unittest.main()
