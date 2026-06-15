from openpyxl import load_workbook

from app.constants.colors_conciliation import COLOR_AMARILLO
from app.constants.colums_conciliation import (
    COLUMNA_BANCO_CONCEPTO,
    COLUMNA_FOLIO_MATCH,
    COLUMNA_TIPO_MATCH,
    COLUMNA_VALOR_MATCH,
    COLUMNA_SCORE_MATCH
)


def pintar_excel(
        salida,
        df_conciliacion,
        colores_filas
):

    wb = load_workbook(salida)

    ws_conciliacion = wb["Conciliacion"]
    ws_banco = wb["Banco Original"]

    # ==========================
    # Hoja conciliación
    # ==========================

    columna_excel_concepto = (
        list(df_conciliacion.columns)
        .index(COLUMNA_BANCO_CONCEPTO)
        + 1
    )

    columnas_nuevas = [
        COLUMNA_FOLIO_MATCH,
        COLUMNA_TIPO_MATCH,
        COLUMNA_VALOR_MATCH,
        COLUMNA_SCORE_MATCH
    ]

    columnas_nuevas_excel = [
        list(df_conciliacion.columns).index(col) + 1
        for col in columnas_nuevas
    ]

    for indice_banco, color in colores_filas.items():

        fila_excel = indice_banco + 2

        ws_conciliacion.cell(
            row=fila_excel,
            column=columna_excel_concepto
        ).fill = color

        for columna_excel in columnas_nuevas_excel:

            ws_conciliacion.cell(
                row=fila_excel,
                column=columna_excel
            ).fill = COLOR_AMARILLO

    for columna_excel in columnas_nuevas_excel:

        ws_conciliacion.cell(
            row=1,
            column=columna_excel
        ).fill = COLOR_AMARILLO

    # ==========================
    # Hoja banco original
    # ==========================

    for indice_banco, color in colores_filas.items():

        fila_excel = indice_banco + 2

        for columna_excel in range(
                1,
                ws_banco.max_column + 1
        ):
            ws_banco.cell(
                row=fila_excel,
                column=columna_excel
            ).fill = color

    wb.save(salida)