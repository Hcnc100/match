
from app.constants.colums_conciliation import *
import pandas as pd
def agregar_columnas_match(
    df_banco
):
    if COLUMNA_FOLIO_MATCH not in df_banco.columns:

        posicion = (
            df_banco.columns.get_loc(
                columna_banco_cfdi
            ) + 1
        )

        df_banco.insert(
            posicion,
            COLUMNA_FOLIO_MATCH,
            ""
        )

    if COLUMNA_TIPO_MATCH not in df_banco.columns:

        posicion = (
            df_banco.columns.get_loc(
                COLUMNA_FOLIO_MATCH
            ) + 1
        )

        df_banco.insert(
            posicion,
            COLUMNA_TIPO_MATCH,
            ""
        )
    if COLUMNA_VALOR_MATCH not in df_banco.columns:

        posicion = (
            df_banco.columns.get_loc(
                COLUMNA_TIPO_MATCH
            ) + 1
        )

        df_banco.insert(
            posicion,
            COLUMNA_VALOR_MATCH,
            ""
        )

    if COLUMNA_SCORE_MATCH not in df_banco.columns:

        posicion = (
            df_banco.columns.get_loc(
                COLUMNA_VALOR_MATCH
            ) + 1
        )

        df_banco.insert(
            posicion,
            COLUMNA_SCORE_MATCH,
            pd.NA
        )