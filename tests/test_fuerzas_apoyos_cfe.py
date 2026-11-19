"""Fuerzas de reacción exactas en extremos y equilibrio de los apoyos."""
import unittest
import numpy as np
import pandas as pd
from Analisis_mecanico_conductores.salidas.PDF.fuerzas_apoyos_cfe import (
    calcular_fuerzas_por_apoyo,grafico_red_y_fuerzas,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
)
from Analisis_mecanico_conductores.motor_conductores import ejecutar_motor_conductores


class FuerzasApoyoCFETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],"X":[0.,120.,270.],
            "Y":[0.,0.,0.],"Altitud":[0.,0.,0.],
            "Altura_Amarre_m":[9.5,9.5,9.5],
            "Remate":["SI","SI","SI"],
        })
        ini,fin=seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        cls.props={"Inicial":ini,"Final":fin}
        cls.clima=dict(viento_max_kmh=120.,viento_reducido_kmh=109.,
                        hielo_mm=6.,Cd=1.,rho_kg_m3=1.225,
                        densidad_hielo_kg_m3=913.,
                        modelo_presion_cfe=True)
        cls.resumen,cls.tabla=ejecutar_motor_conductores(
            cls.puntos,ini,fin,viento_max_kmh=120.,
            viento_reducido_kmh=109.,hielo_mm=6.,
            temperaturas_C=[0.,16.,20.,50.],
            incluir_ensayo_viento_16C=True,
        )

    def test_cinco_hipotesis_tres_apoyos(self):
        detalle,suma,envolvente=calcular_fuerzas_por_apoyo(
            self.tabla,self.puntos,self.props,self.clima)
        self.assertEqual(len(detalle),20)
        self.assertEqual(len(suma),15)
        self.assertEqual(len(envolvente),3)
        self.assertTrue(np.isfinite(suma["F resultante (kN)"]).all())
        for caso in ["H1","H2","H3","H4","H5"]:
            p2=detalle[(detalle["Hipótesis"]==caso)&(detalle["Apoyo"]=="P2")]
            self.assertEqual(len(p2),2)
            f=p2[["Fx (kN)","Fy (kN)","Fz (kN)"]].sum().to_numpy(float)
            total=suma[(suma["Hipótesis"]==caso)&(suma["Apoyo"]=="P2")]
            np.testing.assert_allclose(total[["Fx (kN)","Fy (kN)","Fz (kN)"]].iloc[0],f,atol=1e-10)
        self.assertLess(abs(float(suma[(suma["Hipótesis"]=="H1")&
                           (suma["Apoyo"]=="P2")]["Fx (kN)"].iloc[0])),2.)
        grafico=grafico_red_y_fuerzas(self.puntos,detalle,suma)
        self.assertTrue(grafico.getvalue().startswith(bytes([137,80,78,71])))


    def test_pdf_integrado_incluye_red_y_esfuerzos(self):
        from io import BytesIO
        from pypdf import PdfReader
        from Analisis_mecanico_conductores.salidas.PDF.generar_pdf_corrida_cfe import (
            generar_pdf_corrida_cfe,
        )
        from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
        xyz,_=_geometria(self.puntos)
        datos=generar_pdf_corrida_cfe(
            resumen=self.resumen,tabla=self.tabla,
            conductor="1/0 RAVEN",fuente_material="CFE 07 FT 01",
            clima=self.clima,
            propiedades_inicial=self.props["Inicial"],
            propiedades_final=self.props["Final"],
            geometria_xyz=xyz,puntos_apoyos=self.puntos,
        )
        self.assertTrue(datos.startswith(b"%PDF"))
        lector=PdfReader(BytesIO(datos))
        texto=" ".join(page.extract_text() or "" for page in lector.pages)
        self.assertIn("Red completa",texto)
        self.assertIn("Envolvente por apoyo",texto)
        self.assertIn("Fx (kN)",texto)
        self.assertIn("Fy (kN)",texto)
        self.assertIn("Fz (kN)",texto)
        self.assertIn("S1",texto)
        self.assertIn("S2",texto)
        paginas=[p.extract_text() or "" for p in lector.pages]
        self.assertIn("RESUMEN EJECUTIVO",paginas[0])
        self.assertIn("Red completa",paginas[1])
        self.assertIn("Envolvente por apoyo",paginas[1],
                      "El plano y la tabla de resultantes deben compartir página")
        self.assertIn("Control de las cinco hipótesis",paginas[2],
                      "Las verificaciones CFE deben ser visibles en la tercera página")
        self.assertIn("Anexo A",texto)
        self.assertNotIn("Anexo A", " ".join(paginas[:3]))

    def test_fuerzas_requieren_tensiones_reproducibles(self):
        tabla=self.tabla.copy()
        tabla.loc[0,"T máx. (kN)"]+=.1
        with self.assertRaisesRegex(ValueError,"tensión de extremos no coincide"):
            calcular_fuerzas_por_apoyo(tabla,self.puntos,self.props,self.clima)
