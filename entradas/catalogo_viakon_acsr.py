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

FUENTE_VIAKON_ACSR = "https://viakon.com/wp-content/uploads/2020/11/ManualElectricista_2020.pdf"
DOCUMENTO_VIAKON = "Viakon, Manual del Electricista, junio 2020, ACSR"

# clave de selección, código, calibre, aluminio N/hilo(mm), acero N/hilo(mm),
# área mm², diámetro total mm, masa kg/km, carga rotura kgf, Rdc ohm/km, página.
_FILAS = (
    ("6 ACSR — TURKEY", "TURKEY", "6", 6, 1.68, 1, 1.68, 13.30, 5.04, 53.70, 540, 2.15, 18),
    ("4 ACSR — SWAN", "SWAN", "4", 6, 2.12, 1, 2.12, 21.15, 6.36, 86.50, 846, 1.35, 18),
    ("2 ACSR — SPARROW", "SPARROW", "2", 6, 2.67, 1, 2.67, 33.62, 8.01, 135.7, 1292, 0.853, 18),
    ("1 ACSR — ROBIN", "ROBIN", "1", 6, 3.00, 1, 3.00, 42.41, 9.00, 171.3, 1618, 0.674, 18),
    ("1/0 ACSR — RAVEN", "RAVEN", "1/0", 6, 3.37, 1, 3.37, 53.48, 10.11, 216.2, 1986, 0.535, 18),
    ("2/0 ACSR — QUAIL", "QUAIL", "2/0", 6, 3.78, 1, 3.78, 67.43, 11.34, 272.0, 2398, 0.424, 18),
    ("3/0 ACSR — PIGEON", "PIGEON", "3/0", 6, 4.25, 1, 4.25, 85.01, 12.75, 344.3, 2996, 0.336, 18),
    ("4/0 ACSR — PENGUIN", "PENGUIN", "4/0", 6, 4.77, 1, 4.77, 107.2, 14.31, 433.1, 3776, 0.267, 18),
    ("266.8 MCM — OWL", "OWL", "266.8", 6, 5.36, 7, 1.79, 135.2, 16.07, 511.1, 4330, 0.208, 18),
    ("266.8 MCM — WAXWING", "WAXWING", "266.8", 18, 3.09, 1, 3.09, 135.2, 15.46, 430.4, 3123, 0.213, 18),
    ("266.8 MCM — PARTRIDGE", "PARTRIDGE", "266.8", 26, 2.57, 7, 2.00, 135.2, 16.30, 545.4, 5121, 0.214, 18),
    ("336.4 MCM — MERLIN", "MERLIN", "336.4", 18, 3.47, 1, 3.47, 170.5, 17.35, 542.8, 3939, 0.169, 19),
    ("336.4 MCM — LINNET", "LINNET", "336.4", 26, 2.89, 7, 2.25, 170.5, 18.29, 689.9, 6423, 0.170, 19),
    ("477 MCM — HAWK", "HAWK", "477", 26, 3.44, 7, 2.67, 241.7, 21.77, 975.8, 8825, 0.119, 19),
    ("477 MCM — FLICKER", "FLICKER", "477", 24, 3.58, 7, 2.39, 241.7, 21.49, 914.6, 7801, 0.119, 19),
    ("795 MCM — DRAKE", "DRAKE", "795", 26, 4.44, 7, 3.45, 402.8, 28.11, 1626, 14283, 0.0716, 20),
)


def _construir():
    catalogo={}
    for (clave,codigo,calibre,na,da,ns,ds,area,diametro,masa,rotura,r20,pagina) in _FILAS:
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


CONDUCTORES_VIAKON_ACSR = _constru()


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
