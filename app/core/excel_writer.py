import pandas as pd


def guardar_excel(
        df_conciliacion,
        df_banco_original,
        salida
):
    """
    Genera archivo con dos hojas:
    - Conciliacion
    - Banco Original
    """

    with pd.ExcelWriter(
            salida,
            engine="openpyxl"
    ) as writer:

        df_conciliacion.to_excel(
            writer,
            sheet_name="Conciliacion",
            index=False
        )

        df_banco_original.to_excel(
            writer,
            sheet_name="Banco Original",
            index=False
        )

    return salida