"""Regresiones del cribado resistente con datos ficticios de ensayo.

Ni las capacidades ni los resultados de estos casos representan postes reales.
"""
import unittest

import pandas as pd

from calculos.resistencia_postes import (
    cribar_resistencia_postes, resumen_resistencia_postes,
    validar_capacidades,
)


def secciones():
    filas=[]
    for caso, mx, n in (("C1", 6., -4.), ("C2", 15., 3.)):
        for z in (0., 5.):
            filas.append({
                "Punto":"P1","Caso":caso,"Altura corte (m)":z,
                "Estado sección":"SOLICITACIÓN, RESISTENCIA NO VERIFICABLE",
                "Mx (kN·m)":mx,"My (kN·m)":4.,
                "V transversal (kN)":2.,"N axial (kN)":n,
                "Mz (kN·m)":1.,
            })
    return pd.DataFrame(filas)


def capacidades():
    return pd.DataFrame({
        "Punto":["P1","P1"],
        "Altura_corte_m":[0.,5.],
        "Mx_Rd_kNm":[10.,20.],"My_Rd_kNm":[10.,20.],
        "V_Rd_kN":[10.,10.],
        "N_comp_Rd_kN":[8.,8.],"N_trac_Rd_kN":[2.,2.],
        "Mz_Rd_kNm":[5.,5.],
        "Fuente":["FICHA FICTICIA ENSAYO"]*2,
        "Criterio_diseno":["MODELO FICTICIO SOLO PRUEBA"]*2,
    })


class ResistenciaPostesTest(unittest.TestCase):
    def test_excede_limite_identifica_caso_y_cota(self):
        cr=cribar_resistencia_postes(secciones(),capacidades())
        resumen=resumen_resistencia_postes(cr)
        self.assertEqual(len(cr),4)
        self.assertEqual(resumen.iloc[0]["Estado"],"EXCEDE LÍMITE INDIVIDUAL DOCUMENTADO")
        self.assertEqual(resumen.iloc[0]["Caso gobernante"],"C2")
        self.assertEqual(resumen.iloc[0]["Altura crítica (m)"],0.)
        self.assertAlmostEqual(resumen.iloc[0]["Ratio individual crítico"],1.5)

    def test_comprension_y_traccion_tienen_capacidades_distintas(self):
        cr=cribar_resistencia_postes(secciones(),capacidades())
        grupo=cr.loc[cr["Altura corte (m)"]==5.]
        a,b=grupo["Ratio N axial (kN)"].tolist()
        self.assertAlmostEqual(a, .5)
        self.assertAlmostEqual(b, 1.5)

    def test_sin_fuente_no_se_acepta_capacidad(self):
        caps=capacidades()
        caps.loc[0,"Fuente"]=""
        with self.assertRaisesRegex(ValueError,"Fuente"):
            validar_capacidades(caps)

    def test_sin_todos_los_cortes_no_declara_cumplimiento(self):
        caps=capacidades().iloc[[0]]
        cr=cribar_resistencia_postes(secciones(),caps)
        r=resumen_resistencia_postes(cr)
        self.assertGreater(r.iloc[0]["Sin capacidad documentada"],0)
        self.assertIn("EXCEDE",r.iloc[0]["Estado"])
        self.assertTrue(cr["Estado resistencia"].str.contains(
            "NO VERIFICABLE|EXCEDE|INTERACCIÓN"
        ).all())

    def test_demandas_menores_no_equivalen_a_cumple(self):
        caps=capacidades().copy()
        for col in ("Mx_Rd_kNm","My_Rd_kNm","V_Rd_kN",
                    "N_comp_Rd_kN","N_trac_Rd_kN","Mz_Rd_kNm"):
            caps[col]=10000.
        cr=cribar_resistencia_postes(secciones(),caps)
        r=resumen_resistencia_postes(cr)
        self.assertEqual(r.iloc[0]["Estado"],"INTERACCIÓN Y ESTABILIDAD PENDIENTES")
        self.assertFalse(cr["Estado resistencia"].str.fullmatch("CUMPLE").any())

    def test_no_interpolar_limites_de_una_cota_a_otra(self):
        caps=capacidades()
        caps.loc[1,"Altura_corte_m"]=4.8
        cr=cribar_resistencia_postes(secciones(),caps)
        self.assertEqual(
            cr.loc[cr["Altura corte (m)"]==5.,
                   "Estado resistencia"].unique().tolist(),
            ["NO VERIFICABLE"],
        )

    def test_limite_no_positivo_rechazado(self):
        caps=capacidades()
        caps.loc[0,"Mx_Rd_kNm"]=0
        with self.assertRaises(ValueError):
            validar_capacidades(caps)


if __name__=="__main__":
    unittest.main()
