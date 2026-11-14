"""Regresión del barrido BVP: no confundirlo con catenaria de carga uniforme.

Los ensayos utilizan parámetros sintéticos, no una ficha de diseño.
"""
import unittest

import numpy as np

from calculos.barrido_no_lineal_3d import ejecutar_barrido_no_lineal_3d
from calculos.auditoria_cargas import auditar_reacciones_por_vano
from calculos.catenaria import resolver_catenaria


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
        auditar_reacciones_por_vano(r["extremos"],r["nodos"])

    def test_solucion_sin_viento_se_reutiliza_entre_azimuts(self):
        from unittest.mock import patch
        from calculos.cable_no_lineal import resolver_cable_no_lineal
        vanos,args=datos()
        args.update(direcciones_viento_deg=[0,90,180,270],
                    viento_min_ms=0,viento_max_ms=0)
        with patch(
            "calculos.barrido_no_lineal_3d.resolver_cable_no_lineal",
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


if __name__=="__main__":
    unittest.main()
