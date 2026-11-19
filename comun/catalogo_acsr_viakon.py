"""Catálogo trazable de conductores ACSR Viakon.

Fuente primaria: Viakon, Manual del Electricista, junio de 2020,
tablas 'Cable Viakon de aluminio desnudo con alma de acero (ACSR)',
páginas impresas 18, 19 y 20 (PDF páginas 23, 24 y 25 contando portada).

Los datos son NOMINALES / APROXIMADOS del fabricante. La carga de
ruptura NO es tensión admisible de diseño. Ni EA ni coeficiente de
dilatación aparecen en estas tablas, por lo que se mantienen en None.
No usar ACSR/AS (núcleo de acero recubierto de aluminio) como si fuera
el ACSR convencional de alma galvanizada.

Los nombres de calibre 266.8, 336.4 y 477 pueden corresponder a varias
construcciones. La clave de producto incluye el código de ave siempre
que sea posible; las claves históricas conservan código explícito.
"""
from __future__ import annotations

from copy import deepcopy
from math import pi, isfinite

FUENTE_VIAKON_ACSR = "https://viakon.com/wp-content/uploads/2020/11/ManualElectricista_2020.pdf"
DOCUMENTO_VIAKON = "Viakon, Manual del Electricista, junio 2020, ACSR"

# clave de selección, código, calibre, aluminio N/hilo(mm), acero N/hilo(mm),
# área mm², diámetro total mm, masa kg/km, carga rotura kgf, Rdc ohm/km, página.
_FILAS = (
    ("6 ACSR — TURKEY", "TURKEY", "6", 6, 1.68, 1, 1.68, 13.30, 5.04, 53.70, 540, 2.15, 18),
    ("5 ACSR — THRUSH", "THRUSH", "5", 6, 1.89, 1, 1.89, 16.76, 5.67, 68.0, 677, 1.71, 18),
    ("4 ACSR — SWAN", "SWAN", "4", 6, 2.12, 1, 2.12, 21.15, 6.36, 86.50, 846, 1.35, 18),
    ("3 ACSR — SWALLOW", "SWALLOW", "3", 6, 2.38, 1, 2.38, 26.67, 7.14, 107.8, 1044, 1.08, 18),
    ("2 ACSR — SPARROW", "SPARROW", "2", 6, 2.67, 1, 2.67, 33.62, 8.01, 135.7, 1292, 0.853, 18),
    ("1 ACSR — ROBIN", "ROBIN", "1", 6, 3.00, 1, 3.00, 42.41, 9.00, 171.3, 1618, 0.674, 18),
    ("1/0 ACSR — RAVEN", "RAVEN", "1/0", 6, 3.37, 1, 3.37, 53.48, 10.11, 216.2, 1986, 0.535, 18),
    ("2/0 ACSR — QUAIL", "QUAIL", "2/0", 6, 3.78, 1, 3.78, 67.43, 11.34, 272.0, 2398, 0.424, 18),
    ("3/0 ACSR — PIGEON", "PIGEON", "3/0", 6, 4.25, 1, 4.25, 85.01, 12.75, 344.3, 2996, 0.336, 18),
    ("4/0 ACSR — PENGUIN", "PENGUIN", "4/0", 6, 4.77, 1, 4.77, 107.2, 14.31, 433.1, 3776, 0.267, 18),
    ("266.8 MCM — OWL", "OWL", "266.8", 6, 5.36, 7, 1.79, 135.2, 16.07, 511.1, 4330, 0.208, 18),
    ("266.8 MCM — WAXWING", "WAXWING", "266.8", 18, 3.09, 1, 3.09, 135.2, 15.46, 430.4, 3123, 0.213, 18),
    ("266.8 MCM — PARTRIDGE", "PARTRIDGE", "266.8", 26, 2.57, 7, 2.00, 135.2, 16.30, 545.4, 5121, 0.214, 18),
    ("300 MCM — OSTRICH", "OSTRICH", "300", 26, 2.73, 7, 2.12, 152.0, 17.27, 614.2, 5755, 0.190, 18),
    ("300 MCM — PIPER", "PIPER", "300", 30, 2.54, 7, 2.54, 152.0, 17.78, 699.3, 6999, 0.187, 18),
    ("336.4 MCM — MERLIN", "MERLIN", "336.4", 18, 3.47, 1, 3.47, 170.5, 17.35, 542.8, 3939, 0.169, 19),
    ("336.4 MCM — LINNET", "LINNET", "336.4", 26, 2.89, 7, 2.25, 170.5, 18.29, 689.9, 6423, 0.170, 19),
    ("397.5 MCM — LARK", "LARK", "397.5", 30, 2.92, 7, 2.92, 201.4, 20.44, 924.4, 9245, 0.144, 19),
    ("336.4 MCM — ORIOLE", "ORIOLE", "336.4", 30, 2.69, 7, 2.69, 170.5, 18.83, 784.5, 7887, 0.170, 19),
    ("397.5 MCM — IBIS", "IBIS", "397.5", 26, 3.14, 7, 2.44, 201.4, 19.89, 813.4, 6648, 0.143, 19),
    ("477 MCM — PELICAN", "PELICAN", "477", 18, 4.14, 1, 4.14, 241.7, 20.70, 772.7, 5318, 0.119, 19),
    ("477 MCM — HAWK", "HAWK", "477", 26, 3.44, 7, 2.67, 241.7, 21.77, 975.8, 8825, 0.119, 19),
    ("477 MCM — FLICKER", "FLICKER", "477", 24, 3.58, 7, 2.39, 241.7, 21.49, 914.6, 7801, 0.119, 19),
    ("500 MCM — HERON", "HERON", "500", 30, 3.28, 7, 3.28, 253.4, 22.95, 1166.0, 11090, 0.112, 19),
    ("556.5 MCM — OSPREY", "OSPREY", "556.5", 18, 4.47, 1, 4.47, 282.0, 22.35, 900.8, 6265, 0.102, 19),
    ("556.5 MCM — PARAKEET", "PARAKEET", "556.5", 24, 3.87, 7, 2.58, 282.0, 23.22, 1068.0, 9025, 0.102, 19),
    ("556.5 MCM — DOVE", "DOVE", "556.5", 26, 3.72, 7, 2.89, 282.0, 23.55, 1142.0, 10322, 0.102, 19),
    ("556.5 MCM — EAGLE", "EAGLE", "556.5", 30, 3.46, 7, 3.46, 282.0, 24.22, 1228.0, 12550, 0.103, 19),
    ("477 MCM — HEN", "HEN", "477", 30, 3.20, 7, 3.20, 241.7, 22.40, 1110.0, 10743, 0.120, 19),
    ("605 MCM — PEACOCK", "PEACOCK", "605", 24, 4.03, 7, 2.69, 306.6, 24.19, 1159.0, 9812, 0.0941, 19),
    ("605 MCM — DUCK", "DUCK", "605", 54, 2.69, 7, 2.69, 306.6, 24.19, 1158.0, 10206, 0.0925, 19),
    ("636 MCM — ROOK", "ROOK", "636", 24, 4.14, 7, 2.76, 322.3, 24.84, 1222.0, 10322, 0.0895, 20),
    ("795 MCM — DRAKE", "DRAKE", "795", 26, 4.44, 7, 3.45, 402.8, 28.11, 1626, 14283, 0.0716, 20),
)


