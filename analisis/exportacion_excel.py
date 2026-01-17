# analisis/exportacion_excel.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any


def exportar_resultados_excel(
    ruta_salida: str,
    *,
    df_entrada: pd.DataFrame,
    resultados: Dict[str, Any],
):
    """
    Exporta los resultados del análisis mecánico a un archivo Excel.

    Hojas:
    - Entrada
    - Tramos
    - Deflexiones
    - Resumen
    - Cargas_tramo
    - Fuerzas_nodo
    - Decision_soporte
    """

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:

        # -----------------------------
        # 1) Entrada
        # -----------------------------
        df_entrada.to_excel(writer, sheet_name="Entrada", index=False)

        # -----------------------------
        # 2) Geometría
        # -----------------------------
        if "tramos" in resultados:
            resultados["tramos"].to_excel(
                writer, sheet_name="Tramos", index=False
            )

        if "deflexiones" in resultados and resultados["deflexiones"] is not None:
            resultados["deflexiones"].to_excel(
                writer, sheet_name="Deflexiones", index=False
            )

        if "resumen" in resultados:
            resultados["resumen"].to_excel(
                writer, sheet_name="Resumen_por_punto", index=False
            )

        # -----------------------------
        # 3) Cargas
        # -----------------------------
        if "cargas_tramo" in resultados:
            resultados["cargas_tramo"].to_excel(
                writer, sheet_name="Cargas_por_tramo", index=False
            )

        # -----------------------------
        # 4) Fuerzas
        # -----------------------------
        if "fuerzas_nodo" in resultados:
            resultados["fuerzas_nodo"].to_excel(
                writer, sheet_name="Fuerzas_por_poste", index=False
            )

        # -----------------------------
        # 5) Decisión estructural
        # -----------------------------
        if "decision" in resultados:
            resultados["decision"].to_excel(
                writer, sheet_name="Decision_soporte", index=False
            )
