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
    TableStyle, PageBreak, KeepTogether, CondPageBreak,
)


def _texto(valor):
    if pd.isna(valor) if not isinstance(valor, (list, tuple, dict)) else False:
        return "—"
    if isinstance(valor, float):
        if abs(valor) >= 10000:
            return f"{valor:.3f}"
        if abs(valor) >= 1:
            return f"{valor:.5f}".rstrip("0").rstrip(".")
        if valor == 0:
            return "0"
        if abs(valor) < 1e-4:
            return f"{valor:.3e}"
        return f"{valor:.5f}".rstrip("0").rstrip(".")
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
    pesos = [max(8, min(23, len(str(c)))) for c in cols]
    anchos = [ancho * w / sum(pesos) for w in pesos]
    est = estilos["CeldaPDF"]
    encabezado = estilos["CabeceraPDF"]
    matriz = [[_par(c, encabezado) for c in cols]]
    matriz.extend([[_par(v, est) for v in fila] for fila in datos.itertuples(index=False, name=None)])
    tabla = Table(matriz, colWidths=anchos, repeatRows=1, hAlign="LEFT", splitByRow=1)
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
        fontSize=7.1,leading=9.5,spaceAfter=0
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
        st.append(CondPageBreak(65))
        st.append(Spacer(1,8))
        st.append(_par(t,estilos["Heading2"]))
        st.append(Spacer(1,5))

    def tabla(t,df):
        titulo(t)
        st.extend(_tabla(df,disponible,estilos))
        st.append(Spacer(1,8))

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
    graf=_grafico_tension(resultado.tabla_tendido,disponible)
    if graf is not None:
        st.append(KeepTogether([
            Spacer(1,8), _par("7. Tensión horizontal frente a temperatura", estilos["Heading2"]),
            Spacer(1,5),graf,
        ]))
    tabla("8. Tabla de tendido completa",resultado.tabla_tendido)
    if resultado.barrido:
        # Tabla principal de condiciones extremas: solo el valor que gobierna
        # y la condición física que lo causa; los demás valores están en anexo.
        gobernantes=resultado.barrido["gobernantes"].copy()
        principales={
            "Condición gobernante":"Condición",
            "Valor gobernante":"Valor",
            "Magnitud gobernante":"Magnitud y unidad",
            "Vano":"Vano",
            "Temperatura (°C)":"T (°C)",
            "Viento (km/h)":"V (km/h)",
            "Hielo radial (mm)":"Hielo (mm)",
        }
        cols=[c for c in principales if c in gobernantes.columns]
        tabla("9. Condiciones gobernantes del barrido",
              gobernantes[cols].rename(columns=principales))
        st.append(_par(
            "El barrido climático es EXPLORATORIO: no equivale a un límite "
            "de diseño ni certifica simultaneidad meteorológica.",
            estilos["NotaPDF"]))
        titulo("10. Conclusiones y limitaciones")
        st.append(_par(
            f"En esta sección, la tensión de referencia calculada es "
            f"{resultado.H_tendido_kN:.4f} kN por conductor y la hipótesis "
            f"gobernante es {resultado.caso_gobernante}. "
            "Los resultados son válidos solamente dentro de los supuestos del "
            "modelo convencional declarados. No se emite dictamen de cumplimiento "
            "normativo estructural ni certificación de seguridad.",
            estilos["NotaPDF"]))
        st.append(PageBreak())
        titulo("Anexos técnicos - Barrido climático")
        st.append(_par(
            "Se conservan los estados por vano. Para facilitar la lectura se "
            "separan las corridas por temperatura y viento, con sus unidades. "
            "Los datos auxiliares de convergencia y la etiqueta constante "
            "EXPLORATORIO permanecen disponibles en el CSV íntegro.",
            estilos["NotaPDF"]))
        detalles=resultado.barrido["detalle"].copy()
        nombres={
            "Vano":"Vano",
            "Temperatura (°C)":"T (°C)",
            "Viento (km/h)":"V (km/h)",
            "Hielo radial (mm)":"Hielo (mm)",
            "H estado (kN)":"H (kN)",
            "T máxima vano (kN)":"T máx. (kN)",
            "Flecha vertical (m)":"Flecha (m)",
            "Desviación lateral máxima (m)":"Lateral (m)",
        }
        # Se evita repetir una columna de texto larga en cada fila.
        campos=list(nombres)
        disponibles=[c for c in campos if c in detalles.columns]
        vista=detalles[disponibles].rename(columns=nombres)
        if "Viento (km/h)" in detalles.columns:
            temperatura=vista[detalles["Viento (km/h)"].eq(0)]
            viento=vista[detalles["Viento (km/h)"].ne(0)]
            tabla("Anexo A - Estados sin viento (por temperatura)",temperatura)
            if not viento.empty:
                tabla("Anexo B - Estados con viento y combinaciones",viento)
        else:
            tabla("Anexo A - Todos los estados",vista)
        titulo("Anexo C - Diagnóstico de compatibilidad")
        st.append(_par(
            "Residual de compatibilidad (m): control numérico del motor, "
            "no resultado de diseño. Los valores por corrida se conservan "
            "en la exportación CSV sin pérdida de precisión.",
            estilos["NotaPDF"]))
    doc.build(st)
    return buffer.getvalue()
