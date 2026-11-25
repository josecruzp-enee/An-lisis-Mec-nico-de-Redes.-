import pandas as pd
import pytest
from Analisis_mecanico_estructuras.calculos.fuerzas_exactas import ensamblar_fuerzas_exactas

def detalle():
    return pd.DataFrame([
        ("H1","Final","AB","A",4,0,-.2),
        ("H1","Final","AB","B",-4,0,-.3),
        ("H1","Final","BC","B",3,4,-.4),
        ("H1","Final","BC","C",-3,-4,-.5),
    ],columns=["Hipótesis","Condición","Vano","Apoyo","Fx (kN)","Fy (kN)","Fz (kN)"])

def test_resultante_trifasica():
    r=ensamblar_fuerzas_exactas(detalle(),n_fases=3).set_index("Apoyo")
    assert r.loc["B","Fx (kN)"] == pytest.approx(-3)
    assert r.loc["B","Fy (kN)"] == pytest.approx(12)
    assert r.loc["B","Fz (kN)"] == pytest.approx(-2.1)
    assert r.loc["B","H (kN)"] == pytest.approx(153**.5)
    assert r.loc["B","F resultante (kN)"] == pytest.approx(157.41**.5)

def test_no_mezclar_hipotesis():
    d=detalle()
    e=d.copy()
    e["Hipótesis"]="H2"
    e["Fx (kN)"] *= 2
    r=ensamblar_fuerzas_exactas(pd.concat([d,e])).set_index(["Hipótesis","Apoyo"])
    assert r.loc[("H1","B"),"Fx (kN)"] == pytest.approx(-1)
    assert r.loc[("H2","B"),"Fx (kN)"] == pytest.approx(-2)

def test_rechazar_extremo_faltante():
    with pytest.raises(ValueError):
        ensamblar_fuerzas_exactas(detalle().iloc[:-1])

def test_rechazar_duplicados():
    d=detalle()
    with pytest.raises(ValueError):
        ensamblar_fuerzas_exactas(pd.concat([d,d.iloc[:1]]))

def test_rechazar_hipotesis_incompleta():
    d=detalle()
    e=d.iloc[:2].copy()
    e["Hipótesis"]="H2"
    with pytest.raises(ValueError):
        ensamblar_fuerzas_exactas(pd.concat([d,e]))

def test_no_multiplicar_conductores_explicitos():
    d=detalle().assign(Conductor="F1")
    with pytest.raises(ValueError):
        ensamblar_fuerzas_exactas(d,n_fases=3)
