"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_resistencia_postes.py ===
"""Regresiones del cribado resistente con datos ficticios de ensayo.

Ni las capacidades ni los resultados de estos casos representan postes reales.
"""
import unittest

import pandas as pd

from Analisis_mecanico_estructuras.calculos.resistencia_postes import (
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


# === Casos conservados de tests/test_verificacion_poste.py ===
"""Validaciones mecánicas independientes del diagrama del fuste.

Incluye fuerza puntual en amarre, viento sin cables y equilibrio con base.
No confundir la demanda elástica de corte con resistencia del material.
"""
import math
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_estructuras.calculos.verificacion_poste import (
    calcular_secciones_poste, secciones_gobernantes,
)
from Analisis_mecanico_estructuras.calculos.solicitaciones_poste import (
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


# === Casos conservados de tests/test_solicitaciones_poste.py ===
"""Regresiones independientes de viento en fuste y casos gobernantes."""
import math
import unittest

import numpy as np
import pandas as pd

from Analisis_mecanico_estructuras.calculos.solicitaciones_poste import (
    geometria_fuste, viento_fuste, combinar_solicitaciones_postes,
)
from Analisis_mecanico_conductores.verificaciones.envolventes_3d import mayores_por_apoyo, envolventes_apoyos


class TestVientoEnPoste(unittest.TestCase):
    def test_integral_fuste_cilindrico(self):
        g={"Altura expuesta (m)":10.,"Diámetro terreno (m)":.3,
           "Diámetro punta (m)":.3}
        f=viento_fuste(g,20,0,rho_kg_m3=1.2,Cd_poste=1)
        fuerza=.5*1.2*20**2*.3*10/1000
        np.testing.assert_allclose(f,[fuerza,0,0,0,5*fuerza,0],atol=1e-12)

    def test_integral_fuste_conico_vs_integracion_numerica(self):
        g={"Altura expuesta (m)":10.,"Diámetro terreno (m)":.4,
           "Diámetro punta (m)":.2}
        result=viento_fuste(g,30,90,rho_kg_m3=1.225,Cd_poste=1.2)
        z=np.linspace(0,10,100001)
        d=.4+(.2-.4)*z/10
        q=.5*1.225*1.2*30**2*d/1000
        self.assertAlmostEqual(result[1],np.trapezoid(q,z),places=7)
        self.assertAlmostEqual(result[3],-np.trapezoid(z*q,z),places=7)

    def test_simetria_inversion_viento(self):
        g=geometria_fuste("PC-40")
        self.assertIsNotNone(g)
        self.assertAlmostEqual(g["Empotramiento (m)"],
                               .1*12.19+.6096,places=10)
        a=viento_fuste(g,25,0)
        b=viento_fuste(g,25,180)
        np.testing.assert_allclose(a,-b,atol=1e-12)

    def test_acciones_combinadas_y_envolventes(self):
        df=pd.DataFrame({
            "Punto":["P1","P1"],"Caso":["v0","v20"],
            "Viento (m/s)":[0.,20.],"Azimut viento (°)":[0.,0.],
            "Temperatura (°C)":[20.,20.],"H inicial (kN)":[6.,6.],
            "Fx (kN)":[5.,5.],"Fy (kN)":[0.,0.],"Fz (kN)":[-1.,-1.],
            "Mx (kN·m)":[0.,0.],"My (kN·m)":[45.,45.],
            "Mz (kN·m)":[0.,0.],"H resultante (kN)":[5.,5.],
        })
        postes=pd.DataFrame({"Punto":["P1"],"Poste":["PC-40"],
                             "Empotramiento_m":[1.8]})
        combinado=combinar_solicitaciones_postes(df,postes)
        self.assertEqual(combinado.iloc[0]["Fx (kN)"],5.)
        self.assertGreater(combinado.iloc[1]["Fx (kN)"],5.)
        self.assertGreater(combinado.iloc[1]["My (kN·m)"],45.)
        resumen=mayores_por_apoyo(combinado)
        self.assertEqual(resumen.iloc[0]["Caso de H máxima"],"v20")
        self.assertEqual(resumen.iloc[0]["Caso de M máxima"],"v20")
        env=envolventes_apoyos(combinado)
        self.assertEqual(len(env),8)

    def test_sin_geometria_no_aprueba(self):
        df=pd.DataFrame({
            "Punto":["P1"],"Caso":["a"],"Viento (m/s)":[20.],
            "Azimut viento (°)":[90.],"Fx (kN)":[1.],"Fy (kN)":[2.],
            "Fz (kN)":[0.],"Mx (kN·m)":[0.],"My (kN·m)":[0.],
            "Mz (kN·m)":[0.]
        })
        postes=pd.DataFrame({"Punto":["P1"],"Poste":["TIPO SIN FICHA"]})
        result=combinar_solicitaciones_postes(df,postes)
        self.assertTrue(math.isnan(result.iloc[0]["Fx (kN)"]))
        self.assertIn("INCOMPLETO",result.iloc[0]["Estado viento poste"])


# === Casos conservados de tests/test_retenidas_xyz.py ===
"""Ensayos de estática 3D de retenidas, sin criterios de aprobación."""
import unittest
import numpy as np

from Analisis_mecanico_estructuras.calculos.retenidas_xyz import RetenidaXYZ, estudiar_equilibrio_retenidas


class RetenidasXYZTest(unittest.TestCase):
    def test_retenida_inclinada_equilibra_momento_en_y(self):
        retenida = RetenidaXYZ(
            "R1", (0., 0., 9.), (-12., 0., 0.)
        )
        res = estudiar_equilibrio_retenidas(
            [10., 0., -1.], [0., 90., 0.], [retenida]
        )
        self.assertTrue(res.equilibrio_momentos)
        esperado = 90. / (9. * 12. / 15.)
        self.assertAlmostEqual(res.tensiones_kN["R1"], esperado, places=7)
        np.testing.assert_allclose(
            res.momento_residual_base_kNm, [0,0,0], atol=1e-7
        )
        # La componente vertical de la retenida se transmite a la base.
        self.assertLess(res.fuerza_resultante_base_kN[2], -1.)
        self.assertFalse(res.capacidades_documentadas)
        self.assertIn("NO VERIFICABLE", res.estado)

    def test_orientacion_opuesta_no_se_aprovecha_como_compresion(self):
        res=estudiar_equilibrio_retenidas(
            [0,0,0], [0,90,0],
            [RetenidaXYZ("R1",(0,0,9),(12,0,0))]
        )
        self.assertFalse(res.equilibrio_momentos)
        self.assertGreater(res.residual_momento_kNm,89.99)
        self.assertAlmostEqual(res.tensiones_kN["R1"],0.,places=6)

    def test_topes_documentados_pueden_volver_insuficiente_la_solucion(self):
        res=estudiar_equilibrio_retenidas(
            [0,0,0], [0,90,0],
            [RetenidaXYZ(
                "R1",(0,0,9),(-12,0,0),
                tension_limite_kN=5.,
                fuente_limite="Capacidad de ensayo hipotética"
            )]
        )
        self.assertFalse(res.equilibrio_momentos)
        self.assertLessEqual(res.tensiones_kN["R1"],5.+1e-6)
        self.assertTrue(res.capacidades_documentadas)

    def test_torsion_sin_brazo_lateral_no_puede_equilibrarse(self):
        res=estudiar_equilibrio_retenidas(
            [0,0,0], [0,0,7],
            [RetenidaXYZ("R1",(0,0,9),(-10,0,0))]
        )
        self.assertFalse(res.equilibrio_momentos)
        self.assertAlmostEqual(res.momento_residual_base_kNm[2],7.,places=7)

    def test_no_acepta_falsa_capacidad_sin_fuente(self):
        with self.assertRaisesRegex(ValueError,"capacidad sin fuente"):
            RetenidaXYZ(
                "R1",(0,0,9),(-10,0,0),tension_limite_kN=20
            )

    def test_no_admite_anclaje_por_encima_del_amarre(self):
        with self.assertRaisesRegex(ValueError,"por debajo"):
            RetenidaXYZ("R1",(0,0,9),(-10,0,10))


# === Casos conservados de tests/test_analisis_retenidas_red.py ===
"""Contratos y resultados de retenidas XYZ sobre múltiples estados."""
import unittest
import pandas as pd

from Analisis_mecanico_estructuras.calculos.analisis_retenidas_red import (
    leer_configuraciones_retenidas, evaluar_retenidas_en_barrido,
)


class RetenidasRedTest(unittest.TestCase):
    def setUp(self):
        self.tabla=pd.DataFrame({
            "Punto":["P1"],"Retenida":["R1"],
            "Amarre_X_m":[0],"Amarre_Y_m":[0],"Amarre_Z_m":[9],
            "Anclaje_X_m":[-12],"Anclaje_Y_m":[0],"Anclaje_Z_m":[0],
        })
        self.casos=pd.DataFrame({
            "Punto":["P1","P1"],"Caso":["C1","C2"],
            "Fx (kN)":[10,20],"Fy (kN)":[0,0],"Fz (kN)":[-1,-1],
            "Mx (kN·m)":[0,0],"My (kN·m)":[90,180],
            "Mz (kN·m)":[0,0],
        })

    def test_distintas_demandas_no_se_mezclan(self):
        grupos=leer_configuraciones_retenidas(self.tabla)
        estados,detalles=evaluar_retenidas_en_barrido(self.casos,grupos)
        self.assertEqual(len(estados),2)
        self.assertEqual(len(detalles),2)
        self.assertTrue((estados["Equilibrio momento"]=="FACTIBLE").all())
        a,b=detalles["Tensión solicitada (kN)"].tolist()
        self.assertAlmostEqual(b/a,2,places=6)

    def test_no_inventa_limite_de_ruptura(self):
        grupos=leer_configuraciones_retenidas(self.tabla)
        estados,_=evaluar_retenidas_en_barrido(self.casos,grupos)
        self.assertFalse(estados["Capacidades documentadas"].any())
        self.assertTrue(estados["Estado"].str.contains("NO VERIFICABLE").all())

    def test_retenida_sin_poste_no_se_descarta_silenciosamente(self):
        datos=self.tabla.copy()
        datos.loc[0,"Punto"]="P9"
        with self.assertRaisesRegex(ValueError,"no calculados"):
            evaluar_retenidas_en_barrido(
                self.casos,leer_configuraciones_retenidas(datos)
            )
