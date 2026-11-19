"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_cfe_hipotesis_documentadas.py ===
"""CFE DCCIAMBT: pruebas de hipótesis y separación de tablas ENEE."""
import unittest

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    construir_hipotesis_cfe,
)


class HipotesisCfeDocumentadas(unittest.TestCase):
    def test_condiciones_cfe_por_estado(self):
        inicial,final=construir_hipotesis_cfe(
            20.,viento_max_kmh=120.,viento_reducido_kmh=90.,hielo_mm=2.,
        )
        self.assertEqual(len(inicial),1)
        self.assertEqual(len(final),4)
        self.assertEqual(inicial[0].temperatura_C,0.)
        self.assertAlmostEqual(inicial[0].limite_tension_kN,6.6)
        self.assertEqual(
            [(c.temperatura_C,c.viento_kmh,c.hielo_mm) for c in final],
            [(16.,0.,0.),(0.,0.,0.),(-10.,90.,2.),(0.,120.,0.)],
        )
        self.assertEqual(
            [c.limite_tension_kN for c in final],[4.,5.,9.,9.],
        )
        for caso in inicial+final:
            caso.validar()

    def test_cero_hielo_y_viento_es_valido(self):
        inicial, final = construir_hipotesis_cfe(
            20., viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
        )
        self.assertEqual(final[2].hielo_mm, 0.)
        self.assertEqual(final[2].viento_kmh, 0.)
        self.assertIn("SIN hielo", final[2].nombre)
        for caso in inicial + final:
            caso.validar()

    def test_no_admitir_clima_negativo(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20., viento_max_kmh=120., viento_reducido_kmh=90., hielo_mm=-1.,
            )
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20., viento_max_kmh=120., viento_reducido_kmh=-1., hielo_mm=0.,
            )

    def test_corrida_integral_un_vano_sin_p_importado(self):
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import (
            seleccionar_conductor_enee,
        )
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
            ejecutar_corridas_cfe_por_vano,
        )
        puntos=pd.DataFrame({
            "Punto":["P1","P2"],"X":[0.,50.],"Y":[0.,0.],
            "Altitud":[100.,100.],"Altura_Amarre_m":[9.5,9.5],
        })
        ini=seleccionar_conductor_enee("1/0","RAVEN","Inicial")
        fin=seleccionar_conductor_enee("1/0","RAVEN","Final")
        resumen,tabla=ejecutar_corridas_cfe_por_vano(
            puntos,ini,fin,viento_max_kmh=120.,
            viento_reducido_kmh=90.,hielo_mm=2.,
            temperaturas_C=[20.,50.],
        )
        self.assertEqual(set(tabla["Condición"]),{"Inicial","Final"})
        self.assertEqual(len(tabla),8)
        self.assertTrue((tabla["Flecha (m)"]>0).all())
        self.assertTrue((tabla["T máx. (kN)"]>0).all())
        self.assertEqual(len(resumen),2)

    def test_corrida_integral_sin_hielo(self):
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        inicial = seleccionar_conductor_enee("1/0", "RAVEN", "Inicial")
        final = seleccionar_conductor_enee("1/0", "RAVEN", "Final")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final, viento_max_kmh=120.,
            viento_reducido_kmh=0., hielo_mm=0., temperaturas_C=[20., 50.],
        )
        self.assertEqual(len(resumen), 2)
        self.assertTrue((tabla["Hielo (mm)"] == 0).all())
        self.assertTrue((tabla["Flecha (m)"] > 0).all())

    def test_pigeon_3_0_sin_hielo_en_vano_50m(self):
        """Regresión: H50 no monótona a cargas tangenciales altas."""
        import pandas as pd
        import numpy as np
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        inicial = seleccionar_conductor_enee("3/0", "PIGEON", "Inicial")
        final = seleccionar_conductor_enee("3/0", "PIGEON", "Final")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final,
            viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
            temperaturas_C=[-10., 0., 20., 50.],
        )
        self.assertEqual(len(resumen), 2)
        self.assertEqual(len(tabla), 12)
        self.assertTrue(np.isfinite(tabla["H (kN)"]).all())
        self.assertTrue((tabla["H (kN)"] > 0).all())
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())

    def test_fuente_cfe_tendido_inicial_tiene_P_mayor_que_final(self):
        """CFE 07 FT 10/11: P inicial supera P final a 50 °C."""
        import pandas as pd
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
            seleccionar_propiedades_cfe_07_ft_01, ejecutar_corridas_cfe_por_vano,
        )
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        for nombre in ("RAVEN", "PIGEON"):
            ini, fin = seleccionar_propiedades_cfe_07_ft_01(nombre)
            resumen, _ = ejecutar_corridas_cfe_por_vano(
                puntos, ini, fin,
                viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
                temperaturas_C=[20., 50.],
            )
            p_ini = float(resumen.iloc[0]["parametro_P_m"])
            p_fin = float(resumen.iloc[1]["parametro_P_m"])
            self.assertGreater(p_ini, p_fin,
                f"{nombre}: P inicial {p_ini:.3f} no supera P final {p_fin:.3f}")

    def test_limites_estructurales_cfe_pigeon_y_raven(self):
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import construir_hipotesis_cfe
        for nombre, th1, th2 in [
            ("RAVEN", 6.495, 5.618),
            ("PIGEON", 8.824, 7.513),
        ]:
            _ini, finales = construir_hipotesis_cfe(
                100., viento_max_kmh=120.,
                viento_reducido_kmh=80., hielo_mm=3.,
                nombre_conductor=nombre,
            )
            self.assertAlmostEqual(finales[2].limite_tension_kN, 45.)
            self.assertAlmostEqual(finales[3].limite_tension_kN, 45.)
            self.assertAlmostEqual(finales[2].limite_horizontal_kN, th1)
            self.assertAlmostEqual(finales[3].limite_horizontal_kN, th2)
        _ini, sin_especificar = construir_hipotesis_cfe(
            100., viento_max_kmh=120., viento_reducido_kmh=80.,
            hielo_mm=3.,
        )
        self.assertAlmostEqual(sin_especificar[2].limite_tension_kN, 45.)
        self.assertIsNone(sin_especificar[2].limite_horizontal_kN)

    def test_th_horizontal_y_porcentaje_total_son_restricciones_distintas(self):
        inicial, final = construir_hipotesis_cfe(
            19.4774, viento_max_kmh=120., viento_reducido_kmh=0.,
            hielo_mm=6., nombre_conductor="RAVEN",
        )
        self.assertAlmostEqual(final[2].limite_tension_kN, 19.4774 * .45)
        self.assertAlmostEqual(final[3].limite_tension_kN, 19.4774 * .45)
        self.assertAlmostEqual(final[2].limite_horizontal_kN, 6.495)
        self.assertAlmostEqual(final[3].limite_horizontal_kN, 5.618)
        self.assertIsNone(inicial[0].limite_horizontal_kN)

    def test_estado_inicial_acoplado_al_extremo_final(self):
        """CFE 07 FT 01: misma tensión extrema a -10 °C, no P iguales."""
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        for calibre, nombre in [("1/0", "RAVEN"), ("3/0", "PIGEON")]:
            ini = seleccionar_conductor_enee(calibre, nombre, "Inicial")
            fin = seleccionar_conductor_enee(calibre, nombre, "Final")
            resumen, tabla = ejecutar_corridas_cfe_por_vano(
                puntos, ini, fin, viento_max_kmh=120.,
                viento_reducido_kmh=0., hielo_mm=0.,
                temperaturas_C=[-10., 20., 50.],
            )
            extremos = tabla[
                (tabla["Hipótesis"] == "CFE viento reducido SIN hielo")
            ].set_index("Condición")
            self.assertAlmostEqual(
                float(extremos.loc["Inicial", "T máx. (kN)"]),
                float(extremos.loc["Final", "T máx. (kN)"]),
                delta=1e-5,
            )
            self.assertNotAlmostEqual(
                resumen.iloc[0]["parametro_P_m"],
                resumen.iloc[1]["parametro_P_m"], delta=1e-4,
            )

    def test_pigeon_3_0_desnivel_10m(self):
        import pandas as pd
        from Analisis_mecanico_conductores.conductores.seleccionar_propiedades_enee import seleccionar_conductor_enee
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import ejecutar_corridas_cfe_por_vano
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"], "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 110.], "Altura_Amarre_m": [9.5, 9.5],
        })
        inicial = seleccionar_conductor_enee("3/0", "PIGEON", "Inicial")
        final = seleccionar_conductor_enee("3/0", "PIGEON", "Final")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final,
            viento_max_kmh=120., viento_reducido_kmh=0., hielo_mm=0.,
            temperaturas_C=[0., 20., 50.],
        )
        self.assertEqual(resumen["Desnivel máximo entre apoyos (m)"].iloc[0], 10.)
        self.assertTrue((tabla["Flecha (m)"] >= 0).all())
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())

    def test_rechaza_viento_reducido_mayor(self):
        with self.assertRaises(ValueError):
            construir_hipotesis_cfe(
                20.,viento_max_kmh=100.,viento_reducido_kmh=140.,hielo_mm=2.,
            )


    def test_diagnostico_acoplamiento_real_en_cinco_vanos(self):
        """El residuo reportado debe coincidir con las tablas fisicas emitidas."""
        import numpy as np
        import pandas as pd
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
            seleccionar_propiedades_cfe_07_ft_01, ejecutar_corridas_cfe_por_vano,
        )
        ini, fin = seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        puntos=pd.DataFrame({
            "Punto":[f"P{i+1}" for i in range(6)],
            "X":np.cumsum([0.,50.,65.,75.,120.,150.]),
            "Y":[0.]*6,
            "Altitud":[100.]*6,
            "Altura_Amarre_m":[10.]*6,
        })
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, ini, fin,
            viento_max_kmh=120., viento_reducido_kmh=109.,
            hielo_mm=6., temperaturas_C=[0.,20.,50.],
            Cd=1., modelo_presion_cfe=True,
        )
        extremo=tabla[
            (tabla["Temperatura (°C)"] == -10.)
            & (tabla["Viento (km/h)"] == 109.)
            & (tabla["Hielo (mm)"] == 6.)
        ]
        self.assertEqual(len(extremo),10)
        max_ini=float(extremo[extremo["Condición"]=="Inicial"]["T máx. (kN)"].max())
        max_fin=float(extremo[extremo["Condición"]=="Final"]["T máx. (kN)"].max())
        error=abs(max_ini-max_fin)
        self.assertAlmostEqual(
            float(resumen.iloc[0]["Diferencia real de acoplamiento H4 (kN)"]),
            error,delta=1e-9,
        )
        self.assertAlmostEqual(
            float(resumen.iloc[0]["Diferencia real de acoplamiento H4 (%)"]),
            100.*error/max_fin,delta=1e-8,
        )
        self.assertEqual(
            bool(resumen.iloc[0]["Igualdad extrema publicada verificada"]),
            error <= max(1e-5,1e-6*max_fin),
        )
        self.assertTrue((tabla["Residual (m)"].abs()<1e-7).all())


