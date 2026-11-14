"""Pruebas de flecha y despeje de referencia con catenaria espacial."""
import unittest
import math
import numpy as np

from calculos.catenaria import resolver_catenaria
from calculos.cambio_estado import resolver_cambio_estado
from calculos.barrido_3d import _carga_viento

from calculos.barrido_3d import ejecutar_barrido_3d


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


if __name__=="__main__":
    unittest.main()
