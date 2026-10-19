"""Pruebas de cargas estructurales: convención de signos y seguridad."""
import unittest

from analisis.estados_limite import Estado, estado_conjunto
from analisis.resistencia_postes import demandas_poste, verificar_poste


def _ficha(valor, unidad, tipo='admisible'):
    """Capacidad de prueba sintética; no corresponde a poste real."""
    return {'valor': valor, 'tipo': tipo, 'metodo': 'servicio',
            'unidad': unidad, 'fuente': 'ensayo sintético unitario'}


class TestResistenciaPostes(unittest.TestCase):
    def test_compresion_y_traccion_no_se_confunden(self):
        comp = demandas_poste([0, 0, -12, 0, 0, 0])
        trac = demandas_poste([0, 0, 12, 0, 0, 0])
        self.assertEqual(comp['axial'], 12)
        self.assertNotIn('traccion_axial', comp)
        self.assertEqual(trac['axial'], 0)
        self.assertEqual(trac['traccion_axial'], 12)

    def test_traccion_requiere_capacidad_diferente(self):
        cap = {'axial': _ficha(30, 'kN')}
        checks = verificar_poste([0, 0, 5, 0, 0, 0], cap)
        traccion = next(v for v in checks if v.nombre == 'traccion_axial')
        self.assertEqual(traccion.estado, Estado.NO_VERIFICABLE)

    def test_flexion_biaxial_interaccion_sin_inventar_resistencia(self):
        cap = {
            'axial': _ficha(20, 'kN'),
            'flexion_x': _ficha(10, 'kN·m'),
            'flexion_y': _ficha(10, 'kN·m'),
            'flexocompresion': {'modelo': 'suma_lineal',
                                'fuente': 'criterio sintético',
                                'metodo': 'servicio'},
        }
        checks = verificar_poste([0, 0, -10, 4, 3, 0], cap)
        interaccion = next(v for v in checks if v.nombre == 'flexocompresion')
        self.assertEqual(interaccion.estado, Estado.NO_CUMPLE)
        self.assertAlmostEqual(interaccion.utilizacion, 1.2)
        self.assertEqual(estado_conjunto(checks), Estado.NO_CUMPLE)

    def test_ruptura_y_unidad_incompatible_no_aprueban(self):
        cap = {'axial': _ficha(9999, 'kN', tipo='ruptura'),
               'flexion_x': _ficha(5, 'kN')}
        checks = verificar_poste([0, 0, -2, 1, 0, 0], cap)
        for nombre in ('axial', 'flexion_x'):
            v = next(v for v in checks if v.nombre == nombre)
            self.assertEqual(v.estado, Estado.NO_VERIFICABLE)

    def test_entrada_no_finita_o_incompleta(self):
        for fuerzas in ([1, 2], [0, 0, float('nan'), 0, 0, 0]):
            with self.assertRaises(ValueError):
                verificar_poste(fuerzas, {})
        with self.assertRaises(ValueError):
            verificar_poste([0] * 6, {}, desplazamiento=[0, 0, 0])
        with self.assertRaises(ValueError):
            verificar_poste([0] * 6, None)


if __name__ == '__main__':
    unittest.main()
