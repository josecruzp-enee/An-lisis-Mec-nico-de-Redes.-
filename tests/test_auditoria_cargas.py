"""Regresiones de la suma 6D de cargas del conductor sobre postes."""
import unittest

import numpy as np

from calculos.barrido_3d import ejecutar_barrido_3d
from calculos.auditoria_cargas import auditar_reacciones_por_vano, COMPONENTES


def estudiar():
    vanos=[
        {"nombre":"AB","inicio":"A","fin":"B",
         "base_inicio_m":[0,0,0],"base_fin_m":[45,5,3],
         "amarre_inicio_m":[0,0,9],"amarre_fin_m":[0,0,9.5]},
        {"nombre":"BC","inicio":"B","fin":"C",
         "base_inicio_m":[45,5,3],"base_fin_m":[80,40,8],
         "amarre_inicio_m":[0,0,9.5],"amarre_fin_m":[0,0,10]},
    ]
    return ejecutar_barrido_3d(
        vanos,peso_kN_m=.008,diametro_m=.02,
        EA_kN=16000,alpha_por_C=1.8e-5,
        temperatura_tendido_C=20,temperaturas_C=[20,40],
        tensiones_iniciales_kN=[5.],viento_max_ms=3.,
        direcciones_viento_deg=[0,90,180],
        cantidad_conductores=3,fuente_conductor="ENSAYO SINTÉTICO",
    )


class AuditoriaCargaTest(unittest.TestCase):
    def test_auditoria_sin_perdida_de_vanos(self):
        resultado=estudiar()
        ex=resultado["extremos"]
        nodos=resultado["nodos"]
        self.assertEqual(len(ex),len(resultado["vanos"])*2)
        d=auditar_reacciones_por_vano(ex,nodos)
        self.assertLess(d["Residual máximo carga o momento"],1e-9)
        self.assertEqual(set(ex["Punto"]),{"A","B","C"})

    def test_momento_de_cada_extremo_es_brazo_por_fuerza(self):
        ex=estudiar()["extremos"]
        for _,fila in ex.iterrows():
            altura=fila["Altura amarre (m)"]
            self.assertAlmostEqual(
                fila["Mx (kN·m)"],-altura*fila["Fy (kN)"],places=9
            )
            self.assertAlmostEqual(
                fila["My (kN·m)"],altura*fila["Fx (kN)"],places=9
            )
            self.assertAlmostEqual(fila["Mz (kN·m)"],0.,places=9)

    def test_auditoria_detecta_error_en_suma(self):
        r=estudiar()
        cargas=r["nodos"].copy()
        cargas.loc[cargas.index[0],"Fx (kN)"]+=.25
        with self.assertRaisesRegex(ValueError,"no equilibradas"):
            auditar_reacciones_por_vano(r["extremos"],cargas)

    def test_auditoria_rechaza_nodo_faltante(self):
        r=estudiar()
        with self.assertRaisesRegex(ValueError,"mismos casos"):
            auditar_reacciones_por_vano(
                r["extremos"],r["nodos"].iloc[1:]
            )


if __name__=="__main__":
    unittest.main()
