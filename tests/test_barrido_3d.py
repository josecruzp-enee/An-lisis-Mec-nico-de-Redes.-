"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_barrido_3d.py ===
"""Regresiones de la catenaria 3D y barridos con datos sintéticos."""
import math
import unittest

import numpy as np

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado, longitud_natural
from Analisis_mecanico_conductores.hipotesis_climaticas.evaluar_estados_climaticos_catenaria_3d import ejecutar_barrido_3d


def ejemplo_vanos():
    return [{
        "nombre": "P1-P2", "inicio": "P1", "fin": "P2",
        "base_inicio_m": [0, 0, 100], "base_fin_m": [40, 0, 104],
        "amarre_inicio_m": [0, 0, 10], "amarre_fin_m": [0, 0, 9],
    }]


def barrido(**kwargs):
    params = dict(
        vanos=ejemplo_vanos(),
        peso_kN_m=0.0095, diametro_m=0.021,
        EA_kN=16000, alpha_por_C=1.8e-5,
        temperatura_tendido_C=20, temperaturas_C=[20],
        tensiones_iniciales_kN=[8], viento_min_ms=0,
        viento_max_ms=2, incremento_viento_ms=1,
        direcciones_viento_deg=[90], Cd=1.2, rho_kg_m3=1.225,
        cantidad_conductores=3, fuente_conductor="Datos sintéticos de ensayo",
    )
    params.update(kwargs)
    return ejecutar_barrido_3d(**params)


class TestCatenariaTridimensional(unittest.TestCase):
    def test_apoyos_desnivelados_con_y_sin_viento(self):
        for carga in ([0, 0, -.01], [0, .02, -.01]):
            c = resolver_catenaria([0, 0, 110], [40, 0, 113], carga, 8)
            np.testing.assert_allclose(c.puntos(0), [0, 0, 110], atol=1e-11)
            np.testing.assert_allclose(c.puntos(c.luz), [40, 0, 113], atol=1e-11)
            f1, f2 = c.fuerzas
            np.testing.assert_allclose(f1 + f2, np.asarray(carga) * c.longitud,
                                       rtol=1e-10, atol=1e-11)

    def test_catenaria_nivelada_con_solucion_cerrada(self):
        c = resolver_catenaria([0, 0, 10], [40, 0, 10], [0, 0, -.01], 8)
        a = 8 / .01
        esperado = a * (math.cosh(40 / (2*a)) - 1)
        self.assertAlmostEqual(10-c.puntos(20)[2], esperado, places=11)
        self.assertGreater(c.longitud, 40)

    def test_identidad_termica_y_calor(self):
        vano = ([0, 0, 10], [40, 0, 13], [0, 0, -.01], [0, 0, -.01])
        r0 = resolver_cambio_estado([vano], 8, 16000, 1.8e-5, 0)
        r1 = resolver_cambio_estado([vano], 8, 16000, 1.8e-5, 30)
        self.assertAlmostEqual(r0["H_kN"], 8, places=5)
        self.assertLess(r1["H_kN"], 8)
        self.assertLess(abs(r1["residual_m"]), 1e-8)

    def test_cuadratura_con_orden_superior(self):
        c = resolver_catenaria([0, 0, 10], [40, 0, 14], [0, 0, -.01], 8)
        x, w = np.polynomial.legendre.leggauss(128)
        x = (x+1)*c.luz/2
        ref = c.luz/2 * np.dot(w, np.cosh((x-c.xc)/c.a) /
                                (1+c.tension(x)/16000))
        self.assertAlmostEqual(longitud_natural(c,16000),ref,places=10)


