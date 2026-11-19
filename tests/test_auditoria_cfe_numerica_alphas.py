"""Suite consolidada: se conservan todos los casos originales."""


# === Casos conservados de tests/test_auditoria_cfe_numerica_alphas.py ===
"""Regresion transparente contra CFE 07 FT 10, 11, 12 y 14 (PDF original).
Comparacion SOLO para claros regla individuales equivalentes, no secciones de 5 vanos.
El P se calcula independientemente: no se introduce P CFE al motor.
"""
import json
import math
import unittest

import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
    ejecutar_corridas_cfe_por_vano,
)

# P (m), tension (kgf) y flecha (cm) a 20 y 50 grados del manual.
# En la hoja inicial PIGEON (07 FT 11 p.615 PDF) aparece repetida
# erróneamente RAVEN, por eso NO se inventa la referencia inicial PIGEON.
REFERENCIAS = (
    ("RAVEN",50,{"Inicial":(760,353,164,19,41),"Final":(660,329,143,20,47)}),
    ("RAVEN",75,{"Inicial":(920,363,199,42,76),"Final":(835,343,180,44,84)}),
    ("RAVEN",109,{"Inicial":(1025,348,222,92,145),"Final":(965,332,209,97,154)}),
    ("PIGEON",101,{"Final":(830,447,286,98,154)}),
    ("PARTRIDGE",82,{"Inicial":(605,465,330,99,139),"Final":(550,424,300,108,153)}),
    ("HAWK",65,{"Inicial":(355,427,346,121,149),"Final":(345,420,336,123,153)}),
)


class AuditoriaNumericaCfeAlphaOriginal(unittest.TestCase):
    def test_cfe_claros_independientes(self):
        errores=[]
        for nombre, luz, estados in REFERENCIAS:
            with self.subTest(conductor=nombre,vano=luz):
                puntos=pd.DataFrame({
                    "Punto":["P1","P2"],"X":[0.,float(luz)],
                    "Y":[0.,0.],"Altitud":[100.,100.],
                    "Altura_Amarre_m":[10.,10.],
                })
                ini,fin=seleccionar_propiedades_cfe_07_ft_01(nombre)
                resumen,tabla=ejecutar_corridas_cfe_por_vano(
                    puntos,ini,fin,viento_max_kmh=120.,
                    viento_reducido_kmh=109.,hielo_mm=6.,
                    temperaturas_C=[20.,50.],Cd=1.,
                    rho_kg_m3=1.225,modelo_presion_cfe=True,
                )
                for estado, (p_ref, t20_ref,t50_ref,f20_ref,f50_ref) in estados.items():
                    row=resumen[resumen["Condición"].str.startswith(estado)].iloc[0]
                    p=float(row["parametro_P_m"])
                    t=tabla[(tabla["Condición"]==estado)
                         &(tabla["Hipótesis"]=="Tabla térmica")]
                    t20=t[t["Temperatura (°C)"]==20.].iloc[0]
                    t50=t[t["Temperatura (°C)"]==50.].iloc[0]
                    resultados={
                        "conductor":nombre,"vano_m":luz,"estado":estado,
                        "P_CFE_m":p_ref,"P_motor_m":round(p,5),
                        "error_P_pct":round(100*(p/p_ref-1),3),
                        "T20_CFE_kgf":t20_ref,
                        "T20_motor_kgf":round(float(t20["T máx. (kN)"])*1000/9.80665,3),
                        "T50_CFE_kgf":t50_ref,
                        "T50_motor_kgf":round(float(t50["T máx. (kN)"])*1000/9.80665,3),
                        "f20_CFE_cm":f20_ref,
                        "f20_motor_cm":round(float(t20["Flecha (m)"])*100,3),
                        "f50_CFE_cm":f50_ref,
                        "f50_motor_cm":round(float(t50["Flecha (m)"])*100,3),
                        "acoplamiento_H4_pct":round(float(row["Diferencia real de acoplamiento H4 (%)"]),6),
                    }
                    print("CFE_AUDIT_RESULT:"+json.dumps(resultados,sort_keys=True),flush=True)
                    for k,v in resultados.items():
                        if isinstance(v,(int,float)):
                            self.assertTrue(math.isfinite(v),(nombre,luz,estado,k))
                    errores.append(abs(resultados["error_P_pct"]))
        print("CFE_AUDIT_TOTAL:"+json.dumps({
            "comparaciones":len(errores),
            "error_P_medio_abs_pct":round(sum(errores)/len(errores),3),
            "error_P_max_abs_pct":round(max(errores),3),
        }),flush=True)


