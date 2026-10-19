"""Adaptador de exportación compatible con la aplicación anterior."""
from pathlib import Path
from .memoria_calculo import exportar_excel_memoria


def exportar_resultados_excel(ruta_salida,*,df_entrada,resultados):
    """Conserva todas las tablas, unidades, entrada y paquete JSON completo."""
    datos = exportar_excel_memoria(resultados,df_entrada)
    if hasattr(ruta_salida,'write'):
        ruta_salida.write(datos)
    else:
        Path(ruta_salida).write_bytes(datos)
