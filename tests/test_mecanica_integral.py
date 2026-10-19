"""Pruebas físicas independientes: geometría, equilibrio, compatibilidad y no aprobación."""
import copy
import json
import math
import unittest
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
from analisis.catenaria import resolver_catenaria
from analisis.cambio_estado import resolver_cambio_estado, longitud_natural
from analisis.retenidas_espaciales import resolver_poste_retenidas
from analisis.estados_limite import Estado, verificar_capacidad, estado_conjunto
from analisis.alternativas_estructurales import seleccionar_alternativa
from analisis.motor_integral import ejecutar_proyecto_integral
from analisis.engine import ejecutar_todo
from analisis.perfil import analizar_perfil, evaluar_despeje_por_vano
from analisis.io_excel import leer_puntos_excel
from analisis.memoria_calculo import exportar_json, exportar_excel_memoria

ROOT = Path(__file__).resolve().parents[1]


def proyecto():
    """Ejemplo sintético, nunca una ficha real de ACSR Flicker."""
    return json.loads((ROOT/'ejemplos/piloto_477_sintetico.json').read_text())


def puntos():
    """Giro de 90° y dos remates, amarres reales de 10 m sobre terreno plano."""
    return pd.DataFrame({'Punto':['A','B','C'],'X':[0.,40.,40.],'Y':[0.,0.,40.],
        'Altitud':[100.,100.,100.],'Altura_Amarre_m':[10.,10.,10.],
        'Poste':['PC-40']*3,'Espacio Retenida':['SI']*3})


class CatenariaTest(unittest.TestCase):
    def test_apoyos_desnivelados_y_equilibrio_3d(self):
        for q in ([0,0,-.01],[0,.02,-.01]):
            c=resolver_catenaria([0,0,10],[40,0,14],q,8)
            np.testing.assert_allclose(c.puntos(0),[0,0,10],atol=1e-12)
            np.testing.assert_allclose(c.puntos(c.luz),[40,0,14],atol=1e-12)
            a,b=c.fuerzas
            np.testing.assert_allclose(a+b,np.array(q)*c.longitud,atol=1e-12)
            self.assertGreater(c.longitud,math.sqrt(40**2+4**2))

    def test_solucion_nivelada_independiente(self):
        c=resolver_catenaria([0,0,10],[40,0,10],[0,0,-.01],8)
        a=8/.01
        self.assertAlmostEqual(10-c.puntos(20)[2],2*a*math.sinh(40/(4*a))**2,places=12)
        self.assertAlmostEqual(c.longitud,2*a*math.sinh(40/(2*a)),places=12)
        self.assertAlmostEqual(float(c.tension(0)),8*math.cosh(40/(2*a)),places=12)

    def test_limites_y_entradas_invalidas(self):
        for H in (0,-1,float('nan')):
            with self.assertRaises(ValueError):
                resolver_catenaria([0,0,0],[40,0,0],[0,0,-.01],H)
        with self.assertRaises(ValueError):
            resolver_catenaria([0,0,0],[0,0,20],[0,0,-.01],10)
        c=resolver_catenaria([0,0,0],[40,0,0],[0,0,-1e-7],10)
        self.assertAlmostEqual(-c.puntos(20)[2],1e-7*40**2/(8*10),places=12)

    def test_cambio_estado_identidad_y_calor(self):
        vano=([0,0,10],[40,0,12],[0,0,-.01],[0,0,-.01])
        r0=resolver_cambio_estado([vano],8,16000,1.8e-5,0)
        r1=resolver_cambio_estado([vano],8,16000,1.8e-5,30)
        self.assertAlmostEqual(r0['H_kN'],8,places=6)
        self.assertLess(r1['H_kN'],8)
        self.assertLess(abs(r1['residual_m']),1e-8)

    def test_cuadratura_y_seccion(self):
        c=resolver_catenaria([0,0,10],[40,0,20],[0,0,-.01],5)
        x,w=np.polynomial.legendre.leggauss(128)
        x=(x+1)*c.luz/2
        independiente=c.luz/2*np.dot(w,np.cosh((x-c.xc)/c.a)/(1+c.tension(x)/16000))
        self.assertAlmostEqual(longitud_natural(c,16000),independiente,places=11)
        vanos=[([0,0,0],[L,0,0],[0,0,-.01],[0,0,-.015]) for L in (20,40,48)]
        r=resolver_cambio_estado(vanos,8,16000,1.8e-5,0)
        self.assertGreater(r['H_kN'],8)

    def test_despeje_no_depende_malla(self):
        args=(0,40,0,2,10,13,2)
        a=evaluar_despeje_por_vano(*args,3)[3]
        b=evaluar_despeje_por_vano(*args,5000)[3]
        self.assertEqual(a,b)
        datos=puntos().iloc[:2].copy()
        datos['Altitud']=[100,103]
        r=analizar_perfil(datos,'PC-40','477 MCM',H_kN=10)
        self.assertEqual(r['tabla_vanos'][0]['Cumple despeje'],'NO VERIFICABLE')
        np.testing.assert_allclose(r['Y_prof'][[0,-1]],r['amarre'])
        self.assertNotEqual(r['tabla_vanos'][0]['Ts A (kN)'],r['tabla_vanos'][0]['Ts B (kN)'])


