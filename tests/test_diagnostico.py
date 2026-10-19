# Pruebas de diagnóstico para el estado de main.
# Ejecutar: python -m unittest discover -s tests -v
# No certifican el diseño completo; comprueban propiedades matemáticas puntuales.
import math
import unittest
from analisis.geometria import deflexion_deg
from analisis.perfil import sag_catenaria_m
from analisis.norma_postes import H_max_poste_kN

class PruebasBase(unittest.TestCase):
    def test_tangente_angulos(self):
        self.assertAlmostEqual(deflexion_deg((0,0),(10,0),(20,0)),180.0)
    def test_giro_recto(self):
        self.assertAlmostEqual(deflexion_deg((0,0),(10,0),(10,10)),90.0)
    def test_catenaria_limite_parabolico(self):
        L,w,H=50.0,0.00957,4.0
        calculado=sag_catenaria_m(L,w,H)
        aproximado=w*L*L/(8*H)
        self.assertAlmostEqual(calculado,aproximado,delta=0.0005)
    @unittest.expectedFailure
    def test_poste_desconocido_no_puede_aprobar(self):
        # Defecto conocido: actual default=9999 kN. Debe corregirse para devolver estado no verificable.
        self.assertTrue(math.isnan(H_max_poste_kN("POSTE-NO-CATALOGADO",default_kN=float("nan"))))
        self.assertNotEqual(H_max_poste_kN("POSTE-NO-CATALOGADO"),9999.0)

if __name__=="__main__":
    unittest.main()
