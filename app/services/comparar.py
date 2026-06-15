import pandas as pd

# ==========================
# Archivos
# ==========================

banco = "banco.xlsx"
ventas = "ventas.xlsx"
salida = "coincidencias.xlsx"

# ==========================
# Lectura
# ==========================

print("Leyendo archivos...")

df_banco = pd.read_excel(
    banco,
    header=1
)

df_ventas = pd.read_excel(
    ventas,
    header=1
)

df_banco.columns = df_banco.columns.str.strip()
df_ventas.columns = df_ventas.columns.str.strip()

# ==========================
# Validaciones
# ==========================

columnas_banco_requeridas = [
    "Concepto / Referencia",
    "Abono",
    "FOLIO CONTROL"
]

columnas_ventas_requeridas = [
    "FOLIO CONTROL",
    "Nombre",
    "Correo",
    "Razon social",
    "Monto"
]

for columna in columnas_banco_requeridas:
    if columna not in df_banco.columns:
        raise ValueError(
            f"No existe la columna '{columna}' en banco.xlsx"
        )

for columna in columnas_ventas_requeridas:
    if columna not in df_ventas.columns:
        raise ValueError(
            f"No existe la columna '{columna}' en ventas.xlsx"
        )

# ==========================
# Normalizar FOLIO CONTROL
# ==========================

df_banco["FOLIO CONTROL"] = (
    df_banco["FOLIO CONTROL"]
    .fillna("")
    .astype(str)
    .str.strip()
)

df_ventas["FOLIO CONTROL"] = (
    df_ventas["FOLIO CONTROL"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# ==========================
# Seleccionar columnas
# ==========================

df_banco_filtrado = df_banco[
    [
        "Concepto / Referencia",
        "Abono",
        "FOLIO CONTROL"
    ]
]

df_ventas_filtrado = df_ventas[
    [
        "FOLIO CONTROL",
        "Nombre",
        "Correo",
        "Razon social",
        "Monto"
    ]
]

# ==========================
# Cruce por FOLIO CONTROL
# ==========================

df_resultado = df_banco_filtrado.merge(
    df_ventas_filtrado,
    on="FOLIO CONTROL",
    how="inner"
)

# ==========================
# Renombrar columnas
# ==========================

df_resultado = df_resultado.rename(
    columns={
        "Concepto / Referencia": "CONCEPTO_BANCO",
        "Abono": "ABONO_BANCO",
        "FOLIO CONTROL": "FOLIO_CONTROL_MATCH",
        "Nombre": "NOMBRE_VENTAS",
        "Correo": "CORREO_VENTAS",
        "Razon social": "RAZON_SOCIAL_VENTAS",
        "Monto": "MONTO_VENTAS"
    }
)

# ==========================
# Guardar resultado
# ==========================

df_resultado.to_excel(
    salida,
    index=False
)

# ==========================
# Resumen
# ==========================

print()
print(
    f"Coincidencias encontradas: "
    f"{len(df_resultado)}"
)

print(
    f"Archivo generado: {salida}"
)