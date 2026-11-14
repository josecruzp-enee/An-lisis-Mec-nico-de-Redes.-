"""Pruebas del equilibrio de una sección con guía sin fricción.

Las propiedades usadas son estrictamente sintéticas. Una grapa de suspensión
fija NO pertenece a este modelo.
"""
import unittest
import numpy as np

from calculos.modelo_red import RedMecanica
from calculos.suspension_deslizante import resolver_seccion_deslizante


def ejemplo(luz2=40.,desnivel=0.,tipo="DESLIZANTE"):
    nodos=[
        {"nombre":"A","base_m":(0.,0.,0.),"modelo_apoyo":"ensayo"},
        {"nombre":"B","base_m":(40.,0.,desnivel),"modelo_apoyo":"ensayo"},
        {"nombre":"C","base_m":(40.+luz2,0.,0.),"modelo_apoyo":"ensayo"},
    ]
    vanos=[
        {"nombre":"V1","origen":"A","destino":"B",
         "circuito":"C1","seccion_tendido":"S1",
         "conductor":"ensayo","amarre_origen_m":(0,0,10),
         "amarre_destino_m":(0,0,10),
         "conexion_origen":"ANCLAJE","conexion_destino":tipo},
        {"nombre":"V2","origen":"B","destino":"C",
         "circuito":"C1","seccion_tendido":"S1",
         "conductor":"ensayo","amarre_origen_m":(0,0,10),
         "amarre_destino_m":(0,0,10),
         "conexion_origen":tipo,"conexion_destino":"ANCLAJE"},
    ]
    red=RedMecanica.desde_registros(nodos,vanos)
    materiales={"ensayo":{
        "peso_kN_m":.01,"diametro_m":.021,
        "EA_kN":16000.,"alpha_por_C":1.8e-5,
        "H_tendido_kN":8.,
        "temperatura_tendido_C":20.,
        "fuente":"ensayo sintético",
    }}
    return red,materiales


class SeccionDeslizanteTest(unittest.TestCase):
    def test_guia_ideal_equilibrio_y_conservacion(self):
        red,materiales=ejemplo()
        r=resolver_seccion_deslizante(
            red,materiales,circuito="C1",seccion="S1",
            temperatura_C=20,viento_ms=0,azimut_deg=90,
        )
        self.assertLess(r.residual_max_kN,1e-4)
        self.assertAlmostEqual(
            sum(r.longitudes_naturales_referencia_m.values()),
            r.longitud_natural_total_m,places=9
        )
        self.assertEqual(len(r.vanos),2)
        self.assertAlmostEqual(
            np.linalg.norm(r.vanos["V1"].tensiones_xyz[-1]),
            np.linalg.norm(r.vanos["V2"].tensiones_xyz[0]),places=4
        )
        np.testing.assert_allclose(
            r.fuerzas_apoyos_kN["B"][:2],[0,0],atol=1e-4
        )

    def test_guia_no_es_grapa_fija(self):
        red,materiales=ejemplo(tipo="SUSPENSION")
        with self.assertRaisesRegex(ValueError,"DESLIZANTE"):
            resolver_seccion_deslizante(
                red,materiales,circuito="C1",seccion="S1",
                temperatura_C=20,viento_ms=0,azimut_deg=0
            )


if __name__=="__main__":
    unittest.main()
