import unittest

import pandas as pd

from app.core.validator import validar_archivos, validar_columnas


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.banco = pd.DataFrame([
            {
                "Día": "2026-08-11",
                "Concepto / Referencia": "SPEI RECIBIDO",
                "Abono": 325,
                "Saldo": 1000,
            }
        ])
        self.ventas = pd.DataFrame([
            {
                "Monto": 325,
                "FOLIO CONTROL": "ABC",
                "Correo": "persona@example.com",
                "Nombre": "Persona",
                "Razon social": "Empresa",
            }
        ])

    def test_detects_reversed_files(self):
        with self.assertRaisesRegex(ValueError, "archivos parecen estar invertidos"):
            validar_columnas(self.ventas, self.banco)

    def test_identifies_missing_bank_columns_without_dumping_dataframe(self):
        with self.assertRaisesRegex(
            ValueError,
            "archivo seleccionado como Banco.*Concepto / Referencia",
        ):
            validar_columnas(
                pd.DataFrame([{"Abono": 325, "Saldo": 1000}]),
                self.ventas,
            )

    def test_identifies_empty_file_role(self):
        with self.assertRaisesRegex(
            ValueError,
            "seleccionado como Banco no contiene",
        ):
            validar_archivos(pd.DataFrame(), self.ventas)


if __name__ == "__main__":
    unittest.main()
