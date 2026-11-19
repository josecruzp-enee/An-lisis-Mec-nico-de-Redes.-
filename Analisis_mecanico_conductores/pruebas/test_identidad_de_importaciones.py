"""Pruebas de invariantes físicos y catálogo único tras eliminar rutas heredadas.

Preserva la identidad del catálogo y la invariante geométrica de Checa.
"""
from __future__ import annotations

import unittest

from comun.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR as catalogo_heredado

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import (
    resolver_cambio_estado, vano_regulador,
)
from Analisis_mecanico_conductores.catenaria.resolver_cable_tridimensional_bvp import resolver_cable_no_lineal
from Analisis_mecanico_conductores.tension_tendido.resolver_seccion_deslizante_ideal import resolver_seccion_deslizante
from Analisis_mecanico_conductores.conductores.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR


class CompatibilidadEtapa1Test(unittest.TestCase):
    def test_catalogo_comun_mantiene_identidad(self):
        pares=(
            (catalogo_heredado,CONDUCTORES_VIAKON_ACSR),
        )
        for antiguo,nuevo in pares:
            with self.subTest(funcion=nuevo.__class__.__name__):
                self.assertIs(antiguo,nuevo)

    def test_resultado_de_checa_permanece_inalterado(self):
        self.assertAlmostEqual(vano_regulador([45.53,45.53]),45.53,places=8)
        self.assertAlmostEqual(vano_regulador([30,60]),((30**3+60**3)/90)**.5,delta=1e-9)

    def test_el_catalogo_conserva_ficha_de_quail(self):
        ficha=CONDUCTORES_VIAKON_ACSR["2/0 ACSR — QUAIL"]
        self.assertGreater(ficha["carga_rotura_kN"],0)
        self.assertGreater(ficha["peso_kg_m"],0)


if __name__=="__main__":
    unittest.main()
