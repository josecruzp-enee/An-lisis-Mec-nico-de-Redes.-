"""Pruebas de regresión de decisiones estructurales preliminares."""
import unittest
import pandas as pd

from analisis.decision_soporte import decidir_fila, cumple_poste
from analisis.norma_postes import H_max_poste_kN


class TestDecisionSegura(unittest.TestCase):
    def fila(self, **cambios):
        base = {
            "Espacio Retenida": "SI",
            "Retenidas": 1,
            "Cumple cimentación": "SI",
            "Cumple poste": "SI",
            "Cumple retenida": "SI",
        }
        base.update(cambios)
        return pd.Series(base)

    def test_poste_desconocido_no_aprueba(self):
        self.assertEqual(H_max_poste_kN("POSTE_DESCONOCIDO"), 0.0)
        self.assertEqual(cumple_poste(0, 0), "NO")

    def test_sin_espacio_no_aprueba_autosoportado(self):
        solucion, _ = decidir_fila(self.fila(**{"Espacio Retenida": "NO"}))
        self.assertEqual(solucion, "REQUIERE DISEÑO")

    def test_retenida_insuficiente_no_aprueba(self):
        solucion, _ = decidir_fila(self.fila(**{"Cumple retenida": "NO"}))
        self.assertEqual(solucion, "REQUIERE DISEÑO")

    def test_cimentacion_no_aprueba(self):
        solucion, _ = decidir_fila(self.fila(**{"Cumple cimentación": "NO"}))
        self.assertEqual(solucion, "REQUIERE DISEÑO")

    def test_sin_retenida_requiere_verificar_poste(self):
        solucion, _ = decidir_fila(self.fila(**{"Retenidas": 0, "Cumple poste": "NO"}))
        self.assertEqual(solucion, "REQUIERE DISEÑO")


if __name__ == "__main__":
    unittest.main()
