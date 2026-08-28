import unittest

import pandas as pd

from app.constants.colums_conciliation import (
    COLUMNA_FOLIO_MATCH,
    COLUMNA_SCORE_MATCH,
    COLUMNA_TIPO_MATCH,
    COLUMNA_VALOR_MATCH,
)
from app.core.match_columns import agregar_columnas_match
from app.core.reconciliation import procesar_matches


class ReconciliationTests(unittest.TestCase):
    def test_uses_fecha_pago_when_fecha_is_empty(self):
        banco = pd.DataFrame([
            {
                "Día": "2026-08-11",
                "Concepto / Referencia": (
                    "SPEI RECIBIDOAZTECA/0131002599  127 1723930"
                    "juanpachecojrhotmailcom50MENSU"
                ),
                "Abono": 325.0,
                "Saldo": 9_306_747.36,
            }
        ])
        ventas = pd.DataFrame([
            {
                "FECHA": pd.NaT,
                "Fecha pago": "2026-08-11",
                "Fecha ingreso": "2026-08-11",
                "Monto": 325.0,
                "Correo": "juanpachecojr@hotmail.com",
                "Nombre": "Juan Pacheco Salazar",
                "Razon social": pd.NA,
                "FOLIO CONTROL": "2479-11-325-BBVA-SPEI",
                "Referencia Bancaria": "8914I",
            }
        ])
        agregar_columnas_match(banco)

        procesar_matches(
            df_banco=banco,
            df_ventas=ventas,
            existe_referencia_bancaria=True,
        )

        self.assertEqual(banco.at[0, COLUMNA_TIPO_MATCH], "CORREO")
        self.assertEqual(
            banco.at[0, COLUMNA_VALOR_MATCH],
            "juanpachecojr@hotmail.com",
        )
        self.assertEqual(
            banco.at[0, COLUMNA_FOLIO_MATCH],
            "2479-11-325-BBVA-SPEI",
        )
        self.assertEqual(banco.at[0, COLUMNA_SCORE_MATCH], 100.0)

    def test_progress_is_reported_during_matching(self):
        banco = pd.DataFrame([{
            "Día": "2026-08-11",
            "Concepto / Referencia": "SIN COINCIDENCIA",
            "Abono": 100.0,
            "Saldo": 1000.0,
        }])
        ventas = pd.DataFrame([{
            "FECHA": "2026-08-11",
            "Monto": 200.0,
            "Correo": "persona@example.com",
            "Nombre": "Persona",
            "Razon social": "Empresa",
            "FOLIO CONTROL": "ABC",
        }])
        agregar_columnas_match(banco)
        progress = []

        procesar_matches(banco, ventas, False, progreso=progress.append)

        self.assertEqual(progress[-1], 100)


if __name__ == "__main__":
    unittest.main()
