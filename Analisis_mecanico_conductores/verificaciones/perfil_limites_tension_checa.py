"""Perfil técnico de límites dinámicos ACSR descritos por Luis María Checa.

Checa, «Líneas de Transporte de Energía», §4.3 (tensado al límite
dinámico, TCD y THF; comprobar edición concreta al citar páginas):
  - TCD: 15 °C, sin viento ni hielo, 20 % de carga de rotura.
  - THF: -5 °C, sin viento ni hielo, 22.5 % de carga de rotura.
Son límites de REFERENCIA de ese contexto técnico, NO normas ENEE.
No se presume límite estático de rotura bajo máximo viento o hielo.
"""
from __future__ import annotations

from math import isfinite

import pandas as pd

NOMBRE_PERFIL="Checa — TCD/THF ACSR (referencia técnica)"
REFERENCIA=(
    "Luis María Checa, Líneas de Transporte de Energía, "
    "cap. 4, tensado al límite dinámico (TCD/THF); "
    "referencia técnica, NO norma ENEE."
)


def construir_hipotesis_checa_acsr(carga_rotura_kN):
    """Calcula límites TCD/THF (kN) a partir de RTS del conductor seleccionado.

    El valor RTS debe ser kN positivos, procedentes de una sola ficha de
    conductor (ENEE o Viakon). No crea criterio de viento/hielo.
    """
    try:
        rotura=float(carga_rotura_kN)
    except (ValueError,TypeError) as exc:
        raise ValueError("Se requiere carga de rotura válida en kN") from exc
    if not isfinite(rotura) or rotura<=0:
        raise ValueError("La carga de rotura debe ser finita y positiva")
    return pd.DataFrame([
        {
            "Hipotesis":"TCD — Checa",
            "Temperatura_C":15.,
            "Viento_ms":0.,
            "T_limite_kN":.20*rotura,
            "Fuente_limite":REFERENCIA,
            "Criterio_diseno":"TCD ACSR ≤ 20 % RTS a 15 °C, sin sobrecarga",
        },
        {
            "Hipotesis":"THF — Checa",
            "Temperatura_C":-5.,
            "Viento_ms":0.,
            "T_limite_kN":.225*rotura,
            "Fuente_limite":REFERENCIA,
            "Criterio_diseno":"THF ACSR ≤ 22.5 % RTS a -5 °C, sin sobrecarga",
        },
    ])
