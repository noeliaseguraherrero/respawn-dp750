# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Ingesta Bronze con Auto Loader (Fase 4 · Bloques C y D)
# MAGIC
# MAGIC **Qué hace este notebook**
# MAGIC 1. **Publica el día N**: copia los ficheros de `_staging/dia_N` a `landing/`, simulando que el juego deja los ficheros nuevos del día.
# MAGIC 2. **Ingiere con Auto Loader** (`cloudFiles`) los ficheros de `landing/` en tres tablas Delta Bronze.
# MAGIC 3. **Valida** que el número de filas cargadas coincide con el origen (`resumen_esperado.json`).
# MAGIC
# MAGIC **Por qué Auto Loader**
# MAGIC - Es **incremental**: guarda en un *checkpoint* qué ficheros ya ha procesado, así que cada ejecución solo lee los nuevos (no hay duplicados si se ejecuta dos veces).
# MAGIC - Gestiona la **evolución del esquema** (*schema drift*): cuando el día 3 trae la columna nueva `version_juego`, la añade a la tabla.
# MAGIC - Los valores que no encajan con el tipo esperado no se pierden: van a la columna `_rescued_data`.
# MAGIC - `trigger(availableNow=True)` procesa todo lo pendiente y se detiene, como un batch. Es el modo compatible con serverless.
# MAGIC
# MAGIC Bronze guarda los datos **tal y como llegan** más columnas de auditoría. La limpieza se hace en Silver.

# COMMAND ----------

dbutils.widgets.dropdown("dia", "1", ["1", "2", "3"], "Día de juego a publicar")
dbutils.widgets.dropdown("inyectar_error", "no", ["no", "si"], "Inyectar fichero corrupto (demo)")
DIA = int(dbutils.widgets.get("dia"))
INYECTAR_ERROR = dbutils.widgets.get("inyectar_error") == "si"

CATALOGO = "respawn"
VOLUMEN = "/Volumes/respawn/bronze/raw_files"
STAGING = f"{VOLUMEN}/_staging"
LANDING = f"{VOLUMEN}/landing"
CHECKPOINTS = f"{VOLUMEN}/_checkpoints"

