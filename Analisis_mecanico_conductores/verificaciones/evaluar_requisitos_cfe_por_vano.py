"""Integra requisitos CFE 1/2/3 con resultados del solucionador existente.

No genera flechas, tensiones ni geometría ausentes. CFE es referencia
documental, no certificación de los herrajes o estructuras ENEE.
"""
from __future__ import annotations

import pandas as pd
from Analisis_mecanico_conductores.verificaciones.verificar_restricciones_documentadas_cfe import (
    verificar_tabla_estructura,verificar_traccion,verificar_fases,
    verificar_horizontal_construccion,verificar_vertical_superficie,
)

def evaluar_requisitos_cfe_por_vano(resultado, *, ruptura_N, configuracion):
    """Retorna dict con DataFrame y evaluación de tracción por 5 hipótesis.

    configuracion es explícita; claves opcionales:
        conductor, clase_kV, ambiente, estructura_por_vano,
        clases_cfe_por_hipotesis, flecha_final_50C_por_vano,
        separacion_real_entre_fases_por_vano_m, area_conductor_mm2,
        cota_min_conductor_50C_por_vano_m, cota_superficie_por_vano_m,
        tipo_superficie_por_vano,
        distancia_reposo_a_construccion_por_vano_m,
        desplazamiento_viento_16C_por_vano_m.
    Vanos son las etiquetas EXACTAS del resultado.flechas.
    """
    if not isinstance(configuracion,dict):raise ValueError("Configuración explícita requerida")
    cable=configuracion.get("conductor")
    clase=configuracion.get("clase_kV")
    ambiente=configuracion.get("ambiente","normal")
    f=resultado.flechas
    cols=("Vano","Luz (m)","Hipótesis","T máxima vano (kN)")
    if not isinstance(f,pd.DataFrame) or any(c not in f for c in cols):
        raise ValueError("El motor debe aportar por vano luz, hipótesis y T máxima")
    # Relación explícita con nombres documentados, sin inventar estado CFE.
    clases=configuracion.get("clases_cfe_por_hipotesis",{})
    maximas={}
    for caso,cfe in clases.items():
        seleccionado=f.loc[f["Hipótesis"].eq(caso),"T máxima vano (kN)"]
        if not seleccionado.empty:maximas[cfe]=max(maximas.get(cfe,0.),float(seleccionado.max())*1000.)
    traccion=verificar_traccion(float(ruptura_N),maximas)

    def dato(nombre,vano):
        x=configuracion.get(nombre,{})
        return x.get(vano) if isinstance(x,dict) else None

    filas=[]
    for vano,g in f.groupby("Vano",sort=False):
        luz=float(g["Luz (m)"].iloc[0])
        estructura=dato("estructura_por_vano",vano)
        if estructura and cable and clase:
            tabla=verificar_tabla_estructura(luz,estructura,cable,clase,ambiente=ambiente)
        else:
            tabla={"estado":"NO VERIFICABLE","motivo":"Estructura CFE o conductor no asignados"}
        flecha=dato("flecha_final_50C_por_vano",vano)
        area=configuracion.get("area_conductor_mm2")
        fase_real=dato("separacion_real_entre_fases_por_vano_m",vano)
        fases=(verificar_fases(clase,flecha,area,fase_real)
               if clase and flecha is not None and area is not None
               else {"estado":"NO VERIFICABLE","motivo":"Falta flecha final 50 °C, área o geometría de fases"})
        vertical=verificar_vertical_superficie(
            dato("cota_min_conductor_50C_por_vano_m",vano),
            dato("cota_superficie_por_vano_m",vano),
            dato("tipo_superficie_por_vano",vano))
        horizontal=(verificar_horizontal_construccion(
            clase,dato("distancia_reposo_a_construccion_por_vano_m",vano),
            dato("desplazamiento_viento_16C_por_vano_m",vano))
            if clase else {"estado":"NO VERIFICABLE","motivo":"Falta clase de tensión"})
        filas.append({"Vano":vano,"Luz (m)":luz,
                      "Tabla estructura CFE":tabla["estado"],
                      "Separación entre fases":fases["estado"],
                      "Libramiento vertical":vertical["estado"],
                      "Libramiento horizontal construcciones":horizontal["estado"],
                      "Detalle tabla":str(tabla),"Detalle fases":str(fases),
                      "Detalle vertical":str(vertical),"Detalle horizontal":str(horizontal)})
    return {"traccion_CFE":traccion,"verificaciones_vanos":pd.DataFrame(filas),
            "advertencia":"Solo CFE: no certifica capacidades de estructuras ENEE"}