# === Casos conservados de tests/test_tablas_cfe_inicial_final.py ===
"""Validación de condiciones inicial/final contra anexo 8 ENEE, AAC 1/0.

Datos publicados en tablas ENEE (redondeados a kgf y centímetros).
P50 se proporciona desde encabezados ENEE: estos tests validan estados
térmicos, NO la obtención independiente de P50 por criterios de diseño.
"""
import unittest

import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    EstadoReferenciaCFE,
    HipotesisDisenoCFE,
    PropiedadesConductorCFE,
    calcular_parametro_cfe_desde_limites,
    calcular_tablas_inicial_final,
)

KG_F_A_KN = 9.80665 / 1000.


def propiedades_aac():
    return PropiedadesConductorCFE(
        peso_kN_m=0.001442,
        diametro_m=0.0117,
        EA_inicial_kN=41.202 * 53.49,
        EA_final_kN=59.841 * 53.49,
        alpha_inicial_por_C=23e-6,
        alpha_final_por_C=23e-6,
        ruptura_kN=8.84,
        fuente="CFE 07 FT 01, AAC 1/0; propiedades de prueba",
    )


def vano(luz):
    return pd.DataFrame({
        "Punto": ["P1", "P2"], "X": [0., float(luz)], "Y": [0., 0.],
    })


class TablasCFETest(unittest.TestCase):

    def test_84_m_estado_inicial_y_final(self):
        tabla = calcular_tablas_inicial_final(
            vano(84), propiedades_aac(),
            EstadoReferenciaCFE(675., "ENEE, anexo 8, inicial, 84 m"),
            EstadoReferenciaCFE(585., "ENEE, anexo 8, final, 84 m"),
            [-10, 0, 20, 50],
        )
        objetivos = {
            ("Inicial", -10): (283., 46.),
            ("Inicial", 0): (239., 54.),
            ("Inicial", 20): (164., 79.),
            ("Inicial", 50): (99., 131.),
            ("Final", -10): (283., 46.),
            ("Final", 0): (224., 58.),
            ("Final", 20): (139., 93.),
            ("Final", 50): (86., 151.),
        }
        self.assertEqual(len(tabla), 8)
        for _, fila in tabla.iterrows():
            tension, flecha = objetivos[
                (fila["Condición"], int(fila["Temperatura (°C)"]))
            ]
            self.assertLess(abs(fila["H (kN)"] / KG_F_A_KN - tension), 2.)
            self.assertLess(abs(fila["Flecha (m)"] * 100 - flecha), 1.)
            self.assertLess(abs(fila["Residual (m)"]), 1e-7)

    def test_vanos_independientes_y_estados_de_viento(self):
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2", "P3"],
            "X": [0., 40., 125.], "Y": [0., 0., 0.],
        })
        tabla = calcular_tablas_inicial_final(
            puntos, propiedades_aac(),
            EstadoReferenciaCFE(675., "Referencia de ensayo"),
            EstadoReferenciaCFE(585., "Referencia de ensayo"),
            [20., 50.],
            estados_climaticos=[("Viento", 20., 40., 0.)],
        )
        self.assertEqual(len(tabla), 12)
        t20 = tabla[(tabla["Condición"] == "Inicial") &
                    (tabla["Temperatura (°C)"] == 20.) &
                    (tabla["Viento (km/h)"] == 0.)]
        self.assertEqual(len(t20), 2)
        self.assertGreater(
            abs(t20.iloc[0]["H (kN)"] - t20.iloc[1]["H (kN)"]), 0.001
        )
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())
        self.assertTrue((tabla[tabla["Viento (km/h)"] > 0]["Lateral (m)"] > 0).all())

    def test_dimensionamiento_desde_limite_documentado(self):
        import numpy as np
        xyz = np.array([[0., 0., 0.], [80., 0., 0.]])
        p = propiedades_aac()
        hipotesis = [
            HipotesisDisenoCFE(
                "Hipótesis de prueba 0°C", 0., 0., 0., 3.5,
                "Límite sintético para ensayo, no límite CFE",
            ),
        ]
        res = calcular_parametro_cfe_desde_limites(
            xyz, p, hipotesis, H_min_kN=0.1, H_max_kN=5.,
        )
        self.assertGreater(res["parametro_P_m"], 0.)
        self.assertAlmostEqual(res["relacion_critica"], 1., delta=1e-5)

    def test_rechaza_condicion_final_sin_referencia(self):
        with self.assertRaises((ValueError, AttributeError)):
            calcular_tablas_inicial_final(
                vano(50.), propiedades_aac(),
                EstadoReferenciaCFE(495., "ENEE"), None, [20.]
            )


