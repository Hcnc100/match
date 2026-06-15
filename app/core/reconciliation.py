from app.constants.colums_conciliation import *
from app.constants.colors_conciliation import *
from app.core.matcher import buscar_match


def procesar_matches(
        df_banco,
        df_ventas,
        existe_referencia_bancaria
):
    """
    Recorre banco y ventas buscando coincidencias.

    Modifica df_banco directamente.

    Retorna:
        (
            colores_filas_banco,
            colores_filas_ventas
        )
    """

    colores_filas_banco = {}
    colores_filas_ventas = {}

    print("\nProcesando registros...")

    for indice_banco, fila_banco in df_banco.iterrows():

        monto_banco = fila_banco[
            COLUMNA_BANCO_ABNONO
        ]

        coincidencias = df_ventas[
            (
                df_ventas[COLUMNA_VENTAS_MONTO]
                - monto_banco
            ).abs() < 0.01
        ]

        color = COLOR_GRIS
        tipo_match = "SIN_MATCH"
        folio_control = ""
        valor_match = ""
        score_match = 0

        if not coincidencias.empty:

            concepto_banco = fila_banco[
                COLUMNA_BANCO_CONCEPTO
            ]

            for indice_venta, fila_venta in coincidencias.iterrows():

                resultado = buscar_match(
                    concepto_banco=concepto_banco,
                    fila_venta=fila_venta,
                    existe_referencia_bancaria=existe_referencia_bancaria
                )

                if resultado:

                    color = resultado["color"]

                    tipo_match = resultado["tipo"]

                    valor_match = resultado["valor"]

                    score_match = resultado["score"]

                    folio_control = fila_venta[
                        COLUMNA_VENTAS_FOLIO_CONTROL
                    ]

                    # Marcar venta para colorear
                    colores_filas_ventas[
                        indice_venta
                    ] = {
                        "color": color,
                        "tipo_match": tipo_match
                    }

                    break

        df_banco.at[
            indice_banco,
            COLUMNA_FOLIO_MATCH
        ] = folio_control

        df_banco.at[
            indice_banco,
            COLUMNA_TIPO_MATCH
        ] = tipo_match

        df_banco.at[
            indice_banco,
            COLUMNA_VALOR_MATCH
        ] = str(valor_match)

        df_banco.at[
            indice_banco,
            COLUMNA_SCORE_MATCH
        ] = float(score_match)

        colores_filas_banco[
            indice_banco
        ] = color

    return (
        colores_filas_banco,
        colores_filas_ventas
    )