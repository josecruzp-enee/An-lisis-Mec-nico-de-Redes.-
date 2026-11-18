"""Pruebas de integridad de tablas CFE y condiciones no verificables."""
import csv
from Analisis_mecanico_conductores.verificaciones.verificar_restricciones_documentadas_cfe import (
    CATALOGO, fila_tabla, verificar_tabla_estructura, verificar_traccion,
    separacion_fases_minima, verificar_horizontal_construccion, verificar_fases,
)

def test_catalogo_fuente_662_filas_sin_rellenar_ausentes():
    with CATALOGO.open(encoding="utf-8-sig",newline="") as f:
        filas=list(csv.DictReader(f))
    assert len(filas)==662
    assert len({(r["estructura"],r["ambiente"],r["conductor"],r["tension_clase_kV"]) for r in filas})==662
    assert fila_tabla("VD3N","ACSR HAWK 477",33) is None

def test_raven_ts3n_fuente_181():
    f=fila_tabla("TS3N","ACSR RAVEN 1/0",13)
    assert int(f["pagina_pdf"])==181
    assert [int(f[c]) for c in ("poste_max_m","cable_max_m","cruceta_con_hielo_max_m",
                                 "libramiento_piso_max_m","separacion_fases_max_m")]==[109,109,242,126,123]
    v=verificar_tabla_estructura(120,"TS3N","ACSR RAVEN 1/0",13)
    assert v["estado"]=="EXCEDE TABLA CFE"
    assert v["criterios"]["poste_max_m"]["cumple"] is False
    assert v["criterios"]["libramiento_piso_max_m"]["cumple"] is True

def test_limites_de_traccion_requieren_casos_completos():
    r=verificar_traccion(19477.4,{"final_0C_sin_viento":4800})
    assert r["final_0C_sin_viento"]["estado"]=="CUMPLE"
    assert r["inicial_0C_sin_viento"]["estado"]=="NO VERIFICABLE"
    assert abs(r["final_0C_sin_viento"]["limite_N"]-4869.35)<1e-5

def test_separacion_fases_no_extrapola():
    assert separacion_fases_minima(13,1.50,62.4378)==.55
    assert separacion_fases_minima(13,4.0,62.4378) is None
    assert verificar_fases(13,4.0,62.4378,1.0)["estado"]=="NO VERIFICABLE"

def test_horizontal_requiere_obstaculo_y_viento_especificado():
    assert verificar_horizontal_construccion(13,None,None)["estado"]=="NO VERIFICABLE"
    assert verificar_horizontal_construccion(13,3.0,.5)["estado"]=="CUMPLE"
    assert verificar_horizontal_construccion(13,2.5,.5)["estado"]=="NO CUMPLE"


def test_vertical_no_confunde_suelo_plano_con_tipo_via():
    from Analisis_mecanico_conductores.verificaciones.verificar_restricciones_documentadas_cfe import (
        verificar_vertical_superficie,
    )
    assert verificar_vertical_superficie(6.0,0.0,None)["estado"]=="NO VERIFICABLE"
    assert verificar_vertical_superficie(6.0,0.0,
        "a_lo_largo_caminos_y_zonas_rurales")["estado"]=="CUMPLE"
    assert verificar_vertical_superficie(6.0,0.0,
        "carreteras_calles_callejones_caminos_vecinales")["estado"]=="NO CUMPLE"

def test_integracion_tablas_y_geometrias_incompletas():
    from types import SimpleNamespace
    import pandas as pd
    from Analisis_mecanico_conductores.verificaciones.evaluar_requisitos_cfe_por_vano import (
        evaluar_requisitos_cfe_por_vano,
    )
    muestra=SimpleNamespace(flechas=pd.DataFrame([
        {"Vano":"P1 → P2","Luz (m)":50.0,"Hipótesis":"Final 0C",
         "T máxima vano (kN)":3.0},
        {"Vano":"P2 → P3","Luz (m)":150.0,"Hipótesis":"Final 0C",
         "T máxima vano (kN)":3.2},
    ]))
    r=evaluar_requisitos_cfe_por_vano(muestra,ruptura_N=19477.4,configuracion={
        "conductor":"ACSR RAVEN 1/0","clase_kV":13,
        "estructura_por_vano":{"P1 → P2":"TS3N","P2 → P3":"TS3N"},
        "clases_cfe_por_hipotesis":{"Final 0C":"final_0C_sin_viento"},
    })
    f=r["verificaciones_vanos"]
    assert f.iloc[0]["Tabla estructura CFE"].startswith("DENTRO")
    assert f.iloc[1]["Tabla estructura CFE"]=="EXCEDE TABLA CFE"
    assert f.iloc[0]["Libramiento vertical"]=="NO VERIFICABLE"
    assert r["traccion_CFE"]["final_0C_sin_viento"]["estado"]=="CUMPLE"
    assert r["traccion_CFE"]["inicial_0C_sin_viento"]["estado"]=="NO VERIFICABLE"
