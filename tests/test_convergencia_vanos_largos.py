"""Benchmarks no lineales para vanos largos, desnivel y viento oblicuo.

Son ensayos numéricos de convergencia con datos sintéticos. Comparar
mallas y tolerancias evita considerar fiable una curva por solo
converger en una discretización. No valida ACSR de fabricante.
"""
import unittest

import numpy as np

from calculos.cable_no_lineal import resolver_cable_no_lineal


def calcular(*, puntos=70, tolerancia=2e-5, viento=22, T=35):
    return resolver_cable_no_lineal(
        inicio=(0.,0.,12.),
        fin=(225.,45.,80.),
        peso_kN_m=.0085,
        diametro_m=.021,
        EA_kN=8000.,
        alpha_por_C=19.1e-6,
        H_tendido_kN=12.,
        temperatura_tendido_C=20.,
        temperatura_estado_C=T,
        velocidad_viento_ms=viento,
        azimut_viento_deg=75.,
        puntos=puntos,
        tolerancia=tolerancia,
        max_nodos=12000,
    )


class ConvergenciaVanoLargoTest(unittest.TestCase):
    def test_convergencia_malla_y_tolerancia(self):
        a=calcular(puntos=70,tolerancia=2e-5)
        b=calcular(puntos=130,tolerancia=5e-6)
        np.testing.assert_allclose(a.xyz[0],[0,0,12],atol=2e-4)
        np.testing.assert_allclose(a.xyz[-1],[225,45,80],atol=2e-4)
        np.testing.assert_allclose(b.xyz[0],[0,0,12],atol=2e-4)
        np.testing.assert_allclose(b.xyz[-1],[225,45,80],atol=2e-4)
        self.assertLess(a.residual_equilibrio_kN,2e-4)
        self.assertLess(b.residual_equilibrio_kN,1e-4)
        self.assertAlmostEqual(a.tension_maxima_kN,b.tension_maxima_kN,delta=.01)
        self.assertAlmostEqual(
            a.longitud_deformada_m,b.longitud_deformada_m,delta=.01,
        )
        np.testing.assert_allclose(a.puntos([.25,.5,.75]),
                                   b.puntos([.25,.5,.75]),atol=.01)

    def test_carga_de_viento_cambia_geometria(self):
        aire=calcular(viento=22)
        calma=calcular(viento=0)
        self.assertGreater(
            np.max(np.linalg.norm(aire.puntos([.25,.5,.75])
                                  -calma.puntos([.25,.5,.75]),axis=1)),
            .005
        )
        self.assertTrue(np.isfinite(aire.tensiones_xyz).all())


if __name__=="__main__":
    unittest.main()