# === Casos conservados de tests/test_restricciones_cfe_documentadas.py ===
"""Pruebas de integridad de tablas CFE y condiciones no verificables."""
import csv
from Analisis_mecanico_conductores.verificaciones.verificar_restricciones_documentadas_cfe import (
    CATALOGO, fila_tabla, verificar_tabla_estructura, verificar_traccion,
    separacion_fases_minima, verificar_horizontal_construccion, verificar_fases,
)

def test_catalogo_fuente_662_filas_sin_rellenar_ausentes():
    with CATALOGO.open(encoding="utf-8-sig",newline="") as f:
        filas=list(csv.DictReader(f))
    assert len(filas)==662
    assert len({(r["estructura"],r["ambiente"],r["conductor"],r["tension_clase_kV"]) for r in filas})==662
    assert fila_tabla("VD3N","ACSR HAWK 477",33) is None

def test_raven_ts3n_fuente_181():
    f=fila_tabla("TS3N","ACSR RAVEN 1/0",13)
    assert int(f["pagina_pdf"])==181
    assert [int(f[c]) for c in ("poste_max_m","cable_max_m","cruceta_con_hielo_max_m",
                                 "libramiento_piso_max_m","separacion_fases_max_m")]==[109,109,242,126,123]
    v=verificar_tabla_estructura(120,"TS3N","ACSR RAVEN 1/0",13)
    assert v["estado"]=="EXCEDE TABLA CFE"
    assert v["criterios"]["poste_max_m"]["cumple"] is False
    assert v["criterios"]["libramiento_piso_max_m"]["cumple"] is True

