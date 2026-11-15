"""Regresión integral: red de dos vanos con amarres fijos, casos reales BVP.

Datos numéricos sintéticos; los resultados no son diseño certificado.
"""
import unittest
import numpy as np
import pandas as pd

from calculos.modelo_red import RedMecanica
from calculos.hipotesis_red import calcular_hipotesis_red


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


if __name__=="__main__":
    unittest.main()
