"""Referencias mecánicas ACSR por construcción: fuente NEXANS.

No son datos certificados de Viakon. La tabla Nexans identifica
módulo ELÁSTICO final y coeficiente de dilatación final POR
CONFIGURACIÓN (Al/Acero), no por código de ave/fabricante.

La rigidez axial EA no es E nominal: se calcula utilizando el área
metálica TOTAL estimada a partir de número y diámetro de cada hilo:
A_total = pi/4 * (N_al*d_al² + N_acero*d_acero²).

ATENCIÓN: el módulo final corresponde al régimen final/post-creep
de la tabla de referencia Nexans. NO representa necesariamente la
rigidez inicial de tendido ni sustituye curvas de esfuerzo-deformación
de alambres y del conductor real. Esta aproximación de elasticidad
lineal homogénea es solamente para análisis de sensibilidad, y no
valida la utilización estructural de una red real.

Referencia primaria:
https://www.nexans.com.br/.rest/eservice/dam/v1/file/223724/StressStrainACSR_es.pdf

Fuentes secundarias de contraste:
https://www.trefinasa.com/wp-content/uploads/2017/04/overhead_conductors_trefinasa_2016web.pdf
"""
from __future__ import annotations

from math import pi

from entradas.catalogo_viakon_acsr import ficha_viakon_acsr

NEXANS_ACSR_URL = (
    "https://www.nexans.com.br/.rest/eservice/dam/v1/file/223724/"
    "StressStrainACSR_es.pdf"
)

# (Módulo final kgf/mm2; alpha final 1/°C)
# Fuente: Nexans T-ACSR Cable Stress and Strain Characteristics, tabla única.
NEXANS_ACSR_FINAL = {
    (6, 1): (8156, 19.1e-6),
    (6, 7): (7734, 19.8e-6),
    (8, 1): (9492, 16.9e-6),
    (8, 7): (8789, 17.6e-6),
    (12, 7): (10687, 15.3e-6),
    (16, 19): (11812, 14.4e-6),
    (18, 1): (6750, 21.2e-6),
    (18, 7): (6609, 21.6e-6),
    (22, 7): (7031, 20.2e-6),
    (24, 7): (7312, 19.4e-6),
    (26, 7): (7593, 18.9e-6),
    (30, 7): (8156, 17.8e-6),
    (30, 19): (8015, 18.0e-6),
    (36, 1): (6328, 22.1e-6),
    (42, 7): (6539, 21.4e-6),
    (45, 7): (6679, 20.9e-6),
    (48, 7): (6890, 20.3e-6),
    (54, 7): (7242, 19.4e-6),
    (54, 19): (7172, 19.6e-6),
    (72, 37): (8156, 17.6e-6),
    (72, 7): (6398, 21.6e-6),
    (76, 19): (6398, 21.2e-6),
    (84, 19): (6700, 20.5e-6),
}

# Exacta para unidad convencional 1 kgf = 9.80665 N.
KGFM2_A_GPA = 9.80665 / 1000.0


def referencia_mecanica_nexans(conductor):
    """Obtiene E_final y alpha_final para construcción equivalente.

    Devuelve propiedad de REFERENCIA de otro fabricante; no modifica
    ni completa los campos EA/alpha certificados del catálogo Viakon.
    """
    ficha = ficha_viakon_acsr(conductor)
    forma = (ficha["hilos_aluminio"], ficha["hilos_acero"])
    if forma not in NEXANS_ACSR_FINAL:
        raise ValueError(
            f"No hay referencia Nexans de construcción {forma[0]}/{forma[1]}"
        )
    e_kgf_mm2, alpha = NEXANS_ACSR_FINAL[forma]
    area_al = pi / 4 * (
        ficha["hilos_aluminio"] * ficha["diametro_hilo_aluminio_mm"]**2
    )
    area_acero = pi / 4 * (
        ficha["hilos_acero"] * ficha["diametro_hilo_acero_mm"]**2
    )
    area_total = area_al + area_acero
    # E en kgf/mm² por A en mm² -> kgf; kgf->kN.
    ea_kn = e_kgf_mm2 * area_total * 9.80665 / 1000
    return {
        "nombre": conductor,
        "codigo": ficha["codigo"],
        "configuracion": f"{forma[0]}/{forma[1]}",
        "area_aluminio_mm2": area_al,
        "area_acero_mm2": area_acero,
        "area_total_mm2": area_total,
        "E_final_GPa": e_kgf_mm2 * KGFM2_A_GPA,
        "EA_final_referencia_kN": ea_kn,
        "alpha_final_referencia_por_C": alpha,
        "fuente": NEXANS_ACSR_URL,
        "origen": "Nexans, referencia por construcción; NO Viakon",
        "estado": (
            "REFERENCIA COMPARATIVA, NO PROPIEDAD CERTIFICADA VIakON; "
            "MODELO LINEAL NO VALIDA CREEP NI ESTADO INICIAL"
        ),
        "apto_para_diseno": False,
    }
