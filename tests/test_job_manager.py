import os
import tempfile
import time
import unittest
from unittest.mock import patch

from app.services.job_manager import JobManager


class JobManagerTests(unittest.TestCase):
    def test_reports_monotonic_progress_and_result_url(self):
        directory = tempfile.mkdtemp()
        banco = os.path.join(directory, "banco.xlsx")
        ventas = os.path.join(directory, "ventas.xlsx")
        open(banco, "wb").close()
        open(ventas, "wb").close()
        manager = JobManager(max_workers=1)

        def fake_process(**kwargs):
            kwargs["progreso"](35, "conciliando", "Comparando")
            kwargs["progreso"](80, "generando_excel", "Generando")
            with open(kwargs["salida"], "wb") as output:
                output.write(b"resultado")

        with patch("app.services.job_manager.procesar_conciliacion", fake_process):
            job = manager.create(directory, banco, ventas, True)
            deadline = time.time() + 2
            snapshots = [job]
            while snapshots[-1]["status"] not in ("completed", "failed"):
                self.assertLess(time.time(), deadline)
                snapshots.append(manager.snapshot(job["id"]))
                time.sleep(0.01)

        final = snapshots[-1]
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["progress"], 100)
        self.assertEqual(final["result_url"], f"/conciliaciones/{job['id']}/resultado")
        self.assertTrue(all(
            current["progress"] <= following["progress"]
            for current, following in zip(snapshots, snapshots[1:])
        ))


if __name__ == "__main__":
    unittest.main()
