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

    def test_cero_hielo_y_viento_es_valido(self):
        inicial, final = construir_hipotesis_cfe(
            20., viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
        )
        self.assertEqual(final[2].hielo_mm, 0.)
        self.assertEqual(final[2].viento_kmh, 0.)
        self.assertIn("SIN hielo", final[2].nombre)
        for caso in inicial + final:
            caso.validar()

    def test_no_admitir_clima_negativo(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20., viento_max_kmh=120., viento_reducido_kmh=90., hielo_mm=-1.,
            )
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20., viento_max_kmh=120., viento_reducido_kmh=-1., hielo_mm=0.,
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

    def test_corrida_integral_sin_hielo(self):
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        inicial = seleccionar_conductor_enee("1/0", "RAVEN", "Inicial")
        final = seleccionar_conductor_enee("1/0", "RAVEN", "Final")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final, viento_max_kmh=120.,
            viento_reducido_kmh=0., hielo_mm=0., temperaturas_C=[20., 50.],
        )
        self.assertEqual(len(resumen), 2)
        self.assertTrue((tabla["Hielo (mm)"] == 0).all())
        self.assertTrue((tabla["Flecha (m)"] > 0).all())

    def test_pigeon_3_0_sin_hielo_en_vano_50m(self):
        """Regresión: H50 no monótona a cargas tangenciales altas."""
        import pandas as pd
        import numpy as np
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        inicial = seleccionar_conductor_enee("3/0", "PIGEON", "Inicial")
        final = seleccionar_conductor_enee("3/0", "PIGEON", "Final")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final,
            viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
            temperaturas_C=[-10., 0., 20., 50.],
        )
        self.assertEqual(len(resumen), 2)
        self.assertEqual(len(tabla), 12)
        self.assertTrue(np.isfinite(tabla["H (kN)"]).all())
        self.assertTrue((tabla["H (kN)"] > 0).all())
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())

    def test_limites_estructurales_cfe_pigeon_y_raven(self):
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import construir_hipotesis_cfe
        for nombre, th1, th2 in [
            ("RAVEN", 6.495, 5.618),
            ("PIGEON", 8.824, 7.513),
        ]:
            _ini, finales = construir_hipotesis_cfe(
                100., viento_max_kmh=120.,
                viento_reducido_kmh=80., hielo_mm=3.,
                nombre_conductor=nombre,
            )
            self.assertAlmostEqual(finales[2].limite_tension_kN, th1)
            self.assertAlmostEqual(finales[3].limite_tension_kN, th2)
        _ini, sin_especificar = construir_hipotesis_cfe(
            100., viento_max_kmh=120., viento_reducido_kmh=80.,
            hielo_mm=3.,
        )
        self.assertAlmostEqual(sin_especificar[2].limite_tension_kN, 45.)

    def test_estado_inicial_acoplado_al_extremo_final(self):
        """CFE 07 FT 01: misma tensión extrema a -10 °C, no P iguales."""
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        for calibre, nombre in [("1/0", "RAVEN"), ("3/0", "PIGEON")]:
            ini = seleccionar_conductor_enee(calibre, nombre, "Inicial")
            fin = seleccionar_conductor_enee(calibre, nombre, "Final")
            resumen, tabla = ejecutar_corridas_cfe_por_vano(
                puntos, ini, fin, viento_max_kmh=120.,
                viento_reducido_kmh=0., hielo_mm=0.,
                temperaturas_C=[-10., 20., 50.],
            )
            extremos = tabla[
                (tabla["Hipótesis"] == "CFE viento reducido SIN hielo")
            ].set_index("Condición")
            self.assertAlmostEqual(
                float(extremos.loc["Inicial", "T máx. (kN)"]),
                float(extremos.loc["Final", "T máx. (kN)"]),
                delta=1e-5,
            )
            self.assertNotAlmostEqual(
                resumen.iloc[0]["parametro_P_m"],
                resumen.iloc[1]["parametro_P_m"], delta=1e-4,
            )

    def test_pigeon_3_0_desnivel_10m(self):
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 110.], "Altura_Amarre_m": [9.5, 9.5],
        })
        inicial = seleccionar_conductor_enee("3/0", "PIGEON", "Inicial")
        final = seleccionar_conductor_enee("3/0", "PIGEON", "Final")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final,
            viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
            temperaturas_C=[0., 20., 50.],
        )
        self.assertEqual(resumen["Desnivel máximo entre apoyos (m)"].iloc[0], 10.)
        self.assertTrue((tabla["Flecha (m)"] >= 0).all())
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())

    def test_rechaza_viento_reducido_mayor(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20.,viento_max_kmh=100.,viento_reducido_kmh=140.,hielo_mm=2.,
            )


if __name__=="__main__":
    unittest.main()
