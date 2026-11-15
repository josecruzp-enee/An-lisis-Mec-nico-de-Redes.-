"""Barridos climáticos configurables; ensayos SINTÉTICOS, no normativos."""
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import (
    ConfiguracionBarrido, _casos_climaticos, _peso_hielo_kN_m,
    ejecutar_barrido_climatico, comparar_tensiones_hipotesis_y_barrido,
)
from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    EvaluadorEstadosRegulacion,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    resolver_seccion_regulacion,
)


class BarridoClimaticoTest(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2"],"X":[0.,45.53],"Y":[0.,0.],
            "Altitud":[0.,0.],"Altura_Amarre_m":[10.,10.],
        })
        self.evaluador=EvaluadorEstadosRegulacion(
            np.array([[0.,0.,10.],[45.53,0.,10.]]),
            .0085,.020,15000.,1.91e-5,20.,1.2,1.225
        )

    def test_configuracion_por_defecto_y_conversion_velocidades(self):
        casos=_casos_climaticos(ConfiguracionBarrido(),20.)
        self.assertEqual(len(casos),77)  # 51 T + 27 V, menos caso T=20,V=0
        self.assertIn((50.,0.,0.,"Temperatura, sin viento"),casos)
        self.assertIn((20.,130.,0.,"Viento a T de referencia"),casos)

    def test_independientes_matriz_e_hielo(self):
        compacta=dict(
            temperatura_min_C=19.,temperatura_max_C=21.,
            temperatura_paso_C=1.,viento_max_kmh=36.,
            viento_paso_kmh=18.,
        )
        independiente=_casos_climaticos(ConfiguracionBarrido(**compacta),20.)
        matriz=_casos_climaticos(ConfiguracionBarrido(
            **compacta,modo_matriz_completa=True
        ),20.)
        self.assertEqual(len(independiente),5)
        self.assertEqual(len(matriz),9)
        con_hielo=ConfiguracionBarrido(
            **compacta,incluir_hielo=True,hielo_max_mm=10.,
            hielo_paso_mm=5.,combinar_hielo_viento=True
        )
        casos=_casos_climaticos(con_hielo,20.)
        self.assertEqual(len(casos),9)
        self.assertIn((0.,36.,10.,"Hielo+viento (exploratoria)"),casos)

    def test_barrido_gobernantes_y_lateral_por_viento(self):
        config=ConfiguracionBarrido(
            temperatura_min_C=19.,temperatura_max_C=21.,
            temperatura_paso_C=1.,viento_max_kmh=36.,
            viento_paso_kmh=18.,
        )
        resultado=ejecutar_barrido_climatico(
            self.puntos,5.,self.evaluador,config
        )
        detalle=resultado["detalle"]
        self.assertEqual(resultado["total_estados"],5)
        self.assertEqual(len(detalle),5)
        self.assertEqual(len(resultado["gobernantes"]),5)
        self.assertEqual(set(detalle["Viento (km/h)"]),{0.,18.,36.})
        self.assertAlmostEqual(
            detalle.loc[detalle["Viento (km/h)"]==36.,
                        "Viento (m/s)"].iloc[0],10.
        )
        self.assertGreater(
            detalle.loc[detalle["Viento (km/h)"]==36.,
                        "Desviación lateral máxima (m)"].iloc[0],0
        )
        self.assertTrue((detalle["Flecha vertical (m)"]>0).all())
        self.assertTrue((detalle["Residual compatibilidad (m)"].abs()<1e-6).all())

    def test_manguito_incrementa_peso_y_desplazamiento_en_caso_seco(self):
        config=ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=20.,
            viento_max_kmh=36.,viento_paso_kmh=36.,
            incluir_hielo=True,hielo_max_mm=5.,hielo_paso_mm=5.,
            temperatura_hielo_C=20.,
        )
        resultado=ejecutar_barrido_climatico(
            self.puntos,5.,self.evaluador,config
        )
        tabla=resultado["detalle"]
        seco=tabla[(tabla["Hielo radial (mm)"]==0)&
                   (tabla["Viento (km/h)"]==0)].iloc[0]
        hielo=tabla[tabla["Hielo radial (mm)"]==5.].iloc[0]
        self.assertGreater(_peso_hielo_kN_m(.02,5.,900.),0)
        self.assertGreater(hielo["T máxima vano (kN)"],seco["T máxima vano (kN)"])
        self.assertEqual(hielo["Viento (km/h)"],0.)

    def test_regulacion_entrega_barrido_sin_cambiar_hipotesis(self):
        hip=pd.DataFrame([{
            "Hipotesis":"referencia","Temperatura_C":20.,"Viento_ms":0.,
            "T_limite_kN":9.,"Fuente_limite":"Ensayo sintético",
            "Criterio_diseno":"No válido para obra",
        }])
        config=ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=20.,
            viento_max_kmh=0.,viento_paso_kmh=5.,
        )
        args=dict(
            puntos=self.puntos,hipotesis=hip,temperaturas_tabla_C=[20.],
            peso_kN_m=.0085,diametro_m=.02,EA_kN=15000.,
            alpha_por_C=1.91e-5,fuente_material="Sintético",
            temperatura_tendido_C=20.,H_min_kN=1.,H_max_kN=6.,
        )
        normal=resolver_seccion_regulacion(**args)
        nuevo=resolver_seccion_regulacion(**args,configuracion_barrido=config)
        self.assertAlmostEqual(normal.H_tendido_kN,nuevo.H_tendido_kN)
        self.assertIsNone(normal.barrido)
        self.assertEqual(nuevo.barrido["total_estados"],1)
        self.assertEqual(len(nuevo.barrido["gobernantes"]),5)

    def test_resumen_gobernante_muestra_la_magnitud_correcta(self):
        config=ConfiguracionBarrido(
            temperatura_min_C=19.,temperatura_max_C=21.,
            viento_max_kmh=36.,viento_paso_kmh=18.,
        )
        r=ejecutar_barrido_climatico(self.puntos,5.,self.evaluador,config)
        tabla=r["gobernantes"]
        for _,fila in tabla.iterrows():
            self.assertAlmostEqual(
                fila["Valor gobernante"],
                fila[fila["Magnitud gobernante"]],
            )
        lateral=tabla[tabla["Condición gobernante"]==
                      "Máxima desviación lateral"].iloc[0]
        self.assertEqual(lateral["Magnitud gobernante"],
                         "Desviación lateral máxima (m)")
        self.assertGreater(lateral["Valor gobernante"],0.)

    def test_comparacion_distingue_diseno_barrido_y_maximo_global(self):
        config=ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=20.,
            viento_max_kmh=0.,viento_paso_kmh=5.,
        )
        r=ejecutar_barrido_climatico(self.puntos,5.,self.evaluador,config)
        hip=pd.DataFrame([{
            "Hipótesis":"Frío fuera del barrido",
            "Temperatura (°C)":-5.,"Viento (m/s)":0.,
            "T máxima sección (kN)":8.,
        }])
        tabla=comparar_tensiones_hipotesis_y_barrido(hip,r)
        self.assertEqual(len(tabla),3)
        self.assertEqual(tabla.iloc[0]["Ámbito"],"Hipótesis de diseño")
        self.assertEqual(tabla.iloc[1]["Ámbito"],"Barrido exploratorio")
        self.assertEqual(tabla.iloc[2]["Ámbito"],"Máximo global evaluado")
        self.assertEqual(tabla.iloc[2]["T máxima (kN)"],8.)
        self.assertEqual(tabla.iloc[2]["Temperatura (°C)"],-5.)

    def test_rechaza_intervalos_no_divisibles(self):
        config=ConfiguracionBarrido(
            temperatura_min_C=0.,temperatura_max_C=50.,
            temperatura_paso_C=3.,
        )
        with self.assertRaisesRegex(ValueError,"divisible"):
            _casos_climaticos(config,20.)


if __name__=="__main__":
    unittest.main()
