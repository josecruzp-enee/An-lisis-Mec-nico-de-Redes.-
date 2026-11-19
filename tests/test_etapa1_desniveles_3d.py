"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_etapa1_desniveles_3d.py ===
"""Ensayos sintéticos de Etapa 1 3D: desnivel y regresión nivelada.

Se verifica el cálculo geométrico respecto a cuerda, sin suponer que el
modelo de regulación representa suspensión real con fricción.
"""
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.flechas.calcular_desplazamientos_catenaria_3d import (
    calcular_flecha_y_desviacion_3d,
)
from Analisis_mecanico_conductores.hipotesis_climaticas.generar_barrido_de_temperatura_viento_hielo import (
    ConfiguracionBarrido,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import (
    resolver_seccion_regulacion,
)


def puntos(cotas=(0.,6.,-3.),amarres=(10.,10.,10.)):
    return pd.DataFrame({
        "Punto":["P1","P2","P3"],
        "X":[0.,45.,90.],
        "Y":[0.,0.,0.],
        "Altitud":list(cotas),
        "Altura_Amarre_m":list(amarres),
    })


def entradas(df, barrido=True):
    hip=pd.DataFrame([{
        "Hipotesis":"Caso sintético",
        "Temperatura_C":0.,"Viento_ms":0.,
        "T_limite_kN":12.,
        "Fuente_limite":"Límite de ensayo NO normativo",
        "Criterio_diseno":"Prueba mecánica sintética",
    }])
    return dict(
        puntos=df,hipotesis=hip,temperaturas_tabla_C=[0.,20.,40.],
        peso_kN_m=.0085,diametro_m=.020,EA_kN=15000.,
        alpha_por_C=1.91e-5,fuente_material="Ensayo sintético",
        temperatura_tendido_C=20.,H_min_kN=1.,H_max_kN=5.,
        configuracion_barrido=(ConfiguracionBarrido(
            temperatura_min_C=20.,temperatura_max_C=40.,
            temperatura_paso_C=20.,
            viento_max_kmh=36.,viento_paso_kmh=18.,
        ) if barrido else None),
    )


class Etapa1Desnivel3DTest(unittest.TestCase):
    def test_flecha_cuerda_desnivelada_no_es_descenso_de_altitud(self):
        a=np.array([0.,0.,100.])
        b=np.array([45.,0.,108.])
        c=resolver_catenaria(a,b,np.array([0.,0.,-.0085]),4.)
        flecha,lateral=calcular_flecha_y_desviacion_3d(c,a,b)
        self.assertGreater(flecha,0.)
        self.assertLess(flecha,1.)
        self.assertAlmostEqual(lateral,0.,delta=1e-8)
        # Con igual geometría y diferencia de cotas invertida,
        # se recupera la misma flecha geométrica respecto a cuerda.
        abajo=np.array([45.,0.,92.])
        c2=resolver_catenaria(a,abajo,np.array([0.,0.,-.0085]),4.)
        self.assertAlmostEqual(
            flecha,calcular_flecha_y_desviacion_3d(c2,a,abajo)[0],delta=.002
        )

    def test_regulacion_con_desnivel_sin_viento_y_con_viento(self):
        r=resolver_seccion_regulacion(**entradas(puntos()))
        self.assertEqual(len(r.hipotesis),1)
        self.assertEqual(len(r.flechas),2)
        self.assertEqual(len(r.tabla_tendido),6)
        self.assertTrue(np.isfinite(r.flechas["Flecha vertical (m)"]).all())
        self.assertTrue((r.flechas["Flecha vertical (m)"]>0).all())
        self.assertTrue((r.hipotesis["Residual compatibilidad (m)"].abs()<1e-7).all())
        detalle=r.barrido["detalle"]
        self.assertEqual(r.barrido["total_estados"],4)
        viento=detalle[detalle["Viento (km/h)"]>0]
        self.assertGreater(viento["Desviación lateral máxima (m)"].max(),0.)
        self.assertTrue((detalle["Residual compatibilidad (m)"].abs()<1e-7).all())
        self.assertIn("3D",r.modelo)

    def test_alturas_de_amarre_diferentes(self):
        df=puntos(cotas=(0.,0.,0.),amarres=(9.,11.,9.))
        r=resolver_seccion_regulacion(**entradas(df,barrido=False))
        self.assertEqual(len(r.tabla_tendido),6)
        self.assertTrue((r.flechas["Flecha vertical (m)"]>=0).all())

    def test_altitud_parcial_se_rechaza(self):
        df=puntos()
        df.loc[1,"Altitud"]=float("nan")
        with self.assertRaisesRegex(ValueError,"Altitud parcial"):
            resolver_seccion_regulacion(**entradas(df))

    def test_no_asumir_amarre_en_suelo_si_altitudes_difieren(self):
        df=puntos()
        df=df.drop(columns=["Altura_Amarre_m"])
        with self.assertRaisesRegex(ValueError,"Altura_Amarre_m"):
            resolver_seccion_regulacion(**entradas(df))

    def test_no_asumir_terreno_nivelado_si_alturas_difieren(self):
        df=puntos(cotas=(0.,0.,0.),amarres=(9.,11.,9.))
        df=df.drop(columns=["Altitud"])
        with self.assertRaisesRegex(ValueError,"Altitud completa"):
            resolver_seccion_regulacion(**entradas(df))

    def test_nivelados_preservan_flecha_legacy(self):
        from Analisis_mecanico_conductores.flechas.calcular_flecha_vertical_de_catenaria import (
            calcular_flecha_vertical_de_catenaria,
        )
        a=np.array([0.,0.,10.])
        b=np.array([45.,0.,10.])
        c=resolver_catenaria(a,b,np.array([0.,0.,-.0085]),4.)
        f,_=calcular_flecha_y_desviacion_3d(c,a,b)
        self.assertAlmostEqual(f,calcular_flecha_vertical_de_catenaria(c,a,b),delta=1e-7)


# === Casos conservados de tests/test_desniveles_extremos_diagnostico.py ===
"""Diagnóstico numérico de vanos con desniveles severos; no forzar cumplimiento."""
import unittest
import pandas as pd
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01, ejecutar_corridas_cfe_por_vano
)

