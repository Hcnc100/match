
from app.constants.colums_conciliation import (
    COLUMNA_TIPO_MATCH
)

def imprimir_resumen(
    df_banco
):

    print("\nProceso terminado.")

    print(
        df_banco[COLUMNA_TIPO_MATCH]
        .value_counts()
    )