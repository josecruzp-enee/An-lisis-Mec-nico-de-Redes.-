"""Memoria y paquete reproducible; entradas, unidades y faltantes viajan con resultados."""
from __future__ import annotations
from io import BytesIO
import json
import textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from .estados_limite import Verificacion


def serializable(valor):
    """Convierte objetos científicos a JSON estándar, sin NaN/Infinity."""
    if isinstance(valor,pd.DataFrame):
        return serializable(valor.to_dict(orient='records'))
    if isinstance(valor,Verificacion):
        return serializable(valor.como_dict())
    if isinstance(valor,np.ndarray):
        return serializable(valor.tolist())
    if isinstance(valor,dict):
        return {str(k):serializable(v) for k,v in valor.items()}
    if isinstance(valor,(tuple,list)):
        return [serializable(v) for v in valor]
    if isinstance(valor,np.generic):
        return serializable(valor.item())
    if isinstance(valor,float) and not np.isfinite(valor):
        return None
    if valor is pd.NA:
        return None
    return valor


def exportar_json(resultados):
    """Bytes UTF-8 con entrada, alternativas y residuales completos."""
    return json.dumps(serializable(resultados),ensure_ascii=False,indent=2,
                      allow_nan=False).encode('utf-8')


def exportar_excel_memoria(resultados,entrada=None):
    """Todas las tablas sin redondeo; trazabilidad y JSON fragmentado sin truncar."""
    salida = BytesIO()
    with pd.ExcelWriter(salida,engine='openpyxl') as escritor:
        for nombre,valor in resultados.items():
            if isinstance(valor,pd.DataFrame):
                valor.to_excel(escritor,sheet_name=nombre[:31],index=False)
        pd.DataFrame(list(resultados.get('trazabilidad',{}).items()),columns=['Dato','Valor']).to_excel(
            escritor,sheet_name='Trazabilidad',index=False)
        if isinstance(entrada,pd.DataFrame):
            entrada.to_excel(escritor,sheet_name='Entrada',index=False)
        texto = exportar_json(resultados).decode('utf-8')
        pd.DataFrame({'Orden':range((len(texto)+29999)//30000),
                      'JSON concatenar en orden':[texto[i:i+30000] for i in range(0,len(texto),30000)]}).to_excel(
                      escritor,sheet_name='Paquete_JSON',index=False)
    return salida.getvalue()


def _lineas_tabla(tabla):
    """Bloques compactos; JSON/Excel conservan precisión y campos completos."""
    if tabla is None or len(tabla)==0:
        return ['Sin datos suficientes. NO VERIFICABLE.']
    salida = []
    for fila in serializable(tabla):
        partes = []
        for nombre,valor in fila.items():
            if valor is None or valor == '':
                continue
            texto = f'{valor:.6g}' if isinstance(valor,float) else str(valor)
            partes.append(f'{nombre}: {texto}')
        salida.extend(textwrap.wrap(' | '.join(partes),width=88))
        salida.append('')
    return salida


def _secciones(resultados):
    """Cobertura explícita: lo no modelado se informa, no se rellena con supuestos."""
    return [
        ('1. Proyecto y alcance',[f'{k}: {v}' for k,v in resultados.get('trazabilidad',{}).items()]),
        ('2. Referencias y ecuaciones',['Ecuaciones deducidas: docs/ECUACIONES.md.',
         'ENEE/NESC/IEC/ASCE: aplicabilidad y cláusulas pendientes de revisión documental.']),
        ('3. Hipótesis',['Cable flexible, carga constante por longitud real, vanos retenidos.',
         'Poste lineal de desplazamientos pequeños; no incluye fisuración ni P-delta.']),
        ('4. Conductores',_lineas_tabla(resultados.get('verificaciones_conductor'))),
        ('5. Geometría', ['Coordenadas y amarres completos en el JSON reproducible adjunto a la exportación Excel.']),
        ('6. Catenaria y 7. Cambio de estado',_lineas_tabla(resultados.get('vanos_estados'))),
        ('8. Clima y 9. Fuerzas y momentos',_lineas_tabla(resultados.get('acciones_nodos',resultados.get('fuerzas_nodo')))),
        ('10. Postes, 11. Retenidas, 12. Anclajes y 13. Cimentaciones',_lineas_tabla(resultados.get('verificaciones'))),
        ('14. Alternativas y 15. Decisión',_lineas_tabla(resultados.get('decision'))),
        ('16. Conclusiones',['Una ejecución numérica no certifica cumplimiento normativo.',
         'NO VERIFICABLE identifica datos o modelos que faltan. No habilita construcción.']),
        ('17. Envolventes y anexos',_lineas_tabla(resultados.get('envolventes')))]


def exportar_pdf_memoria(resultados):
    """PDF paginado; acompañar con Excel/JSON para reproducir todos los datos."""
    salida = BytesIO()
    with PdfPages(salida) as pdf:
        pagina = 0
        for titulo,lineas in _secciones(resultados):
            texto = []
            for linea in lineas:
                texto.extend(textwrap.wrap(str(linea),88) or [''])
            for inicio in range(0,max(1,len(texto)),43):
                pagina += 1
                _pagina(pdf,titulo,texto[inicio:inicio+43],pagina)
    return salida.getvalue()


def _pagina(pdf,titulo,lineas,numero):
    """A4 con márgenes constantes; cerrar figura evita memoria retenida en Streamlit."""
    fig = plt.figure(figsize=(8.27,11.69))
    fig.text(.08,.95,'MEMORIA DE CÁLCULO · VERSIÓN CANDIDATA',fontsize=12,weight='bold')
    fig.text(.08,.91,titulo,fontsize=10,weight='bold')
    fig.text(.08,.87,'\n'.join(lineas),fontsize=9,va='top',linespacing=1.5)
    fig.text(.08,.04,f'Página {numero} · Datos completos y fuentes: exportación JSON/Excel',fontsize=8)
    pdf.savefig(fig)
    plt.close(fig)
