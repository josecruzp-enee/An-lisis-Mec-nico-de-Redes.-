"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_auditoria_claros_cfe.py ===
"""Regresiones de terminología y cálculo geométrico en ruta CFE.

No validan las tablas ENEE ni un modelo de fluencia del ACSR.
"""
import math

import pytest

from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import vano_regulador
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import construir_hipotesis_cfe


def test_claro_regla_tres_vanos():
    luces = [40.0, 50.0, 60.0]
    esperado = math.sqrt(sum(l**3 for l in luces) / sum(luces))
    assert vano_regulador(luces) == pytest.approx(esperado)


def test_claro_regla_un_vano():
    assert vano_regulador([50.0]) == pytest.approx(50.0)


def test_cfe_admite_viento_reducido_y_hielo_cero():
    ini, fin = construir_hipotesis_cfe(
        19.0249, viento_max_kmh=120,
        viento_reducido_kmh=0, hielo_mm=0,
    )
    assert len(ini) == 1
    assert len(fin) == 4
    frio = next(h for h in fin if h.temperatura_C == -10)
    assert frio.viento_kmh == 0
    assert frio.hielo_mm == 0


def test_cfe_no_admite_espesor_negativo():
    with pytest.raises(ValueError):
        construir_hipotesis_cfe(
            19.0249, viento_max_kmh=120,
            viento_reducido_kmh=0, hielo_mm=-1,
        )


# === Casos conservados de tests/test_cfe_claro_diseno_y_claros_regla.py ===
"""Pruebas del acoplamiento CFE: referencias, conservación y claro regla.

Estos ensayos comprueban consistencia física y ausencia de consulta a
flechas ENEE; NO prueban equivalencia exacta con el programa SAGSEC.
"""
import unittest
import numpy as np

from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE,HipotesisDisenoCFE,
)
from Analisis_mecanico_conductores.tension_tendido.cfe_claro_diseno_y_claros_regla import (
    DisenoCFE,_H_50_desde_flecha,_H_inicial_por_compatibilidad,
    calcular_referencia_diseno,calcular_corridas_claros,
)
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural


class DisenoCfeTest(unittest.TestCase):
    def setUp(self):
        self.prop=PropiedadesConductorCFE(
            peso_kN_m=.00212,diametro_m=.01011,
            EA_inicial_kN=3000.,EA_final_kN=3976.3,
            alpha_inicial_por_C=1.921e-5,alpha_final_por_C=1.921e-5,
            ruptura_kN=19.0249,fuente="Conductor sintético con dimensiones ENEE",
        )
        self.diseno=DisenoCFE(
            claro_diseno_m=50.,
            flecha_final_referencia_50C_m=.4,
            epsilon_permanente=0.,
        )
        self.hf=[
            HipotesisDisenoCFE("16 C",16.,0.,0.,15.,"Límite sintético"),
            HipotesisDisenoCFE("0 C",0.,0.,0.,16.,"Límite sintético"),
        ]
        self.hi=[
            HipotesisDisenoCFE("0 C",0.,0.,0.,18.,"Límite sintético"),
        ]

    def test_catenaria_flecha_referencia_exacta(self):
        H=_H_50_desde_flecha(50.,.4,.00212)
        a=H/.00212
        f=a*(np.cosh(50/(2*a))-1)
        self.assertAlmostEqual(f,.4,delta=1e-8)

    def test_longitud_natural_inicial_y_final_ligadas(self):
        L=50.
        hf=_H_50_desde_flecha(L,.4,.00212)
        h0=_H_inicial_por_compatibilidad(L,hf,self.prop,0.)
        q=np.array([0.,0.,-self.prop.peso_kN_m])
        a=np.array([0.,0.,0.]);b=np.array([L,0.,0.])
        Ln_f=longitud_natural(resolver_catenaria(a,b,q,hf),self.prop.EA_final_kN)
        Ln_i=longitud_natural(resolver_catenaria(a,b,q,h0),self.prop.EA_inicial_kN)
        self.assertAlmostEqual(Ln_f,Ln_i,delta=1e-7)

    def test_ambas_condiciones_y_claros_separados(self):
        ref,r,tabla=calcular_corridas_claros(
            self.prop,self.diseno,self.hf,self.hi,
            [40.,50.],[20.,50.],
        )
        self.assertEqual(len(tabla),8)
        self.assertEqual(set(tabla["Condición"]),{"Inicial","Final"})
        self.assertEqual(set(tabla["Claro regla (m)"]),{40.,50.})
        self.assertGreater(ref["P50 final (m)"],0.)
        self.assertTrue((tabla["Residual (m)"].abs()<1e-7).all())

    def test_rechaza_flecha_invalida(self):
        with self.assertRaises(ValueError):
            _H_50_desde_flecha(50.,-1.,.00212)


# === Casos conservados de tests/test_cfe_doble_limite_horizontal_total.py ===
"""Regresiones de CFE: TH1/TH2 son H horizontales, RTS aplica a T total."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    construir_hipotesis_cfe,
)
from Analisis_mecanico_conductores.salidas.PDF.verificacion_hipotesis_cfe import verificar_cinco_hipotesis


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