# === Casos conservados de tests/test_tramo_510m_cfe_limites.py ===
"""Regresion del tramo de usuario P1..P6, 510 m y amarres nivelados.

No utiliza valores de flecha, H o P publicados como entradas.
Verifica magnitudes distintas de CFE: max(T) y H en hipotesis H4/H5.
"""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01, ejecutar_corridas_cfe_por_vano,
)
from Analisis_mecanico_conductores.salidas.PDF.verificacion_hipotesis_cfe import verificar_cinco_hipotesis


class Tramo510CFE(unittest.TestCase):
    def test_tramo_50_70_120_150_120(self):
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2", "P3", "P4", "P5", "P6"],
            "X": [0., 50., 120., 240., 390., 510.],
            "Y": [0.] * 6, "Altitud": [0.] * 6,
            "Altura_Amarre_m": [9.5] * 6,
        })
        inicial, final = seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        resumen, tabla = ejecutar_corridas_cfe_por_vano(
            puntos, inicial, final, viento_max_kmh=120.,
            viento_reducido_kmh=0., hielo_mm=6.,
            temperaturas_C=[0., 16., 20., 30., 50.],
        )
        self.assertEqual(len(resumen), 2)
        self.assertEqual(set(tabla["Luz (m)"]), {50., 70., 120., 150.})
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())
        control = verificar_cinco_hipotesis(
            tabla, ruptura_kN=inicial["ruptura_kN"],
            nombre_conductor="RAVEN", viento_max_kmh=120.,
            viento_reducido_kmh=0., hielo_mm=6.,
        )
        self.assertEqual(len(control), 5)
        self.assertTrue((control["Estado"] == "CUMPLE").all(),
                        control.to_string(index=False))
        h5 = control.loc[control["Código"] == "H5"].iloc[0]
        self.assertLessEqual(h5["H máxima (kN)"], 5.618 * (1 + 1e-6))
        self.assertLessEqual(h5["T máxima (kN)"],
                             inicial["ruptura_kN"] * .45 * (1 + 1e-6))


# === Casos conservados de tests/test_regresion_catenaria_cfe_raven_50C.py ===
"""Regresión independiente de geometría: CFE 07 FT 10, PDF p609.

No usa P de CFE como entrada del motor de proyecto: únicamente verifica
que la fórmula analítica de catenaria reproduce 21 registros publicados.
"""
import csv
import math
from pathlib import Path

def test_catenaria_geometria_raven_21_claros_publicados():
    ruta=Path(__file__).resolve().parent/"fixtures/validacion_catenaria_CFE_RAVEN_50C.csv"
    with ruta.open(encoding="utf-8-sig",newline="") as f:reg=list(csv.DictReader(f))
    assert len(reg)==21
    w=2.12 # N/m: CFE 07 FT 02, propiedades de conductor RAVEN
    for x in reg:
        L=float(x["vano_m"]);P=float(x["P_CFE_m"])
        tension_kgf=w*P/9.80665
        flecha_cm=100*P*(math.cosh(L/(2*P))-1)
        assert abs(tension_kgf-float(x["H_50C_tabla_kgf"]))<=.55
        assert abs(flecha_cm-float(x["flecha_50C_tabla_cm"]))<=.75
