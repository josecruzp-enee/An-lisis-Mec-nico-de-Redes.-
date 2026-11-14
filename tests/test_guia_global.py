"""Acoplamiento global con guías deslizantes ideales entre dos anclajes."""
import unittest
import numpy as np

from calculos.modelo_red import RedMecanica
from calculos.ensamblador_global import resolver_equilibrio_global


def datos(tipo="DESLIZANTE"):
    red=RedMecanica.desde_registros([
        {"nombre":"A","base_m":(0,0,0),"modelo_apoyo":"ensayo"},
        {"nombre":"B","base_m":(40,0,2),"modelo_apoyo":"ensayo"},
        {"nombre":"C","base_m":(85,10,3),"modelo_apoyo":"ensayo"},
    ],[
        {"nombre":"AB","origen":"A","destino":"B",
         "circuito":"C1","seccion_tendido":"S1",
         "conductor":"sintetico",
         "amarre_origen_m":(0,0,10),"amarre_destino_m":(0,0,10),
         "conexion_origen":"ANCLAJE","conexion_destino":tipo},
        {"nombre":"BC","origen":"B","destino":"C",
         "circuito":"C1","seccion_tendido":"S1",
         "conductor":"sintetico",
         "amarre_origen_m":(0,0,10),"amarre_destino_m":(0,0,10),
         "conexion_origen":tipo,"conexion_destino":"ANCLAJE"},
    ])
    return red,{
        "sintetico":{
            "peso_kN_m":.009,"diametro_m":.020,
            "EA_kN":16000.,"alpha_por_C":1.8e-5,
            "H_tendido_kN":7.,"temperatura_tendido_C":20.,
            "fuente":"ENSAYO SINTÉTICO",
        }
    }


class GuiaGlobalTest(unittest.TestCase):
    def test_guia_ideal_conserva_continuidad_en_red(self):
        red,mat=datos()
        res=resolver_equilibrio_global(
            red,mat,temperatura_C=20,viento_ms=0,azimut_deg=0,
        )
        self.assertEqual(len(res.vanos),2)
        self.assertIn(("C1","S1"),res.secciones_deslizantes)
        seccion=res.secciones_deslizantes[("C1","S1")]
        self.assertLess(seccion.residual_max_kN,1e-4)
        for nombre in red.apoyos:
            np.testing.assert_allclose(
                res.fuerzas_conductor_kN[nombre]
                +res.reacciones_anclajes_kN[nombre],
                [0,0,0],atol=1e-7,
            )

    def test_no_confunde_grapa_real_con_guia(self):
        red,mat=datos(tipo="SUSPENSION")
        with self.assertRaisesRegex(ValueError,"grapa real"):
            resolver_equilibrio_global(
                red,mat,temperatura_C=20,viento_ms=0,azimut_deg=0
            )


if __name__=="__main__":
    unittest.main()
