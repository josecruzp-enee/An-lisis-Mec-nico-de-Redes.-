"""Pruebas de perfiles: geometría exacta y matriz CFE en la memoria PDF."""
import unittest
from io import BytesIO

import pandas as pd
from pypdf import PdfReader

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, EstadoReferenciaCFE, calcular_tablas_inicial_final,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
from Analisis_mecanico_conductores.salidas.PDF.graficos_catenarias_cfe import graficar_perfiles_cfe
from Analisis_mecanico_conductores.salidas.PDF.verificacion_hipotesis_cfe import verificar_cinco_hipotesis
from Analisis_mecanico_conductores.salidas.PDF.generar_pdf_corrida_cfe import generar_pdf_corrida_cfe


class PerfilesCFE(unittest.TestCase):
    def setUp(self):
        self.ini, self.fin = seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        p=self.ini
        self.prop=PropiedadesConductorCFE(
            peso_kN_m=p["peso_kN_m"],diametro_m=p["diametro_m"],
            EA_inicial_kN=p["EA_kN"],EA_final_kN=self.fin["EA_kN"],
            alpha_inicial_por_C=p["alpha_por_C"],
            alpha_final_por_C=self.fin["alpha_por_C"],
            ruptura_kN=p["ruptura_kN"],fuente="CFE 07 FT 01",
        )
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],"X":[0.,50.,115.],"Y":[0.,0.,10.],
            "Altitud":[100.,100.,103.],"Altura_Amarre_m":[9.5,9.5,9.5],
        })
        self.xyz,_=_geometria(self.puntos)
        self.tabla=calcular_tablas_inicial_final(
            self.puntos,self.prop,
            EstadoReferenciaCFE(760.,"CFE"),EstadoReferenciaCFE(660.,"CFE"),
            [0.,16.,20.,50.],
            estados_climaticos=[
                ("CFE viento reducido + hielo",-10.,0.,6.),
                ("CFE viento máximo",0.,120.,0.),
            ],Cd=1.0,
        )
        self.clima={
            "viento_max_kmh":120.,"viento_reducido_kmh":0.,
            "hielo_mm":6.,"rho_kg_m3":1.225,"Cd":1.,
        }
    def test_curvas_reconstruyen_dos_vanos(self):
        salidas=graficar_perfiles_cfe(self.tabla,self.xyz,
                      {"Inicial":self.ini,"Final":self.fin},self.clima)
        self.assertEqual(len(salidas),2)
        for nombre,buf in salidas:
            self.assertTrue(buf.getvalue().startswith(bytes((137,80,78,71))))
    def test_control_cinco_hipotesis(self):
        c=verificar_cinco_hipotesis(
            self.tabla,ruptura_kN=self.ini["ruptura_kN"],
            nombre_conductor="RAVEN",
            viento_max_kmh=120.,viento_reducido_kmh=0.,hielo_mm=6.,
        )
        self.assertEqual(len(c),5)
        self.assertNotIn("SIN EVALUAR",set(c["Estado"]))
    def test_pdf_perfiles_y_cumplimiento(self):
        resumen=pd.DataFrame([
            {"Condición":"Inicial", "H_50_kN":760*self.ini["peso_kN_m"],
             "parametro_P_m":760., "hipotesis_gobernante":"Referencia",
             "relacion_critica":.9},
            {"Condición":"Final","H_50_kN":660*self.fin["peso_kN_m"],
             "parametro_P_m":660., "hipotesis_gobernante":"Referencia",
             "relacion_critica":.95},
        ])
        pdf=generar_pdf_corrida_cfe(
            resumen=resumen,tabla=self.tabla,conductor="1/0 RAVEN",
            fuente_material="CFE 07 FT 01",clima=self.clima,
            propiedades_inicial=self.ini,propiedades_final=self.fin,
            geometria_xyz=self.xyz,
        )
        lector=PdfReader(BytesIO(pdf))
        texto=" ".join(page.extract_text() or "" for page in lector.pages)
        self.assertGreaterEqual(len(lector.pages),5)
        self.assertIn("cinco hipótesis",texto.lower())
        self.assertIn("Perfil de catenarias",texto)
        self.assertIn("P1",texto)
        self.assertIn("P2",texto)


if __name__=="__main__":
    unittest.main()
