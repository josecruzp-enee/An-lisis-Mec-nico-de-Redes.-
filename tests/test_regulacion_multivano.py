"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_regulacion_multivano.py ===
"""Validación de sección reguladora Checa: igualdad de vanos,
cambio térmico, longitudes y rechazo de datos no sustentados.
Todos los datos de los ensayos son SINTÉTICOS.
"""
import unittest
import numpy as np
import pandas as pd
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import vano_regulador
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import resolver_seccion_regulacion
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_inversa_de_un_vano import HipotesisTendido, dimensionar_tension_tendido


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


# === Casos conservados de tests/test_etapa1_vanos_amarrados.py ===
"""Distribución: ensayos de independencia mecánica tras amarre en espigas.

Cargas y límites sintéticos. Un H inicial de instalación compartido NO
implica H de servicio compartida ni redistribución de conductor entre vanos.
"""
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.evaluar_vanos_amarrados_independientes import (
    EvaluadorVanosAmarrados,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    resolver_seccion_regulacion,
)
from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import ConfiguracionBarrido
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import longitud_natural
from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria


class VanosFijosDistribucionTest(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0.,40.,125.],
            "Y":[0.,0.,15.],
            "Altitud":[100.,106.,96.],
            "Altura_Amarre_m":[9.5,9.5,9.5],
        })
        xyz=np.column_stack((
            self.puntos[["X","Y"]].to_numpy(float),
            (self.puntos["Altitud"]+self.puntos["Altura_Amarre_m"]).to_numpy(float),
        ))
        self.eval=EvaluadorVanosAmarrados(
            xyz,.0085,.02,15000.,1.91e-5,20.,1.2,1.225,
        )

    def test_tension_inicial_comun_y_servicio_independiente(self):
        h0,t0,c0,res0,_=self.eval.evaluar_estado(4.,20.,0.)
        self.assertEqual(h0,[4.,4.])
        self.assertEqual(res0,[0.,0.])
        h,t,c,res,_=self.eval.evaluar_estado(4.,40.,0.)
        self.assertEqual(len(h),2)
        self.assertGreater(abs(h[0]-h[1]),.01)
        self.assertTrue(all(abs(v)<1e-7 for v in res))
        # Cada vano verifica su propia longitud natural, no una suma libre.
        for i in range(2):
            L0=longitud_natural(c0[i],15000.)
            L1=longitud_natural(c[i],15000.)
            self.assertAlmostEqual(L1,L0*(1+1.91e-5*20),delta=1e-7)

    def test_regulacion_entrega_estados_por_vano_y_barrido_con_hielo(self):
        hip=pd.DataFrame([{
            "Hipotesis":"Frío","Temperatura_C":-5.,
            "Viento_ms":0.,"T_limite_kN":8.,
            "Fuente_limite":"Ensayo sintético",
            "Criterio_diseno":"Solo prueba",
        }])
        config=ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=40.,temperatura_paso_C=20.,
            viento_max_kmh=36.,viento_paso_kmh=18.,
            incluir_hielo=True,hielo_max_mm=5.,hielo_paso_mm=5.,
            temperatura_hielo_C=20.,
        )
        r=resolver_seccion_regulacion(
            self.puntos,hipotesis=hip,
            temperaturas_tabla_C=[20.,40.],
            peso_kN_m=.0085,diametro_m=.02,EA_kN=15000.,
            alpha_por_C=1.91e-5,fuente_material="Sintético",
            temperatura_tendido_C=20.,H_min_kN=1.,H_max_kN=6.,
            configuracion_barrido=config,
        )
        f=r.tabla_tendido
        f40=f[f["Temperatura (°C)"]==40.]
        self.assertEqual(len(f40),2)
        self.assertGreater(abs(f40.iloc[0]["H del estado (kN)"]-
                               f40.iloc[1]["H del estado (kN)"]),.001)
        self.assertTrue((f["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertEqual(len(r.barrido["detalle"]),r.barrido["total_estados"]*2)
        self.assertTrue((r.barrido["detalle"]["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertIn("amarres fijos",r.modelo)

    def test_mismo_vano_conserva_valores_entre_modelos(self):
        from Analisis_mecanico_conductores.tension_tendido.evaluar_estados_de_la_seccion import EvaluadorEstadosRegulacion
        a=self.eval.xyz[:2]
        a0=EvaluadorEstadosRegulacion(a,.0085,.02,15000.,1.91e-5,20.,1.2,1.225)
        fixed=EvaluadorVanosAmarrados(a,.0085,.02,15000.,1.91e-5,20.,1.2,1.225)
        h1,ten1,_,res1,_=a0.evaluar_estado(4.,40.,10.)
        hs,ten,_,res,_=fixed.evaluar_estado(4.,40.,10.)
        self.assertAlmostEqual(h1,hs[0],delta=1e-7)
        self.assertAlmostEqual(ten1[0],ten[0],delta=1e-7)
        self.assertAlmostEqual(res1,res[0],delta=1e-7)


# === Casos conservados de tests/test_comparacion_multivano_cfe.py ===
"""Ensayo real del ensamblador de sección continua ideal."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.comparar_multivano_deslizante_cfe import (
    construir_red_deslizante_de_puntos,
    calcular_comparacion_multivano_final,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
)


class MultivanoCFEIntegrado(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0.,50.,100.],
            "Y":[0.,0.,0.],
            "Altitud":[0.,0.,0.],
            "Altura_Amarre_m":[10.,10.,10.],
        })

    def test_conectividad_anclajes_y_guias(self):
        red=construir_red_deslizante_de_puntos(self.puntos,"RAVEN")
        self.assertEqual(len(red.vanos),2)
        v=list(red.vanos.values())
        self.assertEqual(v[0].conexion_origen,"ANCLAJE")
        self.assertEqual(v[0].conexion_destino,"DESLIZANTE")
        self.assertEqual(v[1].conexion_origen,"DESLIZANTE")
        self.assertEqual(v[1].conexion_destino,"ANCLAJE")

    def test_ensayo_numerico_dos_vanos_simetrico(self):
        _,ficha=seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        tabla=calcular_comparacion_multivano_final(
            self.puntos,ficha,1.5,
            temperaturas_C=(50.,),viento_ms=0.,
        )
        self.assertEqual(len(tabla),2)
        self.assertTrue((tabla["Continuidad residual máx. (kN)"]<1e-4).all())
        self.assertLess(
            abs(float(tabla.iloc[0]["Flecha vertical (m)"])
                -float(tabla.iloc[1]["Flecha vertical (m)"])),1e-3
        )
