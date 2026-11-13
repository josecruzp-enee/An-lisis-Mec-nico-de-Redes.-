"""Validaciones mecánicas independientes del diagrama del fuste.

Incluye fuerza puntual en amarre, viento sin cables y equilibrio con base.
No confundir la demanda elástica de corte con resistencia del material.
"""
import math
import unittest

import numpy as np
import pandas as pd

from calculos.verificacion_poste import (
    calcular_secciones_poste, secciones_gobernantes,
)
from calculos.solicitaciones_poste import (
    combinar_solicitaciones_postes,
)


def nodos(fx=0.,fy=0.,fz=0.,mx=0.,my=0.,v=0.,az=0.):
    return pd.DataFrame([{
        "Punto":"P1","Caso":"C1","Viento (m/s)":v,
        "Azimut viento (°)":az,"H inicial (kN)":6.,
        "Temperatura (°C)":20.,"Fx (kN)":fx,"Fy (kN)":fy,
        "Fz (kN)":fz,"Mx (kN·m)":mx,
        "My (kN·m)":my,"Mz (kN·m)":0.,
        "H resultante (kN)":math.hypot(fx,fy),
    }])


def poste(amarre=9.,empotramiento=1.9):
    return pd.DataFrame([{
        "Punto":"P1","Poste":"PC-40",
        "Altura_Amarre_m":amarre,"Empotramiento_m":empotramiento,
    }])


class SeccionesTest(unittest.TestCase):
    def test_fuerza_puntual_decrece_linealmente(self):
        p=poste()
        h=9.
        casos=nodos(fx=2.,fz=-.4,my=2*h)
        r=calcular_secciones_poste(casos,p,cantidad_secciones=51)
        self.assertAlmostEqual(r.iloc[0]["M flector (kN·m)"],18.,places=8)
        self.assertAlmostEqual(r.iloc[0]["V transversal (kN)"],2.,places=8)
        self.assertAlmostEqual(r.iloc[0]["N axial (kN)"],-.4,places=8)
        dentro=r.loc[r["Altura corte (m)"]<h]
        for _, fila in dentro.iterrows():
            self.assertAlmostEqual(
                fila["My (kN·m)"],2*(h-fila["Altura corte (m)"]),places=8
            )
        arriba=r.loc[r["Altura corte (m)"]>h]
        self.assertTrue((arriba["M flector (kN·m)"]==0).all())

    def test_viento_cono_equilibrio_base(self):
        p=poste()
        cases=nodos(v=25.,az=90.)
        cortes=calcular_secciones_poste(cases,p)
        total=combinar_solicitaciones_postes(cases,p)
        fila=cortes.iloc[0]
        base=total.iloc[0]
        for componente in (
            "Fx (kN)","Fy (kN)","Mx (kN·m)","My (kN·m)"
        ):
            self.assertAlmostEqual(fila[componente],base[componente],places=8)
        self.assertAlmostEqual(cortes.iloc[-1]["M flector (kN·m)"],0,places=8)
        self.assertAlmostEqual(cortes.iloc[-1]["V transversal (kN)"],0,places=8)

    def test_demanda_maxima_no_equivale_resistencia(self):
        p=poste()
        r=calcular_secciones_poste(nodos(fx=2.,my=18.),p)
        env=secciones_gobernantes(r)
        self.assertEqual(len(env),4)
        self.assertTrue((env["Estado"]=="RESISTENCIA NO VERIFICABLE").all())

    def test_rechaza_amarre_sobre_punta(self):
        with self.assertRaisesRegex(ValueError,"supera altura"):
            calcular_secciones_poste(nodos(fx=1.,my=15.),poste(amarre=15.))

    def test_poste_sin_catalogo_no_inventa_secciones(self):
        p=poste()
        p.loc[0,"Poste"]="DESCONOCIDO"
        r=calcular_secciones_poste(nodos(fx=2.,my=18.),p)
        self.assertIn("NO VERIFICABLE",r.iloc[0]["Estado sección"])
        self.assertTrue(secciones_gobernantes(r).empty)


if __name__=="__main__":
    unittest.main()
