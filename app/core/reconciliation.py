import pandas as pd

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

    Reglas:
    - Mismo monto
    - Misma fecha
    - Correo / Nombre / Razón Social / Referencia

    Modifica df_banco directamente.

    Retorna:
        (
            colores_filas_banco,
            colores_filas_ventas
        )
    """

    # ==========================
    # Normalizar fechas
    # ==========================

    df_banco[COLUMNA_BANCO_FECHA] = pd.to_datetime(
        df_banco[COLUMNA_BANCO_FECHA],
        errors="coerce"
    )

    df_ventas[COLUMNA_VENTAS_FECHA] = pd.to_datetime(
        df_ventas[COLUMNA_VENTAS_FECHA],
        errors="coerce"
    )

    colores_filas_banco = {}
    colores_filas_ventas = {}

    print("\nProcesando registros...")

    for indice_banco, fila_banco in df_banco.iterrows():

        monto_banco = fila_banco[
            COLUMNA_BANCO_ABNONO
        ]

        fecha_banco = fila_banco[
            COLUMNA_BANCO_FECHA
        ]

        color = COLOR_GRIS
        tipo_match = "SIN_MATCH"
        folio_control = ""
        valor_match = ""
        score_match = 0

        # ==========================
        # Fecha inválida
        # ==========================

        if pd.isna(fecha_banco):

            df_banco.at[
                indice_banco,
                COLUMNA_FOLIO_MATCH
            ] = ""

            df_banco.at[
                indice_banco,
                COLUMNA_TIPO_MATCH
            ] = "SIN_FECHA"

            df_banco.at[
                indice_banco,
                COLUMNA_VALOR_MATCH
            ] = ""

            df_banco.at[
                indice_banco,
                COLUMNA_SCORE_MATCH
            ] = 0

            colores_filas_banco[
                indice_banco
            ] = COLOR_GRIS

            continue

        fecha_banco = fecha_banco.date()

        # ==========================
        # Coincidencias por monto y fecha
        # ==========================

        coincidencias = df_ventas[
            (
                (
                    df_ventas[COLUMNA_VENTAS_MONTO]
                    - monto_banco
                ).abs() < 0.01
            )
            &
            (
                df_ventas[
                    COLUMNA_VENTAS_FECHA
                ].dt.date
                == fecha_banco
            )
        ]

        # ==========================
        # Buscar match
        # ==========================

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

                    colores_filas_ventas[
                        indice_venta
                    ] = {
                        "color": color,
                        "tipo_match": tipo_match
                    }

                    break

        # ==========================
        # Resultado en banco
        # ==========================

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