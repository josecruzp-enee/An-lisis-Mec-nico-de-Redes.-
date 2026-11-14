"""Regresiones del problema de contorno tridimensional no lineal.

La semilla numérica no constituye la solución. Se contrastan extremos,
tensiones y longitud con catenaria cerrada sin viento y se evalúa viento
perpendicular a la tangente LOCAL en los estados con viento.
"""
import unittest
import numpy as np

from calculos.catenaria import resolver_catenaria
from calculos.cable_no_lineal import resolver_cable_no_lineal


def resolver(**cambios):
    datos={
        "inicio":[0,0,10], "fin":[40,0,13],
        "peso_kN_m":.01,"diametro_m":.021,
        "EA_kN":16000,"alpha_por_C":1.8e-5,
        "H_tendido_kN":8,
        "temperatura_tendido_C":20,"temperatura_estado_C":20,
        "velocidad_viento_ms":0,"azimut_viento_deg":90,
        "tolerancia":2e-5,"puntos":70,
    }
    datos.update(cambios)
    return resolver_cable_no_lineal(**datos)


class CablesNoLinealesTest(unittest.TestCase):
    def test_reproduce_catenaria_analitica_sin_viento(self):
        r=resolver()
        referencia=resolver_catenaria(
            [0,0,10],[40,0,13],[0,0,-.01],8
        )
        f0,f1=referencia.fuerzas
        np.testing.assert_allclose(r.xyz[0],[0,0,10],atol=2e-5)
        np.testing.assert_allclose(r.xyz[-1],[40,0,13],atol=2e-5)
        np.testing.assert_allclose(r.fuerza_a,f0,atol=1e-3)
        np.testing.assert_allclose(r.fuerza_b,f1,atol=1e-3)
        self.assertAlmostEqual(r.longitud_deformada_m,
                               referencia.longitud,places=3)
        self.assertLess(r.residual_equilibrio_kN,1e-4)

    def test_viento_local_y_equilibrio_con_desnivel(self):
        r=resolver(velocidad_viento_ms=25)
        np.testing.assert_allclose(r.xyz[0],[0,0,10],atol=2e-5)
        np.testing.assert_allclose(r.xyz[-1],[40,0,13],atol=2e-5)
        self.assertLess(r.residual_equilibrio_kN,2e-4)
        self.assertGreater(float(np.max(np.abs(r.xyz[:,1]))),1e-4)
        self.assertTrue(np.isfinite(r.tensiones_xyz).all())

    def test_tension_maxima_no_es_solo_muestra_gruesa(self):
        r=resolver(velocidad_viento_ms=27,azimut_viento_deg=80)
        # Cotejo independiente en una rejilla más densa, evaluando la
        # interpolación del BVP y no solo sus nodos de exportación.
        u=np.linspace(0,1,6001)
        from_spline=r._solucion(u)[3:6]
        max_denso=float(np.linalg.norm(from_spline,axis=0).max())
        self.assertGreaterEqual(r.tension_maxima_kN+1e-8,max_denso)
        self.assertGreaterEqual(
            r.tension_maxima_kN+1e-8,
            float(np.linalg.norm(r.fuerza_a))
        )
        self.assertGreaterEqual(
            r.tension_maxima_kN+1e-8,
            float(np.linalg.norm(r.fuerza_b))
        )

    def test_expansion_termica_cambia_tension(self):
        caliente=resolver(temperatura_estado_C=40)
        base=resolver()
        self.assertLess(caliente.tension_maxima_kN,base.tension_maxima_kN)
        self.assertGreater(caliente.longitud_natural_estado_m,
                           base.longitud_natural_estado_m)

    def test_rechaza_datos_invalidos(self):
        with self.assertRaises(ValueError):
            resolver(EA_kN=0)
        with self.assertRaises(ValueError):
            resolver(inicio=[0,0,10],fin=[0,0,15])


if __name__=="__main__":
    unittest.main()
