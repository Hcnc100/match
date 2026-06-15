
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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    logger.info("Leyendo archivos")

    # Lectura
    df_banco, df_ventas = leer_archivos(
        banco=banco,
        ventas=ventas,
        header_row=header_row
    )
    
    df_banco_original = df_banco.copy()
    

    # ==========================
    # Validaciones
    # ==========================

    logger.info("Validando archivos")

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
    logger.info(
        "Validación de archivos completada. "
        "Existe columna de referencia bancaria: %s",
        existe_referencia_bancaria
    )

    

    # ==========================
    # Montos
    # ==========================
    
    logger.info("Convirtiendo montos a formato numérico")

    convertir_montos(
        df_banco=df_banco,
        df_ventas=df_ventas,
        columna_banco=COLUMNA_BANCO_ABNONO,
        columna_ventas=COLUMNA_VENTAS_MONTO
    )

    # ==========================
    # Nuevas columnas
    # ==========================

    logger.info("Agregando columnas para resultados de conciliación")

    agregar_columnas_match(
        df_banco=df_banco
    )

    logger.info("Procesando coincidencias")

    colores_filas = procesar_matches(
        df_banco=df_banco,
        df_ventas=df_ventas,
        existe_referencia_bancaria=existe_referencia_bancaria
    )

    logger.info("Guardando archivo Excel")

    guardar_excel(
        df_conciliacion=df_banco,
        df_banco_original=df_banco_original,
        salida=salida
    )

    pintar_excel(
        salida=salida,
        df_conciliacion=df_banco,
        colores_filas=colores_filas
    )

    logger.info("Imprimiendo resumen")

    imprimir_resumen(
        df_banco=df_banco
    )

    return salida