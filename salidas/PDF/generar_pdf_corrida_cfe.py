"""Memoria independiente del módulo 1 para la corrida CFE por vano.

El informe recibe DataFrames RESULTADO del motor: no recalcula ni altera
tensiones, flechas ni parámetros de referencia. Puede combinarse con las
memorias de otras etapas mediante pypdf (coordinar_pdf.py).
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, KeepTogether


_COLUMNAS = (
    "Condición", "Hipótesis", "Temperatura (°C)", "Viento (km/h)",
    "Hielo (mm)", "Vano", "Luz (m)", "P a 50 °C (m)", "H (kN)",
    "T máx. (kN)", "Flecha (m)", "Lateral (m)", "Residual (m)",
)


def _numero(x):
    if pd.isna(x):
        return "—"
    if isinstance(x, (float, np.floating)):
        return f"{x:.8g}"
    return str(x)


def _tabla(tabla, columnas, ancho, normal, cabecera):
    col = [c for c in columnas if c in tabla.columns]
    if not col:
        return []
    # Columnas resumidas en papel: todas las filas siguen disponibles.
    datos = [[Paragraph(escape(str(c)), cabecera) for c in col]]
    for fila in tabla[col].itertuples(index=False, name=None):
        datos.append([Paragraph(escape(_numero(v)), normal) for v in fila])
    pesos = [min(20, max(7, len(str(c)))) for c in col]
    anchos = [ancho*p/sum(pesos) for p in pesos]
    t = LongTable(datos, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
        ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [t]


def generar_pdf_corrida_cfe(*, resumen: pd.DataFrame, tabla: pd.DataFrame,
                            conductor: str, fuente_material: str,
                            clima: dict | None = None,
                            proyecto: dict | None = None) -> bytes:
    """Genera memoria PDF en bytes, validando datos sin volver a calcular."""
    if not isinstance(resumen, pd.DataFrame) or len(resumen) != 2:
        raise ValueError("Se requieren referencias inicial y final")
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        raise ValueError("No hay resultados por vano para el PDF")
    faltan = [c for c in _COLUMNAS if c not in tabla.columns]
    if faltan:
        raise ValueError("Faltan columnas del cálculo: " + ", ".join(faltan))
    for c in ("H (kN)", "T máx. (kN)", "Flecha (m)", "Residual (m)"):
        valores = pd.to_numeric(tabla[c], errors="coerce").to_numpy(float)
        if not np.isfinite(valores).all():
            raise ValueError("Resultados no finitos en " + c)
    if (tabla["H (kN)"] <= 0).any() or (tabla["T máx. (kN)"] <= 0).any():
        raise ValueError("Tensiones no positivas en resultados")
    clima = clima or {}
    proyecto = proyecto or {}
    salida = BytesIO()
    pagina = landscape(A4)
    margen = 15*mm
    doc = SimpleDocTemplate(
        salida, pagesize=pagina,
        leftMargin=margen, rightMargin=margen,
        topMargin=15*mm, bottomMargin=15*mm,
        title="Módulo 1 — Análisis mecánico de conductores",
        author=str(proyecto.get("responsable", "Memoria técnica")),
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CeldaM1", parent=styles["Normal"],
                              fontSize=6.5, leading=8))
    styles.add(ParagraphStyle(name="CabeceraM1", parent=styles["CeldaM1"],
                              fontName="Helvetica-Bold", alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="NotaM1", parent=styles["Normal"],
                              fontSize=8, leading=11))
    story = []
    ancho = pagina[0]-2*margen
    def p(texto, estilo="Normal"):
        story.append(Paragraph(escape(str(texto)), styles[estilo]))
        story.append(Spacer(1, 3*mm))
    p("MÓDULO 1 — ANÁLISIS MECÁNICO DE CONDUCTORES", "Heading1")
    p(f"Proyecto: {proyecto.get('nombre', 'Sin identificar')}  |  "
      f"Fecha: {proyecto.get('fecha', datetime.today().date().isoformat())}")
    p(f"Conductor: {conductor}  |  Fuente material: {fuente_material}")
    p(f"Viento máximo: {clima.get('viento_max_kmh', '—')} km/h; "
      f"viento reducido: {clima.get('viento_reducido_kmh', '—')} km/h; "
      f"hielo: {clima.get('hielo_mm', '—')} mm; "
      f"densidad de aire: {clima.get('rho_kg_m3', '—')} kg/m³.")
    p("Alcance: catenaria exacta, compatibilidad termoelástica, "
      "condiciones de referencia, tensiones, flechas, desviación lateral "
      "y residuales numéricos por vano.", "NotaM1")
    p("Límites: la reproducción de parámetros normativos no demuestra "
      "por sí sola un tendido aprobado; el modelo de amarres fijos no "
      "representa automáticamente el claro regla ni predice creep. "
      "No incluye verificación de postes, crucetas, retenidas o cimentación.",
      "NotaM1")
    p("Referencias mecánicas por condición", "Heading2")
    cols_res = ["Condición", "H_50_kN", "parametro_P_m",
                "hipotesis_gobernante", "relacion_critica",
                "tension_maxima_gobernante_kN", "residuo_maximo_gobernante_m"]
    story.extend(_tabla(resumen, cols_res, ancho, styles["CeldaM1"], styles["CabeceraM1"]))
    story.append(Spacer(1, 6*mm))
    p("Resultados completos por vano y estado", "Heading2")
    p("Las tablas siguientes son transcripción de resultados ya calculados; "
      "no se ajustan parámetros para coincidir con CFE.", "NotaM1")
    # No comprimir todos los 13 campos en una sola tabla ilegible.
    geometria = ["Condición", "Hipótesis", "Temperatura (°C)", "Vano",
                 "Luz (m)", "Flecha (m)", "Lateral (m)"]
    mecanica = ["Condición", "Hipótesis", "Temperatura (°C)", "Vano",
                "H (kN)", "T máx. (kN)", "P a 50 °C (m)",
                "Viento (km/h)", "Hielo (mm)", "Residual (m)"]
    p("Anexo A — Flechas y desplazamientos", "Heading3")
    story.extend(_tabla(tabla, geometria, ancho, styles["CeldaM1"], styles["CabeceraM1"]))
    story.append(Spacer(1, 6*mm))
    p("Anexo B — Tensiones y control numérico", "Heading3")
    story.extend(_tabla(tabla, mecanica, ancho, styles["CeldaM1"], styles["CabeceraM1"]))

    def paginar(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(pagina[0]-margen, 9*mm,
                               f"Módulo 1 | Página {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=paginar, onLaterPages=paginar)
    pdf = salida.getvalue()
    if not pdf.startswith(b"%PDF"):
        raise ValueError("La generación de la memoria PDF falló")
    return pdf
