"""Pruebas de validación de contratos de entrada; no validan el diseño físico."""
import unittest
from analisis.modelos_datos import Conductor, EstadoClimatico, Nodo, Vano, Combinacion


def conductor(**cambios):
    datos = dict(nombre='ACSR_prueba', peso_kN_m=.01, diametro_m=.02,
                 H_tendido_kN=8, temperatura_tendido_C=20,
                 fuente='Ensayo sintético')
    datos.update(cambios)
    return Conductor(**datos)


class TestModelosEntrada(unittest.TestCase):
    def test_conductor_valido(self):
        self.assertEqual(conductor().H_tendido_kN, 8)

    def test_conductor_sin_nombre(self):
        with self.assertRaisesRegex(ValueError, 'nombre del conductor'):
            conductor(nombre=' ')

    def test_capacidad_admisible_requiere_fuente(self):
        with self.assertRaisesRegex(ValueError, 'fuente de tensión admisible'):
            conductor(tension_admisible_kN=10)

    def test_capacidad_admisible_con_fuente(self):
        self.assertEqual(conductor(tension_admisible_kN=10,
                         fuente_admisible='Especificación de ensayo').tension_admisible_kN, 10)

    def test_estado_climatico_sin_fuente(self):
        with self.assertRaisesRegex(ValueError, 'fuente del estado climático'):
            EstadoClimatico('viento', 20, 25, 90, '')

    def test_nodo_sin_identificador(self):
        with self.assertRaisesRegex(ValueError, 'nombre del nodo'):
            Nodo(' ', (0, 0, 0))

    def test_vano_sin_conductor(self):
        with self.assertRaisesRegex(ValueError, 'conductor del vano'):
            Vano('AB', 'A', 'B', (0, 0, 10), (0, 0, 10), '')

    def test_vano_con_extremos_iguales(self):
        with self.assertRaisesRegex(ValueError, 'extremos idénticos'):
            Vano('AA', 'A', 'A', (0, 0, 10), (0, 0, 10), 'ACSR_prueba')

    def test_combinacion_sin_estado(self):
        with self.assertRaisesRegex(ValueError, 'estado de la combinación'):
            Combinacion('normal', '', 'Ensayo')

    def test_combinacion_valida(self):
        self.assertEqual(Combinacion('normal', 'tendido', 'Ensayo').factor_conductor, 1)


if __name__ == '__main__':
    unittest.main()
