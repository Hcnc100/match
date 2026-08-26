from app.constants.colums_conciliation import *


COLUMNAS_BANCO_REQUERIDAS = (
    COLUMNA_BANCO_ABNONO,
    COLUMNA_BANCO_CONCEPTO,
    COLUMNA_BANCO_SALDO,
)

COLUMNAS_VENTAS_REQUERIDAS = (
    COLUMNA_VENTAS_MONTO,
    COLUMNA_VENTAS_FOLIO_CONTROL,
    COLUMNA_VENTAS_CORREO,
    COLUMNA_VENTAS_NOMBRE,
    COLUMNA_VENTAS_RAZON_SOCIAL,
)


def _columnas_faltantes(df, requeridas):
    return [columna for columna in requeridas if columna not in df.columns]

def validar_archivos(
    df_banco,
    df_ventas
):
    if df_banco.empty:
        raise ValueError(
            "El archivo seleccionado como Banco no contiene registros."
        )

    if df_ventas.empty:
        raise ValueError(
            "El archivo seleccionado como Ventas no contiene registros."
        )

def validar_columnas(
    df_banco,
    df_ventas
):
    faltantes_banco = _columnas_faltantes(
        df_banco,
        COLUMNAS_BANCO_REQUERIDAS,
    )
    faltantes_ventas = _columnas_faltantes(
        df_ventas,
        COLUMNAS_VENTAS_REQUERIDAS,
    )

    banco_parece_ventas = not _columnas_faltantes(
        df_banco,
        COLUMNAS_VENTAS_REQUERIDAS,
    )
    ventas_parece_banco = not _columnas_faltantes(
        df_ventas,
        COLUMNAS_BANCO_REQUERIDAS,
    )

    if banco_parece_ventas and ventas_parece_banco:
        raise ValueError(
            "Los archivos parecen estar invertidos. Selecciona el estado "
            "de cuenta en 'Archivo Banco' y el reporte de operaciones en "
            "'Archivo Ventas'."
        )

    if faltantes_banco:
        raise ValueError(
            "El archivo seleccionado como Banco no tiene las columnas "
            "esperadas. Faltan: "
            f"{', '.join(faltantes_banco)}"
        )

    if faltantes_ventas:
        raise ValueError(
            "El archivo seleccionado como Ventas no tiene las columnas "
            "esperadas. Faltan: "
            f"{', '.join(faltantes_ventas)}"
        )


    