print(f"Procesando el día de juego {DIA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Publicar los ficheros del día en `landing/`

# COMMAND ----------

import shutil, os

publicaciones = [
    (f"{STAGING}/articulos/articulos.csv",             f"{LANDING}/articulos/articulos.csv"),
    (f"{STAGING}/dia_{DIA}/jugadores_dia_{DIA}.csv",  f"{LANDING}/jugadores/jugadores_dia_{DIA}.csv"),
    (f"{STAGING}/dia_{DIA}/eventos_dia_{DIA}.json",   f"{LANDING}/eventos/eventos_dia_{DIA}.json"),
]
for origen, destino in publicaciones:
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if not os.path.exists(destino):          # si ya estaba publicado, no se vuelve a copiar
        shutil.copy(origen, destino)
        print("Publicado:", destino)
    else:
        print("Ya existía:", destino)

# Demostración de errores: se deja además un fichero corrupto en landing
if INYECTAR_ERROR:
    corrupto = f"{LANDING}/eventos/eventos_corrupto_dia_{DIA}.json"
    shutil.copy(f"{STAGING}/errores/eventos_corrupto.json", corrupto)
    print("Aviso: Inyectado fichero corrupto:", corrupto)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1b. Control de entrada: los ficheros JSON corruptos van a cuarentena
# MAGIC Antes de ingerir se comprueba que cada línea de los ficheros de eventos es un JSON válido.
# MAGIC Si un fichero tiene líneas rotas, se **mueve a `_cuarentena/`** y la tarea **falla a propósito**:
# MAGIC el Job se detiene, no se procesan datos parciales y el equipo recibe la notificación.
# MAGIC Una vez apartado el fichero, basta con **reparar la ejecución** (*Repair run*) para continuar.

# COMMAND ----------

import json

CUARENTENA = f"{VOLUMEN}/_cuarentena"

def lineas_corruptas(ruta: str) -> int:
    malas = 0
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                try:
                    json.loads(linea)
                except json.JSONDecodeError:
                    malas += 1
    return malas

apartados = []
for nombre in sorted(os.listdir(f"{LANDING}/eventos")):
    ruta = f"{LANDING}/eventos/{nombre}"
    malas = lineas_corruptas(ruta)
    if malas:
        os.makedirs(CUARENTENA, exist_ok=True)
        shutil.move(ruta, f"{CUARENTENA}/{nombre}")
        apartados.append(f"{nombre} ({malas} líneas no válidas)")

if apartados:
    raise ValueError("Ficheros corruptos enviados a cuarentena: " + ", ".join(apartados)
                     + ". Revise el origen y repare la ejecución.")
print("Todos los ficheros de eventos son JSON válidos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ingesta incremental con Auto Loader
# MAGIC
# MAGIC Una función reutilizable para las tres fuentes. Columnas de auditoría que se añaden:
# MAGIC | Columna | Contenido |
# MAGIC |---|---|
# MAGIC | `_fichero_origen` | Ruta del fichero del que viene la fila (`_metadata.file_path`) |
# MAGIC | `_fecha_ingesta` | Momento en que se cargó |
# MAGIC | `_dia_carga` | Día de juego de la ejecución |

# COMMAND ----------

from pyspark.sql import functions as F

def ingestar(fuente: str, formato: str, tabla: str, opciones: dict | None = None) -> None:
    """Carga de forma incremental landing/<fuente> en respawn.bronze.<tabla>."""
    lector = (spark.readStream.format("cloudFiles")
              .option("cloudFiles.format", formato)
              .option("cloudFiles.schemaLocation", f"{CHECKPOINTS}/{tabla}/esquema")
              .option("cloudFiles.inferColumnTypes", "true")
              .option("cloudFiles.schemaEvolutionMode", "addNewColumns"))
    for clave, valor in (opciones or {}).items():
        lector = lector.option(clave, valor)

    df = (lector.load(f"{LANDING}/{fuente}")
          .withColumn("_fichero_origen", F.col("_metadata.file_path"))
          .withColumn("_fecha_ingesta", F.current_timestamp())
          .withColumn("_dia_carga", F.lit(DIA)))

    consulta = (df.writeStream
                .option("checkpointLocation", f"{CHECKPOINTS}/{tabla}/checkpoint")
                .option("mergeSchema", "true")
                .trigger(availableNow=True)
                .toTable(f"{CATALOGO}.bronze.{tabla}"))
    consulta.awaitTermination()


def ingestar_con_reintento(*args, **kwargs) -> None:
    """Auto Loader detiene el stream cuando detecta una columna nueva (schema drift)
    para que la tabla se actualice de forma controlada. Al relanzarlo, continúa con el esquema nuevo."""
    try:
        ingestar(*args, **kwargs)
    except Exception as e:
        if "UnknownFieldException" in str(e) or "UNKNOWN_FIELD" in str(e):
            print(f"Schema drift detectado en {args[2]}: se añade la columna nueva y se reintenta")
            ingestar(*args, **kwargs)
        else:
            raise

# COMMAND ----------

ESQUEMA_DETALLE = ("detalle STRUCT<id_partida: STRING, duracion_seg: BIGINT, puntuacion: BIGINT, "
                   "bajas: BIGINT, id_articulo: STRING, importe_eur: DOUBLE, nuevo_rango: STRING>")

ingestar_con_reintento("articulos", "csv", "articulos_raw", {"header": "true"})
ingestar_con_reintento("jugadores", "csv", "jugadores_raw", {"header": "true"})
ingestar_con_reintento("eventos", "json", "eventos_raw", {"cloudFiles.schemaHints": ESQUEMA_DETALLE})
print("Ingesta Bronze completada")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Validación: origen frente a Bronze

# COMMAND ----------

import json

with open(f"{STAGING}/resumen_esperado.json", encoding="utf-8") as f:
    esperado = json.load(f)

def contar(tabla, dia):
    return spark.table(f"{CATALOGO}.bronze.{tabla}").filter(F.col("_dia_carga") == dia).count()

resultados = []
for d in range(1, DIA + 1):
    e = esperado[f"dia_{d}"]
    resultados += [
        (d, "jugadores_raw", e["jugadores_fichero"], contar("jugadores_raw", d)),
        (d, "eventos_raw",   e["eventos_fichero"],   contar("eventos_raw", d)),
    ]
resultados.append((0, "articulos_raw", esperado["articulos"],
                   spark.table(f"{CATALOGO}.bronze.articulos_raw").count()))

validacion = (spark.createDataFrame(resultados, "dia int, tabla string, filas_origen long, filas_bronze long")
              .withColumn("resultado", F.when(F.col("filas_origen") == F.col("filas_bronze"), "OK")
                                         .otherwise("DIFERENCIA")))
display(validacion)

assert validacion.filter("resultado != 'OK'").count() == 0, "Bronze no coincide con el origen"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Evidencias

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Filas por fichero y día: cada ejecución solo añade el fichero nuevo
# MAGIC SELECT _dia_carga, regexp_extract(_fichero_origen, '[^/]+$', 0) AS fichero, count(*) AS filas
# MAGIC FROM respawn.bronze.eventos_raw
# MAGIC GROUP BY ALL
# MAGIC ORDER BY _dia_carga

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Historial Delta: una versión nueva (STREAMING UPDATE) por cada ejecución
# MAGIC DESCRIBE HISTORY respawn.bronze.eventos_raw
