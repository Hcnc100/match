
from app.constants.colums_conciliation import (
    COLUMNA_TIPO_MATCH
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def imprimir_resumen(
    df_banco
):

    logger.info("\nProceso terminado.")

    logger.info(
        df_banco[COLUMNA_TIPO_MATCH]
        .value_counts()
    )