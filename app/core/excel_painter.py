from openpyxl import load_workbook

from app.constants.colors_conciliation import COLOR_AMARILLO
from app.constants.colums_conciliation import (
    columna_banco_concepto,
    COLUMNA_FOLIO_MATCH,
    COLUMNA_TIPO_MATCH,
    COLUMNA_VALOR_MATCH,
    COLUMNA_SCORE_MATCH
)


def pintar_excel(
        salida,
        df_banco,
        colores_filas
):
    """
    Pinta:
    - Columna Concepto según el tipo de match.
    - Columnas agregadas en amarillo.
    - Encabezados de columnas agregadas en amarillo.
    """

    wb = load_workbook(salida)

    ws = wb.active

    # ==========================
    # Columna Concepto
    # ==========================

    columna_excel_concepto = (
        list(df_banco.columns)
        .index(columna_banco_concepto)
        + 1
    )

    # ==========================
    # Columnas agregadas
    # ==========================

    columnas_nuevas = [
        COLUMNA_FOLIO_MATCH,
        COLUMNA_TIPO_MATCH,
        COLUMNA_VALOR_MATCH,
        COLUMNA_SCORE_MATCH
    ]

    columnas_nuevas_excel = [
        list(df_banco.columns).index(columna) + 1
        for columna in columnas_nuevas
    ]

    # ==========================
    # Pintar filas
    # ==========================

    for indice_banco, color in colores_filas.items():

        fila_excel = indice_banco + 2

        # Pintar Concepto

        ws.cell(
            row=fila_excel,
            column=columna_excel_concepto
        ).fill = color

        # Pintar columnas nuevas

        for columna_excel in columnas_nuevas_excel:

            ws.cell(
                row=fila_excel,
                column=columna_excel
            ).fill = COLOR_AMARILLO

    # ==========================
    # Pintar encabezados
    # ==========================

    for columna_excel in columnas_nuevas_excel:

        ws.cell(
            row=1,
            column=columna_excel
        ).fill = COLOR_AMARILLO

    wb.save(salida)