"""Distribución: ensayos de independencia mecánica tras amarre en espigas.

Cargas y límites sintéticos. Un H inicial de instalación compartido NO
implica H de servicio compartida ni redistribución de conductor entre vanos.
"""
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.evaluar_vanos_amarrados_independientes import (
    EvaluadorVanosAmarrados,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    resolver_seccion_regulacion,
)
from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import ConfiguracionBarrido
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria


class VanosFijosDistribucionTest(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0.,40.,125.],
            "Y":[0.,0.,15.],
            "Altitud":[100.,106.,96.],
            "Altura_Amarre_m":[9.5,9.5,9.5],
        })
        xyz=np.column_stack((
            self.puntos[["X","Y"]].to_numpy(float),
            (self.puntos["Altitud"]+self.puntos["Altura_Amarre_m"]).to_numpy(float),
        ))
        self.eval=EvaluadorVanosAmarrados(
            xyz,.0085,.02,15000.,1.91e-5,20.,1.2,1.225,
        )

    def test_tension_inicial_comun_y_servicio_independiente(self):
        h0,t0,c0,res0,_=self.eval.evaluar_estado(4.,20.,0.)
        self.assertEqual(h0,[4.,4.])
        self.assertEqual(res0,[0.,0.])
        h,t,c,res,_=self.eval.evaluar_estado(4.,40.,0.)
        self.assertEqual(len(h),2)
        self.assertGreater(abs(h[0]-h[1]),.01)
        self.assertTrue(all(abs(v)<1e-7 for v in res))
        # Cada vano verifica su propia longitud natural, no una suma libre.
        for i in range(2):
            L0=longitud_natural(c0[i],15000.)
            L1=longitud_natural(c[i],15000.)
            self.assertAlmostEqual(L1,L0*(1+1.91e-5*20),delta=1e-7)

    def test_regulacion_entrega_estados_por_vano_y_barrido_con_hielo(self):
        hip=pd.DataFrame([{
            "Hipotesis":"Frío","Temperatura_C":-5.,
            "Viento_ms":0.,"T_limite_kN":8.,
            "Fuente_limite":"Ensayo sintético",
            "Criterio_diseno":"Solo prueba",
        }])
        config=ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=40.,temperatura_paso_C=20.,
            viento_max_kmh=36.,viento_paso_kmh=18.,
            incluir_hielo=True,hielo_max_mm=5.,hielo_paso_mm=5.,
            temperatura_hielo_C=20.,
        )
        r=resolver_seccion_regulacion(
            self.puntos,hipotesis=hip,
            temperaturas_tabla_C=[20.,40.],
            peso_kN_m=.0085,diametro_m=.02,EA_kN=15000.,
            alpha_por_C=1.91e-5,fuente_material="Sintético",
            temperatura_tendido_C=20.,H_min_kN=1.,H_max_kN=6.,
            configuracion_barrido=config,
        )
        f=r.tabla_tendido
        f40=f[f["Temperatura (°C)"]==40.]
        self.assertEqual(len(f40),2)
        self.assertGreater(abs(f40.iloc[0]["H del estado (kN)"]-
                               f40.iloc[1]["H del estado (kN)"]),.001)
        self.assertTrue((f["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertEqual(len(r.barrido["detalle"]),r.barrido["total_estados"]*2)
        self.assertTrue((r.barrido["detalle"]["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertIn("amarres fijos",r.modelo)

    def test_mismo_vano_conserva_valores_entre_modelos(self):
        from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import EvaluadorEstadosRegulacion
        a=self.eval.xyz[:2]
        a0=EvaluadorEstadosRegulacion(a,.0085,.02,15000.,1.91e-5,20.,1.2,1.225)
        fixed=EvaluadorVanosAmarrados(a,.0085,.02,15000.,1.91e-5,20.,1.2,1.225)
        h1,ten1,_,res1,_=a0.evaluar_estado(4.,40.,10.)
        hs,ten,_,res,_=fixed.evaluar_estado(4.,40.,10.)
        self.assertAlmostEqual(h1,hs[0],delta=1e-7)
        self.assertAlmostEqual(ten1[0],ten[0],delta=1e-7)
        self.assertAlmostEqual(res1,res[0],delta=1e-7)


if __name__=="__main__":
    unittest.main()
