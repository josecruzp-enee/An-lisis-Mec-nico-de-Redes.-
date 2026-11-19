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


if __name__=="__main__":
    unittest.main()
