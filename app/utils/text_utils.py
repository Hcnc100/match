import re
import pandas as pd
from rapidfuzz import fuzz

def normalizar(valor):

        if pd.isna(valor):
            return ""

        texto = str(valor).upper()

        # Eliminar espacios
        texto = re.sub(r"\s+", "", texto)

        # Dejar únicamente letras y números
        texto = re.sub(
            r'[^A-Z0-9]',
            '',
            texto
        )

        return texto

## Verifica si un valor está contenido dentro de un concepto, con opción de usar comparación difusa.
## - concepto: texto del concepto a analizar
## - valor: texto del valor a buscar dentro del concepto
## - usar_fuzzy: si es True, se usará comparación difusa para encontrar coincidencias aproximadas
## - umbral: porcentaje mínimo de similitud para considerar una coincidencia válida (solo si usar_fuzzy es True)

def contiene_valor(
    concepto,
    valor,
    usar_fuzzy=False,
    umbral=90
):

    concepto_normalizado = normalizar(concepto)
    valor_normalizado = normalizar(valor)

    if not valor_normalizado:
        return False, 0

    # Match exacto
    if valor_normalizado in concepto_normalizado:
        return True, 100

    if not usar_fuzzy:
        return False, 0

    score = fuzz.partial_ratio(
         valor_normalizado,
        concepto_normalizado
    )

    return score >= umbral, score