"""Regresión de coordinación entre estados, catenaria y tablas.

Todos los parámetros son sintéticos y NO justifican una instalación.
Las magnitudes y la interpretación convencional se mantienen
independientes del módulo que genera las tablas CSV.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import (
    EvaluadorEstadosRegulacion,
    calcular_cargas_transversales_por_vano,
)
from Analisis_mecanico_conductores.tension_tendido.construir_resultados_regulacion import (
    construir_tablas_de_hipotesis,
    construir_tabla_de_tendido,
)


class EstadosYTablasTest(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0.,45.53,91.06],"Y":[0.,0.,0.],
        })
        self.xyz=np.array([[0,0,10],[45.53,0,10],[91.06,0,10]],dtype=float)
        self.evaluador=EvaluadorEstadosRegulacion(
            self.xyz,.0085,.02,15000.,1.91e-5,20.,1.2,1.225
        )

    def test_referencia_sin_viento_mantiene_H(self):
        H,tensiones,cables,residual,viento=self.evaluador.evaluar_estado(5.,20.,0.)
        self.assertEqual(H,5.)
        self.assertEqual(residual,0.)
        self.assertEqual(viento,0.)
        self.assertEqual(len(tensiones),2)
        self.assertTrue(all(t>=H for t in tensiones))

    def test_viento_convencional_usa_carga_transversal_y_conserva_peso(self):
        cargas,viento=calcular_cargas_transversales_por_vano(
            self.xyz,.0085,.02,15.,1.2,1.225
        )
        self.assertEqual(len(cargas),2)
        self.assertAlmostEqual(viento,.5*1.225*1.2*.02*15**2/1000)
        np.testing.assert_allclose(cargas[0][0],[0,0,-.0085],atol=1e-12)
        np.testing.assert_allclose(cargas[0][1],[0,viento,-.0085],atol=1e-12)

    def test_tablas_conservan_unidades_columnas_y_flechas_individuales(self):
        hip=pd.DataFrame([{
            "Hipotesis":"Referencia","Temperatura_C":20.,
            "Viento_ms":0.,"T_limite_kN":8.,
            "Fuente_limite":"Ensayo sintético",
            "Criterio_diseno":"Caso de prueba",
        }])
        tabla_h,tabla_f=construir_tablas_de_hipotesis(
            self.puntos,self.xyz,np.array([45.53,45.53]),
            hip,5.,self.evaluador.evaluar_estado
        )
        tabla_t=construir_tabla_de_tendido(
            self.puntos,self.xyz,[0.,20.,40.],5.,
            self.evaluador.evaluar_estado
        )
        self.assertEqual(len(tabla_h),1)
        self.assertEqual(len(tabla_f),2)
        self.assertEqual(len(tabla_t),6)
        self.assertAlmostEqual(tabla_h.iloc[0]["H estado (kN)"],5.)
        self.assertTrue((tabla_f["Flecha vertical (m)"]>0).all())
        self.assertEqual(tabla_f["Vano"].tolist(),["P1 → P2","P2 → P3"])
        self.assertEqual(tabla_t["Temperatura (°C)"].tolist(),
                         [0.,0.,20.,20.,40.,40.])
        self.assertTrue((tabla_t["Residual compatibilidad (m)"].abs()<1e-7).all())


if __name__=="__main__":
    unittest.main()
