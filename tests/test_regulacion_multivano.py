"""Validación de sección reguladora Checa: igualdad de vanos,
cambio térmico, longitudes y rechazo de datos no sustentados.
Todos los datos de los ensayos son SINTÉTICOS.
"""
import unittest
import numpy as np
import pandas as pd
from calculos.cambio_estado import vano_regulador
from calculos.regulacion_multivano import resolver_seccion_regulacion
from calculos.tendido_inverso import HipotesisTendido, dimensionar_tension_tendido


def puntos(luces=(45.53,45.53)):
    x=np.r_[0.,np.cumsum(luces)]
    return pd.DataFrame({
        "Punto":[f"P{i+1}" for i in range(len(x))],
        "X":x,"Y":np.zeros(len(x)),
        "Altitud":np.zeros(len(x)),
        "Altura_Amarre_m":np.full(len(x),10.),
    })


def hip():
    return pd.DataFrame([
        {"Hipotesis":"frio","Temperatura_C":-10.,
         "Viento_ms":0.,"T_limite_kN":7.,
         "Fuente_limite":"Criterio ficticio de ensayo",
         "Criterio_diseno":"Frío, ensayo"},
        {"Hipotesis":"viento","Temperatura_C":20.,
         "Viento_ms":15.,"T_limite_kN":9.,
         "Fuente_limite":"Criterio ficticio de ensayo",
         "Criterio_diseno":"Viento, ensayo"},
    ])


def kwargs(p):
    return {
        "puntos":p,"hipotesis":hip(),
        "temperaturas_tabla_C":[0,20,40],
        "peso_kN_m":.0085,"diametro_m":.020,
        "EA_kN":15000.,"alpha_por_C":1.91e-5,
        "fuente_material":"Material de ensayo sintético",
        "temperatura_tendido_C":20.,
        "H_min_kN":1.,"H_max_kN":6.,
    }


class RegulacionChecaTest(unittest.TestCase):
    def test_igual_luz_conserva_vano_regulador(self):
        self.assertAlmostEqual(vano_regulador([45.53,45.53]),45.53,places=9)
        self.assertAlmostEqual(
            vano_regulador([30.,60.]),
            np.sqrt((30**3+60**3)/90),
        )

    def test_seccion_dos_vanos_flechas_y_tabla(self):
        r=resolver_seccion_regulacion(**kwargs(puntos()))
        self.assertAlmostEqual(r.vano_regulador_m,45.53,places=6)
        self.assertEqual(len(r.flechas),4)
        self.assertEqual(len(r.tabla_tendido),6)
        self.assertEqual(len(r.hipotesis),2)
        self.assertGreater(r.H_tendido_kN,0)
        self.assertLessEqual(r.relacion_maxima,1.00001)
        self.assertTrue((r.tabla_tendido["Flecha vertical (m)"]>0).all())
        self.assertTrue((r.hipotesis["Residual compatibilidad (m)"].abs()<1e-7).all())
        t=r.tabla_tendido
        f0=t[t["Temperatura (°C)"]==0]["Flecha vertical (m)"].mean()
        f40=t[t["Temperatura (°C)"]==40]["Flecha vertical (m)"].mean()
        self.assertGreater(f40,f0)

    def test_un_vano_sin_viento_coincide_con_inverso_existente(self):
        p=puntos((45.53,))
        k=kwargs(p)
        k["hipotesis"]=hip().iloc[[0]].copy()
        r=resolver_seccion_regulacion(**k)
        solo=dimensionar_tension_tendido(
            (0,0,10),(45.53,0,10),
            hipotesis=[HipotesisTendido(
                "frio",-10,0,0,7.,
                "Criterio ficticio de ensayo","Frío, ensayo")],
            temperaturas_tabla_C=[0,20,40],
            temperatura_tendido_C=20,
            peso_kN_m=.0085,diametro_m=.020,
            EA_kN=15000.,alpha_por_C=1.91e-5,
            fuente_material="Material de ensayo sintético",
            H_min_kN=1.,H_max_kN=6.,
        )
        self.assertAlmostEqual(
            r.H_tendido_kN,solo.H_tendido_kN,delta=.02
        )

    def test_desnivel_resuelto_en_seccion_3d(self):
        p=puntos()
        p.loc[1,"Altitud"]=5.
        r=resolver_seccion_regulacion(**kwargs(p))
        self.assertEqual(len(r.tabla_tendido),6)
        self.assertIn("3D",r.modelo)
        self.assertTrue((r.flechas["Flecha vertical (m)"]>=0).all())

    def test_limites_sin_fuente_no_se_aceptan(self):
        k=kwargs(puntos())
        k["hipotesis"].loc[0,"Fuente_limite"]=""
        with self.assertRaisesRegex(ValueError,"fuente"):
            resolver_seccion_regulacion(**k)


if __name__=="__main__":
    unittest.main()
