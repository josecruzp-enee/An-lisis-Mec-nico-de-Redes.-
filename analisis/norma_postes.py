# analisis/norma_postes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
import re

from .catalogos import POSTES_CONCRETO_TABLA_1, POSTES_CLASES_APENDICE
from .unidades import kgf_to_kN, lbf_to_kN


# ============================================================
# 1) MAPA DE ALIAS (TU NOMENCLATURA -> ID NORMATIVO)
# ------------------------------------------------------------
# Ajusta esto según tu norma/empresa.
# Ejemplo inicial (TEMPORAL): PM-40 se interpreta como PC-12-750.
# ============================================================
ALIAS_POSTES: Dict[str, str] = {
    "PM-40": "PC-12-750",
    "PC-40": "PC-12-750",
    "PC-35": "PC-10-450",
    "PC-30": "PC-9-450",
    # agrega más si usas otros...
}


# ============================================================
# Índices para búsqueda rápida
# ============================================================
_IDX_CONCRETO = {str(r["id"]).strip().upper(): r for r in POSTES_CONCRETO_TABLA_1}
_IDX_CLASES = {int(r["clase"]): r for r in POSTES_CLASES_APENDICE}


def _norm(s: str) -> str:
    return str(s).strip().upper()


def _resolver_id_normativo(tipo_poste: str) -> str:
    """
    Convierte tu nomenclatura (PM-40) a un ID normativo (PC-12-750),
    o deja el mismo si ya viene como ID normativo.
    """
    key = _norm(tipo_poste)
    if key in _IDX_CONCRETO:
        return key
    return _norm(ALIAS_POSTES.get(key, key))


def _parse_clase(tipo_poste: str) -> Optional[int]:
    """
    Permite usar en Excel: 'CLASE 3', 'Clase-3', 'CL-3', etc.
    """
    s = _norm(tipo_poste)
    m = re.search(r"(CLASE|CL)\s*[-:]?\s*(\d+)", s)
    if not m:
        return None
    try:
        return int(m.group(2))
    except Exception:
        return None


# ============================================================
# API pública para el resto del proyecto
# ============================================================
def obtener_ficha_poste(tipo_poste: str) -> Dict[str, Any]:
    """
    Retorna una ficha unificada del poste (normativo o por clase).
    """
    tipo_poste = str(tipo_poste).strip()
    clase = _parse_clase(tipo_poste)
    if clase is not None and clase in _IDX_CLASES:
        r = _IDX_CLASES[clase]
        return {
            "fuente": "CLASES_APENDICE",
            "id": f"CLASE {clase}",
            "clase": clase,
            "carga_horizontal_kN": float(r["carga_horizontal_kN"]),
        }

    id_norm = _resolver_id_normativo(tipo_poste)
    if id_norm in _IDX_CONCRETO:
        r = _IDX_CONCRETO[id_norm]
        return {
            "fuente": "CONCRETO_TABLA_1",
            "id": id_norm,
            "longitud_m": float(r["longitud_m"]),
            "diam_punta_cm": float(r["diam_punta_cm"]),
            "diam_base_cm": float(r["diam_base_cm"]),
            "carga_ruptura_kgf": float(r["carga_ruptura_kgf"]),
            "carga_ruptura_lbf": float(r["carga_ruptura_lbf"]),
            "notas": str(r.get("notas", "") or ""),
        }

    # No encontrado
    return {
        "fuente": "NO_ENCONTRADO",
        "id": id_norm,
    }


def altura_poste_m(tipo_poste: str, default_m: float = 12.0) -> float:
    """
    Altura del poste (m):
    - Si viene por tabla normativo: longitud_m
    - Si viene por clase: no trae longitud -> default_m
    """
    ficha = obtener_ficha_poste(tipo_poste)
    if ficha.get("fuente") == "CONCRETO_TABLA_1":
        return float(ficha["longitud_m"])
    return float(default_m)


def h_amarre_tipica_m(tipo_poste: str, default_m: float = 7.5, offset_desde_punta_m: float = 0.30) -> float:
    """
    Altura de amarre típica (m) para cálculos rápidos:
    h_amarre ≈ altura_poste - offset_desde_punta
    (offset por defecto 0.30 m, consistente con el apéndice de carga)
    """
    h = altura_poste_m(tipo_poste, default_m=max(default_m, 1.0))
    val = h - float(offset_desde_punta_m)
    return float(val if val > 0 else default_m)


def H_max_poste_kN(tipo_poste: str, default_kN: float = 9999.0) -> float:
    """
    Capacidad horizontal 'H_max' (kN) unificada:
    - Si viene por CLASE: usa carga_horizontal_kN (ya está en kN)
    - Si viene por TABLA 1: convierte carga_ruptura (kgf o lbf) -> kN (carga última)
      (FASE 1: se usa como referencia base. En FASE 2 aquí aplicarás FS, modelo de esfuerzos, etc.)
    """
    ficha = obtener_ficha_poste(tipo_poste)

    if ficha.get("fuente") == "CLASES_APENDICE":
        return float(ficha["carga_horizontal_kN"])

    if ficha.get("fuente") == "CONCRETO_TABLA_1":
        # Preferimos kgf si existe, si no lbf.
        kgf = ficha.get("carga_ruptura_kgf", None)
        if kgf is not None:
            return float(kgf_to_kN(float(kgf)))
        lbf = ficha.get("carga_ruptura_lbf", None)
        if lbf is not None:
            return float(lbf_to_kN(float(lbf)))

    return float(default_kN)
