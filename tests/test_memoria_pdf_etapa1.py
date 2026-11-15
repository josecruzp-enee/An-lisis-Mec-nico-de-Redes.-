"""Pruebas PDF: salida legible, trazabilidad y orquestación sin motor."""
from io import BytesIO
from types import SimpleNamespace
import unittest

import pandas as pd
from pypdf import PdfReader

from salidas.PDF import generar_memoria_pdf
from salidas.PDF.coordinar_pdf import registrar_generador


class MemoriaPDFTest(unittest.TestCase):
    def setUp(self):
        puntos=pd.DataFrame({
            "Punto":["P1","P2"],"X":[0.,45.53],"Y":[0.,0.],
            "Altitud":[0.,0.],"Altura_Amarre_m":[10.,10.],
        })
        hip=pd.DataFrame([{
            "Hipótesis":"TCD prueba","Temperatura (°C)":15.,
            "Viento (m/s)":0.,"H estado (kN)":3.5,
            "T máxima sección (kN)":3.51,"Límite (kN)":4.75,
            "Relación T/límite":.74,"Fuente límite":"Dato sintético",
        }])
        flechas=pd.DataFrame([{
            "Hipótesis":"TCD prueba","Vano":"P1 → P2","Luz (m)":45.53,
            "Flecha vertical (m)":.2,"T máxima vano (kN)":3.51,
        }])
        tendido=pd.DataFrame([
            {"Temperatura (°C)":t,"Vano":"P1 → P2","H del estado (kN)":h,
             "Flecha vertical (m)":f}
            for t,h,f in [(10.,4.,.17),(20.,3.14,.22),(30.,2.4,.29)]
        ])
        detalle=pd.DataFrame([{
            "Tipo de corrida":"Viento a T de referencia","Vano":"P1 → P2",
            "Temperatura (°C)":20.,"Viento (km/h)":130.,
            "H estado (kN)":5.,"T máxima vano (kN)":5.01,
            "Flecha vertical (m)":.14,"Desviación lateral máxima (m)":.56,
        }])
        gobernantes=detalle.copy()
        gobernantes.insert(0,"Condición gobernante","Máxima tensión")
        self.datos={
            "resultado":SimpleNamespace(
                H_tendido_kN=3.1446,vano_regulador_m=45.53,
                longitud_tramo_m=45.53,caso_gobernante="TCD prueba",
                relacion_maxima=.74,cota_busqueda_activa=False,
                modelo="Sección nivelada: H común",
                hipotesis=hip,flechas=flechas,tabla_tendido=tendido,
                barrido={"detalle":detalle,"gobernantes":gobernantes,
                         "total_estados":2},
            ),
            "puntos":puntos,
            "proyecto":{"nombre":"Proyecto de ensayo","lugar":"Honduras",
                        "calibre":"2/0 ACSR","fecha":"2026-11-15"},
            "propiedades":{"fuente":"ENEE Tabla 16","EA_kN":5012.77,
                            "alpha_por_C":1.921e-5,"peso_kN_m":.002668},
        }

    def test_pdf_etapa1_incluye_resultados_y_anexos(self):
        pdf=generar_memoria_pdf(etapas=[1],datos_por_etapa={1:self.datos})
        self.assertTrue(pdf.startswith(b"%PDF"))
        lector=PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(lector.pages),2)
        contenido=" ".join(p.extract_text() or "" for p in lector.pages)
        for palabra in ("Proyecto de ensayo","3.1446",
                        "Tabla de tendido","Barrido climático",
                        "ENEE Tabla 16","No se emite dictamen"):
            self.assertIn(palabra,contenido)

    def test_faltan_etapas_y_datos_no_se_omiten(self):
        with self.assertRaisesRegex(ValueError,"etapa 2"):
            generar_memoria_pdf(etapas=[1,2],datos_por_etapa={1:self.datos})
        with self.assertRaisesRegex(ValueError,"Faltan datos"):
            generar_memoria_pdf(etapas=[1],datos_por_etapa={})

    def test_coordinador_puede_combinar_generadores_futuros(self):
        from reportlab.pdfgen.canvas import Canvas
        def etapa_99(**kwargs):
            b=BytesIO()
            c=Canvas(b)
            c.drawString(50,750,"Etapa simulada 99")
            c.save()
            return b.getvalue()
        registrar_generador(99,etapa_99)
        uno=generar_memoria_pdf(etapas=[1],datos_por_etapa={1:self.datos})
        ambos=generar_memoria_pdf(
            etapas=[1,99],datos_por_etapa={1:self.datos,99:{}},
        )
        self.assertEqual(
            len(PdfReader(BytesIO(ambos)).pages),
            len(PdfReader(BytesIO(uno)).pages)+1,
        )


if __name__ == "__main__":
    unittest.main()
