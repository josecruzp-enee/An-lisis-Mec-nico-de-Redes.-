"""Ensayos sintéticos de Etapa 1 3D: desnivel y regresión nivelada.

Se verifica el cálculo geométrico respecto a cuerda, sin suponer que el
modelo de regulación representa suspensión real con fricción.
"""
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import (
    calcular_flecha_y_desviacion_3d,
)
from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import (
    ConfiguracionBarrido,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    resolver_seccion_regulacion,
)


def puntos(cotas=(0.,6.,-3.),amarres=(10.,10.,10.)):
    return pd.DataFrame({
        "Punto":["P1","P2","P3"],
        "X":[0.,45.,90.],
        "Y":[0.,0.,0.],
        "Altitud":list(cotas),
        "Altura_Amarre_m":list(amarres),
    })


def entradas(df, barrido=True):
    hip=pd.DataFrame([{
        "Hipotesis":"Caso sintético",
        "Temperatura_C":0.,"Viento_ms":0.,
        "T_limite_kN":12.,
        "Fuente_limite":"Límite de ensayo NO normativo",
        "Criterio_diseno":"Prueba mecánica sintética",
    }])
    return dict(
        puntos=df,hipotesis=hip,temperaturas_tabla_C=[0.,20.,40.],
        peso_kN_m=.0085,diametro_m=.020,EA_kN=15000.,
        alpha_por_C=1.91e-5,fuente_material="Ensayo sintético",
        temperatura_tendido_C=20.,H_min_kN=1.,H_max_kN=5.,
        configuracion_barrido=(ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=40.,
            temperatura_paso_C=20.,
            viento_max_kmh=36.,viento_paso_kmh=18.,
        ) if barrido else None),
    )


class Etapa1Desnivel3DTest(unittest.TestCase):
    def test_flecha_cuerda_desnivelada_no_es_descenso_de_altitud(self):
        a=np.array([0.,0.,100.])
        b=np.array([45.,0.,108.])
        c=resolver_catenaria(a,b,np.array([0.,0.,-.0085]),4.)
        flecha,lateral=calcular_flecha_y_desviacion_3d(c,a,b)
        self.assertGreater(flecha,0.)
        self.assertLess(flecha,.5)
        self.assertAlmostEqual(lateral,0.,delta=1e-8)
        # Con igual geometría y diferencia de cotas invertida,
        # se recupera la misma flecha geométrica respecto a cuerda.
        abajo=np.array([45.,0.,92.])
        c2=resolver_catenaria(a,abajo,np.array([0.,0.,-.0085]),4.)
        self.assertAlmostEqual(
            flecha,calcular_flecha_y_desviacion_3d(c2,a,abajo)[0],delta=.002
        )

    def test_regulacion_con_desnivel_sin_viento_y_con_viento(self):
        r=resolver_seccion_regulacion(**entradas(puntos()))
        self.assertEqual(len(r.hipotesis),1)
        self.assertEqual(len(r.flechas),2)
        self.assertEqual(len(r.tabla_tendido),6)
        self.assertTrue(np.isfinite(r.flechas["Flecha vertical (m)"]).all())
        self.assertTrue((r.flechas["Flecha vertical (m)"]>0).all())
        self.assertTrue((r.hipotesis["Residual compatibilidad (m)"].abs()<1e-7).all())
        detalle=r.barrido["detalle"]
        self.assertEqual(r.barrido["total_estados"],4)
        viento=detalle[detalle["Viento (km/h)"]>0]
        self.assertGreater(viento["Desviación lateral máxima (m)"].max(),0.)
        self.assertTrue((detalle["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertIn("3D",r.modelo)

    def test_alturas_de_amarre_diferentes(self):
        df=puntos(cotas=(0.,0.,0.),amarres=(9.,11.,9.))
        r=resolver_seccion_regulacion(**entradas(df,barrido=False))
        self.assertEqual(len(r.tabla_tendido),6)
        self.assertTrue((r.flechas["Flecha vertical (m)"]>=0).all())

    def test_altitud_parcial_se_rechaza(self):
        df=puntos()
        df.loc[1,"Altitud"]=float("nan")
        with self.assertRaisesRegex(ValueError,"Altitud parcial"):
            resolver_seccion_regulacion(**entradas(df))

    def test_nivelados_preservan_flecha_legacy(self):
        from Analisis_mecanico_conductores.flechas.calcular_flecha_vertical_de_catenaria import (
            calcular_flecha_vertical_de_catenaria,
        )
        a=np.array([0.,0.,10.])
        b=np.array([45.,0.,10.])
        c=resolver_catenaria(a,b,np.array([0.,0.,-.0085]),4.)
        f,_=calcular_flecha_y_desviacion_3d(c,a,b)
        self.assertAlmostEqual(f,calcular_flecha_vertical_de_catenaria(c,a,b),delta=1e-7)


if __name__=="__main__":
    unittest.main()
