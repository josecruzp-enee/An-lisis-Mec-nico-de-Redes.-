"""Validación de condiciones inicial/final contra anexo 8 ENEE, AAC 1/0.

Datos publicados en tablas ENEE (redondeados a kgf y centímetros).
P50 se proporciona desde encabezados ENEE: estos tests validan estados
térmicos, NO la obtención independiente de P50 por criterios de diseño.
"""
import unittest

import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    EstadoReferenciaCFE,
    HipotesisDisenoCFE,
    PropiedadesConductorCFE,
    calcular_parametro_cfe_desde_limites,
    calcular_tablas_inicial_final,
)

KG_F_A_KN = 9.80665 / 1000.


def propiedades_aac():
    return PropiedadesConductorCFE(
        peso_kN_m=0.001442,
        diametro_m=0.0117,
        EA_inicial_kN=41.202 * 53.49,
        EA_final_kN=59.841 * 53.49,
        alpha_inicial_por_C=23e-6,
        alpha_final_por_C=23e-6,
        ruptura_kN=8.84,
        fuente="CFE 07 FT 01, AAC 1/0; propiedades de prueba",
    )


def vano(luz):
    return pd.DataFrame({
        "Punto": ["P1", "P2"], "X": [0., float(luz)], "Y": [0., 0.],
    })


class TablasCFETest(unittest.TestCase):

    def test_84_m_estado_inicial_y_final(self):
        tabla = calcular_tablas_inicial_final(
            vano(84), propiedades_aac(),
            EstadoReferenciaCFE(675., "ENEE, anexo 8, inicial, 84 m"),
            EstadoReferenciaCFE(585., "ENEE, anexo 8, final, 84 m"),
            [-10, 0, 20, 50],
        )
        objetivos = {
            ("Inicial", -10): (283., 46.),
            ("Inicial", 0): (239., 54.),
            ("Inicial", 20): (164., 79.),
            ("Inicial", 50): (99., 131.),
            ("Final", -10): (283., 46.),
            ("Final", 0): (224., 58.),
            ("Final", 20): (139., 93.),
            ("Final", 50): (86., 151.),
        }
        self.assertEqual(len(tabla), 8)
        for _, fila in tabla.iterrows():
            tension, flecha = objetivos[
                (fila["Condición"], int(fila["Temperatura (°C)"]))
            ]
            self.assertLess(abs(fila["H (kN)"] / KG_F_A_KN - tension), 2.)
            self.assertLess(abs(fila["Flecha (m)"] * 100 - flecha), 1.)
            self.assertLess(abs(fila["Residual (m)"]), 1e-7)

    def test_vanos_independientes_y_estados_de_viento(self):
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2", "P3"],
            "X": [0., 40., 125.], "Y": [0., 0., 0.],
        })
        tabla = calcular_tablas_inicial_final(
            puntos, propiedades_aac(),
            EstadoReferenciaCFE(675., "Referencia de ensayo"),
            EstadoReferenciaCFE(585., "Referencia de ensayo"),
            [20., 50.],
            estados_climaticos=[("Viento", 20., 40., 0.)],
        )
        self.assertEqual(len(tabla), 12)
        t20 = tabla[(tabla["Condición"] == "Inicial") &
                    (tabla["Temperatura (°C)"] == 20.) &
                    (tabla["Viento (km/h)"] == 0.)]
        self.assertEqual(len(t20), 2)
        self.assertGreater(
            abs(t20.iloc[0]["H (kN)"] - t20.iloc[1]["H (kN)"]), 0.001
        )
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())
        self.assertTrue((tabla[tabla["Viento (km/h)"] > 0]["Lateral (m)"] > 0).all())

    def test_dimensionamiento_desde_limite_documentado(self):
        import numpy as np
        xyz = np.array([[0., 0., 0.], [80., 0., 0.]])
        p = propiedades_aac()
        hipotesis = [
            HipotesisDisenoCFE(
                "Hipótesis de prueba 0°C", 0., 0., 0., 3.5,
                "Límite sintético para ensayo, no límite CFE",
            ),
        ]
        res = calcular_parametro_cfe_desde_limites(
            xyz, p, hipotesis, H_min_kN=0.1, H_max_kN=5.,
        )
        self.assertGreater(res["parametro_P_m"], 0.)
        self.assertAlmostEqual(res["relacion_critica"], 1., delta=1e-5)

    def test_rechaza_condicion_final_sin_referencia(self):
        with self.assertRaises((ValueError, AttributeError)):
            calcular_tablas_inicial_final(
                vano(50.), propiedades_aac(),
                EstadoReferenciaCFE(495., "ENEE"), None, [20.]
            )


if __name__ == "__main__":
    unittest.main()
