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

    def test_corrida_integral_un_vano_sin_p_importado(self):
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
            seleccionar_conductor_enee,
        )
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
            ejecutar_corridas_cfe_por_vano,
        )
        puntos=pd.DataFrame({
            "Punto":["P1","P2"],"X":[0.,50.],"Y":[0.,0.],
            "Altitud":[100.,100.],"Altura_Amarre_m":[9.5,9.5],
        })
        ini=seleccionar_conductor_enee("1/0","RAVEN","Inicial")
        fin=seleccionar_conductor_enee("1/0","RAVEN","Final")
        resumen,tabla=ejecutar_corridas_cfe_por_vano(
            puntos,ini,fin,viento_max_kmh=120.,
            viento_reducido_kmh=90.,hielo_mm=2.,
            temperaturas_C=[20.,50.],
        )
        self.assertEqual(set(tabla["Condición"]),{"Inicial","Final"})
        self.assertEqual(len(tabla),8)
        self.assertTrue((tabla["Flecha (m)"]>0).all())
        self.assertTrue((tabla["T máx. (kN)"]>0).all())
        self.assertEqual(len(resumen),2)

    def test_rechaza_viento_reducido_mayor(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20.,viento_max_kmh=100.,viento_reducido_kmh=140.,hielo_mm=2.,
            )


if __name__=="__main__":
    unittest.main()
