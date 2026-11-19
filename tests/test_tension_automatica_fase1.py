"""La tensión ya NO es una entrada obligatoria en Fase 1.

El cálculo automático exige límites/fuentes y una conexión declarada,
y rechaza dos vanos sin topología para evitar ingeniería incorrecta.
"""
import unittest
from io import BytesIO

import pandas as pd

from entradas.catalogos import CONDUCTORES_ACSR
from Analisis_mecanico_conductores.entradas.leer_tension_inversa_desde_excel_historico import calcular_tension_desde_libro, plantilla_tension_automatica


def _entrada(puntos=2, incluir_limites=True):
    nombre="2/0 ACSR"
    f=CONDUCTORES_ACSR[nombre]
    pts=pd.DataFrame({
        "Punto":["P1","P2","P3"][:puntos],
        "X":[0.,45.,90.][:puntos],
        "Y":[0.,0.,0.][:puntos],
        "Altitud":[0.,0.,0.][:puntos],
        "Altura_Amarre_m":[10.,10.,10.][:puntos],
        "Poste":["PC-40"]*puntos,
        "Espacio Retenida":["SI"]*puntos,
    })
    vanos=pd.DataFrame([{
        "Inicio":"P1","Fin":"P2",
        "Conexion_Inicio":"ANCLAJE","Conexion_Fin":"ANCLAJE",
    }])
    materiales=pd.DataFrame([{
        "Conductor":nombre,
        "Peso_kN_m":f["peso_kg_m"]*9.80665/1000,
        "Diametro_m":f["diametro_m"],
        "EA_kN":15000.,
        "Alpha_por_C":1.91e-5,
        "Temperatura_tendido_C":20.,
        "Fuente":"Propiedades SINTÉTICAS para prueba, no ficha de fabricante",
    }])
    hip=pd.DataFrame([{
        "Hipotesis":"frio","Temperatura_C":-10.,
        "Viento_ms":0.,"Azimut_deg":0.,
        "T_limite_kN":8. if incluir_limites else None,
        "Fuente_limite":"Criterio SINTÉTICO para prueba",
        "Criterio_diseno":"Sin validez normativa",
    }])
    buff=BytesIO()
    with pd.ExcelWriter(buff,engine="openpyxl") as wr:
        pts.to_excel(wr,sheet_name="Puntos",index=False)
        vanos.to_excel(wr,sheet_name="Vanos",index=False)
        materiales.to_excel(wr,sheet_name="Materiales",index=False)
        hip.to_excel(wr,sheet_name="Hipotesis",index=False)
    buff.seek(0)
    return buff,pts


class AutoFase1Test(unittest.TestCase):
    def test_plantilla_no_pide_H_y_no_inventa_limites(self):
        libro=pd.read_excel(BytesIO(plantilla_tension_automatica()),sheet_name=None)
        self.assertEqual(set(libro),{"Puntos","Vanos","Materiales","Hipotesis"})
        self.assertNotIn("H_tendido_kN",libro["Materiales"].columns)
        self.assertTrue(libro["Hipotesis"]["T_limite_kN"].isna().all())
        self.assertTrue(libro["Materiales"]["EA_kN"].isna().all())

    def test_tension_surge_de_hipotesis_no_de_usuario(self):
        buff,pts=_entrada()
        res=calcular_tension_desde_libro(buff,pts,"2/0 ACSR")
        self.assertGreater(res.H_tendido_kN,0)
        self.assertLessEqual(res.razon_maxima,1.0001)
        self.assertEqual(len(res.hipotesis),1)

    def test_varios_vanos_no_crean_una_tension_ficticia(self):
        buff,pts=_entrada(puntos=3)
        with self.assertRaisesRegex(ValueError,"varios vanos|único vano|2 vanos"):
            calcular_tension_desde_libro(buff,pts,"2/0 ACSR")

    def test_sin_limites_no_se_calcula_tension(self):
        buff,pts=_entrada(incluir_limites=False)
        with self.assertRaisesRegex(ValueError,"incompletos"):
            calcular_tension_desde_libro(buff,pts,"2/0 ACSR")

    def test_no_convertir_suspension_en_anclaje(self):
        buff,pts=_entrada()
        hojas=pd.read_excel(buff,sheet_name=None)
        hojas["Vanos"]["Conexion_Fin"]="SUSPENSION"
        nuevo=BytesIO()
        with pd.ExcelWriter(nuevo,engine="openpyxl") as wr:
            for k,v in hojas.items():
                v.to_excel(wr,sheet_name=k,index=False)
        nuevo.seek(0)
        with self.assertRaisesRegex(ValueError,"ANCLAJE"):
            calcular_tension_desde_libro(nuevo,pts,"2/0 ACSR")


if __name__=="__main__":
    unittest.main()
