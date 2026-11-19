"""Regresion del tramo de usuario P1..P6, 510 m y amarres nivelados.

No utiliza valores de flecha, H o P publicados como entradas.
Verifica magnitudes distintas de CFE: max(T) y H en hipotesis H4/H5.
"""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01, ejecutar_corridas_cfe_por_vano,
)
from Analisis_mecanico_conductores.salidas.PDF.verificacion_hipotesis_cfe import verificar_cinco_hipotesis


class Tramo510CFE(unittest.TestCase):
    def test_tramo_50_70_120_150_120(self):
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2", "P3", "P4", "P5", "P6"],
            "X": [0., 50., 120., 240., 390., 510.],
            "Y": [0.] * 6, "Altitud": [0.] * 6,
            "Altura_Amarre_m": [9.5] * 6,
        })
        inicial, final = seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final, viento_max_kmh=120.,
            viento_reducido_kmh=0., hielo_mm=6.,
            temperaturas_C=[0., 16., 20., 30., 50.],
        )
        self.assertEqual(len(resumen), 2)
        self.assertEqual(set(tabla["Luz (m)"]), {50., 70., 120., 150.})
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())
        control = verificar_cinco_hipotesis(
            tabla, ruptura_kN=inicial["ruptura_kN"],
            nombre_conductor="RAVEN", viento_max_kmh=120.,
            viento_reducido_kmh=0., hielo_mm=6.,
        )
        self.assertEqual(len(control), 5)
        self.assertTrue((control["Estado"] == "CUMPLE").all(),
                        control.to_string(index=False))
        h5 = control.loc[control["Código"] == "H5"].iloc[0]
        self.assertLessEqual(h5["H máxima (kN)"], 5.618 * (1 + 1e-6))
        self.assertLessEqual(h5["T máxima (kN)"],
                             inicial["ruptura_kN"] * .45 * (1 + 1e-6))


if __name__ == "__main__":
    unittest.main()
