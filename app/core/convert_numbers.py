import pandas as pd

def convertir_montos(
    df_banco,
    df_ventas,
    columna_banco,
    columna_ventas
):

    df_banco[columna_banco] = pd.to_numeric(
        df_banco[columna_banco],
        errors="coerce"
    )

    df_ventas[columna_ventas] = pd.to_numeric(
        df_ventas[columna_ventas],
        errors="coerce"
    )