"""Restricciones documentadas CFE, calculadas sobre resultados del motor; NO ENEE.

Fuente: Manual CFE DCCIAMBT 2014, 02 00 03/04/06 (PDF pp.43-49);
05 00 03 (p.156); 05 T0 02 (pp.181-184), 05 T0 09 (210-213),
05 P0 02 (241-242), 05 P0 05 (256-257), 05 R0 02 (273),
05 V0 02 (409-412).

Las tablas se basan en viento 120 km/h y materiales/postes CFE:
NO asignar automáticamente estas capacidades a una estructura ENEE.
"""
from __future__ import annotations
import csv
import math
from pathlib import Path

CATALOGO = Path(__file__).resolve().parents[2] / "Analisis_mecanico_conductores/entradas/catalogos/cfe_limitantes_estructuras_120kmh.csv"
PORCENTAJE_RTS = {
    "final_16C_sin_viento": .20,
    "final_0C_sin_viento": .25,
    "inicial_0C_sin_viento": .33,
    "final_menos10C_viento_reducido_hielo": .45,
    "final_0C_viento_maximo": .45,
}
FLECHAS_TABLA_CM = (60, 80, 100, 150, 200, 250, 300)
SEPARACION_FASES_TABLA_CM = {
    13: (36, 43, 47, 55, 62, 69, 74),
    23: (46, 50, 54, 62, 69, 76, 81),
    33: (56, 59, 63, 71, 78, 84, 90),
}
SEPARACION_APOYOS_CM = {13:35,23:45,33:56}
SEPARACION_HORIZONTAL_CONSTRUCCIONES_M = {13:2.3,23:2.3,33:2.5}

def fila_tabla(estructura, conductor, clase_kV, ambiente="normal", catalogo=None):
    """Consultar SOLO coincidencia exacta; sin interpolar entre estructuras."""
    with Path(catalogo or CATALOGO).open(encoding="utf-8-sig", newline="") as f:
        filas=[x for x in csv.DictReader(f)
            if x["estructura"]==estructura and x["conductor"]==conductor
            and x["ambiente"]==ambiente and int(x["tension_clase_kV"])==int(clase_kV)]
    if len(filas)>1: raise ValueError("Fila de tabla ambigua")
    return filas[0] if filas else None

def verificar_tabla_estructura(luz_m, estructura, conductor, clase_kV,
                               ambiente="normal", catalogo=None,
                               angulo_grados=None, desnivel_m=None, hielo=False):
    """Valida LIMITES DE TABLA CFE; nunca acredita componentes hondureños."""
    if not math.isfinite(luz_m) or luz_m<=0:raise ValueError("Luz inválida")
    f=fila_tabla(estructura,conductor,clase_kV,ambiente,catalogo)
    if f is None:return {"estado":"NO VERIFICABLE","motivo":"Fila documental inexistente"}
    cols=("poste_max_m","cable_max_m","perno_max_m","punta_poste_max_m",
          "cruceta_con_hielo_max_m" if hielo else "cruceta_sin_hielo_max_m",
          "libramiento_piso_max_m","separacion_fases_max_m")
    evaluacion={}
    for c in cols:
        if f.get(c):
            limite=float(f[c])
            evaluacion[c]={"valor":luz_m,"limite":limite,
                           "cumple":luz_m<=limite+1e-9}
    extra=(("deflexion_max_grados",angulo_grados),
           ("desnivel_con_hielo_max_m" if hielo else "desnivel_sin_hielo_max_m",desnivel_m))
    for c,v in extra:
        if v is not None and f.get(c):
            limite=float(f[c])
            evaluacion[c]={"valor":abs(float(v)),"limite":limite,
                           "cumple":abs(float(v))<=limite+1e-9}
    return {"estado":("EXCEDE TABLA CFE" if any(not x["cumple"] for x in evaluacion.values())
                      else "DENTRO DE TABLA CFE; NO ES APROBACION ENEE"),
            "pagina_pdf":int(f["pagina_pdf"]),"criterios":evaluacion}

def verificar_traccion(rotura_N, tensiones_maximas_N):
    """Tensiones RESULTANTES máximas por estado, no H horizontal (CFE p.156)."""
    if not math.isfinite(rotura_N) or rotura_N<=0:raise ValueError("RTS inválida")
    sal={}
    for estado,frac in PORCENTAJE_RTS.items():
        maximo=tensiones_maximas_N.get(estado);lim=frac*rotura_N
        if maximo is None:
            sal[estado]={"estado":"NO VERIFICABLE","limite_N":lim};continue
        if not math.isfinite(float(maximo)) or float(maximo)<=0:
            raise ValueError("Tensión inválida: "+estado)
        sal[estado]={"estado":"CUMPLE" if maximo<=lim+1e-8 else "NO CUMPLE",
                     "tension_N":float(maximo),"limite_N":lim,"utilizacion":float(maximo)/lim}
    return sal

def separacion_fases_minima(clase_kV, flecha_final_50C_m, area_mm2):
    """02 00 06: valor tabulado siguiente para flechas >60cm, sin extrapolar."""
    k=int(clase_kV)
    if k not in SEPARACION_FASES_TABLA_CM:return None
    f=float(flecha_final_50C_m)
    if not math.isfinite(f) or f<0:raise ValueError("Flecha inválida")
    if f<=.60:return SEPARACION_APOYOS_CM[k]/100.
    if area_mm2<53.49:return None
    for fc,sc in zip(FLECHAS_TABLA_CM,SEPARACION_FASES_TABLA_CM[k]):
        if f*100<=fc+1e-9:return sc/100.
    return None   # el manual no tabula flecha >300 cm

