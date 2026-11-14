"""Barrido de estados acoplados con una red de anclajes fijos."""
import unittest

from calculos.modelo_red import RedMecanica
from calculos.barrido_global import barrido_red_global


def datos():
    red=RedMecanica.desde_registros(
        [
            {"nombre":"A","base_m":(0,0,0),"modelo_apoyo":"referencia sintética"},
            {"nombre":"B","base_m":(35,0,3),"modelo_apoyo":"referencia sintética"},
        ],[
            {
                "nombre":"V1","origen":"A","destino":"B",
                "circuito":"C1","seccion_tendido":"S1",
                "conductor":"cable sintético",
                "amarre_origen_m":(0,0,9.5),
                "amarre_destino_m":(0,0,9.5),
                "conexion_origen":"ANCLAJE",
                "conexion_destino":"ANCLAJE",
            },
        ]
    )
    fichas={"cable sintético":{
        "peso_kN_m":.01,"diametro_m":.02,
        "EA_kN":16000,"alpha_por_C":1.8e-5,
        "H_tendido_kN":8,
        "temperatura_tendido_C":20,
        "fuente":"ENSAYO SINTÉTICO",
    }}
    return red,fichas


class BarridoRedGlobalTest(unittest.TestCase):
    def test_barrido_no_interpela_fuerzas_ni_muta_material(self):
        red,mat=datos()
        r=barrido_red_global(
            red,mat,temperaturas_C=[20],
            tensiones_iniciales_kN=[7,8],
            direcciones_viento_deg=[0],
            viento_min_ms=0,viento_max_ms=1,
        )
        self.assertEqual(len(r["estados"]),4)
        self.assertEqual(len(r["apoyos"]),8)
        self.assertEqual(len(r["vanos"]),4)
        self.assertEqual(mat["cable sintético"]["H_tendido_kN"],8)
        self.assertLess(
            r["vanos"]["Residual equilibrio vano (kN)"].max(),1e-4,
        )

    def test_limite_estados_es_explicito(self):
        red,mat=datos()
        with self.assertRaisesRegex(ValueError,"superan"):
            barrido_red_global(
                red,mat,temperaturas_C=[20,40],
                tensiones_iniciales_kN=[5,6,7],
                direcciones_viento_deg=[0,90],
                viento_min_ms=0,viento_max_ms=20,
                limite_casos=100,
            )


if __name__=="__main__":
    unittest.main()