def test_limites_de_traccion_requieren_casos_completos():
    r=verificar_traccion(19477.4,{"final_0C_sin_viento":4800})
    assert r["final_0C_sin_viento"]["estado"]=="CUMPLE"
    assert r["inicial_0C_sin_viento"]["estado"]=="NO VERIFICABLE"
    assert abs(r["final_0C_sin_viento"]["limite_N"]-4869.35)<1e-5

def test_separacion_fases_no_extrapola():
    assert separacion_fases_minima(13,1.50,62.4378)==.55
    assert separacion_fases_minima(13,4.0,62.4378) is None
    assert verificar_fases(13,4.0,62.4378,1.0)["estado"]=="NO VERIFICABLE"

def test_horizontal_requiere_obstaculo_y_viento_especificado():
    assert verificar_horizontal_construccion(13,None,None)["estado"]=="NO VERIFICABLE"
    assert verificar_horizontal_construccion(13,3.0,.5)["estado"]=="CUMPLE"
    assert verificar_horizontal_construccion(13,2.5,.5)["estado"]=="NO CUMPLE"


def test_vertical_no_confunde_suelo_plano_con_tipo_via():
    from Analisis_mecanico_conductores.verificaciones.verificar_restricciones_documentadas_cfe import (
        verificar_vertical_superficie,
    )
    assert verificar_vertical_superficie(6.0,0.0,None)["estado"]=="NO VERIFICABLE"
    assert verificar_vertical_superficie(6.0,0.0,
        "a_lo_largo_caminos_y_zonas_rurales")["estado"]=="CUMPLE"
    assert verificar_vertical_superficie(6.0,0.0,
        "carreteras_calles_callejones_caminos_vecinales")["estado"]=="NO CUMPLE"

