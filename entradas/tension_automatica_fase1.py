"""Puente entre Fase 1 y cálculo INVERSO documentado de un vano.

No convierte una red de varios vanos en un supuesto vano regulador.
El algoritmo solo admite un único tramo con ambos extremos ANCLAJE o
FIJA, declarados en la hoja Vanos. H se obtiene de límites documentados,
NO de una cifra arbitraria en la barra lateral.

Plantilla: igual a la del cálculo de red (Puntos, Vanos, Materiales,
Hipotesis), agregando columnas T_limite_kN, Fuente_limite y
Criterio_diseno en Hipotesis. La fuente de los límites es obligatoria.
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd

from calculos.tendido_inverso import dimensionar_tension_tendido
from calculos.validacion_mecanica import finito
from entradas.interfaz_tendido_inverso import leer_hipotesis_tabla
from entradas.catalogos import CONDUCTORES_ACSR
from entradas.catalogo_viakon_acsr import CONDUCTORES_VIAKON_ACSR


def calcular_tension_desde_libro(libro_excel, puntos, conductor, *, Cd=1.2, rho=1.225):
    """Calcula H con información explícita y sin inventar estados normativos."""
    if len(puntos)!=2:
        raise ValueError(
            "El cálculo automático de Fase 1 exige un único vano "
            "ANCLAJE–ANCLAJE. El Excel contiene "
            f"{len(puntos)-1} vanos. Para varios vanos usá "
            "'Red completa — conectividad' y declaralos con sus "
            "amarres; no podemos deducir una tensión común sin "
            "conocer el tipo de sujeción intermedia."
        )
    libro=pd.ExcelFile(libro_excel)
    requeridas={"Vanos","Materiales","Hipotesis"}
    faltantes=requeridas-set(libro.sheet_names)
    if faltantes:
        raise ValueError(
            "Para determinar H automáticamente añadí estas hojas "
            "al Excel: "+", ".join(sorted(faltantes))+
            ". Se requieren conexiones y criterios de tensión, no "
            "una tensión de tendido elegida arbitrariamente."
        )
    vanos=libro.parse("Vanos")
    if len(vanos)!=1:
        raise ValueError("Debe existir un solo vano declarado en hoja Vanos")
    fila=vanos.iloc[0]
    extremos=[str(p).strip() for p in puntos["Punto"]]
    if (str(fila["Inicio"]).strip(),str(fila["Fin"]).strip())!=tuple(extremos):
        raise ValueError("El vano declarado no coincide con los puntos del Excel")
    for columna in ("Conexion_Inicio","Conexion_Fin"):
        if str(fila[columna]).strip().upper() not in ("ANCLAJE","FIJA"):
            raise ValueError(
                "El cálculo automático de un vano fijo exige "
                "ANCLAJE o FIJA en ambos extremos; "
                "SUSPENSION y DESLIZANTE requieren cálculo de sección"
            )

    nombre_full=(
        CONDUCTORES_ACSR[conductor]["nombre_mostrado"]
        if conductor in CONDUCTORES_ACSR else conductor
    )
    if nombre_full not in CONDUCTORES_VIAKON_ACSR:
        raise ValueError("Conductor sin ficha nominal Viakon: "+nombre_full)
    ficha=CONDUCTORES_VIAKON_ACSR[nombre_full]
    material_tabla=libro.parse("Materiales")
    if len(material_tabla)!=1:
        raise ValueError("Materiales debe contener una sola ficha para este vano")
    nombre_material=str(material_tabla.iloc[0]["Conductor"]).strip()
    if nombre_material not in (conductor,nombre_full):
        raise ValueError("La ficha de Materiales no coincide con el conductor seleccionado")
    fila_material=material_tabla.iloc[0]
    requeridas=("Peso_kN_m","Diametro_m","EA_kN",
                "Alpha_por_C","Temperatura_tendido_C","Fuente")
    if any(c not in material_tabla for c in requeridas):
        raise ValueError(
            "La hoja Materiales requiere Peso_kN_m, Diametro_m, "
            "EA_kN, Alpha_por_C, Temperatura_tendido_C y Fuente; "
            "NO requiere tensión de tendido"
        )
    if any(pd.isna(fila_material[c]) for c in requeridas):
        raise ValueError("La hoja Materiales contiene propiedades incompletas")
    if not str(fila_material["Fuente"]).strip():
        raise ValueError("Es obligatorio documentar la fuente de EA y alpha")
    material={
        "peso_kN_m":finito(fila_material["Peso_kN_m"],"peso",0,True),
        "diametro_m":finito(fila_material["Diametro_m"],"diámetro",0,True),
        "EA_kN":finito(fila_material["EA_kN"],"EA",0,True),
        "alpha_por_C":finito(fila_material["Alpha_por_C"],"alpha"),
        "temperatura_tendido_C":finito(
            fila_material["Temperatura_tendido_C"],"temperatura tendido"
        ),
        "fuente":str(fila_material["Fuente"]).strip(),
    }
    # Impedir usar inadvertidamente la masa o diámetro de otro conductor.
    masa_catalogo=float(ficha["peso_kg_m"])*9.80665/1000
    diam_catalogo=float(ficha["diametro_m"])
    if abs(material["peso_kN_m"]-masa_catalogo)>max(1e-7,.01*masa_catalogo):
        raise ValueError("Peso de Materiales no coincide con la ficha Viakon")
    if abs(material["diametro_m"]-diam_catalogo)>max(1e-6,.01*diam_catalogo):
        raise ValueError("Diámetro de Materiales no coincide con la ficha Viakon")
    hip=leer_hipotesis_tabla(libro.parse("Hipotesis"))

    if "Altitud" not in puntos or "Altura_Amarre_m" not in puntos:
        raise ValueError(
            "El cálculo BVP requiere columnas Altitud y Altura_Amarre_m "
            "en ambos extremos del vano"
        )
    columnas=["X","Y","Altitud","Altura_Amarre_m"]
    if puntos[columnas].isna().any().any():
        raise ValueError("Coordenadas o alturas de amarre incompletas")
    coordenadas=[]
    for _,p in puntos.iterrows():
        if float(p["Altura_Amarre_m"])<=0:
            raise ValueError("Altura de amarre no positiva")
        coordenadas.append((
            float(p["X"]),float(p["Y"]),
            float(p["Altitud"])+float(p["Altura_Amarre_m"]),
        ))
    limite_rotura=float(ficha["carga_rotura_kN"])
    # Intervalo NUMÉRICO de búsqueda, NO tensión admisible.
    # Los límites climáticos documentados, no este intervalo,
    # controlan la tensión final aceptable.
    # Dominio de búsqueda NUMÉRICO de la primera versión:
    # 5 % a 95 % de ruptura. No son límites admisibles normativos.
    # Si la solución requiere salir de ese dominio, se informa que
    # no está determinada: jamás se presenta la cota como 'segura'.
    Hmin=.05*limite_rotura
    Hmax=.95*limite_rotura
    if any(h.tension_limite_kN>=limite_rotura for h in hip):
        raise ValueError(
            "Un límite de diseño no puede igualar/superar "
            "la ruptura nominal de la ficha seleccionada"
        )
    return dimensionar_tension_tendido(
        *coordenadas,hipotesis=hip,
        temperaturas_tabla_C=[0,10,20,30,40],
        temperatura_tendido_C=material["temperatura_tendido_C"],
        peso_kN_m=material["peso_kN_m"],
        diametro_m=material["diametro_m"],
        EA_kN=material["EA_kN"],
        alpha_por_C=material["alpha_por_C"],
        fuente_material=material["fuente"],
        H_min_kN=Hmin,H_max_kN=Hmax,
        Cd=Cd,rho_kg_m3=rho,
    )


def plantilla_tension_automatica():
    """Cuatro hojas; NO rellena criterios normativos ni propiedades EA."""
    puntos=pd.DataFrame({
        "Punto":["P1","P2"],"X":[0.,45.],"Y":[0.,0.],
        "Altitud":[0.,0.],"Altura_Amarre_m":[10.,10.],
        "Poste":["PC-40","PC-40"],
        "Espacio Retenida":["SI","SI"],
    })
    vanos=pd.DataFrame([{
        "Inicio":"P1","Fin":"P2",
        "Conexion_Inicio":"ANCLAJE","Conexion_Fin":"ANCLAJE",
    }])
    materiales=pd.DataFrame([{
        "Conductor":"2/0 ACSR",
        "Peso_kN_m":None,"Diametro_m":None,
        "EA_kN":None,"Alpha_por_C":None,
        "Temperatura_tendido_C":None,"Fuente":"",
    }])
    hip=pd.DataFrame([{
        "Hipotesis":"Estado_1","Temperatura_C":None,
        "Viento_ms":None,"Azimut_deg":None,
        "T_limite_kN":None,"Fuente_limite":"",
        "Criterio_diseno":"",
    }])
    memoria=BytesIO()
    with pd.ExcelWriter(memoria,engine="openpyxl") as escritor:
        for nombre,df in (
            ("Puntos",puntos),("Vanos",vanos),
            ("Materiales",materiales),("Hipotesis",hip),
        ):
            df.to_excel(escritor,sheet_name=nombre,index=False)
    return memoria.getvalue()
