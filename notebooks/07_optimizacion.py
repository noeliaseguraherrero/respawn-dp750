# Databricks notebook source
# MAGIC %md
# MAGIC # 07 · Optimización medida: liquid clustering + OPTIMIZE (Fase 10 · Bloque G)
# MAGIC
# MAGIC **Problema**: con 1.240 eventos cualquier consulta tarda milisegundos, así que no se puede medir nada útil.
# MAGIC Para estudiar el comportamiento se crea una **tabla de pruebas** con millones de eventos sintéticos
# MAGIC (`silver.eventos_bench`, mismo esquema que el uso real) escrita *a propósito* de forma poco eficiente:
# MAGIC **muchos ficheros pequeños** y los datos de cada jugador **repartidos por todos ellos**.
# MAGIC
# MAGIC **Consulta representativa** (la típica de un analista o del soporte del juego):
# MAGIC *"¿qué ha hecho el jugador X entre dos fechas?"* → filtro por `id_jugador` + `fecha_evento`.
# MAGIC
# MAGIC ```
# MAGIC ANTES  ─ 200 ficheros, datos desordenados ─► la consulta tiene que abrir casi todos los ficheros
# MAGIC          ALTER TABLE ... CLUSTER BY (id_jugador, fecha_evento) + OPTIMIZE
# MAGIC DESPUÉS ─ pocos ficheros, datos agrupados  ─► data skipping: se leen solo los ficheros del jugador
# MAGIC ```
# MAGIC
# MAGIC Se mide: **ficheros de la tabla**, **ficheros que contienen al jugador** (los que hay que leer),
# MAGIC **tiempo** (mediana de 3 ejecuciones con jugadores distintos para no reutilizar resultados en caché)
# MAGIC y el **Query Profile** de la consulta (enlace *See performance* de las celdas SQL).
# MAGIC
# MAGIC ⚠️ No se ejecuta `VACUUM`: borraría los ficheros antiguos y con ellos el *time travel* a las versiones previas.

# COMMAND ----------

dbutils.widgets.dropdown("millones_filas", "10", ["1", "5", "10"], "Millones de filas de la tabla de pruebas")
N = int(dbutils.widgets.get("millones_filas")) * 1_000_000
BENCH = "respawn.silver.eventos_bench"
JUGADORES = 5000

import time, statistics
from pyspark.sql import functions as F

try:   # caché de disco desactivada para que las mediciones no dependan de lecturas previas (si el entorno lo permite)
    spark.conf.set("spark.databricks.io.cache.enabled", "false")
except Exception as e:
    print("No se puede desactivar la caché de disco en serverless:", type(e).__name__)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Tabla de pruebas "mal escrita" (estado inicial)
# MAGIC `optimizeWrite` y `autoCompact` desactivados para que Databricks no compacte los ficheros por su cuenta.

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {BENCH}")
spark.sql(f"""
CREATE TABLE {BENCH} (
  id_evento BIGINT, id_jugador STRING, tipo_evento STRING, fecha_evento DATE,
  plataforma STRING, puntuacion INT, bajas INT, importe_eur DECIMAL(10,2)
)
COMMENT 'Tabla de pruebas de rendimiento (no forma parte del pipeline)'
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'false', 'delta.autoOptimize.autoCompact' = 'false')
""")

tipos = F.array(*[F.lit(t) for t in ["inicio_sesion", "fin_partida", "fin_partida", "compra", "cierre_sesion"]])
plataformas = F.array(*[F.lit(p) for p in ["PC", "PlayStation", "Xbox", "Switch"]])

def aleatorio(semilla: str, n: int):
    """Entero pseudoaleatorio reproducible en [0, n): hash del id con una semilla distinta por columna,
    para que las columnas sean independientes entre sí (con id*k % n saldrían correlacionadas)."""
    return F.pmod(F.xxhash64(F.col("id"), F.lit(semilla)), F.lit(n)).cast("int")

datos = (spark.range(N)
         .select(F.col("id").alias("id_evento"),
                 F.format_string("p-%04d", aleatorio("jugador", JUGADORES)).alias("id_jugador"),
                 F.element_at(tipos, aleatorio("tipo", 5) + 1).alias("tipo_evento"),
                 F.date_add(F.lit("2026-01-01").cast("date"), aleatorio("fecha", 300)).alias("fecha_evento"),
                 F.element_at(plataformas, aleatorio("plataforma", 4) + 1).alias("plataforma"),
                 aleatorio("puntuacion", 5000).alias("puntuacion"),
                 aleatorio("bajas", 40).alias("bajas"),
                 (aleatorio("importe", 2500) / 100).cast("decimal(10,2)").alias("importe_eur"))
         .repartition(200))                                   # 200 ficheros con jugadores mezclados
datos.write.mode("append").saveAsTable(BENCH)
print(f"Tabla de pruebas creada con {N:,} filas")

# COMMAND ----------

