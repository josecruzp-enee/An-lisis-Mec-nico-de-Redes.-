"""Validaciones de regresión: Checa y dos elasticidades por vano.

No se cargan tablas de flecha ENEE como entradas al cálculo.
"""
import unittest
import pandas as pd
import numpy as np

from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
    seleccionar_conductor_enee,
)
from Analisis_mecanico_conductores.tension_tendido.corridas_por_vano_checa import (
    ejecutar_corridas_por_vano_checa,
    _referencia_final_mismo_largo,
)
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural


class CorridasVanosChecaTest(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0.,50.,125.],"Y":[0.,0.,0.],
            "Altitud":[100.,100.,100.],
            "Altura_Amarre_m":[9.5,9.5,9.5],
        })
        self.ini=seleccionar_conductor_enee("1/0","RAVEN","Inicial")
        self.fin=seleccionar_conductor_enee("1/0","RAVEN","Final")

    def test_conservacion_longitud_natural_sin_creep(self):
        a=np.array([0.,0.,0.]);b=np.array([50.,0.,0.])
        p=self.ini["peso_kN_m"];q=np.array([0.,0.,-p])
        h0=2.5
        hf=_referencia_final_mismo_largo(
            a,b,p,self.ini["EA_kN"],self.fin["EA_kN"],h0,
        )
        n0=longitud_natural(resolver_catenaria(a,b,q,h0),self.ini["EA_kN"])
        nf=longitud_natural(resolver_catenaria(a,b,q,hf),self.fin["EA_kN"])
        self.assertAlmostEqual(n0,nf,delta=1e-7)

    def test_vanos_y_condiciones_por_temperatura(self):
        r,tabla=ejecutar_corridas_por_vano_checa(
            self.puntos,self.ini,self.fin,[20.,50.],
        )
        self.assertEqual(len(tabla),8)
        self.assertEqual(tabla["Vano"].nunique(),2)
        self.assertEqual(tabla["Condición"].nunique(),2)
        self.assertTrue((tabla["Flecha vertical (m)"]>0).all())
        self.assertTrue((tabla["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertGreater(r.H_tendido_kN,0.)

    def test_rechaza_conductores_distintos(self):
        otro=dict(self.fin)
        otro["diametro_m"]*=1.1
        with self.assertRaises(ValueError):
            ejecutar_corridas_por_vano_checa(
                self.puntos,self.ini,otro,[20.],
            )


if __name__=="__main__":
    unittest.main()