class TerrenoExtremo(unittest.TestCase):
    def test_vanos_desnivelados_mensaje_diagnostico(self):
        puntos=pd.DataFrame({
            "Punto":["P1","P2","P3","P4","P5","P6"],
            "X":[0.,50.,120.,240.,390.,690.],
            "Y":[0.,0.,0.,0.,0.,0.],
            "Altitud":[100.,125.,92.,155.,110.,185.],
            "Poste":["PC-40"]*6,
            "Altura_Amarre_m":[9.5,10.5,9.,11.5,10.,12.],
            "Espacio Retenida":["SI"]*6,
        })
        ini,fin=seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        try:
            resumen,tabla=ejecutar_corridas_cfe_por_vano(
                puntos,ini,fin,viento_max_kmh=120.,
                viento_reducido_kmh=0.,hielo_mm=6.,
                temperaturas_C=[-10.,0.,16.,20.,50.],
                Cd=1.,rho_kg_m3=1.225,
            )
        except Exception as exc:
            raise AssertionError(
                f"Diagnóstico de prueba extrema: {type(exc).__name__}: {exc}"
            ) from exc
        self.assertEqual(int(resumen["Número de vanos"].iloc[0]),5)
        self.assertFalse(tabla.empty)


# === Casos conservados de tests/test_flecha_despeje_3d.py ===
"""Pruebas de flecha y despeje de referencia con catenaria espacial."""
import unittest
import math
import numpy as np

from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
from Analisis_mecanico_conductores.cambio_estado.resolver_cambio_de_estado import resolver_cambio_estado
from Analisis_mecanico_conductores.hipotesis_climaticas.evaluar_estados_climaticos_catenaria_3d import _carga_viento

from Analisis_mecanico_conductores.hipotesis_climaticas.evaluar_estados_climaticos_catenaria_3d import ejecutar_barrido_3d