def verificar_fases(clase_kV,flecha_final_50C_m,area_mm2,separacion_real_minima_m):
    minimo=separacion_fases_minima(clase_kV,flecha_final_50C_m,area_mm2)
    if minimo is None or separacion_real_minima_m is None:
        return {"estado":"NO VERIFICABLE","motivo":"Sin tabla o geometría de fases"}
    d=float(separacion_real_minima_m)
    if not math.isfinite(d) or d<0:raise ValueError("Separación geométrica inválida")
    return {"estado":"CUMPLE" if d>=minimo-1e-9 else "NO CUMPLE",
            "real_m":d,"requerida_m":minimo}

def verificar_horizontal_construccion(clase_kV,distancia_reposo_m,
                                      desplazamiento_viento_16C_m,desnudo=True):
    """02 00 04: distancia a construcción BAJO VIENTO (16°C).\n    CFE p45 imprime literalmente 19 kg/m como "presión": unidad ambigua.\n    El solver debe documentar cómo estableció la carga de viento; no\n    convertirla automáticamente a 19 kgf/m².
    El desplazamiento debe provenir del solver; no se inventa.
    """
    k=int(clase_kV)
    if not desnudo or k not in SEPARACION_HORIZONTAL_CONSTRUCCIONES_M:
        return {"estado":"NO VERIFICABLE","motivo":"Clase no documentada"}
    if distancia_reposo_m is None or desplazamiento_viento_16C_m is None:
        return {"estado":"NO VERIFICABLE","motivo":"Faltan obstáculo u oscilación"}
    distancia=float(distancia_reposo_m)-abs(float(desplazamiento_viento_16C_m))
    limite=SEPARACION_HORIZONTAL_CONSTRUCCIONES_M[k]
    if not math.isfinite(distancia):raise ValueError("Distancia inválida")
    return {"estado":"CUMPLE" if distancia>=limite-1e-9 else "NO CUMPLE",
            "distancia_desfavorable_m":distancia,"minimo_m":limite,
            "caso":"16°C final; CFE p45: 19 kg/m impreso, unidad a aclarar"}


# CFE 02 00 03, hoja 1 de 2 (PDF p.43). Conductores desnudos MT.
# Alturas a 50 °C, sin viento y con flecha FINAL. Valores en metros.
ALTURAS_MINIMAS_MT_M = {
    "espacio_no_transitado_vehiculos": 7.0,
    "vias_ferreas": 9.0,
    "carreteras_calles_callejones_caminos_vecinales": 7.0,
    "aguas_no_navegables": 5.5,
    "aguas_navegables_area_hasta_8ha": 6.5,
    "aguas_navegables_area_8_a_80ha": 9.5,
    "aguas_navegables_area_80_a_800ha": 11.6,
    "aguas_navegables_area_mayor_800ha": 13.0,
    "a_lo_largo_caminos_y_zonas_rurales": 6.0,
    "a_lo_largo_carreteras_calles_callejones_zonas_urbanas": 7.0,
}

def verificar_vertical_superficie(cota_conductor_minima_m,
                                 cota_superficie_m, tipo_superficie=None):
    """Distancia vertical a superficie específica, 50 °C final sin viento.

    La clase de superficie NO puede inferirse del hecho 'terreno plano'.
    """
    if tipo_superficie is None:
        return {"estado":"NO VERIFICABLE","motivo":"Falta categoría de superficie"}
    minimo=ALTURAS_MINIMAS_MT_M.get(tipo_superficie)
    if minimo is None:
        return {"estado":"NO VERIFICABLE","motivo":"Categoría no documentada"}
    if cota_conductor_minima_m is None or cota_superficie_m is None:
        return {"estado":"NO VERIFICABLE","motivo":"Faltan cotas de terreno y conductor"}
    real=float(cota_conductor_minima_m)-float(cota_superficie_m)
    if not math.isfinite(real):raise ValueError("Altura inválida")
    return {"estado":"CUMPLE" if real>=minimo-1e-9 else "NO CUMPLE",
            "libramiento_real_m":real,"libramiento_minimo_m":minimo,
            "fuente":"CFE 02 00 03, PDF p.43; MT, final 50C sin viento"}


# Las estructuras H tienen tabla independiente y no son equiparables a TS.
CATALOGO_H = Path(__file__).resolve().parents[2] / "Analisis_mecanico_conductores/entradas/catalogos/cfe_limitantes_estructuras_H_120kmh.csv"

def verificar_estructura_H(estructura, conductor, claro_medio_horizontal_m,
                          claro_vertical_m, *, catalogo=None):
    """CFE 05 H0 02, PDF pp.496-497. Conjunto H con cable de guarda."""
    with Path(catalogo or CATALOGO_H).open(encoding="utf-8-sig",newline="") as f:
        filas=[x for x in csv.DictReader(f) if x["estructura"]==estructura
               and x["conductor"]==conductor]
    if len(filas)!=1:
        return {"estado":"NO VERIFICABLE","motivo":"Sin fila H unívoca"}
    x=filas[0]
    h=float(claro_medio_horizontal_m);v=float(claro_vertical_m)
    if not all(math.isfinite(a) and a>0 for a in (h,v)):
        raise ValueError("Claros H inválidos")
    mh=float(x["claro_medio_horizontal_m"]);mv=float(x["claro_vertical_m"])
    return {"estado":"DENTRO DE TABLA H CFE; NO ES APROBACION ENEE" if h<=mh and v<=mv
                      else "EXCEDE TABLA H CFE",
            "claro_horizontal_m":h,"maximo_horizontal_m":mh,
            "claro_vertical_m":v,"maximo_vertical_m":mv,
            "TH_viento_max_N":float(x["TH_viento_max_conductor_N"]),
            "TH_viento_reducido_hielo_N":float(x["TH_viento_reducido_hielo_conductor_N"]),
            "pagina_pdf":int(x["pagina_pdf"])}
