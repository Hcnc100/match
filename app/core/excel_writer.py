import pandas as pd


def guardar_excel(
        df_conciliacion,
        df_ventas_original,
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

        df_ventas_original.to_excel(
            writer,
            sheet_name="Ventas",
            index=False
        )

    return salida