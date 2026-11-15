"""Conecta un Excel de coordenadas con el método convencional de Checa.

La sección física se delimita desde P1 hasta Pn en el ORDEN del Excel,
como sección única de regulación (dos extremos de retención y apoyos de
suspensión intermedios). La conexión exacta del herraje NO se necesita
para calcular la tensión y flecha convencionales; SÍ para las fuerzas
estructurales precisas. Si Vanos declara varias secciones, rechaza.
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import resolver_seccion_regulacion
from Analisis_mecanico_conductores.validaciones.validar_datos_fisicos import finito
from entradas.catalogos import CONDUCTORES_ACSR
from Analisis_mecanico_conductores.conductores.catalogo_acsr_viakon import CONDUCTORES_VIAKON_ACSR


def ejecutar_regulacion_fase1(archivo, puntos, calibre, *, Cd=1.2, rho=1.225):
    if len(puntos)<2:
        raise ValueError("Necesitamos al menos dos postes para una sección")
    libro=pd.ExcelFile(archivo)
    faltan={"Materiales","Hipotesis"}-set(libro.sheet_names)
    if faltan:
        raise ValueError(
            "La tensión se calcula automáticamente para varios vanos; "
            "tu Excel necesita las hojas Materiales e Hipotesis con "
            "propiedades y límites documentados. Faltan: "
            +", ".join(sorted(faltan))
        )
    # Una sección reguladora convencional se declara expresamente
    # por el modo utilizado, sin deducir diferencias de tensión
    # ni mezclar remates intermedios.
    if "Vanos" in libro.sheet_names:
        vanos=libro.parse("Vanos")
        if "Seccion" in vanos and vanos["Seccion"].dropna().nunique()>1:
            raise ValueError(
                "Vanos declara varias secciones de tendido. "
                "Calculá cada sección reguladora por separado."
            )
        if len(vanos) not in (0,len(puntos)-1):
            raise ValueError("La hoja Vanos no coincide con el número de tramos")
        if "Conexion_Inicio" in vanos and "Conexion_Fin" in vanos:
            for i,fila in vanos.reset_index(drop=True).iterrows():
                intermedios=[]
                if i>0:
                    intermedios.append(str(fila["Conexion_Inicio"]).strip().upper())
                if i<len(vanos)-1:
                    intermedios.append(str(fila["Conexion_Fin"]).strip().upper())
                if any(v in ("ANCLAJE","FIJA") for v in intermedios):
                    raise ValueError(
                        "Vanos declara una retención intermedia; "
                        "dividí el tramo en secciones de regulación."
                    )

    nombre=CONDUCTORES_ACSR[calibre]["nombre_mostrado"] if calibre in CONDUCTORES_ACSR else calibre
    if nombre not in CONDUCTORES_VIAKON_ACSR:
        raise ValueError("Conductor sin ficha Viakon: "+nombre)
    ficha=CONDUCTORES_VIAKON_ACSR[nombre]
    mat=libro.parse("Materiales")
    if len(mat)!=1:
        raise ValueError("Materiales debe contener una ficha del conductor seleccionado")
    fila=mat.iloc[0]
    if "Conductor" not in mat or str(fila["Conductor"]).strip() not in (calibre,nombre):
        raise ValueError("La ficha de Materiales no coincide con el conductor")
    requeridos=("EA_kN","Alpha_por_C","Temperatura_tendido_C","Fuente")
    if any(c not in mat for c in requeridos) or any(pd.isna(fila[c]) for c in requeridos):
        raise ValueError(
            "Materiales requiere EA_kN, Alpha_por_C, Temperatura_tendido_C "
            "y Fuente. No se ingresa H ni se repite peso o diámetro."
        )
    if not str(fila["Fuente"]).strip():
        raise ValueError("Falta fuente técnica de propiedades mecánicas")
    hip=libro.parse("Hipotesis")
    if "T_limite_kN" not in hip:
        raise ValueError("Hipotesis requiere T_limite_kN documentada")
    rotura=float(ficha["carga_rotura_kN"])
    for _,h in hip.iterrows():
        limite=finito(h["T_limite_kN"],"límite de tensión",0,True)
        if limite>=rotura:
            raise ValueError(
                "El límite declarado alcanza la ruptura nominal: "
                "revisá el criterio de diseño"
            )
    return resolver_seccion_regulacion(
        puntos,
        hipotesis=hip,temperaturas_tabla_C=[0,10,20,30,40],
        peso_kN_m=float(ficha["peso_kg_m"])*9.80665/1000,
        diametro_m=float(ficha["diametro_m"]),
        EA_kN=finito(fila["EA_kN"],"EA",0,True),
        alpha_por_C=finito(fila["Alpha_por_C"],"alpha"),
        fuente_material=str(fila["Fuente"]).strip(),
        temperatura_tendido_C=finito(
            fila["Temperatura_tendido_C"],"temperatura tendido"
        ),
        # Intervalo NUMÉRICO, no porcentajes de admisibilidad.
        H_min_kN=.05*rotura,H_max_kN=.95*rotura,
        Cd=Cd,rho_kg_m3=rho,
    )


def plantilla_regulacion():
    """Tres postes y dos vanos: la tensión se CALCULA, no se suministra."""
    puntos=pd.DataFrame({
        "Punto":["P1","P2","P3"],
        "X":[0.,45.53,91.06],"Y":[0.,0.,0.],
        "Altitud":[0.,0.,0.],
        "Altura_Amarre_m":[10.,10.,10.],
        "Poste":["PC-40"]*3,"Espacio Retenida":["SI","NO","SI"],
    })
    materiales=pd.DataFrame([{
        "Conductor":"2/0 ACSR","EA_kN":None,
        "Alpha_por_C":None,"Temperatura_tendido_C":None,"Fuente":"",
    }])
    hip=pd.DataFrame([{
        "Hipotesis":"Estado_1","Temperatura_C":None,"Viento_ms":None,
        "T_limite_kN":None,"Fuente_limite":"","Criterio_diseno":"",
    },{
        "Hipotesis":"Estado_2","Temperatura_C":None,"Viento_ms":None,
        "T_limite_kN":None,"Fuente_limite":"","Criterio_diseno":"",
    }])
    salida=BytesIO()
    with pd.ExcelWriter(salida,engine="openpyxl") as wr:
        puntos.to_excel(wr,sheet_name="Puntos",index=False)
        materiales.to_excel(wr,sheet_name="Materiales",index=False)
        hip.to_excel(wr,sheet_name="Hipotesis",index=False)
    return salida.getvalue()
