# analisis/mecanica.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from analisis.catalogos import CONDUCTORES_ACSR, RETENIDAS_RECOMENDADAS, POSTES, CAP_RETENIDA_ULT_LBF
from analisis.unidades import kgf_to_kN, kg_m_to_kN_m, lbf_to_kN

def tension_trabajo_kN(calibre: str, fraccion_trabajo: float) -> float:
    if calibre not in CONDUCTORES_ACSR:
        raise ValueError(f"Calibre no válido: {calibre}")
    tr_kgf = CONDUCTORES_ACSR[calibre]["TR_kgf"]
    return kgf_to_kN(tr_kgf) * float(fraccion_trabajo)

def peso_lineal_kN_m(calibre: str) -> float:
    if calibre not in CONDUCTORES_ACSR:
        raise ValueError(f"Calibre no válido: {calibre}")
    return kg_m_to_kN_m(CONDUCTORES_ACSR[calibre]["peso_kg_m"])

def retenida_recomendada(calibre: str) -> str:
    return RETENIDAS_RECOMENDADAS.get(calibre, "N/D")

def H_max_poste_kN(tipo_poste: str, default: float = 9999.0) -> float:
    return float(POSTES.get(tipo_poste, {}).get("H_max_kN", default))

def capacidad_retenida_admisible_kN(cable_ret: str, FS_ret: float) -> float:
    ult_lbf = CAP_RETENIDA_ULT_LBF.get(str(cable_ret).strip())
    if ult_lbf is None:
        return 0.0
    return lbf_to_kN(ult_lbf) / float(FS_ret)
