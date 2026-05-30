# Conciliación Banco vs Ventas

Script en Python para realizar conciliación entre movimientos bancarios y registros de ventas mediante coincidencia de montos y búsqueda de datos dentro del concepto bancario.

## Funcionalidades

- Comparación por monto.
- Búsqueda de coincidencias mediante:
  - Correo
  - Nombre
  - Razón Social
  - Referencia Bancaria
- Soporte para coincidencias difusas (fuzzy matching).
- Generación de archivo Excel con resultados.
- Resaltado de coincidencias mediante colores.
- Inclusión del valor exacto que generó el match.
- Inclusión del score de similitud.
- Opción para omitir la primera fila de los archivos Excel.

---

## Requisitos

- Python 3.10 o superior

Se recomienda trabajar dentro de un entorno virtual (`venv`) para evitar conflictos con otras dependencias instaladas en el equipo.

---

## Crear entorno virtual

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Instalación de dependencias

Las dependencias se encuentran definidas en el archivo:

```text
requirements.txt
```

Instalar:

```bash
pip install -r requirements.txt
```

---

## Dependencias principales

- pandas
- openpyxl
- rapidfuzz

---

## Ejecución

### Lectura normal (encabezados en la primera fila)

```bash
python main.py --banco banco.xlsx --ventas ventas.xlsx --salida resultado.xlsx
```

### Omitiendo la primera fila

Utiliza esta opción cuando los encabezados reales se encuentren en la segunda fila del archivo Excel.

```bash
python main.py --banco banco.xlsx --ventas ventas.xlsx --salida resultado.xlsx --omitir-primera-fila
```

---

## Parámetros

| Parámetro             | Descripción                                                 | Obligatorio |
| --------------------- | ----------------------------------------------------------- | ----------- |
| --banco               | Archivo Excel del banco                                     | Sí          |
| --ventas              | Archivo Excel de ventas                                     | Sí          |
| --salida              | Archivo Excel de salida                                     | No          |
| --omitir-primera-fila | Ignora la primera fila y utiliza la segunda como encabezado | No          |

Si no se especifica `--salida`, se utilizará:

```text
banco_resultado.xlsx
```

---

## Ejemplos

### Lectura estándar

```bash
python main.py --banco banco.xlsx --ventas ventas.xlsx
```

### Lectura omitiendo primera fila

```bash
python main.py --banco banco.xlsx --ventas ventas.xlsx --omitir-primera-fila
```

### Salida personalizada

```bash
python main.py --banco estado_cuenta.xlsx --ventas ventas_mayo.xlsx --salida conciliacion_mayo.xlsx --omitir-primera-fila
```

---

## Archivos de entrada

### Banco

El archivo debe contener al menos las columnas:

```text
Abono
Concepto / Referencia
# CFDI
Saldo
```

### Ventas

El archivo debe contener al menos las columnas:

```text
Monto
FOLIO CONTROL
Correo
Nombre
Razon social
```

Opcionalmente:

```text
Referencia Bancaria
```

---

## Resultado

El proceso genera un archivo Excel con nuevas columnas:

| Columna             | Descripción                              |
| ------------------- | ---------------------------------------- |
| FOLIO_CONTROL_MATCH | Folio encontrado                         |
| TIPO_MATCH          | Tipo de coincidencia encontrada          |
| VALOR_MATCH         | Valor exacto que produjo el match        |
| SCORE_MATCH         | Score o porcentaje de similitud obtenido |

---

## Tipos de Match

| Tipo                | Descripción                          |
| ------------------- | ------------------------------------ |
| CORREO              | Coincidencia por correo              |
| NOMBRE              | Coincidencia por nombre              |
| RAZON_SOCIAL        | Coincidencia por razón social        |
| REFERENCIA_BANCARIA | Coincidencia por referencia bancaria |
| SIN_MATCH           | No se encontró coincidencia          |

---

## Colores utilizados

| Color    | Significado                   |
| -------- | ----------------------------- |
| Verde    | Match por correo              |
| Amarillo | Match por nombre              |
| Azul     | Match por razón social        |
| Rojo     | Match por referencia bancaria |
| Gris     | Sin coincidencia              |

Las columnas agregadas por el proceso se resaltan en amarillo para facilitar su identificación.

---

## Generar requirements.txt

Si se agregan nuevas dependencias al proyecto:

```bash
pip freeze > requirements.txt
```

---

## Autor

Proyecto de conciliación Banco vs Ventas.
