import pandas as pd

from app.constants.colums_conciliation import *
from app.constants.colors_conciliation import *
from app.core.matcher import buscar_match
from app.utils.text_utils import normalizar


def normalizar_fecha_ventas(df_ventas):
    """Construye FECHA usando las fechas disponibles por orden de prioridad."""
    columnas_disponibles = [
        columna
        for columna in (
            COLUMNA_VENTAS_FECHA,
            *COLUMNAS_VENTAS_FECHA_ALTERNATIVAS,
        )
        if columna in df_ventas.columns
    ]

    if not columnas_disponibles:
        raise ValueError(
            "El archivo de ventas debe incluir alguna columna de fecha: "
            f"{COLUMNA_VENTAS_FECHA}, "
            f"{', '.join(COLUMNAS_VENTAS_FECHA_ALTERNATIVAS)}"
        )

    fechas = pd.concat(
        [
            pd.to_datetime(df_ventas[columna], errors="coerce")
            for columna in columnas_disponibles
        ],
        axis=1
    )

    df_ventas[COLUMNA_VENTAS_FECHA] = fechas.bfill(axis=1).iloc[:, 0]


def procesar_matches(
        df_banco,
        df_ventas,
        existe_referencia_bancaria,
        progreso=None,
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

    normalizar_fecha_ventas(df_ventas)

    # Indexar una sola vez evita volver a filtrar todas las ventas por cada
    # movimiento bancario. Los centavos enteros también eliminan comparaciones
    # ambiguas entre números de punto flotante.
    ventas_por_fecha_monto = {}
    columnas_texto = [
        COLUMNA_VENTAS_CORREO,
        COLUMNA_VENTAS_NOMBRE,
        COLUMNA_VENTAS_RAZON_SOCIAL,
    ]
    if existe_referencia_bancaria:
        columnas_texto.append(COLUMNA_VENTAS_REFERENCIA_BANCARIA)

    for indice_venta, fila_venta in df_ventas.iterrows():
        fecha_venta = fila_venta[COLUMNA_VENTAS_FECHA]
        monto_venta = fila_venta[COLUMNA_VENTAS_MONTO]
        if pd.isna(fecha_venta) or pd.isna(monto_venta):
            continue

        fila_normalizada = fila_venta.copy()
        for columna in columnas_texto:
            fila_normalizada[columna] = normalizar(fila_venta[columna])

        clave = (fecha_venta.date(), int(round(float(monto_venta) * 100)))
        ventas_por_fecha_monto.setdefault(clave, []).append(
            (indice_venta, fila_venta, fila_normalizada)
        )

    colores_filas_banco = {}
    colores_filas_ventas = {}

    print("\nProcesando registros...")

    total_banco = len(df_banco)
    ultimo_porcentaje = -1

    for posicion, (indice_banco, fila_banco) in enumerate(df_banco.iterrows()):

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

        if pd.isna(monto_banco):
            coincidencias = []
        else:
            clave = (fecha_banco, int(round(float(monto_banco) * 100)))
            coincidencias = ventas_por_fecha_monto.get(clave, [])

        # ==========================
        # Buscar match
        # ==========================

        if coincidencias:

            concepto_banco = normalizar(fila_banco[COLUMNA_BANCO_CONCEPTO])

            for indice_venta, fila_venta, fila_normalizada in coincidencias:

                resultado = buscar_match(
                    concepto_banco=concepto_banco,
                    fila_venta=fila_venta,
                    existe_referencia_bancaria=existe_referencia_bancaria,
                    valores_normalizados=True,
                    fila_venta_normalizada=fila_normalizada,
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

        if progreso and total_banco:
            porcentaje = int(((posicion + 1) / total_banco) * 100)
            if porcentaje != ultimo_porcentaje:
                progreso(porcentaje)
                ultimo_porcentaje = porcentaje

    return (
        colores_filas_banco,
        colores_filas_ventas
    )
