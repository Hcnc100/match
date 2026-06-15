from app.utils.text_utils import contiene_valor
from app.constants.colums_conciliation import *
from app.constants.colors_conciliation import *


def buscar_match(
        concepto_banco,
        fila_venta,
        existe_referencia_bancaria
):
    """
    Busca coincidencia en el siguiente orden:

    1. Correo
    2. Nombre
    3. Razón social
    4. Referencia bancaria

    Retorna:
        {
            "tipo": "...",
            "valor": "...",
            "score": 100,
            "color": COLOR_...
        }

    o None si no encuentra coincidencia.
    """

    # ==========================
    # CORREO
    # ==========================

    encontro, score = contiene_valor(
        concepto_banco,
        fila_venta[COLUMNA_VENTAS_CORREO],
        usar_fuzzy=True,
        umbral=80
    )

    if encontro:
        return {
            "tipo": "CORREO",
            "valor": fila_venta[COLUMNA_VENTAS_CORREO],
            "score": score,
            "color": COLOR_VERDE
        }

    # ==========================
    # NOMBRE
    # ==========================

    encontro, score = contiene_valor(
        concepto_banco,
        fila_venta[COLUMNA_VENTAS_NOMBRE],
        usar_fuzzy=True,
        umbral=90
    )

    if encontro:
        return {
            "tipo": "NOMBRE",
            "valor": fila_venta[COLUMNA_VENTAS_NOMBRE],
            "score": score,
            "color": COLOR_AMARILLO
        }

    # ==========================
    # RAZON SOCIAL
    # ==========================

    encontro, score = contiene_valor(
        concepto_banco,
        fila_venta[COLUMNA_VENTAS_RAZON_SOCIAL],
        usar_fuzzy=True,
        umbral=85
    )

    if encontro:
        return {
            "tipo": "RAZON_SOCIAL",
            "valor": fila_venta[COLUMNA_VENTAS_RAZON_SOCIAL],
            "score": score,
            "color": COLOR_AZUL
        }

    # ==========================
    # REFERENCIA BANCARIA
    # ==========================

    if existe_referencia_bancaria:

        encontro, score = contiene_valor(
            concepto_banco,
            fila_venta[COLUMNA_VENTAS_REFERENCIA_BANCARIA],
            usar_fuzzy=False
        )

        if encontro:
            return {
                "tipo": "REFERENCIA_BANCARIA",
                "valor": fila_venta[COLUMNA_VENTAS_REFERENCIA_BANCARIA],
                "score": score,
                "color": COLOR_ROJO
            }

    return None