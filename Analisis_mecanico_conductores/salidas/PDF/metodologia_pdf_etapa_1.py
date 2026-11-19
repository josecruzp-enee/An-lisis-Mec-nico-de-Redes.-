"""Metodología DOCUMENTADA de la Etapa 1, tomada de los módulos del motor.

Exclusivamente formatea teoría, hipótesis y gráficos de datos calculados.
No ejecuta ecuaciones de cálculo mecánico ni inventa aprobaciones.
"""
from __future__ import annotations

import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.lib import colors
from reportlab.platypus import KeepTogether, Spacer
from .ecuaciones_pdf_etapa_1 import formulas_para_seccion


def paginas_metodologia(par, estilos, propiedades, ancho=680):
    """Párrafos técnicos con las expresiones del código implementado."""
    bloques=[
        ("3. Metodología y modelo mecánico", [
            "El conductor se considera sujeto rígidamente en cada "
            "aislador de espiga después del tendido. Cada vano tiene "
            "su propia longitud natural descargada, sin intercambio "
            "de material con los vanos adyacentes. En instalación se "
            "propone un H inicial común que debe justificarse.",
        ]),
        ("3.1. Geometría de vanos fijados", [
            "Para cada vano se emplean los amarres XYZ, su luz horizontal "
            "y el desnivel real. Ninguna longitud equivalente sustituye "
            "la geometría ni participa en los cálculos de servicio.",
        ]),
        ("3.2. Equilibrio y catenaria", [
            "Con carga vectorial uniforme q por longitud REAL de conductor, "
            "se emplea w = norma(q), a = H/w. En coordenadas locales, "
            "la trayectoria de la catenaria satisface "
            "z(x) = a [cosh((x-x_c)/a) - cosh(x_c/a)]. "
            "La magnitud de tracción es T(x) = H cosh((x-x_c)/a). "
            "El parámetro x_c se determina para satisfacer las cotas "
            "de ambos amarres. H es perpendicular a la carga resultante; "
            "no necesariamente coincide con una componente horizontal "
            "geográfica cuando hay viento.",
        ]),
        ("3.3. Cambio de estado termoelástico", [
            "La longitud natural descargada se determina por integración: "
            "L_n = integral [ds / (1 + T(s)/EA)]. "
            "El motor utiliza cuadratura Gauss-Legendre de 64 puntos por vano. "
            "Para cada vano i, la longitud natural cambia únicamente "
            "por expansión térmica: L_n,i,final = "
            "L_n,i,inicial (1 + alpha DeltaT + epsilon_p). "
            "No se conserva únicamente una suma global: se impone "
            "una ecuación de compatibilidad independiente por vano. "
            "En la Etapa 1 la deformación permanente epsilon_p es cero; "
            "el creep no se predice. La raíz de H se encuentra mediante "
            "bisección con tolerancia de compatibilidad especificada.",
        ]),
        ("3.4. Cargas gravitatorias y viento", [
            "El peso propio se representa por q_g = (0, 0, -w_g), en kN/m. "
            "Para viento transversal: w_v = 0.5 rho C_d D V^2 / 1000, "
            "con rho en kg/m3, D en m y V en m/s. El vector de viento "
            "se toma perpendicular a CADA vano en la envolvente exploratoria; "
            "no se aplica un único azimut geográfico.",
            "Cuando se incluye hielo, se añade la masa por longitud del "
            "anillo de espesor radial especificado y se incrementa el "
            "diámetro expuesto al viento. Estos casos no representan "
            "por sí mismos combinaciones meteorológicas normativas.",
        ]),
        ("3.5. Determinación de tensión de tendido", [
            "El programa propone una H inicial común de instalación. "
            "Para cada candidata H_0, evalúa las hipótesis climáticas "
            "de TODOS los vanos con longitudes fijadas y obtiene "
            "la máxima relación T_max/T_limite. Busca la mayor H_0 "
            "compatible con todos los límites documentados; la "
            "hipótesis y el vano más exigentes gobiernan.",
            "La selección TCD/THF Checa es referencia técnica, "
            "no certificación ENEE. Los máximos del barrido exploratorio "
            "se reportan separadamente de los límites de diseño.",
        ]),
        ("3.6. Flechas, resultados y alcance", [
            "Cada vano se resuelve con su catenaria espacial. La flecha "
            "vertical se mide como máximo descenso respecto a la cuerda "
            "inclinada entre amarres; el desplazamiento lateral, como "
            "separación transversal de esa misma cuerda. "
            "La memoria reproduce los resultados generados por el motor, "
            "sin recalcularlos.",
            "No se verifican postes, retenidas, espigas, amarres, "
            "cimentaciones, despejes ni creep. "
            "La aprobación para construcción requiere verificaciones "
            "normativas y estructurales adicionales.",
        ]),
    ]
    salida=[]
    for titulo,parrafos in bloques:
        # Título y primera explicación se conservan unidos.
        salida.append(KeepTogether([
            par(titulo, estilos["Heading3"]),
            Spacer(1,4),
            par(parrafos[0], estilos["NotaPDF"]),
        ]))
        salida.extend(formulas_para_seccion(titulo, ancho))
        for texto in parrafos[1:]:
            salida.append(Spacer(1,3))
            salida.append(par(texto,estilos["NotaPDF"]))
        salida.append(Spacer(1,9))
    return salida


def grafico_variable(tabla: pd.DataFrame, y_col: str, etiqueta: str, ancho: float):
    """Gráfico vectorial desde los resultados, sin ejecutar el motor."""
    if tabla is None or tabla.empty:
        return None
    if not {"Temperatura (°C)", y_col}.issubset(tabla.columns):
        return None
    serie=tabla.groupby("Temperatura (°C)",as_index=False)[y_col].max()
    serie=serie.sort_values("Temperatura (°C)")
    puntos=[(float(t),float(y)) for t,y in serie.itertuples(index=False,name=None)]
    if len(puntos)<2:
        return None
    tx=[x for x,_ in puntos]
    ys=[y for _,y in puntos]
    t0,t1=min(tx),max(tx)
    y0,y1=min(ys),max(ys)
    if t1<=t0:
        return None
    if y1==y0:
        y1=y0+1
    alto=166
    izq,dcha,abajo,arriba=48,16,30,20
    w,h=ancho-izq-dcha,alto-abajo-arriba
    g=Drawing(ancho,alto)
    g.add(Line(izq,abajo,izq+w,abajo,strokeColor=colors.black))
    g.add(Line(izq,abajo,izq,abajo+h,strokeColor=colors.black))
    for i in range(5):
        val=y0+(y1-y0)*i/4
        y=abajo+h*i/4
        g.add(Line(izq,y,izq+w,y,strokeColor=colors.lightgrey,strokeWidth=.4))
        g.add(String(izq-6,y-2,f"{val:.3f}",fontSize=7,textAnchor="end"))
    coords=[(izq+w*(t-t0)/(t1-t0),abajo+h*(y-y0)/(y1-y0))
            for t,y in puntos]
    for (xa,ya),(xb,yb) in zip(coords,coords[1:]):
        g.add(Line(xa,ya,xb,yb,strokeColor=colors.black,strokeWidth=1.4))
    for t in (t0,t1):
        x=izq+w*(t-t0)/(t1-t0)
        g.add(String(x,abajo-12,f"{t:g}",textAnchor="middle",fontSize=8))
    g.add(String(izq,alto-8,etiqueta,fontSize=8))
    g.add(String(izq+w/2,8,"Temperatura del conductor (°C)",textAnchor="middle",fontSize=8))
    return g
