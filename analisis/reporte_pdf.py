"""Adaptador de reporte histórico. La memoria nueva acepta resultados completos."""
from pathlib import Path
import pandas as pd
from .memoria_calculo import exportar_pdf_memoria


def generar_reporte_pdf(out_pdf,meta,tabla_resultados,tramos,puntos,etiquetas):
    """Firma histórica; no genera fórmulas desconectadas de los resultados."""
    resultados = {'trazabilidad':meta,'decision':pd.DataFrame(tabla_resultados)}
    destino = Path(out_pdf)
    destino.parent.mkdir(parents=True,exist_ok=True)
    destino.write_bytes(exportar_pdf_memoria(resultados))
