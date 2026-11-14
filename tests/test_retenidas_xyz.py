"""Ensayos de estática 3D de retenidas, sin criterios de aprobación."""
import unittest
import numpy as np

from calculos.retenidas_xyz import RetenidaXYZ, estudiar_equilibrio_retenidas


class RetenidasXYZTest(unittest.TestCase):
    def test_retenida_inclinada_equilibra_momento_en_y(self):
        retenida = RetenidaXYZ(
            "R1", (0., 0., 9.), (-12., 0., 0.)
        )
        res = estudiar_equilibrio_retenidas(
            [10., 0., -1.], [0., 90., 0.], [retenida]
        )
        self.assertTrue(res.equilibrio_momentos)
        esperado = 90. / (9. * 12. / 15.)
        self.assertAlmostEqual(res.tensiones_kN["R1"], esperado, places=7)
        np.testing.assert_allclose(
            res.momento_residual_base_kNm, [0,0,0], atol=1e-7
        )
        # La componente vertical de la retenida se transmite a la base.
        self.assertLess(res.fuerza_resultante_base_kN[2], -1.)
        self.assertFalse(res.capacidades_documentadas)
        self.assertIn("NO VERIFICABLE", res.estado)

    def test_orientacion_opuesta_no_se_aprovecha_como_compresion(self):
        res=estudiar_equilibrio_retenidas(
            [0,0,0], [0,90,0],
            [RetenidaXYZ("R1",(0,0,9),(12,0,0))]
        )
        self.assertFalse(res.equilibrio_momentos)
        self.assertGreater(res.residual_momento_kNm,89.99)
        self.assertAlmostEqual(res.tensiones_kN["R1"],0.,places=6)

    def test_topes_documentados_pueden_volver_insuficiente_la_solucion(self):
        res=estudiar_equilibrio_retenidas(
            [0,0,0], [0,90,0],
            [RetenidaXYZ(
                "R1",(0,0,9),(-12,0,0),
                tension_limite_kN=5.,
                fuente_limite="Capacidad de ensayo hipotética"
            )]
        )
        self.assertFalse(res.equilibrio_momentos)
        self.assertLessEqual(res.tensiones_kN["R1"],5.+1e-6)
        self.assertTrue(res.capacidades_documentadas)

    def test_torsion_sin_brazo_lateral_no_puede_equilibrarse(self):
        res=estudiar_equilibrio_retenidas(
            [0,0,0], [0,0,7],
            [RetenidaXYZ("R1",(0,0,9),(-10,0,0))]
        )
        self.assertFalse(res.equilibrio_momentos)
        self.assertAlmostEqual(res.momento_residual_base_kNm[2],7.,places=7)

    def test_no_acepta_falsa_capacidad_sin_fuente(self):
        with self.assertRaisesRegex(ValueError,"capacidad sin fuente"):
            RetenidaXYZ(
                "R1",(0,0,9),(-10,0,0),tension_limite_kN=20
            )

    def test_no_admite_anclaje_por_encima_del_amarre(self):
        with self.assertRaisesRegex(ValueError,"por debajo"):
            RetenidaXYZ("R1",(0,0,9),(-10,0,10))


if __name__ == "__main__":
    unittest.main()
