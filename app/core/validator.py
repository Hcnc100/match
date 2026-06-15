from app.constants.colums_conciliation import *

def validar_archivos(
    df_banco,
    df_ventas
):
    if df_banco.empty:
        raise ValueError(
            f"El archivo {df_banco} no contiene registros."
        )

    if df_ventas.empty:
        raise ValueError(
            f"El archivo {df_ventas} no contiene registros."
        )

def validar_columnas(
    df_banco,
    df_ventas
):
    columnas_banco_requeridas = [
        columna_banco,
        columna_banco_concepto,
        columna_banco_cfdi,
        columna_banco_saldo
    ]

    columnas_ventas_requeridas = [
        columna_ventas,
        columna_ventas_folio_control,
        columna_ventas_correo,
        columna_ventas_nombre,
        columna_ventas_razon_social
    ]

    faltantes_banco = [
        c
        for c in columnas_banco_requeridas
        if c not in df_banco.columns
    ]

    faltantes_ventas = [
        c
        for c in columnas_ventas_requeridas
        if c not in df_ventas.columns
    ]

    if faltantes_banco:
        raise ValueError(
            f"Columnas faltantes en {df_banco}: "
            f"{', '.join(faltantes_banco)}"
        )

    if faltantes_ventas:
        raise ValueError(
            f"Columnas faltantes en {df_ventas}: "
            f"{', '.join(faltantes_ventas)}"
        )


    