def test_integracion_tablas_y_geometrias_incompletas():
    from types import SimpleNamespace
    import pandas as pd
    from Analisis_mecanico_conductores.verificaciones.evaluar_requisitos_cfe_por_vano import (
        evaluar_requisitos_cfe_por_vano,
    )
    muestra=SimpleNamespace(flechas=pd.DataFrame([
        {"Vano":"P1 → P2","Luz (m)":50.0,"Hipótesis":"Final 0C",
         "T máxima vano (kN)":3.0},
        {"Vano":"P2 → P3","Luz (m)":150.0,"Hipótesis":"Final 0C",
         "T máxima vano (kN)":3.2},
    ]))
    r=evaluar_requisitos_cfe_por_vano(muestra,ruptura_N=19477.4,configuracion={
        "conductor":"ACSR RAVEN 1/0","clase_kV":13,
        "estructura_por_vano":{"P1 → P2":"TS3N","P2 → P3":"TS3N"},
        "clases_cfe_por_hipotesis":{"Final 0C":"final_0C_sin_viento"},
    })
    f=r["verificaciones_vanos"]
    assert f.iloc[0]["Tabla estructura CFE"].startswith("DENTRO")
    assert f.iloc[1]["Tabla estructura CFE"]=="EXCEDE TABLA CFE"
    assert f.iloc[0]["Libramiento vertical"]=="NO VERIFICABLE"
    assert r["traccion_CFE"]["final_0C_sin_viento"]["estado"]=="CUMPLE"
    assert r["traccion_CFE"]["inicial_0C_sin_viento"]["estado"]=="NO VERIFICABLE"


