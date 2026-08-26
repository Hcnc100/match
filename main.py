from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import logging
import tempfile
import os
import uuid
from zipfile import BadZipFile
from fastapi.middleware.cors import CORSMiddleware
from app.services.conciliador import procesar_conciliacion


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


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


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}
