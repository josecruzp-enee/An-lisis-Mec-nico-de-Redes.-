"""CFE DCCIAMBT: pruebas de hipótesis y separación de tablas ENEE."""
import unittest

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    construir_hipotesis_cfe,
)


class HipotesisCfeDocumentadas(unittest.TestCase):
    def test_condiciones_cfe_por_estado(self):
        inicial,final=construir_hipotesis_cfe(
            20.,viento_max_kmh=120.,viento_reducido_kmh=90.,hielo_mm=2.,
        )
        self.assertEqual(len(inicial),1)
        self.assertEqual(len(final),4)
        self.assertEqual(inicial[0].temperatura_C,0.)
        self.assertAlmostEqual(inicial[0].limite_tension_kN,6.6)
        self.assertEqual(
            [(c.temperatura_C,c.viento_kmh,c.hielo_mm) for c in final],
            [(16.,0.,0.),(0.,0.,0.),(-10.,90.,2.),(0.,120.,0.)],
        )
        self.assertEqual(
            [c.limite_tension_kN for c in final],[4.,5.,9.,9.],
        )
        for caso in inicial+final:
            caso.validar()

    def test_no_inventar_hielo_ni_viento(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20.,viento_max_kmh=120.,viento_reducido_kmh=90.,hielo_mm=0.,
            )
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20.,viento_max_kmh=120.,viento_reducido_kmh=0.,hielo_mm=2.,
            )

    def test_rechaza_viento_reducido_mayor(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20.,viento_max_kmh=100.,viento_reducido_kmh=140.,hielo_mm=2.,
            )


if __name__=="__main__":
    unittest.main()
