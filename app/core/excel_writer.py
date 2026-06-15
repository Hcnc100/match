def guardar_excel(
        df_banco,
        salida
):
    """
    Guarda el DataFrame en Excel.
    """

    df_banco.to_excel(
        salida,
        index=False
    )

    return salida