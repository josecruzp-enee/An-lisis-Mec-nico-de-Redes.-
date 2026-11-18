"""Regresión del reporte integrado CFE: debe ser conservador con datos faltantes."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.interfaz.mostrar_verificaciones_cfe_integradas import (
    evaluar_corrida_documentada,
)


class TestVerificacionCFEIntegrada(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3","P4","P5","P6"],
            "X":[0.,50.,115.,205.,325.,475.],
            "Y":[0.]*6,"Altitud":[0.]*6,
            "Altura_Amarre_m":[10.]*6,
        })
        filas=[]
        for a,b,L,f in [
            ("P1","P2",50.,.45),("P2","P3",65.,.76),
            ("P3","P4",90.,1.45),("P4","P5",120.,2.58),
            ("P5","P6",150.,4.05),
        ]:
            for condicion,temperatura,tension in [
                ("Inicial",0.,4.5),("Final",0.,4.0),
                ("Final",16.,3.5),("Final",50.,2.2),
            ]:
                filas.append({
                    "Vano":a+" → "+b,"Luz (m)":L,
                    "Condición":condicion,"Temperatura (°C)":temperatura,
                    "Hipótesis":"Tabla térmica","Flecha (m)":f,
                    "P a 50 °C (m)":900.,"T máx. (kN)":tension,
                })
        self.tabla=pd.DataFrame(filas)

    def test_cinco_vanos_sin_datos_de_fases_ni_obstaculos(self):
        r=evaluar_corrida_documentada(
            self.tabla,self.puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,tipo_superficie="a_lo_largo_caminos_y_zonas_rurales",
        )
        self.assertEqual(len(r),5)
        self.assertTrue((r["Separación entre fases"]=="NO VERIFICABLE").all())
        self.assertTrue((r["Libramiento horizontal edificio"]=="NO VERIFICABLE").all())
        self.assertEqual(r.loc[0,"Libramiento vertical"],"CUMPLE")
        self.assertEqual(r.loc[4,"Libramiento vertical"],"NO CUMPLE")
        self.assertIn("EXCEDE",r.loc[4,"Tabla estructura CFE"])

    def test_fases_separacion_conocida(self):
        r=evaluar_corrida_documentada(
            self.tabla,self.puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,separacion_fases_m=.2,
        )
        self.assertTrue((r["Separación entre fases"]=="NO CUMPLE").all())

    def test_alturas_inexistentes_no_aprueba_libramiento(self):
        puntos=self.puntos.drop(columns=["Altura_Amarre_m"])
        r=evaluar_corrida_documentada(
            self.tabla,puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,tipo_superficie="a_lo_largo_caminos_y_zonas_rurales",
        )
        self.assertTrue((r["Libramiento vertical"]=="NO VERIFICABLE").all())


if __name__=="__main__":
    unittest.main()