class TestFlechaDespeje(unittest.TestCase):
    def test_nivelado_sin_viento_cotejo_analitico(self):
        w=.01;H=8.;L=40.;h=10.
        v=[{
            "nombre":"A-B","inicio":"A","fin":"B",
            "base_inicio_m":[0,0,0],"base_fin_m":[L,0,0],
            "amarre_inicio_m":[0,0,h],"amarre_fin_m":[0,0,h],
        }]
        r=ejecutar_barrido_3d(
            v,peso_kN_m=w,diametro_m=.02,EA_kN=16000,
            alpha_por_C=1.8e-5,temperatura_tendido_C=20,
            temperaturas_C=[20],tensiones_iniciales_kN=[H],
            viento_max_ms=0,direcciones_viento_deg=[0],
            fuente_conductor="Ensayo sintético",
        )
        fila=r["vanos"].iloc[0]
        a=H/w
        f=a*(math.cosh(L/(2*a))-1)
        self.assertAlmostEqual(fila["Flecha vertical respecto cuerda (m)"],f,places=5)
        self.assertAlmostEqual(fila["Despeje sobre terreno lineal (m)"],h-f,places=5)

    def test_viento_desnivel_flecha_con_progresiva_horizontal(self):
        # Verificación independiente mediante muestreo denso de la curva,
        # sin reutilizar el algoritmo analítico de mínimos de la interfaz.
        a=np.array([0.,0.,12.])
        b=np.array([70.,15.,29.])
        w=.009
        diametro=.020
        q0=np.array([0.,0.,-w])
        q1=_carga_viento(a,b,w,diametro,30.,90.,1.2,1.225)
        cambio=resolver_cambio_estado(
            [(a,b,q0,q1)],7.,16000.,1.8e-5,0.
        )
        cable=resolver_catenaria(a,b,q1,cambio["H_kN"])
        muestra=cable.puntos(np.linspace(0,cable.luz,40001))
        eje=b[:2]-a[:2]
        t=((muestra[:,:2]-a[:2])@eje)/(eje@eje)
        z_cuerda=a[2]+(b[2]-a[2])*t
        flecha_ref=float(np.max(z_cuerda-muestra[:,2]))
        lateral_ref=float(np.max(np.abs(
            eje[0]*(muestra[:,1]-a[1])
            -eje[1]*(muestra[:,0]-a[0])
        )/np.linalg.norm(eje)))

        vanos=[{
            "nombre":"A-B","inicio":"A","fin":"B",
            "base_inicio_m":[0,0,0],
            "base_fin_m":[70,15,17],
            "amarre_inicio_m":[0,0,12],
            "amarre_fin_m":[0,0,12],
        }]
        r=ejecutar_barrido_3d(
            vanos,peso_kN_m=w,diametro_m=diametro,
            EA_kN=16000,alpha_por_C=1.8e-5,
            temperatura_tendido_C=20,temperaturas_C=[20],
            tensiones_iniciales_kN=[7],
            viento_min_ms=30,viento_max_ms=30,
            direcciones_viento_deg=[90],
            fuente_conductor="Ensayo sintético",
        )
        fila=r["vanos"].iloc[0]
        self.assertAlmostEqual(
            fila["Flecha vertical respecto cuerda (m)"],
            flecha_ref,delta=3e-5
        )
        self.assertGreater(
            fila["Desviación lateral en punto de flecha (m)"],0.
        )
        self.assertGreater(lateral_ref,0.)

    def test_desnivelado_muestra_despeje_sin_aprobar(self):
        v=[{
            "nombre":"A-B","inicio":"A","fin":"B",
            "base_inicio_m":[0,0,0],"base_fin_m":[50,0,8],
            "amarre_inicio_m":[0,0,11],"amarre_fin_m":[0,0,10],
        }]
        r=ejecutar_barrido_3d(
            v,peso_kN_m=.01,diametro_m=.02,EA_kN=16000,
            alpha_por_C=1.8e-5,temperatura_tendido_C=20,
            temperaturas_C=[20],tensiones_iniciales_kN=[5],
            viento_max_ms=10,direcciones_viento_deg=[90],
            fuente_conductor="Ensayo sintético",
        )
        self.assertTrue((r["vanos"]["Despeje sobre terreno lineal (m)"]>0).all())
        self.assertTrue((r["vanos"]["Modelo terreno"].str.contains("NO VERIFICADO")).all())
