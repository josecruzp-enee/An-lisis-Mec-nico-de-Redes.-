"""Invariancias físicas del BVP en coordenadas de proyecto.

Ensayos de física numérica: traslación UTM y rotación de ejes XY deben
conservar las magnitudes del estado mecánico cuando se transforman
también los extremos y la dirección del viento. No depende del origen
UTM de Honduras ni de la orientación del dibujo.
"""
import unittest
import math
import numpy as np

from calculos.cable_no_lineal import resolver_cable_no_lineal


PARAMS=dict(
    peso_kN_m=.0085, diametro_m=.021,
    EA_kN=15000., alpha_por_C=1.91e-5,
    H_tendido_kN=9.,
    temperatura_tendido_C=20.,
    temperatura_estado_C=37.,
    velocidad_viento_ms=19.,
    azimut_viento_deg=48.,
    tolerancia=5e-6, puntos=100,
)


class InvarianciasCableBVP(unittest.TestCase):
    def setUp(self):
        self.a=np.array([0.,0.,10.])
        self.b=np.array([70.,22.,19.])

    def test_traslacion_utm_no_cambia_tensiones_ni_flecha(self):
        base=resolver_cable_no_lineal(self.a,self.b,**PARAMS)
        v=np.array([428000.,1725000.,132.])
        geo=resolver_cable_no_lineal(self.a+v,self.b+v,**PARAMS)
        np.testing.assert_allclose(
            geo.fuerza_a,base.fuerza_a,atol=3e-5
        )
        np.testing.assert_allclose(
            geo.fuerza_b,base.fuerza_b,atol=3e-5
        )
        self.assertAlmostEqual(
            geo.tension_maxima_kN,base.tension_maxima_kN,delta=3e-5
        )
        np.testing.assert_allclose(
            geo.puntos(np.array([.2,.5,.8]))-v,
            base.puntos(np.array([.2,.5,.8])),atol=3e-5,
        )

    def test_rotacion_xy_equivalente_preserva_tension(self):
        ang=math.radians(37.)
        c,s=math.cos(ang),math.sin(ang)
        R=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
        base=resolver_cable_no_lineal(self.a,self.b,**PARAMS)
        rotados={**PARAMS,"azimut_viento_deg":PARAMS["azimut_viento_deg"]+37.}
        girado=resolver_cable_no_lineal(R@self.a,R@self.b,**rotados)
        np.testing.assert_allclose(
            girado.fuerza_a,R@base.fuerza_a,atol=3e-5
        )
        np.testing.assert_allclose(
            girado.fuerza_b,R@base.fuerza_b,atol=3e-5
        )
        self.assertAlmostEqual(
            girado.tension_maxima_kN,base.tension_maxima_kN,delta=3e-5,
        )

    def test_invertir_sentido_vano_intercambia_reacciones(self):
        base=resolver_cable_no_lineal(self.a,self.b,**PARAMS)
        inv=resolver_cable_no_lineal(self.b,self.a,**PARAMS)
        np.testing.assert_allclose(inv.fuerza_a,base.fuerza_b,atol=3e-5)
        np.testing.assert_allclose(inv.fuerza_b,base.fuerza_a,atol=3e-5)
        self.assertAlmostEqual(
            inv.longitud_deformada_m,base.longitud_deformada_m,delta=3e-5
        )


if __name__=="__main__":
    unittest.main()