def _construir():
    catalogo={}
    for (clave,codigo,calibre,na,da,ns,ds,area,diametro,masa,rotura,r20,pagina) in _FILAS:
        # La sección declarada por Viakon corresponde al ALUMINIO, no
        # al área compuesta de acero + aluminio. Detecta errores de copia.
        area_al_hilos = na * pi * (da / 2)**2
        if not isfinite(area_al_hilos) or abs(area_al_hilos-area)/area > .015:
            raise ValueError(
                f"{codigo}: área nominal Al incompatible con {na} hilos "
                f"de diámetro {da} mm: {area_al_hilos:.3f} vs {area:g} mm²"
            )
        catalogo[clave] = {
            "fabricante": "Viakon",
            "familia": "ACSR, aluminio 1350-H19 / alma acero galvanizado",
            "codigo": codigo,
            "nombre_pajarito": codigo,
            "nombre_mostrado": clave,
            "calibre": calibre,
            "hilos_aluminio": na,
            "diametro_hilo_aluminio_mm": da,
            "hilos_acero": ns,
            "diametro_hilo_acero_mm": ds,
            "area_nominal_mm2": area,
            "diametro_mm": diametro,
            "diametro_m": diametro / 1000,
            "peso_kg_km": masa,
            "peso_kg_m": masa / 1000,
            "TR_kgf": rotura,
            "carga_rotura_kN": rotura * 9.80665 / 1000,
            "resistencia_dc_20_ohm_km": r20,
            "EA_kN": None,
            "alpha_por_C": None,
            "fuente": FUENTE_VIAKON_ACSR,
            "documento": DOCUMENTO_VIAKON,
            "pagina_impresa": pagina,
            "estado_propiedades_mecanicas": (
                "INCOMPLETO: faltan EA y alpha de ficha del modelo específico"
            ),
        }
    return catalogo


CONDUCTORES_VIAKON_ACSR = _construir()


def ficha_viakon_acsr(clave):
    """Entrega copia aislada para evitar alterar catálogo global."""
    if clave not in CONDUCTORES_VIAKON_ACSR:
        raise KeyError("Conductor Viakon no catalogado: "+str(clave))
    return deepcopy(CONDUCTORES_VIAKON_ACSR[clave])


def propiedades_mecanicas_documentadas(clave):
    """No inventar EA y alpha; expone qué falta para cálculo definitivo."""
    ficha=ficha_viakon_acsr(clave)
    faltan=[p for p in ("EA_kN","alpha_por_C") if ficha[p] is None]
    return {"conductor":clave,"faltantes":faltan,"completo":not faltan}
