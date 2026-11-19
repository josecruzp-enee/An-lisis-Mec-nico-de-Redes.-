"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_modelo_red.py ===
"""Topología de secciones de tendido y conexiones mecánicas explícitas."""
import unittest

from Analisis_mecanico_conductores.calculos.modelo_red import RedMecanica


def ejemplo():
    nodos=[
        dict(nombre=n,base_m=xyz,modelo_apoyo="PC-40")
        for n,xyz in [
            ("P1",(0,0,0)),("P2",(40,0,2)),("P3",(80,30,5)),
        ]
    ]
    vanos=[]
    for n,a,b,ca,cb in [
        ("V1","P1","P2","ANCLAJE","SUSPENSION"),
        ("V2","P2","P3","SUSPENSION","ANCLAJE"),
    ]:
        vanos.append(dict(
            nombre=n,origen=a,destino=b,circuito="C1",
            conductor="ACSR 2/0",seccion_tendido="S1",
            amarre_origen_m=(0,0,9.5),amarre_destino_m=(0,0,9.5),
            conexion_origen=ca,conexion_destino=cb,
        ))
    return nodos,vanos


class TopologiaTest(unittest.TestCase):
    def test_seccion_con_suspension_y_desnivel(self):
        nodos,vanos=ejemplo()
        red=RedMecanica.desde_registros(nodos,vanos)
        self.assertEqual(len(red.secciones()),1)
        self.assertEqual(red.secciones()[0]["Vanos"],2)
        self.assertEqual(len(red.componentes_conexas()),1)
        self.assertEqual(len(red.apoyos_conectados()["P2"]),2)

    def test_no_inferir_suspension_si_no_declara(self):
        nodos,vanos=ejemplo()
        vanos[1]["conexion_origen"]="ANCLAJE"
        with self.assertRaisesRegex(ValueError,"suspensión"):
            RedMecanica.desde_registros(nodos,vanos)

    def test_suspension_suelta_no_valida(self):
        nodos,vanos=ejemplo()
        vanos.pop()
        with self.assertRaises(ValueError):
            RedMecanica.desde_registros(nodos,vanos)

    def test_conexiones_con_diferente_conductor(self):
        nodos,vanos=ejemplo()
        vanos[1]["conductor"]="ACSR 4/0"
        with self.assertRaisesRegex(ValueError,"discontinuo"):
            RedMecanica.desde_registros(nodos,vanos)

    def test_no_admitir_ids_duplicados(self):
        nodos,vanos=ejemplo()
        vanos.append(vanos[0].copy())
        with self.assertRaisesRegex(ValueError,"duplicados"):
            RedMecanica.desde_registros(nodos,vanos)

    def test_anclajes_sin_suspension_son_secciones_separadas(self):
        nodos,vanos=ejemplo()
        vanos[0]["conexion_destino"]="ANCLAJE"
        vanos[1]["conexion_origen"]="ANCLAJE"
        vanos[1]["seccion_tendido"]="S2"
        red=RedMecanica.desde_registros(nodos,vanos)
        self.assertEqual(len(red.secciones()),2)


# === Casos conservados de tests/test_ensamblador_global.py ===
"""Ensayos de equilibrio global y rechazo de conexiones no implementadas."""
import unittest
import numpy as np

from Analisis_mecanico_conductores.calculos.modelo_red import RedMecanica
from Analisis_mecanico_conductores.calculos.ensamblador_global import resolver_equilibrio_global


def modelo(centro_movil=False,suspension=False):
    apoyos=[
        {"nombre":n,"base_m":p,"modelo_apoyo":"modelo sintético",
         "fijacion":"MOVIL" if n=="P2" and centro_movil else "FIJO"}
        for n,p in [
            ("P1",(0.,0.,0.)),("P2",(40.,0.,0.)),("P3",(80.,0.,0.)),
        ]
    ]
    vanos=[]
    for idx, a,b,ci,cf in [
        (1,"P1","P2","ANCLAJE","SUSPENSION" if suspension else "ANCLAJE"),
        (2,"P2","P3","SUSPENSION" if suspension else "ANCLAJE","ANCLAJE"),
    ]:
        vanos.append({
            "nombre":f"V{idx}","origen":a,"destino":b,
            "circuito":"C1","seccion_tendido":"S1" if suspension else f"S{idx}",
            "conductor":"sintetico","amarre_origen_m":(0,0,10),
            "amarre_destino_m":(0,0,10),
            "conexion_origen":ci,"conexion_destino":cf,
        })
    return RedMecanica.desde_registros(apoyos,vanos)


