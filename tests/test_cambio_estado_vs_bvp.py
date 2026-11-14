"""Contraste independiente entre cambio de estado analítico y BVP 3D.

El ensayo analítico usa una catenaria exacta para carga gravitatoria
uniforme por longitud de conductor deformado. Aplica compatibilidad
elástica mediante integración de longitud natural, sin emplear el
solucionador BVP. Es un benchmark de software, NO validación de
curvas constitutivas reales ACSR.
"""
import unittest
import numpy as np

from calculos.cambio_estado import resolver_cambio_estado
from calculos.catenaria import resolver_catenaria
from calculos.cable_no_lineal import resolver_cable_no_lineal


class ContrasteCambioEstadoBVP(unittest.TestCase):
    def _contrastar(self, a, b, dt, h0=8.0):
        q=np.array([0.,0.,-.009])
        ea=16000.
        alpha=1.91e-5
        analitico=resolver_cambio_estado(
            [(a,b,q,q)],h0,ea,alpha,dt,
            tolerancia_m=2e-10
        )
        cab=resolver_catenaria(a,b,q,analitico["H_kN"])
        bvp=resolver_cable_no_lineal(
            a,b,peso_kN_m=.009,diametro_m=.021,
            EA_kN=ea,alpha_por_C=alpha,
            H_tendido_kN=h0,
            temperatura_tendido_C=20.,
            temperatura_estado_C=20.+dt,
            velocidad_viento_ms=0,
            azimut_viento_deg=0,
            tolerancia=3e-6,puntos=110
        )
        fa,fb=cab.fuerzas
        np.testing.assert_allclose(bvp.fuerza_a,fa,atol=.004)
        np.testing.assert_allclose(bvp.fuerza_b,fb,atol=.004)
        self.assertAlmostEqual(
            bvp.longitud_deformada_m,cab.longitud,delta=.005
        )
        self.assertLess(bvp.residual_equilibrio_kN,1e-4)
        self.assertLess(abs(analitico["residual_m"]),2e-10)

    def test_vano_nivelado_calor_y_frio(self):
        for dt in (-25.,0.,35.):
            with self.subTest(dt=dt):
                self._contrastar([0,0,10],[75,0,10],dt)

    def test_vano_desnivelado_calor_y_frio(self):
        for dt in (-20.,35.):
            with self.subTest(dt=dt):
                self._contrastar([0,0,12],[85,10,32],dt)


if __name__=="__main__":
    unittest.main()
