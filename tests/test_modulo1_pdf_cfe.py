"""Regresión módulo 1: memoria CFE y reproducción termoelástica documentada."""
import unittest
from io import BytesIO

import numpy as np
import pandas as pd
from pypdf import PdfReader

from salidas.PDF.generar_pdf_corrida_cfe import generar_pdf_corrida_cfe
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, EstadoReferenciaCFE, calcular_tablas_inicial_final,
)

# CFE 07 FT 10, filas seleccionadas; P es condición documentada, NO resultado
# de un diseño independiente. Compara la respuesta térmica del motor.
DATOS = {
    50: (760, 660, 353, 329, 164, 143),
    60: (790, 705, 342, 319, 171, 152),
    75: (920, 835, 363, 343, 199, 180),
    90: (980, 905, 360, 341, 212, 196),
    109: (1025, 965, 348, 332, 222, 209),
    125: (1050, 1005, 335, 324, 227, 217),
    150: (1090, 1055, 322, 314, 236, 228),
}


class ModuloUnoPdfYCatenaria(unittest.TestCase):
    def test_tablas_7_claros_cfe_tension_termoelastica(self):
        ini, fin = seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        props = PropiedadesConductorCFE(
            peso_kN_m=ini["peso_kN_m"],
            diametro_m=ini["diametro_m"],
            EA_inicial_kN=ini["EA_kN"],
            EA_final_kN=fin["EA_kN"],
            alpha_inicial_por_C=ini["alpha_por_C"],
            alpha_final_por_C=fin["alpha_por_C"],
            ruptura_kN=ini["ruptura_kN"],
            fuente="CFE 07 FT 01",
        )
        for luz, (pini,pfin,i20,f20,i50,f50) in DATOS.items():
            with self.subTest(luz=luz):
                puntos = pd.DataFrame({
                    "Punto": ["A","B"], "X": [0.,float(luz)], "Y": [0.,0.],
                    "Altitud": [100.,100.], "Altura_Amarre_m": [9.5,9.5],
                })
                tabla = calcular_tablas_inicial_final(
                    puntos, props, EstadoReferenciaCFE(pini,"CFE"),
                    EstadoReferenciaCFE(pfin,"CFE"), [20.,50.], Cd=1.,
                )
                self.assertEqual(len(tabla),4)
                for estado, t, objetivo in [
                    ("Inicial",20.,i20),("Final",20.,f20),
                    ("Inicial",50.,i50),("Final",50.,f50),
                ]:
                    row=tabla[(tabla["Condición"]==estado) &
                              (tabla["Temperatura (°C)"]==t)].iloc[0]
                    calculada=float(row["H (kN)"])*1000/9.80665
                    self.assertLess(abs(calculada-objetivo)/objetivo, 0.015)
                    self.assertLess(abs(float(row["Residual (m)"]),1e-7)
                    self.assertGreater(float(row["Flecha (m)"]),0.)

    def test_pdf_independiente_sin_recalcular(self):
        resumen=pd.DataFrame([
            {"Condición":"Inicial","H_50_kN":1.6,"parametro_P_m":755.,
             "hipotesis_gobernante":"Caso A","relacion_critica":.95,
             "tension_maxima_gobernante_kN":5.,"residuo_maximo_gobernante_m":1e-9},
            {"Condición":"Final","H_50_kN":1.4,"parametro_P_m":660.,
             "hipotesis_gobernante":"Caso B","relacion_critica":.97,
             "tension_maxima_gobernante_kN":4.9,"residuo_maximo_gobernante_m":2e-9},
        ])
        filas=[]
        for condicion in ("Inicial","Final"):
            for t in (-10.,0.,20.,50.):
                filas.append({
                    "Condición":condicion,"Hipótesis":"Tabla térmica",
                    "Temperatura (°C)":t,"Viento (km/h)":0.,
                    "Hielo (mm)":0.,"Vano":"A → B","Luz (m)":50.,
                    "P a 50 °C (m)":760.,"H (kN)":4.5,
                    "T máx. (kN)":4.51,"Flecha (m)":.2,
                    "Lateral (m)":0.,"Residual (m)":1e-9,
                })
        tabla=pd.DataFrame(filas)
        original=tabla.copy(deep=True)
        pdf=generar_pdf_corrida_cfe(
            resumen=resumen,tabla=tabla,conductor="1/0 RAVEN",
            fuente_material="CFE 07 FT 01",
            clima={"viento_max_kmh":120,"viento_reducido_kmh":0,
                   "hielo_mm":0,"rho_kg_m3":1.225},
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(PdfReader(BytesIO(pdf)).pages),0)
        pd.testing.assert_frame_equal(tabla,original)

    def test_pdf_rechaza_casos_sin_resultados(self):
        with self.assertRaises(ValueError):
            generar_pdf_corrida_cfe(
                resumen=pd.DataFrame(),tabla=pd.DataFrame(),
                conductor="RAVEN",fuente_material="CFE",
            )


if __name__=="__main__":
    unittest.main()
