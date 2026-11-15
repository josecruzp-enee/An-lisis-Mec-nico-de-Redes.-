"""Pruebas del problema inverso, hipótesis climáticas y tabla de tendido.

Casos sintéticos NO constituyen diseño de una línea real.
"""
import unittest
from unittest.mock import patch
import numpy as np

from calculos.tendido_inverso import (
    HipotesisTendido, dimensionar_tension_tendido
)


def args():
    return dict(
        inicio=(0,0,11),fin=(45,4,14),
        hipotesis=[
            HipotesisTendido("frio",-10,0,0,7.0,"Documento ensayo","Caso de frío"),
            HipotesisTendido("viento",15,16,90,9.0,"Documento ensayo","Caso de viento"),
        ],
        temperaturas_tabla_C=[0,20,40],
        temperatura_tendido_C=20,
        peso_kN_m=.009,diametro_m=.02,EA_kN=15000,
        alpha_por_C=1.91e-5,fuente_material="Ensayo sintético",
        H_min_kN=1,H_max_kN=6,muestras_monotonia=5,
    )


class TendidoInversoTest(unittest.TestCase):
    def test_inverso_real_resuelve_hipotesis_y_tabla(self):
        r=dimensionar_tension_tendido(**args())
        self.assertTrue(1<=r.H_tendido_kN<=6)
        self.assertEqual(len(r.hipotesis),2)
        self.assertEqual(len(r.tabla_tendido),3)
        self.assertLessEqual(r.razon_maxima,1.0001)
        self.assertGreater(r.evaluaciones_bvp,0)
        self.assertEqual([x["Temperatura (°C)"] for x in r.tabla_tendido],[0,20,40])
        self.assertTrue(all(x["Flecha vertical sobre cuerda (m)"]>0
                            for x in r.tabla_tendido))
        self.assertGreater(
            r.tabla_tendido[-1]["Flecha vertical sobre cuerda (m)"],
            r.tabla_tendido[0]["Flecha vertical sobre cuerda (m)"],
        )
        self.assertTrue(all(x["Residual equilibrio (kN)"]<1e-4 for x in r.tabla_tendido))

    def test_limite_superior_activo_no_inventa_optimo(self):
        x=args()
        x["hipotesis"]=[HipotesisTendido(
            "alta",20,0,0,1000,"Documento ensayo","Límite alto"
        )]
        r=dimensionar_tension_tendido(**x)
        self.assertAlmostEqual(r.H_tendido_kN,6)
        self.assertTrue(r.cota_superior_activa)

    def test_rechaza_fuente_de_criterio_ausente(self):
        with self.assertRaisesRegex(ValueError,"fuente"):
            HipotesisTendido("frio",0,0,0,4,"","Ensayo")

    def test_rechaza_condiciones_sin_factibilidad(self):
        x=args()
        x["hipotesis"]=[HipotesisTendido(
            "frio",20,0,0,.01,"Documento ensayo","Imposible"
        )]
        with self.assertRaisesRegex(ValueError,"No existe tensión"):
            dimensionar_tension_tendido(**x)

    def test_no_acepta_un_modelo_no_monotono(self):
        # Si se alcanza una rama no monótona no se busca una raíz
        # arbitraria y no se emite una tensión de tendido aprobada.
        class Falso:
            def __init__(self,t):
                self.tension_maxima_kN=t
        x=args()
        x["hipotesis"]=[HipotesisTendido(
            "frio",20,0,0,10,"Documento ensayo","Ensayo"
        )]
        def respuesta(*a,**kw):
            H=kw["H_tendido_kN"]
            return Falso(4-H)
        with patch("calculos.tendido_inverso.resolver_cable_no_lineal",
                   side_effect=respuesta):
            with self.assertRaisesRegex(ValueError,"no monótona"):
                dimensionar_tension_tendido(**x)


if __name__=="__main__":
    unittest.main()
