"""Memoria de cálculo Etapa 1: informe y anexos desde resultados existentes.

No recalcula tensiones, no supone cumplimiento normativo ni reinterpreta
unidades. Funciona en memoria tanto en Streamlit como en pruebas unitarias.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from html import escape

import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, KeepTogether,
)


def _texto(valor):
    if pd.isna(valor) if not isinstance(valor, (list, tuple, dict)) else False:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.5g}"
    return str(valor)


def _par(valor, estilo):
    return Paragraph(escape(_texto(valor)).replace("\n", "<br/>"), estilo)


def _tabla(datos: pd.DataFrame, ancho: float, estilos, *, filas_maximas=None):
    """Tabla paginable: ancho acotado, encabezado repetido y texto envuelto."""
    if not isinstance(datos, pd.DataFrame) or datos.empty:
        return [_par("Sin datos", estilos["Normal"])]
    if filas_maximas is not None and len(datos) > filas_maximas:
        raise ValueError("No se deben truncar los resultados técnicos")
    cols = list(datos.columns)
    # El ancho se reparte conforme a longitudes de encabezados, no a
    # dimensiones sin límite del contenido; ReportLab envuelve cada celda.
    pesos = [max(9, min(24, len(str(c)))) for c in cols]
    anchos = [ancho * w / sum(pesos) for w in pesos]
    est = estilos["CeldaPDF"]
    encabezado = estilos["CabeceraPDF"]
    matriz = [[_par(c, encabezado) for c in cols]]
    matriz.extend([[_par(v, est) for v in fila] for fila in datos.itertuples(index=False, name=None)])
    tabla = Table(matriz, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0),colors.HexColor("#E8EDF2")),
        ("VALIGN", (0,0),(-1,-1),"TOP"),
        ("GRID", (0,0),(-1,-1),0.25,colors.HexColor("#CFD5DD")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8F9FB")]),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("RIGHTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    return [tabla]


def _grafico_tension(tabla: pd.DataFrame, ancho: float):
    """Traza H frente a temperatura desde la tabla de tendido YA CALCULADA."""
    cols = {"Temperatura (°C)", "H del estado (kN)"}
    if tabla is None or tabla.empty or not cols.issubset(tabla.columns):
        return None
    datos = tabla.groupby("Temperatura (°C)", as_index=False)["H del estado (kN)"].mean()
    if len(datos) < 2:
        return None
    puntos = [(float(t), float(h)) for t,h in datos.itertuples(index=False, name=None)]
    min_t,max_t = min(t for t,_ in puntos), max(t for t,_ in puntos)
    min_h,max_h = min(h for _,h in puntos), max(h for _,h in puntos)
    if max_t <= min_t or max_h <= min_h:
        return None
    alto=175
    graf=Drawing(ancho,alto)
    izquierda,derecha,abajo,arriba=46,14,32,22
    w=ancho-izquierda-derecha
    h=alto-abajo-arriba
    graf.add(Line(izquierda,abajo,izquierda,abajo+h,strokeColor=colors.black))
    graf.add(Line(izquierda,abajo,izquierda+w,abajo,strokeColor=colors.black))
    for i in range(5):
        nivel=min_h+(max_h-min_h)*i/4
        y=abajo+i*h/4
        graf.add(Line(izquierda,y,izquierda+w,y,strokeColor=colors.lightgrey,strokeWidth=.35))
        graf.add(String(izquierda-5,y-2,f"{nivel:.2f}",textAnchor="end",fontSize=7))
    graf.add(String(izquierda+w/2,9,"Temperatura del conductor (°C)",textAnchor="middle",fontSize=8))
    graf.add(String(izquierda,alto-8,"H (kN)",fontSize=8))
    xy=[(izquierda+(t-min_t)/(max_t-min_t)*w,
         abajo+(hh-min_h)/(max_h-min_h)*h) for t,hh in puntos]
    for (x1,y1),(x2,y2) in zip(xy,xy[1:]):
        graf.add(Line(x1,y1,x2,y2,strokeColor=colors.black,strokeWidth=1.4))
    for t in (min_t, max_t):
        x=izquierda+(t-min_t)/(max_t-min_t)*w
        graf.add(String(x,abajo-13,f"{t:g}",textAnchor="middle",fontSize=8))
    return graf


def _numero_pagina(canvas, doc):
    canvas.saveState()
    ancho,alto=landscape(A4)
    canvas.setFont("Helvetica",8)
    canvas.setStrokeColor(colors.grey)
    canvas.line(16*mm,14*mm,ancho-16*mm,14*mm)
    canvas.drawString(16*mm,10*mm,"Memoria técnica | Etapa 1 - Conductores")
    canvas.drawRightString(ancho-16*mm,10*mm,f"Página {doc.page}")
    canvas.restoreState()


def generar_pdf_etapa_1(*, resultado, puntos: pd.DataFrame,
                       proyecto: dict, propiedades: dict,
                       geometria: pd.DataFrame | None = None) -> bytes:
    """Devuelve bytes PDF; no lee Streamlit ni invoca el motor de cálculo."""
    if resultado is None or not hasattr(resultado, "H_tendido_kN"):
        raise ValueError("Etapa 1 requiere un resultado mecánico calculado")
    if not isinstance(puntos,pd.DataFrame) or puntos.empty:
        raise ValueError("Etapa 1 requiere puntos geométricos")
    if not propiedades or not propiedades.get("fuente"):
        raise ValueError("Se requiere fuente documentada de propiedades")
    buffer=BytesIO()
    estilos=getSampleStyleSheet()
    estilos.add(ParagraphStyle(
        name="CeldaPDF",parent=estilos["Normal"],fontName="Helvetica",
        fontSize=6.7,leading=8.3,spaceAfter=0
    ))
    estilos.add(ParagraphStyle(
        name="CabeceraPDF",parent=estilos["CeldaPDF"],fontName="Helvetica-Bold",
    ))
    estilos.add(ParagraphStyle(
        name="TituloPDF",parent=estilos["Title"],fontName="Helvetica-Bold",
        fontSize=17,leading=21,alignment=TA_CENTER
    ))
    estilos.add(ParagraphStyle(
        name="NotaPDF",parent=estilos["Normal"],fontSize=8,leading=11
    ))
    anchop,altop=landscape(A4)
    margen=16*mm
    disponible=anchop-2*margen
    doc=BaseDocTemplate(buffer,pagesize=landscape(A4),
                        leftMargin=margen,rightMargin=margen,
                        topMargin=18*mm,bottomMargin=19*mm)
    marco=Frame(margen,19*mm,disponible,altop-37*mm,
                leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="Memoria",frames=[marco],onPage=_numero_pagina))
    st=[]

    def titulo(t):
        st.append(Spacer(1,7))
        st.append(_par(t,estilos["Heading2"]))
        st.append(Spacer(1,4))

    def tabla(t,df):
        titulo(t)
        st.extend(_tabla(df,disponible,estilos))
        st.append(Spacer(1,7))

    st.append(_par("MEMORIA DE CÁLCULO MECÁNICO DE CONDUCTORES",
                   estilos["TituloPDF"]))
    st.append(_par("ETAPA 1 | SECCIÓN CONVENCIONAL DE REGULACIÓN",
                   estilos["Title"]))
    st.append(Spacer(1,12))
    metadatos=pd.DataFrame([
        {"Campo":"Proyecto","Detalle":proyecto.get("nombre","No informado")},
        {"Campo":"Municipio / lugar","Detalle":proyecto.get("lugar","No informado")},
        {"Campo":"Cliente","Detalle":proyecto.get("cliente") or "No informado"},
        {"Campo":"Responsable","Detalle":proyecto.get("responsable") or "No informado"},
        {"Campo":"Fecha","Detalle":proyecto.get("fecha",str(date.today()))},
        {"Campo":"Conductor seleccionado","Detalle":proyecto.get("conductor") or proyecto.get("calibre","No informado")},
        {"Campo":"Fuente de propiedades","Detalle":propiedades["fuente"]},
    ])
    st.extend(_tabla(metadatos,disponible,estilos))
    titulo("1. Resumen ejecutivo")
    resumen=pd.DataFrame([
        {"Indicador":"Tensión de tendido H","Resultado":f"{resultado.H_tendido_kN:.4f} kN/conductor"},
        {"Indicador":"Vano regulador","Resultado":f"{resultado.vano_regulador_m:.3f} m"},
        {"Indicador":"Longitud total","Resultado":f"{resultado.longitud_tramo_m:.3f} m"},
        {"Indicador":"Hipótesis gobernante","Resultado":resultado.caso_gobernante},
        {"Indicador":"Relación crítica T/límite","Resultado":f"{resultado.relacion_maxima:.4f}"},
        {"Indicador":"Búsqueda alcanzó límite superior","Resultado":"Sí" if resultado.cota_busqueda_activa else "No"},
        {"Indicador":"Estados climáticos explorados","Resultado":str(resultado.barrido["total_estados"]) if resultado.barrido else "No ejecutado"},
    ])
    st.extend(_tabla(resumen,disponible,estilos))
    titulo("2. Alcance y metodología")
    st.append(_par(resultado.modelo,estilos["NotaPDF"]))
    st.append(_par(
        "Se evalúan compatibilidad termoelástica y catenarias bajo una tensión "
        "horizontal común para la sección ideal de regulación entre remates. "
        "El vano equivalente se presenta como referencia geométrica; el motor "
        "resuelve cada vano y conserva la suma de longitudes naturales. "
        "El viento exploratorio es perpendicular a cada vano; no constituye "
        "un único vector geográfico de viento.",estilos["NotaPDF"]))
    st.append(Spacer(1,7))
    st.append(_par(
        "ATENCIÓN: este informe no verifica resistencia de postes, retenidas, "
        "cimentaciones, libramientos, deslizamiento/fricción en suspensión ni "
        "creep. El barrido de viento y hielo es exploratorio y no sustituye "
        "criterios normativos de carga ni una aprobación para construcción.",
        estilos["NotaPDF"]))
    st.append(PageBreak())

    tabla("3. Puntos y geometría de entrada",puntos)
    if geometria is not None:
        tabla("3.1. Geometría de vanos",geometria)
    tabla("4. Propiedades mecánicas documentadas",pd.DataFrame([
        {"Propiedad":str(k),"Valor":_texto(v)} for k,v in propiedades.items()
    ]))
    tabla("5. Hipótesis de cálculo y límites",resultado.hipotesis)
    tabla("6. Flechas por vano e hipótesis",resultado.flechas)
    titulo("7. Tensión de tendido frente a temperatura")
    graf=_grafico_tension(resultado.tabla_tendido,disponible)
    if graf:
        st.append(graf)
    tabla("8. Tabla de tendido completa",resultado.tabla_tendido)
    if resultado.barrido:
        tabla("9. Barrido climático - condiciones gobernantes",
              resultado.barrido["gobernantes"])
        tabla("10. Barrido climático - todos los estados por vano",
              resultado.barrido["detalle"])
    titulo("11. Conclusiones y limitaciones")
    st.append(_par(
        f"En esta sección, la tensión de referencia calculada es "
        f"{resultado.H_tendido_kN:.4f} kN por conductor y la hipótesis "
        f"gobernante es {resultado.caso_gobernante}. "
        "Los resultados son válidos solamente dentro de los supuestos del "
        "modelo convencional declarados. No se emite dictamen de cumplimiento "
        "normativo estructural ni certificación de seguridad.",
        estilos["NotaPDF"]))
    doc.build(st)
    return buffer.getvalue()
