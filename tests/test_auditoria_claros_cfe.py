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
