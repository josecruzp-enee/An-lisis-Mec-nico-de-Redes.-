"""Regresiones de CFE: TH1/TH2 son H horizontales, RTS aplica a T total."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    construir_hipotesis_cfe,
)
from salidas.PDF.verificacion_hipotesis_cfe import verificar_cinco_hipotesis


class DobleLimiteCFE(unittest.TestCase):
    def test_h5_invalida_por_h_aunque_t_total_cumpla(self):
        tabla = pd.DataFrame([{
            "Condición": "Final", "Hipótesis": "CFE viento máximo",
            "Temperatura (°C)": 0., "Viento (km/h)": 120.,
            "Hielo (mm)": 0., "H (kN)": 5.70, "T máx. (kN)": 6.0,
        }])
        verificacion = verificar_cinco_hipotesis(
            tabla, ruptura_kN=19.4774, nombre_conductor="RAVEN",
            viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=6.,
        )
        h5 = verificacion.loc[verificacion["Código"] == "H5"].iloc[0]
        self.assertEqual(h5["Estado"], "NO CUMPLE")
        self.assertAlmostEqual(h5["Límite H (kN)"], 5.618)
        self.assertAlmostEqual(h5["Límite (kN)"], 19.4774 * .45)
        self.assertAlmostEqual(h5["H máxima (kN)"], 5.70)

    def test_cumple_ambos_limites(self):
        tabla = pd.DataFrame([{
            "Condición": "Final", "Hipótesis": "CFE viento máximo",
            "Temperatura (°C)": 0., "Viento (km/h)": 120.,
            "Hielo (mm)": 0., "H (kN)": 5.5, "T máx. (kN)": 5.6,
        }])
        resultado = verificar_cinco_hipotesis(
            tabla, ruptura_kN=19.4774, nombre_conductor="RAVEN",
            viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=6.,
        )
        self.assertEqual(resultado.iloc[-1]["Estado"], "CUMPLE")


if __name__ == "__main__":
    unittest.main()