class TestBarridos(unittest.TestCase):
    def test_velocidades_de_uno_en_uno(self):
        r = barrido()
        self.assertEqual(r["parametros"]["velocidades_m_s"], [0, 1, 2])
        self.assertEqual(len(r["vanos"]), 3)
        self.assertEqual(len(r["nodos"]), 6)
        self.assertLess(r["vanos"]["Residual equilibrio (kN)"].max(), 1e-7)
        self.assertLess(r["vanos"]["Residual compatibilidad (m)"].abs().max(), 1e-8)

    def test_barrido_de_tensiones_y_temperaturas(self):
        r = barrido(tensiones_iniciales_kN=[4, 6, 8],
                    temperaturas_C=[20, 40], viento_max_ms=1)
        self.assertEqual(len(r["vanos"]), 12)
        self.assertEqual(len(r["nodos"]), 24)
        self.assertTrue((r["nodos"]["Estado"] ==
                         "SOLICITACIÓN, NO VERIFICABLE").all())

    def test_viento_invertido_cambia_fuerza_transversal(self):
        r = barrido(viento_min_ms=10, viento_max_ms=10,
                    direcciones_viento_deg=[90, 270])
        vanos = r["vanos"]
        self.assertEqual(len(vanos), 2)
        a = r["nodos"].query("Punto == 'P1'").sort_values("Azimut viento (°)")
        self.assertAlmostEqual(a.iloc[0]["Fy (kN)"], -a.iloc[1]["Fy (kN)"], places=8)

    def test_faltan_propiedades_rechazar(self):
        with self.assertRaises(ValueError):
            barrido(EA_kN=None)
        with self.assertRaises(ValueError):
            barrido(fuente_conductor="")
        with self.assertRaises(ValueError):
            barrido(incremento_viento_ms=0)

    def test_amarres_invalidos_rechazar(self):
        v = ejemplo_vanos()
        v[0]["amarre_inicio_m"] = [0, 0, -2]
        with self.assertRaises(ValueError):
            barrido(vanos=v)


# === Casos conservados de tests/test_barrido_no_lineal_3d.py ===
"""Regresión del barrido BVP: no confundirlo con catenaria de carga uniforme.

Los ensayos utilizan parámetros sintéticos, no una ficha de diseño.
"""
import unittest

import numpy as np

from Analisis_mecanico_conductores.hipotesis_climaticas.evaluar_estados_climaticos_bvp_3d import ejecutar_barrido_no_lineal_3d
from Analisis_mecanico_conductores.verificaciones.auditoria_cargas import auditar_reacciones_por_vano
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria


def datos():
    vanos=[{
        "nombre":"A-B","inicio":"A","fin":"B",
        "base_inicio_m":[0,0,0],"base_fin_m":[55,9,5],
        "amarre_inicio_m":[0,0,10],"amarre_fin_m":[0,0,11],
    }]
    args=dict(
        peso_kN_m=.009,diametro_m=.021,
        EA_kN=16000.,alpha_por_C=1.8e-5,
        temperatura_tendido_C=20.,
        temperaturas_C=[20.],
        tensiones_iniciales_kN=[7.],
        viento_min_ms=0.,viento_max_ms=0.,
        direcciones_viento_deg=[90.],
        cantidad_conductores=3,
        fuente_conductor="Ensayo sintético",
    )
    return vanos,args