def parametros():
    return {"sintetico":{
        "peso_kN_m":.01,"diametro_m":.02,"EA_kN":16000.,
        "alpha_por_C":1.8e-5,"H_tendido_kN":8.,
        "temperatura_tendido_C":20.,
        "fuente":"Valores SINTÉTICOS para prueba automatizada",
    }}


class RedGlobalTest(unittest.TestCase):
    def test_dos_vanos_fijos_no_confundir_reaccion_con_cumplimiento(self):
        r=resolver_equilibrio_global(
            modelo(),parametros(),temperatura_C=20,
            viento_ms=0,azimut_deg=90,
        )
        self.assertEqual(len(r.vanos),2)
        self.assertEqual(r.iteraciones,1)
        self.assertLess(r.residual_max_kN,1e-10)
        for n in ("P1","P2","P3"):
            np.testing.assert_allclose(
                r.reacciones_anclajes_kN[n]+r.fuerzas_conductor_kN[n],
                np.zeros(3),atol=1e-10,
            )
        self.assertIn("NO VERIFICACIÓN",r.estado)

    def test_apoyo_movil_resuelve_equilibrio(self):
        r=resolver_equilibrio_global(
            modelo(centro_movil=True),parametros(),
            temperatura_C=20,viento_ms=0,azimut_deg=0,
            rigideces={"P2":{
                "K_kN_m":np.diag([1000.,1000.,1000.]),
                "fuente":"Resorte de ensayo sintético",
            }},
            tolerancia_residual_kN=5e-4,
            max_evaluaciones=30,
        )
        self.assertLess(r.residual_max_kN,5e-4)
        self.assertLess(r.desplazamientos_m["P2"][2],0.)
        self.assertAlmostEqual(r.desplazamientos_m["P2"][0],0.,places=4)
        np.testing.assert_allclose(
            r.fuerzas_conductor_kN["P2"],
            r.fuerzas_rigidez_kN["P2"],atol=5e-4,
        )

    def test_suspension_rechazada_hasta_resolver_movilidad(self):
        with self.assertRaisesRegex(ValueError,"Suspensión"):
            resolver_equilibrio_global(
                modelo(suspension=True),parametros(),
                temperatura_C=20,viento_ms=5,azimut_deg=90,
            )

    def test_movil_no_admite_rigidez_ficticia(self):
        with self.assertRaisesRegex(ValueError,"rigidez sin fuente"):
            resolver_equilibrio_global(
                modelo(centro_movil=True),parametros(),
                temperatura_C=20,viento_ms=0,azimut_deg=0,
            )


# === Casos conservados de tests/test_barrido_global.py ===
"""Barrido de estados acoplados con una red de anclajes fijos."""
import unittest

from Analisis_mecanico_conductores.calculos.modelo_red import RedMecanica
from Analisis_mecanico_conductores.calculos.barrido_global import barrido_red_global


def datos():
    red=RedMecanica.desde_registros(
        [
            {"nombre":"A","base_m":(0,0,0),"modelo_apoyo":"referencia sintética"},
            {"nombre":"B","base_m":(35,0,3),"modelo_apoyo":"referencia sintética"},
        ],[
            {
                "nombre":"V1","origen":"A","destino":"B",
                "circuito":"C1","seccion_tendido":"S1",
                "conductor":"cable sintético",
                "amarre_origen_m":(0,0,9.5),
                "amarre_destino_m":(0,0,9.5),
                "conexion_origen":"ANCLAJE",
                "conexion_destino":"ANCLAJE",
            },
        ]
    )
    fichas={"cable sintético":{
        "peso_kN_m":.01,"diametro_m":.02,
        "EA_kN":16000,"alpha_por_C":1.8e-5,
        "H_tendido_kN":8,
        "temperatura_tendido_C":20,
        "fuente":"ENSAYO SINTÉTICO",
    }}
    return red,fichas


class BarridoRedGlobalTest(unittest.TestCase):
    def test_barrido_no_interpela_fuerzas_ni_muta_material(self):
        red,mat=datos()
        r=barrido_red_global(
            red,mat,temperaturas_C=[20],
            tensiones_iniciales_kN=[7,8],
            direcciones_viento_deg=[0],
            viento_min_ms=0,viento_max_ms=1,
        )
        self.assertEqual(len(r["estados"]),4)
        self.assertEqual(len(r["apoyos"]),8)
        self.assertEqual(len(r["vanos"]),4)
        self.assertEqual(mat["cable sintético"]["H_tendido_kN"],8)
        self.assertLess(
            r["vanos"]["Residual equilibrio vano (kN)"].max(),1e-4,
        )

    def test_limite_estados_es_explicito(self):
        red,mat=datos()
        with self.assertRaisesRegex(ValueError,"superan"):
            barrido_red_global(
                red,mat,temperaturas_C=[20,40],
                tensiones_iniciales_kN=[5,6,7],
                direcciones_viento_deg=[0,90],
                viento_min_ms=0,viento_max_ms=20,
                limite_casos=100,
            )


