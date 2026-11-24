# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Dimensión de jugadores con SCD Tipo 2 (Fase 6 · Bloque D)
# MAGIC
# MAGIC Cada día llega un fichero con **altas y cambios** de jugadores. No queremos sobrescribir: queremos saber
# MAGIC **qué rango tenía cada jugador en cada momento** (por ejemplo, para saber con qué rango jugó una partida).
# MAGIC
# MAGIC **SCD Tipo 2** → cuando cambia un atributo controlado (`rango`, `nivel`, `region`):
# MAGIC 1. Se **cierra** la versión actual (`es_actual = false`, `fecha_fin_vigencia = fecha del cambio`).
# MAGIC 2. Se **inserta** una versión nueva (`es_actual = true`, `fecha_fin_vigencia = NULL`).
# MAGIC
# MAGIC ```
# MAGIC Día 1   p-0033 │ Plata │ 2026-11-01 → NULL       │ es_actual = true
# MAGIC Día 2   p-0033 │ Plata │ 2026-11-01 → 2026-11-02 │ es_actual = false   ← se cierra
# MAGIC         p-0033 │ Oro   │ 2026-11-02 → NULL       │ es_actual = true    ← versión nueva
# MAGIC ```
# MAGIC
# MAGIC Todo se hace en **un único `MERGE` atómico** (técnica *staged updates*): si algo falla, la tabla no queda a medias.
# MAGIC
# MAGIC Extras de Delta Lake que se demuestran:
# MAGIC - **Clave sustituta** `sk_jugador` con `GENERATED ALWAYS AS IDENTITY`.
# MAGIC - **Change Data Feed**: Delta registra qué filas se insertaron o actualizaron en cada versión.
# MAGIC - **Time travel** (`VERSION AS OF`): comparar la tabla antes y después de cada carga.

# COMMAND ----------

dbutils.widgets.dropdown("dia", "1", ["1", "2", "3"], "Día de juego a procesar")
DIA = int(dbutils.widgets.get("dia"))
DIM = "respawn.silver.dim_jugador"
CONTROL = "respawn.silver.control_cargas"
print(f"SCD2 de jugadores · día {DIA}")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Estructura de la dimensión (se crea solo la primera vez)
# MAGIC CREATE TABLE IF NOT EXISTS respawn.silver.dim_jugador (
# MAGIC   sk_jugador            BIGINT GENERATED ALWAYS AS IDENTITY COMMENT 'Clave sustituta (una por versión)',
# MAGIC   id_jugador            STRING  COMMENT 'Clave de negocio',
# MAGIC   nombre_usuario        STRING,
# MAGIC   email                 STRING,
# MAGIC   pais                  STRING,
# MAGIC   region                STRING,
# MAGIC   fecha_alta            DATE,
# MAGIC   rango                 STRING  COMMENT 'Atributo con historial (SCD2)',
# MAGIC   nivel                 INT     COMMENT 'Atributo con historial (SCD2)',
# MAGIC   hash_atributos        STRING  COMMENT 'Huella de rango, nivel y region para detectar cambios',
# MAGIC   fecha_inicio_vigencia DATE,
# MAGIC   fecha_fin_vigencia    DATE    COMMENT 'NULL si es la versión actual',
# MAGIC   es_actual             BOOLEAN,
# MAGIC   _dia_carga            INT
# MAGIC )
# MAGIC COMMENT 'Dimensión de jugadores con historial de rangos (SCD Tipo 2)'
# MAGIC TBLPROPERTIES (delta.enableChangeDataFeed = true);
# MAGIC
# MAGIC CREATE TABLE IF NOT EXISTS respawn.silver.control_cargas (
# MAGIC   tabla STRING, dia INT, version_delta BIGINT, filas_totales BIGINT, filas_actuales BIGINT, fecha_carga TIMESTAMP
# MAGIC ) COMMENT 'Versión Delta resultante de cada carga diaria (para time travel)';

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Preparar los cambios del día (origen)

# COMMAND ----------

from pyspark.sql import functions as F, Window

