"""Ensayos de equilibrio global y rechazo de conexiones no implementadas."""
import unittest
import numpy as np

from calculos.modelo_red import RedMecanica
from calculos.ensamblador_global import resolver_equilibrio_global


def modelo(centro_movil=False,suspension=False):
    apoyos=[
        {"nombre":n,"base_m":p,"modelo_apoyo":"modelo sintético",
         "fijacion":"MOVIL" if n=="P2" and centro_movil else "FIJO"}
        for n,p in [
            ("P1",(0.,0.,0.)),("P2",(40.,0.,0.)),("P3",(80.,0.,0.)),
        ]
    ]
    vanos=[]
    for idx, a,b,ci,cf in [
        (1,"P1","P2","ANCLAJE","SUSPENSION" if suspension else "ANCLAJE"),
        (2,"P2","P3","SUSPENSION" if suspension else "ANCLAJE","ANCLAJE"),
    ]:
        vanos.append({
            "nombre":f"V{idx}","origen":a,"destino":b,
            "circuito":"C1","seccion_tendido":"S1" if suspension else f"S{idx}",
            "conductor":"sintetico","amarre_origen_m":(0,0,10),
            "amarre_destino_m":(0,0,10),
            "conexion_origen":ci,"conexion_destino":cf,
        })
    return RedMecanica.desde_registros(apoyos,vanos)


def parametros():
    return {"sintetico":{
        "peso_kN_m":.01,"diametro_m":.02,"EA_kN":16000.,
        "alpha_por_C":1.8e-5,"H_tendido_kN":8.,
        "temperatura_tendido_C":20.,
        "fuente":"Valores SINTÉTICOS para prueba automatizada",
    }}


class RedGlobalTest(unittest.TestCase):
    def test_dos_vanos_fijos_no_confundir_reaccion_con_cumplimiento(self):
        r=resolver_equilibrio_global(
            modelo(),parametros(),temperatura_C=20,
            viento_ms=0,azimut_deg=90,
        )
        self.assertEqual(len(r.vanos),2)
        self.assertEqual(r.iteraciones,1)
        self.assertLess(r.residual_max_kN,1e-10)
        for n in ("P1","P2","P3"):
            np.testing.assert_allclose(
                r.reacciones_anclajes_kN[n]+r.fuerzas_conductor_kN[n],
                np.zeros(3),atol=1e-10,
            )
        self.assertIn("NO VERIFICACIÓN",r.estado)

    def test_apoyo_movil_resuelve_equilibrio(self):
        r=resolver_equilibrio_global(
            modelo(centro_movil=True),parametros(),
            temperatura_C=20,viento_ms=0,azimut_deg=0,
            rigideces={"P2":{
                "K_kN_m":np.diag([1000.,1000.,1000.]),
                "fuente":"Resorte de ensayo sintético",
            }},
            tolerancia_residual_kN=5e-4,
            max_evaluaciones=30,
        )
        self.assertLess(r.residual_max_kN,5e-4)
        self.assertLess(r.desplazamientos_m["P2"][2],0.)
        self.assertAlmostEqual(r.desplazamientos_m["P2"][0],0.,places=4)
        np.testing.assert_allclose(
            r.fuerzas_conductor_kN["P2"],
            r.fuerzas_rigidez_kN["P2"],atol=5e-4,
        )

    def test_suspension_rechazada_hasta_resolver_movilidad(self):
        with self.assertRaisesRegex(ValueError,"Suspensión"):
            resolver_equilibrio_global(
                modelo(suspension=True),parametros(),
                temperatura_C=20,viento_ms=5,azimut_deg=90,
            )

    def test_movil_no_admite_rigidez_ficticia(self):
        with self.assertRaisesRegex(ValueError,"rigidez sin fuente"):
            resolver_equilibrio_global(
                modelo(centro_movil=True),parametros(),
                temperatura_C=20,viento_ms=0,azimut_deg=0,
            )


if __name__=="__main__":
    unittest.main()
