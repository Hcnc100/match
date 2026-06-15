
from app.utils.text_utils import contiene_valor
from app.constants.colums_conciliation import *
from app.constants.colors_conciliation import *
from app.core.excel_reader import leer_archivos
from app.core.validator import validar_archivos, validar_columnas
from app.core.convert_numbers import convertir_montos
from app.core.match_columns import agregar_columnas_match
from app.core.reconciliation import procesar_matches
from app.core.excel_painter import pintar_excel
from app.core.excel_writer import guardar_excel
from app.core.summary import imprimir_resumen


def procesar_conciliacion(
        banco,
        ventas,
        salida,
        omitir_primera_fila=False
):
    # ==========================
    # Columnas
    # ==========================
    
    header_row = 1 if omitir_primera_fila else 0

    # ==========================

    # Lectura
    df_banco, df_ventas = leer_archivos(
        banco=banco,
        ventas=ventas,
        header_row=header_row
    )

    # ==========================
    # Validaciones
    # ==========================

    validar_archivos(
        df_banco=df_banco,
        df_ventas=df_ventas
    )
    
    validar_columnas(
        df_banco=df_banco,
        df_ventas=df_ventas
    )
    
    existe_referencia_bancaria = (
        COLUMNA_VENTAS_REFERENCIA_BANCARIA
        in df_ventas.columns
    )

    print(
        f"\nReferencia Bancaria encontrada: "
        f"{existe_referencia_bancaria}"
    )

    

    # ==========================
    # Montos
    # ==========================

    convertir_montos(
        df_banco=df_banco,
        df_ventas=df_ventas,
        columna_banco=COLUMNA_BANCO_ABNONO,
        columna_ventas=COLUMNA_VENTAS_MONTO
    )

    # ==========================
    # Nuevas columnas
    # ==========================


    agregar_columnas_match(
        df_banco=df_banco
    )

    colores_filas = procesar_matches(
        df_banco=df_banco,
        df_ventas=df_ventas,
        existe_referencia_bancaria=existe_referencia_bancaria
    )

    guardar_excel(
        df_banco=df_banco,
        salida=salida
    )

    pintar_excel(
        salida=salida,
        df_banco=df_banco,
        colores_filas=colores_filas
    )

    imprimir_resumen(
        df_banco=df_banco
    )

    return salida