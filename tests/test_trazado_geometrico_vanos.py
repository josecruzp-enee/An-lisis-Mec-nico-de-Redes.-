"""Trazado XY con remates: visualización idéntica a la topología del motor."""
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from Analisis_mecanico_conductores.interfaz.trazado_geometrico_vanos import (
    crear_figura_trazado,
)


class TrazadoGeometricoVanosTest(unittest.TestCase):
    def test_remate_intermedio_segmenta_cinco_vanos(self):
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2", "P3", "P4", "P5", "P6"],
            "X": [0, 50, 110, 200, 320, 470],
            "Y": [0, 0, 0, 0, 0, 0],
            "Remate": ["SI", "NO", "SI", "NO", "NO", "SI"],
        })
        fig, vanos, secciones = crear_figura_trazado(puntos)
        try:
            self.assertEqual(len(vanos), 5)
            self.assertEqual(vanos["Sección"].tolist(), ["S1", "S1", "S2", "S2", "S2"])
            self.assertEqual(vanos["Claro horizontal (m)"].tolist(), [50, 60, 90, 120, 150])
            self.assertEqual(secciones["Número de vanos"].tolist(), [2,3])
            self.assertEqual(len(fig.axes), 1)
        finally:
            plt.close(fig)

    def test_single_section_without_remate_column(self):
        p = pd.DataFrame({"Punto":["P1","P2","P3"],
                          "X":[0,120,270],"Y":[0,0,0]})
        fig, vanos, secciones=crear_figura_trazado(p)
        try:
            self.assertEqual(vanos["Claro horizontal (m)"].tolist(), [120,150])
            self.assertEqual(secciones["Sección"].tolist(), ["S1"])
        finally:
            plt.close(fig)
