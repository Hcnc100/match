
from app.utils.text_utils import contiene_valor
from app.constants.colums_conciliation import *
from app.constants.colors_conciliation import *
from app.core.excel_reader import leer_archivos
from app.core.validator import validar_archivos, validar_columnas
from app.core.convert_numbers import convertir_montos
from app.core.match_columns import agregar_columnas_match
from app.core.reconciliation import procesar_matches
from app.core.excel_writer import guardar_excel
from app.core.summary import imprimir_resumen
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalizar_columna_cfdi(df_banco):
    """Acepta variantes de CFDI y la mantiene como dato opcional."""
    columnas_por_nombre = {
        str(columna).strip().upper(): columna
        for columna in df_banco.columns
    }

    for alias in ALIAS_COLUMNAS_BANCO_CFDI:
        columna_encontrada = columnas_por_nombre.get(alias.upper())
        if columna_encontrada is not None:
            if columna_encontrada != COLUMNA_BANCO_CFDI:
                df_banco.rename(
                    columns={columna_encontrada: COLUMNA_BANCO_CFDI},
                    inplace=True
                )
            return


def procesar_conciliacion(
        banco,
        ventas,
        salida,
        omitir_primera_fila=False,
        progreso=None,
):
    # ==========================
    # Columnas
    # ==========================
    
    header_row = 1 if omitir_primera_fila else 0

    # ==========================

    logger.info("Leyendo archivos")
    if progreso:
        progreso(10, "leyendo_archivos", "Leyendo los archivos Excel")

    # Lectura
    df_banco, df_ventas = leer_archivos(
        banco=banco,
        ventas=ventas,
        header_row=header_row
    )
    
    df_ventas_original = df_ventas.copy()
    normalizar_columna_cfdi(df_banco)
    

    # ==========================
    # Validaciones
    # ==========================

    logger.info("Validando archivos")
    if progreso:
        progreso(25, "validando", "Validando estructura y columnas")

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

    if progreso:
        progreso(35, "conciliando", "Buscando coincidencias")

    colores_filas_banco, colores_filas_ventas = procesar_matches(
        df_banco=df_banco,
        df_ventas=df_ventas,
        existe_referencia_bancaria=existe_referencia_bancaria,
        progreso=(
            lambda porcentaje: progreso(
                35 + int(porcentaje * 0.4),
                "conciliando",
                f"Comparando movimientos ({porcentaje}%)",
            )
            if progreso else None
        ),
    )

    logger.info("Guardando archivo Excel")
    if progreso:
        progreso(80, "generando_excel", "Generando el archivo de resultados")

    guardar_excel(
        df_conciliacion=df_banco,
        df_ventas_original=df_ventas_original,
        salida=salida,
        colores_filas_banco=colores_filas_banco,
        colores_filas_ventas=colores_filas_ventas,
    )

    if progreso:
        progreso(98, "finalizando", "Preparando la descarga")

    logger.info("Imprimiendo resumen")

    imprimir_resumen(
        df_banco=df_banco
    )

    return salida