class EquilibrioTest(unittest.TestCase):
    def test_giros_y_remate(self):
        for ang in (0,5,30,60,90):
            d=puntos(); th=math.radians(ang)
            d.loc[2,['X','Y']]=[40+40*math.cos(th),40*math.sin(th)]
            r=ejecutar_todo(d,calibre='477 MCM',n_fases=3,v_viento_ms=0,
                            az_viento_deg=0,diametro_m=.02177,H_tendido_kN=10)
            f=r['fuerzas_nodo']
            self.assertAlmostEqual(f.iloc[1]['H (kN)'],60*math.sin(th/2),places=10)
            self.assertAlmostEqual(f.iloc[0]['H (kN)'],30,places=10)
            self.assertLess(f.iloc[1]['Fz (kN)'],0)
            self.assertTrue((r['decision']['Solución']=='NO VERIFICABLE').all())

    def test_retenida_tres_metros_y_cable_flojo(self):
        K=np.diag([1.,100.,100.,100.,100.,100.])
        retenidas=[{'amarre_m':[0,0,10],'ancla_m':[-3,0,0],'EA_kN':10000},
                   {'amarre_m':[0,0,10],'ancla_m':[3,0,0],'EA_kN':10000}]
        r=resolver_poste_retenidas(K,[1,0,0,0,10,0],retenidas)
        self.assertGreater(r['tensiones_kN'][0],0)
        self.assertEqual(r['tensiones_kN'][1],0)
        self.assertLess(np.linalg.norm(r['residual'],np.inf),1e-8)
        self.assertLess(r['acciones_poste'][2],0)  # compresión inducida conservada
        self.assertGreater(r['tensiones_kN'][0],1)  # anclaje próximo aumenta tracción

    def test_sin_retenidas_y_rigidez_invalida(self):
        K=np.diag([10.,20.,30.,40.,50.,60.]); F=np.array([1,2,-3,4,5,6])
        r=resolver_poste_retenidas(K,F,[])
        np.testing.assert_allclose(r['desplazamiento'],np.linalg.solve(K,F))
        with self.assertRaises(ValueError):
            resolver_poste_retenidas(np.zeros((6,6)),F,[])


class IntegracionTest(unittest.TestCase):
    def test_estados_alternativas_exportacion(self):
        r=ejecutar_proyecto_integral(proyecto())
        self.assertEqual(len(r['vanos_estados']),6)
        self.assertLess(r['vanos_estados']['Residual equilibrio (kN)'].max(),1e-10)
        self.assertTrue(r['decision']['seleccion'].isna().all())
        self.assertIn('NO VERIFICABLE',set(r['verificaciones']['estado']))
        texto=exportar_json(r)
        self.assertNotIn(b'NaN',texto)
        self.assertEqual(json.loads(texto)['entrada']['nombre'],proyecto()['nombre'])
        libro=pd.ExcelFile(BytesIO(exportar_excel_memoria(r)))
        self.assertIn('Trazabilidad',libro.sheet_names)
        self.assertIn('Paquete_JSON',libro.sheet_names)

    def test_no_acepta_propiedades_ausentes(self):
        d=proyecto(); del d['conductores'][0]['EA_kN']
        with self.assertRaisesRegex(ValueError,'EA/alpha'):
            ejecutar_proyecto_integral(d)

    def test_excel_preserva_amarres_y_altitud(self):
        memoria=BytesIO(); puntos().to_excel(memoria,index=False); memoria.seek(0)
        df=leer_puntos_excel(memoria)
        self.assertIn('Altura_Amarre_m',df)
        self.assertIn('Altitud',df)
        d=puntos(); d.loc[1,'Punto']='A'
        memoria=BytesIO(); d.to_excel(memoria,index=False); memoria.seek(0)
        with self.assertRaises(ValueError):
            leer_puntos_excel(memoria)

    def test_faltantes_no_aprueban(self):
        v=verificar_capacidad('suelo',1,None,'kN')
        self.assertEqual(v.estado,Estado.NO_VERIFICABLE)
        self.assertEqual(estado_conjunto([]),Estado.NO_VERIFICABLE)
        self.assertEqual(estado_conjunto([v,verificar_capacidad('poste',2,1,'kN','ensayo')]),Estado.NO_CUMPLE)
        d=puntos().drop(columns=['Altura_Amarre_m'])
        r=ejecutar_todo(d,calibre='477 MCM',n_fases=3,v_viento_ms=0,az_viento_deg=0,diametro_m=.02177)
        self.assertIsNone(r['perfil'])
        self.assertTrue((r['decision']['Solución']=='NO VERIFICABLE').all())

    def test_costos_solo_alternativas_admisibles(self):
        def alt(nombre,estado,costo,caso):
            return dict(nombre=nombre,estado=estado,costo_total=costo,fuente_costo='presupuesto',caso=caso)
        filas=[alt('barata',Estado.CUMPLE,1,'normal'),alt('barata',Estado.NO_CUMPLE,1,'viento'),
               alt('viable',Estado.CUMPLE,10,'normal'),alt('viable',Estado.CUMPLE,10,'viento')]
        self.assertEqual(seleccionar_alternativa(filas)['seleccion'],'viable')
        filas[-1]['costo_total']=None
        # El costo es por alternativa y debe ser consistente: caso validado en el constructor JSON.
        filas[-2]['costo_total']=None
        self.assertIsNone(seleccionar_alternativa(filas)['seleccion'])


if __name__ == '__main__':
    unittest.main()