def medir(etapa: str) -> dict:
    detalle = spark.sql(f"DESCRIBE DETAIL {BENCH}").first()
    jugadores_prueba = ["p-0042", "p-1234", "p-4321"]
    tiempos = []
    for j in jugadores_prueba:
        inicio = time.perf_counter()
        spark.sql(f"""SELECT tipo_evento, count(*) AS eventos, avg(puntuacion) AS media
                      FROM {BENCH}
                      WHERE id_jugador = '{j}' AND fecha_evento BETWEEN '2026-03-01' AND '2026-05-31'
                      GROUP BY tipo_evento""").collect()
        tiempos.append(time.perf_counter() - inicio)
    ficheros_jugador = spark.sql(f"""SELECT count(DISTINCT _metadata.file_path) FROM {BENCH}
                                     WHERE id_jugador = 'p-0042'
                                       AND fecha_evento BETWEEN '2026-03-01' AND '2026-05-31'""").first()[0]
    return {"etapa": etapa, "ficheros_tabla": detalle["numFiles"],
            "tamano_mb": round(detalle["sizeInBytes"] / 1024 / 1024, 1),
            "ficheros_con_el_jugador": ficheros_jugador,
            "tiempo_mediana_s": round(statistics.median(tiempos), 3),
            "clustering": str(detalle["clusteringColumns"])}

antes = medir("ANTES")
display(spark.createDataFrame([antes]))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Consulta ANTES (abrir *See performance* → Query Profile para ver ficheros leídos y podados)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT tipo_evento, count(*) AS eventos, avg(puntuacion) AS media
# MAGIC FROM respawn.silver.eventos_bench
# MAGIC WHERE id_jugador = 'p-0777' AND fecha_evento BETWEEN '2026-03-01' AND '2026-05-31'
# MAGIC GROUP BY tipo_evento

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Optimización: liquid clustering + OPTIMIZE
# MAGIC - `CLUSTER BY (id_jugador, fecha_evento)`: las columnas por las que se filtra. *Liquid clustering* sustituye
# MAGIC   al particionado clásico y al Z-ORDER: no crea carpetas por valor y se puede cambiar sin reescribir la tabla.
# MAGIC - `OPTIMIZE`: compacta los ficheros pequeños y reordena los datos según el clustering, de modo que las
# MAGIC   estadísticas min/max de cada fichero permiten **saltarse** los ficheros que no contienen al jugador.

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE respawn.silver.eventos_bench CLUSTER BY (id_jugador, fecha_evento);
# MAGIC OPTIMIZE respawn.silver.eventos_bench;

# COMMAND ----------

despues = medir("DESPUÉS")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Consulta DESPUÉS (comparar el Query Profile con el de antes)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT tipo_evento, count(*) AS eventos, avg(puntuacion) AS media
# MAGIC FROM respawn.silver.eventos_bench
# MAGIC WHERE id_jugador = 'p-0778' AND fecha_evento BETWEEN '2026-03-01' AND '2026-05-31'
# MAGIC GROUP BY tipo_evento

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Comparación

# COMMAND ----------

def mejora(a, d):
    return f"{(1 - d / a) * 100:.0f} %" if a else "-"

comparacion = spark.createDataFrame([
    ("Ficheros de la tabla", str(antes["ficheros_tabla"]), str(despues["ficheros_tabla"]),
     mejora(antes["ficheros_tabla"], despues["ficheros_tabla"])),
    ("Ficheros que contienen al jugador", str(antes["ficheros_con_el_jugador"]), str(despues["ficheros_con_el_jugador"]),
     mejora(antes["ficheros_con_el_jugador"], despues["ficheros_con_el_jugador"])),
    ("Tiempo de la consulta (mediana, s)", str(antes["tiempo_mediana_s"]), str(despues["tiempo_mediana_s"]),
     mejora(antes["tiempo_mediana_s"], despues["tiempo_mediana_s"])),
    ("Tamaño (MB)", str(antes["tamano_mb"]), str(despues["tamano_mb"]), "-"),
    ("Clustering", antes["clustering"], despues["clustering"], "-"),
], "metrica string, antes string, despues string, reduccion string")
display(comparacion)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Métricas de la operación OPTIMIZE registradas por Delta (ficheros eliminados / añadidos)
# MAGIC SELECT version, operation, operationMetrics.numRemovedFiles, operationMetrics.numAddedFiles,
# MAGIC        operationMetrics.numRemovedBytes, operationMetrics.numAddedBytes
# MAGIC FROM (DESCRIBE HISTORY respawn.silver.eventos_bench)
# MAGIC WHERE operation IN ('OPTIMIZE', 'WRITE', 'CREATE TABLE')
# MAGIC ORDER BY version

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Conclusiones y aplicación al proyecto
# MAGIC - El beneficio principal es el **data skipping**: tras el clustering, los datos de un jugador quedan en muy
# MAGIC   pocos ficheros y la consulta deja de leer la tabla entera. El tiempo absoluto en serverless está influido por
# MAGIC   el arranque y la caché, por eso se mide la mediana de varias ejecuciones y se acompaña de los ficheros leídos.
# MAGIC - Con los datos reales del proyecto (≈1.240 eventos) no compensa: la tabla cabe en un único fichero.
# MAGIC   Si el juego creciera, se aplicaría `CLUSTER BY (id_jugador, fecha_evento)` a `silver.eventos` y
# MAGIC   `silver.fact_partidas`, y se dejaría el mantenimiento a *predictive optimization* de Unity Catalog.
# MAGIC - **Cómputo**: serverless es adecuado para cargas pequeñas e intermitentes como esta (sin clúster encendido
# MAGIC   esperando); un clúster de trabajos dedicado solo compensaría con cargas grandes y constantes.
# MAGIC - Para liberar espacio se puede borrar la tabla de pruebas: `DROP TABLE respawn.silver.eventos_bench`.
