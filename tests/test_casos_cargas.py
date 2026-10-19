"""Casos de integración que distinguen dirección, fase, momento y datos faltantes."""
import copy
import unittest
import numpy as np
from test_mecanica_integral import proyecto
from analisis.motor_integral import ejecutar_proyecto_integral
from analisis.cargas_espaciales import resultante_acciones
from analisis.cargas_tramo import calcular_cargas_por_tramo
from analisis.geometria import calcular_tramos
from analisis.cimentacion import evaluar_cimentacion
from analisis.norma_postes import H_max_poste_kN,obtener_ficha_poste
from analisis.alternativas_estructurales import evaluar_alternativa
from analisis.estados_limite import Estado
import pandas as pd


class CargasTest(unittest.TestCase):
    def test_peso_no_se_convierte_en_fuerza_horizontal(self):
        tr=calcular_tramos([(0,0),(40,0)],['A','B'])
        r=calcular_cargas_por_tramo(tr,calibre='477 MCM',n_fases=3,v_viento_ms=0,
            azimut_viento_deg=90,diametro_conductor_m=.02177)
        self.assertEqual(r.iloc[0]['w_viento_eff (kN/m)'],0)
        self.assertGreater(r.iloc[0]['w_peso (kN/m)'],0)

    def test_viento_fases_y_sentido(self):
        tr=calcular_tramos([(0,0),(40,0)],['A','B'])
        kwargs=dict(calibre='477 MCM',v_viento_ms=25,azimut_viento_deg=90,diametro_conductor_m=.02177)
        a=calcular_cargas_por_tramo(tr,n_fases=1,**kwargs)
        b=calcular_cargas_por_tramo(tr,n_fases=3,**kwargs)
        self.assertAlmostEqual(b.iloc[0]['w_viento_eff (kN/m)'],3*a.iloc[0]['w_viento_eff (kN/m)'])
        d=proyecto(); d['estados'][2]['azimut_deg']=270
        r=ejecutar_proyecto_integral(d)
        base=ejecutar_proyecto_integral(proyecto())
        def fy(r):
            f=r['acciones_nodos'];return f[(f.Caso=='viento') & (f.Punto=='A')].iloc[0].Fy
        self.assertAlmostEqual(fy(r),-fy(base),places=10)

    def test_equipo_excentrico_torsion(self):
        r=resultante_acciones([([1,0,10],[0,2,-3],[0,0,4])])
        np.testing.assert_allclose(r,[0,2,-3,-20,3,6])
        d=proyecto(); d['acciones_adicionales']=[{'nodo':'B','estado':'tendido',
            'posicion_m':[1,0,10],'fuerza_kN':[0,2,-3],'fuente':'Equipo sintético'}]
        r=ejecutar_proyecto_integral(d);f=r['acciones_nodos']
        self.assertEqual(f[(f.Punto=='B') & (f.Caso=='tendido')].iloc[0].Mz,2)

    def test_vanos_desiguales(self):
        d=proyecto();d['nodos'][2]['base_m']=[40,25,100]
        r=ejecutar_proyecto_integral(d)
        v=r['vanos_estados'];v=v[v.Estado=='tendido']
        f=r['acciones_nodos'];f=f[f.Caso=='tendido']
        w=d['conductores'][0]['peso_kN_m']
        self.assertAlmostEqual(f.Fz.sum(),-3*w*v['Longitud real (m)'].sum(),places=10)

    def test_doble_remate_secciones_distintas(self):
        d=proyecto();d['nodos'][2]['base_m']=[80,0,100]
        c=copy.deepcopy(d['conductores'][0]);c['nombre']='otra_seccion';c['H_tendido_kN']=12
        d['conductores'].append(c);d['vanos'][1]['conductor']=c['nombre']
        r=ejecutar_proyecto_integral(d);f=r['acciones_nodos']
        self.assertAlmostEqual(f[(f.Punto=='B') & (f.Caso=='tendido')].iloc[0].Fx,6)

    def test_suelo_desconocido_y_ruptura(self):
        self.assertTrue(np.isnan(H_max_poste_kN('DESCONOCIDO')))
        self.assertTrue(np.isnan(H_max_poste_kN('PC-40')))
        self.assertEqual(obtener_ficha_poste('PM-40')['fuente'],'NO_ENCONTRADO')
        r=evaluar_cimentacion(pd.DataFrame({'H_poste (kN)':[1.],'h_amarre (m)':[10.]}))
        self.assertEqual(r.iloc[0]['Cumple cimentación'],'NO VERIFICABLE')

    def test_capacidad_insuficiente_y_sin_espacio(self):
        alt={'nombre':'Insuficiente','capacidades_poste':{'flexion_y':{
            'valor':1,'fuente':'Capacidad sintética','tipo':'admisible','metodo':'servicio'}}}
        r=evaluar_alternativa(alt,[2,0,0,0,20,0],'carga','servicio')
        self.assertEqual(r['estado'],Estado.NO_CUMPLE)
        alt['retenidas']=[{'amarre_m':[0,0,10],'ancla_m':[-3,0,0],'EA_kN':10000}]
        alt['espacio_retenidas']=False
        r=evaluar_alternativa(alt,[0,0,0,0,0,0],'carga','servicio')
        self.assertEqual(r['estado'],Estado.NO_CUMPLE)


if __name__=='__main__':
    unittest.main()
