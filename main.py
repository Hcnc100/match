from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import logging
import tempfile
import os
from fastapi.middleware.cors import CORSMiddleware

from conciliador import procesar_conciliacion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

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

    with open(banco_path, "wb") as f:
        f.write(await banco.read())

    with open(ventas_path, "wb") as f:
        f.write(await ventas.read())

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


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}