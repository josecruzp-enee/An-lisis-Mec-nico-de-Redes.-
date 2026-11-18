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