class BarridoNoLinealTest(unittest.TestCase):
    def test_sin_viento_contra_catenaria_analitica_y_auditoria(self):
        vanos,args=datos()
        r=ejecutar_barrido_no_lineal_3d(vanos,**args)
        v=r["vanos"].iloc[0]
        a=np.array([0.,0.,10.]);b=np.array([55.,9.,16.])
        referencia=resolver_catenaria(a,b,[0,0,-.009],7.)
        fa,fb=referencia.fuerzas
        self.assertAlmostEqual(v["T extremo A (kN)"],np.linalg.norm(fa),delta=.003)
        self.assertAlmostEqual(v["T extremo B (kN)"],np.linalg.norm(fb),delta=.003)
        self.assertAlmostEqual(v["Longitud cable (m)"],referencia.longitud,delta=.005)
        self.assertGreaterEqual(v["Flecha vertical respecto cuerda (m)"],0.)
        self.assertLess(v["Residual equilibrio (kN)"],1e-4)
        self.assertLess(v["Residual contorno (m)"],1e-4)
        self.assertLess(v["Residual compatibilidad (m)"],.001)
        self.assertLess(v["Error poligonal longitud (m)"],.001)
        self.assertAlmostEqual(
            v["Longitud por derivada BVP (m)"],
            v["Longitud cable (m)"],delta=.001,
        )
        audit=auditar_reacciones_por_vano(r["extremos"],r["nodos"])
        self.assertLess(audit["Residual máximo carga o momento"],1e-9)
        self.assertEqual(len(r["extremos"]),2)
        np.testing.assert_allclose(
            r["extremos"].iloc[0][["Fx (kN)","Fy (kN)","Fz (kN)"]].to_numpy(dtype=float),
            3*fa,atol=.01,
        )

    def test_viento_local_desvia_conductor_y_preserva_carga(self):
        vanos,args=datos()
        args.update(viento_min_ms=20.,viento_max_ms=20.)
        r=ejecutar_barrido_no_lineal_3d(vanos,**args)
        v=r["vanos"].iloc[0]
        self.assertGreater(v["Desviación lateral en punto de flecha (m)"],0.)
        self.assertGreater(v["T máxima (kN)"],0.)
        self.assertLess(v["Residual equilibrio (kN)"],1e-4)
        self.assertLess(v["Residual compatibilidad (m)"],.001)
        auditar_reacciones_por_vano(r["extremos"],r["nodos"])

    def test_solucion_sin_viento_se_reutiliza_entre_azimuts(self):
        from unittest.mock import patch
        from Analisis_mecanico_conductores.catenaria.resolver_cable_tridimensional_bvp import resolver_cable_no_lineal
        vanos,args=datos()
        args.update(direcciones_viento_deg=[0,90,180,270],
                    viento_min_ms=0,viento_max_ms=0)
        with patch(
            "Analisis_mecanico_conductores.hipotesis_climaticas.evaluar_estados_climaticos_bvp_3d.resolver_cable_no_lineal",
            wraps=resolver_cable_no_lineal
        ) as resolver:
            resultados=ejecutar_barrido_no_lineal_3d(vanos,**args)
        self.assertEqual(resolver.call_count,1)
        self.assertEqual(len(resultados["vanos"]),4)
        self.assertEqual(len(resultados["extremos"]),8)
        t=resultados["vanos"]["T máxima (kN)"]
        self.assertAlmostEqual(t.max(),t.min(),places=8)

    def test_expansion_termica_y_casos_independientes(self):
        vanos,args=datos()
        args.update(temperaturas_C=[20.,40.])
        r=ejecutar_barrido_no_lineal_3d(vanos,**args)
        self.assertEqual(len(r["vanos"]),2)
        self.assertLess(
            r["vanos"].iloc[1]["T máxima (kN)"],
            r["vanos"].iloc[0]["T máxima (kN)"],
        )
        self.assertEqual(len(r["nodos"]),4)
        self.assertEqual(len(r["extremos"]),4)


# === Casos conservados de tests/test_cable_no_lineal.py ===
"""Regresiones del problema de contorno tridimensional no lineal.

La semilla numérica no constituye la solución. Se contrastan extremos,
tensiones y longitud con catenaria cerrada sin viento y se evalúa viento
perpendicular a la tangente LOCAL en los estados con viento.
"""
import unittest
import numpy as np

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.catenaria.resolver_cable_tridimensional_bvp import resolver_cable_no_lineal


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


# === Casos conservados de tests/test_invariancias_cable_bvp.py ===
"""Invariancias físicas del BVP en coordenadas de proyecto.

Ensayos de física numérica: traslación UTM y rotación de ejes XY deben
conservar las magnitudes del estado mecánico cuando se transforman
también los extremos y la dirección del viento. No depende del origen
UTM de Honduras ni de la orientación del dibujo.
"""
import unittest
import math
import numpy as np

from Analisis_mecanico_conductores.catenaria.resolver_cable_tridimensional_bvp import resolver_cable_no_lineal


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
