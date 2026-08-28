import pandas as pd
from app.constants.colors_conciliation import COLOR_AMARILLO
from app.constants.colums_conciliation import (
    COLUMNA_FOLIO_MATCH,
    COLUMNA_SCORE_MATCH,
    COLUMNA_TIPO_MATCH,
    COLUMNA_VALOR_MATCH,
)


def guardar_excel(
        df_conciliacion,
        df_ventas_original,
        salida,
        colores_filas_banco=None,
        colores_filas_ventas=None,
):
    """
    Genera archivo con dos hojas:
    - Conciliacion
    - Banco Original
    """

    with pd.ExcelWriter(
            salida,
            engine="openpyxl"
    ) as writer:

        df_conciliacion.to_excel(
            writer,
            sheet_name="Conciliacion",
            index=False
        )

        df_ventas_original.to_excel(
            writer,
            sheet_name="Ventas",
            index=False
        )

        ws_conciliacion = writer.sheets["Conciliacion"]
        ws_ventas = writer.sheets["Ventas"]
        columnas_nuevas = [
            COLUMNA_FOLIO_MATCH,
            COLUMNA_TIPO_MATCH,
            COLUMNA_VALOR_MATCH,
            COLUMNA_SCORE_MATCH,
        ]
        columnas_nuevas_excel = [
            list(df_conciliacion.columns).index(columna) + 1
            for columna in columnas_nuevas
        ]

        for indice_banco, color in (colores_filas_banco or {}).items():
            fila_excel = indice_banco + 2
            for columna_excel in range(1, ws_conciliacion.max_column + 1):
                ws_conciliacion.cell(fila_excel, columna_excel).fill = color
            for columna_excel in columnas_nuevas_excel:
                ws_conciliacion.cell(fila_excel, columna_excel).fill = COLOR_AMARILLO

        for columna_excel in columnas_nuevas_excel:
            ws_conciliacion.cell(1, columna_excel).fill = COLOR_AMARILLO

        columna_tipo_match = ws_ventas.max_column + 1
        ws_ventas.cell(1, columna_tipo_match, "TIPO_MATCH").fill = COLOR_AMARILLO
        for indice_venta, info in (colores_filas_ventas or {}).items():
            fila_excel = indice_venta + 2
            for columna_excel in range(1, columna_tipo_match):
                ws_ventas.cell(fila_excel, columna_excel).fill = info["color"]
            ws_ventas.cell(
                fila_excel,
                columna_tipo_match,
                info["tipo_match"],
            ).fill = info["color"]

    return salida
