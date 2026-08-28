import logging
import os
import shutil
import threading
import time
import uuid
from zipfile import BadZipFile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Optional

from app.services.conciliador import procesar_conciliacion


logger = logging.getLogger(__name__)


@dataclass
class ConciliationJob:
    id: str
    directory: str
    banco_path: str
    ventas_path: str
    output_path: str
    omitir_primera_fila: bool
    status: str = "queued"
    progress: int = 0
    stage: str = "en_cola"
    message: str = "Conciliación en espera"
    error: Optional[str] = None
    sequence: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def public_data(self):
        data = asdict(self)
        for key in ("directory", "banco_path", "ventas_path", "output_path"):
            data.pop(key)
        data["result_url"] = (
            f"/conciliaciones/{self.id}/resultado"
            if self.status == "completed" else None
        )
        data["events_url"] = f"/conciliaciones/{self.id}/eventos"
        return data


class JobManager:
    def __init__(self, max_workers=2, ttl_seconds=3600):
        self._jobs = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="conciliacion",
        )
        self._ttl_seconds = ttl_seconds

    def create(self, directory, banco_path, ventas_path, omitir_primera_fila):
        self.cleanup_expired()
        job_id = uuid.uuid4().hex
        job = ConciliationJob(
            id=job_id,
            directory=directory,
            banco_path=banco_path,
            ventas_path=ventas_path,
            output_path=os.path.join(directory, "resultado.xlsx"),
            omitir_primera_fila=omitir_primera_fila,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job_id)
        return self.snapshot(job_id)

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def snapshot(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return job.public_data() if job else None

    def _update(self, job_id, progress, stage, message, status="running", error=None):
        with self._lock:
            job = self._jobs[job_id]
            job.progress = max(job.progress, min(100, int(progress)))
            job.stage = stage
            job.message = message
            job.status = status
            job.error = error
            job.sequence += 1
            job.updated_at = time.time()

    def _run(self, job_id):
        job = self.get(job_id)
        if not job:
            return

        try:
            self._update(job_id, 2, "iniciando", "Iniciando conciliación")
            procesar_conciliacion(
                banco=job.banco_path,
                ventas=job.ventas_path,
                salida=job.output_path,
                omitir_primera_fila=job.omitir_primera_fila,
                progreso=lambda progress, stage, message: self._update(
                    job_id, progress, stage, message
                ),
            )
            self._update(
                job_id,
                100,
                "completado",
                "Conciliación lista para descargar",
                status="completed",
            )
        except (ValueError, KeyError, BadZipFile) as error:
            logger.warning("Conciliación inválida job_id=%s: %s", job_id, error)
            self._update(
                job_id,
                100,
                "error",
                str(error).strip("'"),
                status="failed",
                error=str(error).strip("'"),
            )
        except Exception:
            reference = uuid.uuid4().hex[:8]
            logger.exception("Error de conciliación job_id=%s ref=%s", job_id, reference)
            message = f"Ocurrió un error inesperado. Referencia: {reference}."
            self._update(
                job_id,
                100,
                "error",
                message,
                status="failed",
                error=message,
            )

    def cleanup_expired(self):
        limit = time.time() - self._ttl_seconds
        with self._lock:
            expired = [
                job_id for job_id, job in self._jobs.items()
                if job.updated_at < limit and job.status in ("completed", "failed")
            ]
            directories = [self._jobs.pop(job_id).directory for job_id in expired]
        for directory in directories:
            shutil.rmtree(directory, ignore_errors=True)


job_manager = JobManager()
