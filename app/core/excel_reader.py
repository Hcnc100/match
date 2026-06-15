import pandas as pd

def leer_archivos(
    banco,
    ventas,
    header_row
):
    print("Leyendo archivos...")

    df_banco = pd.read_excel(
        banco,
        header=header_row
    )

    df_ventas = pd.read_excel(
        ventas,
        header=header_row
    )

    df_banco.columns = df_banco.columns.str.strip()
    df_ventas.columns = df_ventas.columns.str.strip()

    # ==========================
    # Mostrar columnas
    # ==========================

    print("\n=== COLUMNAS BANCO ===")

    for i, columna in enumerate(df_banco.columns, start=1):
        print(f"{i}. [{columna}]")

    print("\n=== COLUMNAS VENTAS ===")

    for i, columna in enumerate(df_ventas.columns, start=1):
        print(f"{i}. [{columna}]")

    return df_banco, df_ventas