# === Casos conservados de tests/test_hipotesis_red.py ===
"""Regresión integral: red de dos vanos con amarres fijos, casos reales BVP.

Datos numéricos sintéticos; los resultados no son diseño certificado.
"""
import unittest
import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.calculos.modelo_red import RedMecanica
from Analisis_mecanico_conductores.calculos.hipotesis_red import calcular_hipotesis_red


def red_fija():
    apoyos=[
        {"nombre":n,"base_m":xyz,"modelo_apoyo":"ENSAYO","fijacion":"FIJO"}
        for n,xyz in [
            ("P1",(0.,0.,0.)),
            ("P2",(50.,0.,2.)),
            ("P3",(85.,25.,5.)),
        ]
    ]
    vanos=[
        {"nombre":f"V{i}","origen":a,"destino":b,
         "circuito":"C1","seccion_tendido":f"S{i}",
         "conductor":"TEST","amarre_origen_m":(0.,0.,10.),
         "amarre_destino_m":(0.,0.,10.),
         "conexion_origen":"ANCLAJE","conexion_destino":"ANCLAJE"}
        for i,a,b in [(1,"P1","P2"),(2,"P2","P3")]
    ]
    return RedMecanica.desde_registros(apoyos,vanos)


MATERIALES={"TEST":{
    "peso_kN_m":.008,"diametro_m":.02,
    "EA_kN":16000.,"alpha_por_C":1.91e-5,
    "H_tendido_kN":8.,"temperatura_tendido_C":20.,
    "fuente":"ENSAYO SINTÉTICO: no apto para diseño",
}}


class HipotesisRedTest(unittest.TestCase):
    def test_dos_vanos_separados_hipotesis_y_resultante(self):
        estados=pd.DataFrame([
            {"Hipotesis":"frio","Temperatura_C":-5,"Viento_ms":0,"Azimut_deg":0},
            {"Hipotesis":"viento","Temperatura_C":25,"Viento_ms":15,"Azimut_deg":90},
        ])
        r=calcular_hipotesis_red(red_fija(),MATERIALES,estados)
        self.assertEqual(len(r["vanos"]),4)
        self.assertEqual(len(r["apoyos"]),6)
        self.assertEqual(set(r["tensiones_gobernantes"]["Vano"]),{"V1","V2"})
        self.assertTrue((r["vanos"]["Flecha vertical sobre cuerda (m)"]>0).all())
        self.assertTrue((r["vanos"]["Residual equilibrio BVP (kN)"]<1e-4).all())
        self.assertTrue((r["vanos"]["Fuente material"]==MATERIALES["TEST"]["fuente"]).all())
        self.assertEqual(len(r["secciones_deslizantes"]),0)
        apoyo=r["apoyos"].query("Apoyo == 'P2'")
        for _,f in apoyo.iterrows():
            np.testing.assert_allclose(
                [f["Fx conductor (kN)"],f["Fy conductor (kN)"],f["Fz conductor (kN)"]],
                [-f["Reacción X (kN)"],-f["Reacción Y (kN)"],-f["Reacción Z (kN)"]],
                atol=1e-6
            )

    def test_rechazar_suspension_real_en_lugar_de_imitar_guia(self):
        r=red_fija()
        # Rehacer la topología interna con suspensión real declarada.
        from dataclasses import replace
        v1=replace(r.vanos["V1"],conexion_destino="SUSPENSION",seccion_tendido="S1")
        v2=replace(r.vanos["V2"],conexion_origen="SUSPENSION",seccion_tendido="S1")
        r=RedMecanica.desde_registros(list(r.apoyos.values()),[v1,v2])
        h=pd.DataFrame([{"Hipotesis":"base","Temperatura_C":20,
                         "Viento_ms":0,"Azimut_deg":0}])
        with self.assertRaisesRegex(ValueError,"Suspensión"):
            calcular_hipotesis_red(r,MATERIALES,h)

    def test_hipotesis_duplicadas_son_error(self):
        h=pd.DataFrame([
            {"Hipotesis":"base","Temperatura_C":20,"Viento_ms":0,"Azimut_deg":0},
            {"Hipotesis":"base","Temperatura_C":30,"Viento_ms":0,"Azimut_deg":0},
        ])
        with self.assertRaisesRegex(ValueError,"duplicados"):
            calcular_hipotesis_red(red_fija(),MATERIALES,h)
