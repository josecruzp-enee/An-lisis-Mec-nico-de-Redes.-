# analisis/norma_postes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any, Optional
import re

from .catalogos import POSTES_CONCRETO_TABLA_1, POSTES_CLASES_APENDICE
from .unidades import kgf_to_kN, lbf_to_kN


# ============================================================
# 0) CONFIGURACIÓN / CONSTANTES
# ============================================================

# Default de altura si el poste viene "por clase" o no se encuentra en tablas
DEFAULT_ALTURA_POSTE_M: float = 12.0

# Offset desde la punta (m) hasta el punto típico de amarre del primario (cruceta superior)
# Nota: si no hay dato específico en catálogo, se usa este valor.
DEFAULT_OFFSET_AMARRE_DESDE_PUNTA_M: float = 2.0

# Default de amarre final (para evitar negativos si algo raro llega)
DEFAULT_H_AMARRE_M: float = 7.5


# ============================================================
# 1) MAPA DE ALIAS (TU NOMENCLATURA -> ID NORMATIVO)
# ============================================================
ALIAS_POSTES: Dict[str, str] = {
    "PM-40": "PC-12-750",
    "PC-40": "PC-12-750",
    "PC-35": "PC-10-450",
    "PC-30": "PC-9-450",
    # agrega más si usas otros...
}


# ============================================================
# 2) CATÁLOGO DE PUNTOS DE AMARRE (OFFSET DESDE PUNTA)
# ------------------------------------------------------------
# OFFSETS en metros (m) desde la punta hacia abajo.
# "uso": primario | retenida | luminaria | telefonica | ctv ...
# Clave: ID normativo (PC-12-750, etc.).
# ============================================================
PUNTOS_AMARRE_DESDE_PUNTA_M: Dict[str, Dict[str, float]] = {
    "PC-9-450": {    # ~ "PC-30"
        "primario": 2.00,
        "retenida": 2.20,
        "luminaria": 5.00,
    },
    "PC-10-450": {   # ~ "PC-35"
        "primario": 2.00,
        "retenida": 2.20,
        "luminaria": 5.40,
    },
    "PC-12-750": {   # ~ "PC-40"
        "primario": 2.00,
        "retenida": 2.20,
        "luminaria": 6.00,
    },
}


# ============================================================
# 3) ÍNDICES PARA BÚSQUEDA RÁPIDA
# ============================================================
_IDX_CONCRETO = {str(r["id"]).strip().upper(): r for r in POSTES_CONCRETO_TABLA_1}
_IDX_CLASES = {int(r["clase"]): r for r in POSTES_CLASES_APENDICE}


# ============================================================
# 4) UTILIDADES INTERNAS
# ============================================================
def _norm(s: str) -> str:
    return str(s).strip().upper()


def _resolver_id_normativo(tipo_poste: str) -> str:
    """
    Convierte tu nomenclatura (PM-40, PC-40) a un ID normativo (PC-12-750),
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
# 5) API PÚBLICA: FICHA DEL POSTE
# ============================================================
def obtener_ficha_poste(tipo_poste: str) -> Dict[str, Any]:
    tipo_poste = str(tipo_poste).strip()

    # 1) Clase
    clase = _parse_clase(tipo_poste)
    if clase is not None and clase in _IDX_CLASES:
        r = _IDX_CLASES[clase]
        return {
            "fuente": "CLASES_APENDICE",
            "id": f"CLASE {clase}",
            "clase": clase,
            "carga_horizontal_kN": float(r["carga_horizontal_kN"]),
        }

    # 2) Tabla concreta (normativo)
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

    # 3) No encontrado
    return {"fuente": "NO_ENCONTRADO", "id": id_norm}


# ============================================================
# 6) ALTURA DEL POSTE
# ============================================================
def altura_poste_m(tipo_poste: str, default_m: float = DEFAULT_ALTURA_POSTE_M) -> float:
    ficha = obtener_ficha_poste(tipo_poste)
    if ficha.get("fuente") == "CONCRETO_TABLA_1":
        return float(ficha["longitud_m"])
    return float(default_m)


# ============================================================
# 7) CAPACIDAD HORIZONTAL (kN)
# ============================================================
def H_max_poste_kN(tipo_poste: str, default_kN: float = 9999.0) -> float:
    ficha = obtener_ficha_poste(tipo_poste)

    if ficha.get("fuente") == "CLASES_APENDICE":
        return float(ficha["carga_horizontal_kN"])

    if ficha.get("fuente") == "CONCRETO_TABLA_1":
        kgf = ficha.get("carga_ruptura_kgf", None)
        if kgf is not None:
            return float(kgf_to_kN(float(kgf)))
        lbf = ficha.get("carga_ruptura_lbf", None)
        if lbf is not None:
            return float(lbf_to_kN(float(lbf)))

    return float(default_kN)


# ============================================================
# 8) AMARRE "RÁPIDO" (compatibilidad)
# ============================================================
def h_amarre_tipica_m(
    tipo_poste: str,
    default_m: float = DEFAULT_H_AMARRE_M,
    offset_desde_punta_m: float = DEFAULT_OFFSET_AMARRE_DESDE_PUNTA_M,
) -> float:
    h = altura_poste_m(tipo_poste, default_m=max(default_m, 1.0))
    val = h - float(offset_desde_punta_m)
    return float(val if val > 0 else default_m)


# ============================================================
# 9) AMARRE NORMATIVO (por catálogo)
# ============================================================
def offset_amarre_desde_punta_m(
    tipo_poste: str,
    *,
    uso: str = "primario",
    default_m: float = DEFAULT_OFFSET_AMARRE_DESDE_PUNTA_M,
) -> float:
    ficha = obtener_ficha_poste(tipo_poste)
    id_norm = str(ficha.get("id", "") or "").strip().upper()

    if not id_norm or ficha.get("fuente") != "CONCRETO_TABLA_1":
        return float(default_m)

    return float(PUNTOS_AMARRE_DESDE_PUNTA_M.get(id_norm, {}).get(str(uso).strip().lower(), default_m))


def h_amarre_norma_m(
    tipo_poste: str,
    *,
    uso: str = "primario",
    default_h_poste_m: float = DEFAULT_ALTURA_POSTE_M,
    default_offset_m: float = DEFAULT_OFFSET_AMARRE_DESDE_PUNTA_M,
    default_h_amarre_m: float = DEFAULT_H_AMARRE_M,
) -> float:
    """
    Calcula h_amarre (m) desde terreno:
      h_amarre = altura_poste - offset_desde_punta(uso)
    """
    h_poste = altura_poste_m(tipo_poste, default_m=default_h_poste_m)
    off = offset_amarre_desde_punta_m(tipo_poste, uso=uso, default_m=default_offset_m)
    val = float(h_poste) - float(off)
    return float(val if val > 0 else default_h_amarre_m)