# === Casos conservados de tests/test_verificacion_cfe_integrada.py ===
"""Regresión del reporte integrado CFE: debe ser conservador con datos faltantes."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.interfaz.mostrar_verificaciones_cfe_integradas import (
    evaluar_corrida_documentada,
)


class TestVerificacionCFEIntegrada(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3","P4","P5","P6"],
            "X":[0.,50.,115.,205.,325.,475.],
            "Y":[0.]*6,"Altitud":[0.]*6,
            "Altura_Amarre_m":[10.]*6,
        })
        filas=[]
        for a,b,L,f in [
            ("P1","P2",50.,.45),("P2","P3",65.,.76),
            ("P3","P4",90.,1.45),("P4","P5",120.,2.58),
            ("P5","P6",150.,4.05),
        ]:
            for condicion,temperatura,tension in [
                ("Inicial",0.,4.5),("Final",0.,4.0),
                ("Final",16.,3.5),("Final",50.,2.2),
            ]:
                filas.append({
                    "Vano":a+" → "+b,"Luz (m)":L,
                    "Condición":condicion,"Temperatura (°C)":temperatura,
                    "Hipótesis":"Tabla térmica","Flecha (m)":f,
                    "P a 50 °C (m)":900.,"T máx. (kN)":tension,
                })
        self.tabla=pd.DataFrame(filas)

    def test_cinco_vanos_sin_datos_de_fases_ni_obstaculos(self):
        r=evaluar_corrida_documentada(
            self.tabla,self.puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,tipo_superficie="a_lo_largo_caminos_y_zonas_rurales",
        )
        self.assertEqual(len(r),5)
        self.assertTrue((r["Separación entre fases"]=="NO VERIFICABLE").all())
        self.assertTrue((r["Libramiento horizontal edificio"]=="NO VERIFICABLE").all())
        self.assertEqual(r.loc[0,"Libramiento vertical"],"CUMPLE")
        self.assertEqual(r.loc[4,"Libramiento vertical"],"NO CUMPLE")
        self.assertIn("EXCEDE",r.loc[4,"Tabla estructura CFE"])

    def test_fases_separacion_conocida(self):
        r=evaluar_corrida_documentada(
            self.tabla,self.puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,separacion_fases_m=.2,
        )
        self.assertTrue((r["Separación entre fases"].iloc[:4]=="NO CUMPLE").all())
        self.assertEqual(r.loc[4,"Separación entre fases"],"NO VERIFICABLE")

    def test_angulo_en_apoyo_se_compara_con_limitante(self):
        puntos=self.puntos.copy()
        # Desvío de 90 grados en un apoyo de paso: supera 1.85° TS3N.
        puntos.loc[2:,"X"]=[50.,50.,50.,50.]
        puntos.loc[2:,"Y"]=[65.,155.,275.,425.]
        r=evaluar_corrida_documentada(
            self.tabla,puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,
        )
        self.assertGreater(r.loc[1,"Deflexión máx. en apoyos (°)"],1.85)
        self.assertIn("deflexion_max_grados",
                      r.loc[1,"Limitantes excedidas CFE"])

    def test_alturas_inexistentes_no_aprueba_libramiento(self):
        puntos=self.puntos.drop(columns=["Altura_Amarre_m"])
        r=evaluar_corrida_documentada(
            self.tabla,puntos,estructura="TS3N",conductor="RAVEN",
            clase_kV=13,tipo_superficie="a_lo_largo_caminos_y_zonas_rurales",
        )
        self.assertTrue((r["Libramiento vertical"]=="NO VERIFICABLE").all())
