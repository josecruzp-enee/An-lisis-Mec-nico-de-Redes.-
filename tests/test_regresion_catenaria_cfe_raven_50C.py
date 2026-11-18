"""Regresión independiente de geometría: CFE 07 FT 10, PDF p609.

No usa P de CFE como entrada del motor de proyecto: únicamente verifica
que la fórmula analítica de catenaria reproduce 21 registros publicados.
"""
import csv
import math
from pathlib import Path

def test_catenaria_geometria_raven_21_claros_publicados():
    ruta=Path(__file__).resolve().parent/"fixtures/validacion_catenaria_CFE_RAVEN_50C.csv"
    with ruta.open(encoding="utf-8-sig",newline="") as f:reg=list(csv.DictReader(f))
    assert len(reg)==21
    w=2.12 # N/m: CFE 07 FT 02, propiedades de conductor RAVEN
    for x in reg:
        L=float(x["vano_m"]);P=float(x["P_CFE_m"])
        tension_kgf=w*P/9.80665
        flecha_cm=100*P*(math.cosh(L/(2*P))-1)
        assert abs(tension_kgf-float(x["H_50C_tabla_kgf"]))<=.55
        assert abs(flecha_cm-float(x["flecha_50C_tabla_cm"]))<=.75
