"""Prueba funcional: entrada ENEE+Checa, una llamada => H, flechas y barridos.

Datos geométricos sintéticos para validar software; no certifica obra.
"""
from io import BytesIO
import unittest

import pandas as pd

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.entradas.leer_datos_y_calcular_regulacion import (
    ejecutar_regulacion_fase1, plantilla_regulacion,
)
from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import (
    ConfiguracionBarrido,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_analisis_integral_de_conductores import (
    ejecutar_analisis_integral,
)


class EjecucionIntegralEtapa1(unittest.TestCase):
    def setUp(self):
        self.hojas=pd.read_excel(
            BytesIO(plantilla_regulacion()),sheet_name=None
        )
        self.config=ConfiguracionBarrido(
            temperatura_min_C=19.,
            temperatura_max_C=21.,
            temperatura_paso_C=1.,
            viento_max_kmh=36.,
            viento_paso_kmh=18.,
        )

    def test_plantilla_lista_para_ejecutar_sin_datos_mecanicos_manuales(self):
        material=self.hojas["Materiales"].iloc[0]
        self.assertEqual(material["Fuente_Propiedades"],"ENEE")
        self.assertEqual(material["Perfil_Tension"],"Checa")
        self.assertEqual(material["Temperatura_tendido_C"],20.)
        self.assertTrue(pd.isna(material["EA_kN"]))
        self.assertTrue(self.hojas["Hipotesis"]["T_limite_kN"].isna().all())
        mem=BytesIO()
        with pd.ExcelWriter(mem,engine="openpyxl") as wr:
            for nombre,tabla in self.hojas.items():
                tabla.to_excel(wr,sheet_name=nombre,index=False)
        mem.seek(0)
        res=ejecutar_regulacion_fase1(
            mem,self.hojas["Puntos"],"2/0 ACSR",
            configuracion_barrido=self.config,
        )
        self._comprobar_salida(res)

    def test_mismo_resultado_por_punto_unico_de_ejecucion(self):
        ficha=seleccionar_conductor_enee("2/0","QUAIL","Final")
        propiedades={
            "peso_kN_m":ficha["peso_kN_m"],
            "diametro_m":ficha["diametro_m"],
            "EA_kN":ficha["EA_kN"],
            "alpha_por_C":ficha["alpha_por_C"],
            "ruptura_kN":ficha["ruptura_kN"],
            "fuente":ficha["fuente"],
        }
        res=ejecutar_analisis_integral(
            self.hojas["Puntos"],
            propiedades=propiedades,
            temperatura_tendido_C=20.,
            perfil_tension="Checa",
            configuracion_barrido=self.config,
        )
        self._comprobar_salida(res)
        self.assertIn("Checa",res.caso_gobernante)

    def _comprobar_salida(self,res):
        self.assertGreater(res.H_tendido_kN,0)
        self.assertLessEqual(res.relacion_maxima,1.00001)
        self.assertEqual(len(res.hipotesis),2)
        self.assertEqual(len(res.flechas),4)
        self.assertEqual(len(res.tabla_tendido),10)
        self.assertIsNotNone(res.barrido)
        self.assertEqual(res.barrido["total_estados"],5)
        self.assertEqual(len(res.barrido["detalle"]),10)
        self.assertEqual(len(res.barrido["gobernantes"]),5)
        self.assertTrue(
            (res.barrido["detalle"]["Residual compatibilidad (m)"].abs()<1e-6).all()
        )


if __name__=="__main__":
    unittest.main()
