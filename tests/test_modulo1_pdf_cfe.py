"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_modulo1_pdf_cfe.py ===
"""Regresión módulo 1: memoria CFE y reproducción termoelástica documentada."""
import unittest
from io import BytesIO

import numpy as np
import pandas as pd
from pypdf import PdfReader

from Analisis_mecanico_conductores.salidas.PDF.generar_pdf_corrida_cfe import generar_pdf_corrida_cfe
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
                    self.assertLess(abs(float(row["Residual (m)"])),1e-7)
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

    def test_resumen_ejecutivo_antes_de_anexos(self):
        resumen=pd.DataFrame([
            {"Condición":"Inicial","H_50_kN":2.,"parametro_P_m":800.,
             "hipotesis_gobernante":"Caso A","relacion_critica":.95},
            {"Condición":"Final","H_50_kN":2.,"parametro_P_m":800.,
             "hipotesis_gobernante":"Caso B","relacion_critica":.95},
        ])
        rows=[]
        for condicion in ("Inicial","Final"):
            for temp in (0.,16.,20.,50.):
                rows.append({"Condición":condicion,"Hipótesis":"Tabla térmica",
                             "Temperatura (°C)":temp,"Viento (km/h)":0.,
                             "Hielo (mm)":0.,"Vano":"A → B","Luz (m)":50.,
                             "P a 50 °C (m)":800.,"H (kN)":2.,
                             "T máx. (kN)":2.01,"Flecha (m)":.3,
                             "Lateral (m)":0.,"Residual (m)":1e-9})
        resultado=generar_pdf_corrida_cfe(
            resumen=resumen,tabla=pd.DataFrame(rows),
            conductor="1/0 RAVEN",fuente_material="CFE",
        )
        txt=[" ".join(page.extract_text() or "" for page in PdfReader(BytesIO(resultado)).pages)]
        self.assertIn("RESUMEN EJECUTIVO",txt[0])
        self.assertIn("Resultado general de la línea",txt[0])
        self.assertLess(txt[0].index("Resultado general de la línea"),
                        txt[0].index("Datos generales"))

    def test_pdf_rechaza_casos_sin_resultados(self):
        with self.assertRaises(ValueError):
            generar_pdf_corrida_cfe(
                resumen=pd.DataFrame(),tabla=pd.DataFrame(),
                conductor="RAVEN",fuente_material="CFE",
            )


# === Casos conservados de tests/test_pdf_perfiles_cfe.py ===
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
    def test_un_solo_pdf_para_dos_secciones_con_remate(self):
        """Un documento y diez verificaciones: cinco por sección."""
        from Analisis_mecanico_conductores.salidas.PDF.generar_pdf_corrida_cfe import (
            generar_pdf_corrida_cfe,
        )
        datos=self.tabla.copy()
        datos["Sección"]=datos["Vano"].map({
            "P1 → P2":"S1", "P2 → P3":"S2",
        })
        referencias=pd.DataFrame([
            {
                "Sección":sec, "Condición":cond,
                "Remate inicial":inicio, "Remate final":fin,
                "H_50_kN":2.1 if sec=="S1" else 2.3,
                "parametro_P_m":990. if sec=="S1" else 1080.,
                "hipotesis_gobernante":"CFE H4",
                "relacion_critica":.95,
                "Creep adicional":0.,
                "Diferencia real de acoplamiento H4 (kN)":.1,
                "Diferencia real de acoplamiento H4 (%)":1.5,
            }
            for sec,inicio,fin in [("S1","P1","P2"),("S2","P2","P3")]
            for cond in ["Inicial","Final"]
        ])
        resultado=generar_pdf_corrida_cfe(
            resumen=referencias,tabla=datos,conductor="1/0 RAVEN",
            fuente_material="CFE 07 FT 01",clima=self.clima,
            propiedades_inicial=self.ini,propiedades_final=self.fin,
            geometria_xyz=self.xyz,
        )
        lector=PdfReader(BytesIO(resultado))
        texto=" ".join(p.extract_text() or "" for p in lector.pages)
        self.assertEqual(texto.count("MEMORIA DE CÁLCULO INDEPENDIENTE"),1)
        self.assertIn("Secciones de tendido de la línea",texto)
        self.assertIn("Se analizaron 2 vanos",texto)
        self.assertIn("S1",texto)
        self.assertIn("S2",texto)
        self.assertIn("Control de las cinco hipótesis",texto)
        self.assertIn("Remate inicial",texto)

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


# === Casos conservados de tests/test_memoria_pdf_etapa1.py ===
"""Pruebas PDF: salida legible, trazabilidad y orquestación sin motor."""
from io import BytesIO
from types import SimpleNamespace
import unittest

import pandas as pd
from pypdf import PdfReader

from Analisis_mecanico_conductores.salidas.PDF import generar_memoria_pdf
from Analisis_mecanico_conductores.salidas.PDF.coordinar_pdf import registrar_generador


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

    def test_indice_y_fuentes_tecnicas_en_memoria(self):
        pdf=generar_memoria_pdf(etapas=[1],datos_por_etapa={1:self.datos})
        lector=PdfReader(BytesIO(pdf))
        texto_indice=lector.pages[1].extract_text() or ""
        self.assertIn("ÍNDICE DE CONTENIDO",texto_indice)
        self.assertIn("1. Resumen ejecutivo",texto_indice)
        self.assertIn("3. Metodología y modelo mecánico",texto_indice)
        texto=" ".join(p.extract_text() or "" for p in lector.pages)
        self.assertIn("Nomenclatura y unidades",texto)
        self.assertIn("Fuentes técnicas y trazabilidad",texto)
        self.assertIn("Fuente del criterio: Dato sintético",texto)
        self.assertIn("Referencia técnica",texto)
        # El índice debe incluir al menos un número de página.
        import re
        self.assertRegex(texto_indice, r"[2-9]\s+1[.] Resumen ejecutivo")

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
