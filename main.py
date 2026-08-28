from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import asyncio
import json
import shutil
import time
import logging
import tempfile
import os
import uuid
from zipfile import BadZipFile
from fastapi.middleware.cors import CORSMiddleware
from app.services.conciliador import procesar_conciliacion
from app.services.job_manager import job_manager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def validar_carga_excel(archivo: UploadFile, contenido: bytes, etiqueta: str):
    nombre = archivo.filename or "archivo sin nombre"

    if not nombre.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{etiqueta} ('{nombre}') debe ser un archivo .xlsx. "
                "Los archivos .xls no son compatibles."
            ),
        )

    if not contenido.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{etiqueta} ('{nombre}') no es un archivo Excel válido "
                "o está dañado."
            ),
        )


async def guardar_upload(archivo: UploadFile, destino: str, etiqueta: str):
    nombre = archivo.filename or "archivo sin nombre"
    if not nombre.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail=f"{etiqueta} ('{nombre}') debe ser un archivo .xlsx.",
        )

    total = 0
    firma = b""
    with open(destino, "wb") as salida:
        while bloque := await archivo.read(1024 * 1024):
            if not firma:
                firma = bloque[:4]
            total += len(bloque)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{etiqueta} supera el límite de 50 MB.",
                )
            salida.write(bloque)

    if firma != b"PK\x03\x04":
        raise HTTPException(
            status_code=400,
            detail=f"{etiqueta} ('{nombre}') no es un archivo Excel válido o está dañado.",
        )


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/conciliar")
async def conciliar(
    banco: UploadFile = File(...),
    ventas: UploadFile = File(...),
    omitir_primera_fila: bool = Form(True)
):
    try:
        logger.info(
            "Solicitud recibida. banco=%s ventas=%s omitir_primera_fila=%s",
            banco.filename,
            ventas.filename,
            omitir_primera_fila
        )

        tmp = tempfile.mkdtemp()

        logger.info("Directorio temporal creado: %s", tmp)

        banco_path = os.path.join(tmp, "banco.xlsx")
        ventas_path = os.path.join(tmp, "ventas.xlsx")
        salida_path = os.path.join(tmp, "resultado.xlsx")

        logger.info("Guardando archivos recibidos")

        banco_contenido = await banco.read()
        ventas_contenido = await ventas.read()

        validar_carga_excel(banco, banco_contenido, "Archivo Banco")
        validar_carga_excel(ventas, ventas_contenido, "Archivo Ventas")

        with open(banco_path, "wb") as f:
            f.write(banco_contenido)

        with open(ventas_path, "wb") as f:
            f.write(ventas_contenido)

        logger.info(
            "Archivos guardados. banco=%s ventas=%s",
            banco_path,
            ventas_path
        )

        logger.info("Iniciando conciliación")

        procesar_conciliacion(
            banco=banco_path,
            ventas=ventas_path,
            salida=salida_path,
            omitir_primera_fila=omitir_primera_fila
        )

        logger.info("Conciliación finalizada")

        existe_archivo = os.path.exists(salida_path)

        logger.info(
            "Resultado generado. ruta=%s existe=%s",
            salida_path,
            existe_archivo
        )

        if not existe_archivo:
            logger.error(
                "No se encontró el archivo de salida: %s",
                salida_path
            )
            raise RuntimeError(
                f"No se generó el archivo {salida_path}"
            )

        logger.info(
            "Enviando archivo resultado.xlsx al cliente"
        )

        return FileResponse(
            salida_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="resultado.xlsx"
        )
    except HTTPException:
        raise
    except (ValueError, KeyError, BadZipFile) as error:
        logger.warning(
            "Datos de conciliación inválidos. banco=%s ventas=%s error=%s",
            banco.filename,
            ventas.filename,
            error,
        )
        raise HTTPException(
            status_code=422,
            detail=str(error).strip("'"),
        ) from error
    except Exception as error:
        referencia = uuid.uuid4().hex[:8]
        logger.exception(
            "Error procesando conciliación. referencia=%s banco=%s ventas=%s",
            referencia,
            banco.filename,
            ventas.filename
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Ocurrió un error inesperado al procesar la conciliación. "
                f"Referencia: {referencia}."
            ),
        ) from error


@app.post("/conciliaciones", status_code=202)
async def crear_conciliacion(
    banco: UploadFile = File(...),
    ventas: UploadFile = File(...),
    omitir_primera_fila: bool = Form(True),
):
    tmp = tempfile.mkdtemp(prefix="conciliacion-")
    banco_path = os.path.join(tmp, "banco.xlsx")
    ventas_path = os.path.join(tmp, "ventas.xlsx")
    try:
        await guardar_upload(banco, banco_path, "Archivo Banco")
        await guardar_upload(ventas, ventas_path, "Archivo Ventas")
        return job_manager.create(
            directory=tmp,
            banco_path=banco_path,
            ventas_path=ventas_path,
            omitir_primera_fila=omitir_primera_fila,
        )
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


@app.get("/conciliaciones/{job_id}")
def obtener_conciliacion(job_id: str):
    job = job_manager.snapshot(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Conciliación no encontrada.")
    return job


@app.get("/conciliaciones/{job_id}/eventos")
async def eventos_conciliacion(job_id: str):
    if not job_manager.get(job_id):
        raise HTTPException(status_code=404, detail="Conciliación no encontrada.")

    async def generar_eventos():
        ultima_secuencia = -1
        ultimo_heartbeat = time.monotonic()
        while True:
            estado = job_manager.snapshot(job_id)
            if not estado:
                return
            if estado["sequence"] != ultima_secuencia:
                ultima_secuencia = estado["sequence"]
                yield (
                    f"id: {ultima_secuencia}\n"
                    "event: progreso\n"
                    f"data: {json.dumps(estado, ensure_ascii=False)}\n\n"
                )
                ultimo_heartbeat = time.monotonic()
            elif time.monotonic() - ultimo_heartbeat >= 15:
                yield ": keep-alive\n\n"
                ultimo_heartbeat = time.monotonic()
            if estado["status"] in ("completed", "failed"):
                return
            await asyncio.sleep(0.25)

    return StreamingResponse(
        generar_eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/conciliaciones/{job_id}/resultado")
def descargar_resultado(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Conciliación no encontrada.")
    if job.status == "failed":
        raise HTTPException(status_code=422, detail=job.error)
    if job.status != "completed" or not os.path.exists(job.output_path):
        raise HTTPException(status_code=409, detail="La conciliación todavía no está lista.")
    return FileResponse(
        job.output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="resultado.xlsx",
    )
@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}
