"""Pruebas: no inventar porcentajes y preservar casos sin clasificación."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.verificaciones.verificar_limites_documentados_de_tension import (
    evaluar_tensiones_diseno, resumen_tension_diseno,
    validar_criterios_tension,
)


def datos():
    vanos=pd.DataFrame({
        "Vano":["V1","V1","V1","V2"],
        "Caso":["E1","E2","E3","E1"],
        "T máxima (kN)":[8.,12.,9.,7.],
    })
    clases=pd.DataFrame({
        "Caso":["E1","E2","E3"],
        "Clase_estado":["operacion","viento","sin_límite"],
    })
    criterios=pd.DataFrame({
        "Clase_estado":["operacion","viento"],
        "T_limite_kN":[10.,11.],
        "Fuente_limite":["Norma ficticia ENSAYO"]*2,
        "Criterio_diseno":["Combinación sintética"]*2,
    })
    return vanos,clases,criterios


class LimitesTensionTest(unittest.TestCase):
    def test_caso_que_excede_y_caso_sin_fuente_no_aprobado(self):
        v,c,l=datos()
        r=evaluar_tensiones_diseno(v,c,l)
        e2=r.loc[(r["Caso"]=="E2")].iloc[0]
        self.assertIn("SUPERA",e2["Estado tensión diseño"])
        e3=r.loc[(r["Caso"]=="E3")].iloc[0]
        self.assertIn("NO VERIFICABLE",e3["Estado tensión diseño"])
        rs=resumen_tension_diseno(r).set_index("Vano")
        self.assertEqual(int(rs.loc["V1","Casos que exceden"]),1)
        self.assertEqual(int(rs.loc["V1","Casos sin criterio"]),1)
        self.assertIn("SUPERA",rs.loc["V1","Estado"])
        self.assertIn("PENDIENTES",rs.loc["V2","Estado"])

    def test_falta_documentacion_rechazada(self):
        v,c,l=datos()
        l.loc[0,"Fuente_limite"]=""
        with self.assertRaisesRegex(ValueError,"Fuente_limite"):
            validar_criterios_tension(l)

    def test_no_inventa_criterio_si_falta_clasificacion(self):
        v,c,l=datos()
        c=c.loc[c["Caso"]!="E1"].copy()
        r=evaluar_tensiones_diseno(v,c,l)
        self.assertTrue(
            r.loc[r["Caso"]=="E1","Estado tensión diseño"]
            .str.startswith("NO VERIFICABLE").all()
        )

    def test_doble_criterio_es_ambiguo(self):
        v,c,l=datos()
        l=pd.concat([l,l.iloc[[0]]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,"duplicada"):
            evaluar_tensiones_diseno(v,c,l)

    def test_no_mezcla_demandas_de_casos_distintos(self):
        v,c,l=datos()
        r=evaluar_tensiones_diseno(v,c,l)
        self.assertEqual(len(r),len(v))
        self.assertEqual(r.loc[r["Caso"]=="E1","T_limite_kN"].tolist(),
                         [10.,10.])


if __name__=="__main__":
    unittest.main()