origen = (spark.table("respawn.bronze.jugadores_raw")
          .filter(F.col("_dia_carga") == DIA)
          .select(F.trim("id_jugador").alias("id_jugador"),
                  F.trim("nombre_usuario").alias("nombre_usuario"),
                  F.lower(F.trim("email")).alias("email"),
                  F.upper(F.trim("pais")).alias("pais"),
                  F.upper(F.trim("region")).alias("region"),
                  F.to_date(F.col("fecha_alta").cast("string")).alias("fecha_alta"),
                  F.initcap(F.trim("rango")).alias("rango"),
                  F.col("nivel").cast("int").alias("nivel"),
                  F.to_date(F.col("fecha_actualizacion").cast("string")).alias("fecha_actualizacion"),
                  "_dia_carga")
          .filter(F.col("id_jugador").isNotNull())
          .withColumn("hash_atributos", F.sha2(F.concat_ws("|", "rango", F.col("nivel").cast("string"), "region"), 256)))

# Si un jugador aparece varias veces en el mismo fichero, nos quedamos con su última actualización
ultima = Window.partitionBy("id_jugador").orderBy(F.col("fecha_actualizacion").desc())
origen = origen.withColumn("_n", F.row_number().over(ultima)).filter("_n = 1").drop("_n")
origen.createOrReplaceTempView("origen_jugadores")
print("Filas de jugadores en el fichero del día:", origen.count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Antes del MERGE: ¿qué va a pasar?

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   CASE WHEN d.id_jugador IS NULL                THEN '🆕 Jugador nuevo → INSERT'
# MAGIC        WHEN d.hash_atributos <> o.hash_atributos THEN '🔁 Cambio de rango → cerrar versión + INSERT'
# MAGIC        ELSE '⏸️ Sin cambios → no se toca' END AS accion,
# MAGIC   count(*) AS jugadores
# MAGIC FROM origen_jugadores o
# MAGIC LEFT JOIN respawn.silver.dim_jugador d ON d.id_jugador = o.id_jugador AND d.es_actual
# MAGIC GROUP BY ALL ORDER BY accion

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. MERGE SCD Tipo 2 (técnica *staged updates*)
# MAGIC
# MAGIC El origen se "duplica" para los jugadores que cambian:
# MAGIC - Copia con `clave_merge = id_jugador` → coincide con la versión actual y la **cierra**.
# MAGIC - Copia con `clave_merge = NULL` → nunca coincide, así que se **inserta** como versión nueva.

# COMMAND ----------

# MAGIC %sql
# MAGIC MERGE INTO respawn.silver.dim_jugador AS d
# MAGIC USING (
# MAGIC   SELECT o.id_jugador AS clave_merge, o.* FROM origen_jugadores o
# MAGIC   UNION ALL
# MAGIC   SELECT NULL AS clave_merge, o.*
# MAGIC   FROM origen_jugadores o
# MAGIC   JOIN respawn.silver.dim_jugador d
# MAGIC     ON d.id_jugador = o.id_jugador AND d.es_actual AND d.hash_atributos <> o.hash_atributos
# MAGIC ) AS s
# MAGIC ON d.id_jugador = s.clave_merge AND d.es_actual
# MAGIC WHEN MATCHED AND d.hash_atributos <> s.hash_atributos THEN UPDATE SET
# MAGIC   d.es_actual = false,
# MAGIC   d.fecha_fin_vigencia = s.fecha_actualizacion
# MAGIC WHEN NOT MATCHED THEN INSERT
# MAGIC   (id_jugador, nombre_usuario, email, pais, region, fecha_alta, rango, nivel, hash_atributos,
# MAGIC    fecha_inicio_vigencia, fecha_fin_vigencia, es_actual, _dia_carga)
# MAGIC VALUES
# MAGIC   (s.id_jugador, s.nombre_usuario, s.email, s.pais, s.region, s.fecha_alta, s.rango, s.nivel, s.hash_atributos,
# MAGIC    s.fecha_actualizacion, NULL, true, s._dia_carga)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Registrar la versión Delta de esta carga (control de cargas)

# COMMAND ----------

version = spark.sql(f"DESCRIBE HISTORY {DIM} LIMIT 1").first()["version"]
dim = spark.table(DIM)
totales, actuales = dim.count(), dim.filter("es_actual").count()

spark.sql(f"DELETE FROM {CONTROL} WHERE tabla = 'dim_jugador' AND dia = {DIA}")
spark.sql(f"""INSERT INTO {CONTROL} VALUES
              ('dim_jugador', {DIA}, {version}, {totales}, {actuales}, current_timestamp())""")
print(f"Día {DIA} → versión Delta {version} · filas: {totales} · versiones actuales: {actuales}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Validación frente a lo esperado
# MAGIC - Versiones actuales = jugadores dados de alta hasta el día N.
# MAGIC - Versiones cerradas (historial) = cambios de rango acumulados hasta el día N.
# MAGIC - Nunca puede haber dos versiones actuales del mismo jugador.

# COMMAND ----------

import json
with open("/Volumes/respawn/bronze/raw_files/_staging/resumen_esperado.json", encoding="utf-8") as f:
    resumen = json.load(f)

esp_actuales = sum(resumen[f"dia_{d}"]["jugadores_nuevos"] for d in range(1, DIA + 1))
esp_historicas = sum(len(resumen[f"dia_{d}"].get("jugadores_suben_rango", [])) for d in range(1, DIA + 1))
duplicadas = dim.filter("es_actual").groupBy("id_jugador").count().filter("count > 1").count()

comprobaciones = [
    ("versiones actuales (jugadores)", esp_actuales, actuales),
    ("versiones cerradas (historial)", esp_historicas, totales - actuales),
    ("jugadores con 2 versiones actuales", 0, duplicadas),
]
resultado = (spark.createDataFrame(comprobaciones, "comprobacion string, esperado long, obtenido long")
             .withColumn("resultado", F.when(F.col("esperado") == F.col("obtenido"), "✅ OK")
                                        .otherwise("❌ DIFERENCIA")))
display(resultado)
assert resultado.filter("resultado != '✅ OK'").count() == 0, "La dimensión SCD2 no es correcta"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Evidencias

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Historial de los jugadores que han cambiado de rango
# MAGIC SELECT id_jugador, rango, nivel, fecha_inicio_vigencia, fecha_fin_vigencia, es_actual, sk_jugador
# MAGIC FROM respawn.silver.dim_jugador
# MAGIC WHERE id_jugador IN (SELECT id_jugador FROM respawn.silver.dim_jugador GROUP BY id_jugador HAVING count(*) > 1)
# MAGIC ORDER BY id_jugador, fecha_inicio_vigencia

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Control de cargas: versión Delta que dejó cada día
# MAGIC SELECT * FROM respawn.silver.control_cargas ORDER BY dia

# COMMAND ----------

# MAGIC %md
# MAGIC ### Time travel: la tabla antes y después de esta carga

# COMMAND ----------

if DIA > 1:
    anterior = spark.sql(f"SELECT version_delta FROM {CONTROL} WHERE tabla='dim_jugador' AND dia={DIA-1}").first()
    if anterior:
        v_ant = anterior[0]
        comparacion = spark.sql(f"""
            SELECT coalesce(a.id_jugador, h.id_jugador) AS id_jugador,
                   a.rango AS rango_dia_{DIA-1}, h.rango AS rango_dia_{DIA},
                   CASE WHEN a.id_jugador IS NULL THEN '🆕 nuevo' ELSE '🔁 sube de rango' END AS cambio
            FROM (SELECT * FROM {DIM} VERSION AS OF {v_ant} WHERE es_actual) a
            FULL OUTER JOIN (SELECT * FROM {DIM} WHERE es_actual) h USING (id_jugador)
            WHERE a.rango IS DISTINCT FROM h.rango
            ORDER BY cambio DESC, id_jugador""")
        print(f"Comparando la versión {v_ant} (fin del día {DIA-1}) con la versión actual (fin del día {DIA})")
        display(comparacion)
else:
    print("Día 1: carga inicial, no hay versión anterior con la que comparar")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Change Data Feed: qué filas cambió el último MERGE

# COMMAND ----------

display(spark.sql(f"""
    SELECT _change_type, id_jugador, rango, es_actual, fecha_inicio_vigencia, fecha_fin_vigencia, _commit_version
    FROM table_changes('{DIM}', {version})
    ORDER BY id_jugador, _change_type"""))

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE HISTORY respawn.silver.dim_jugador
