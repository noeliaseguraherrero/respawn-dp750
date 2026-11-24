# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver y calidad: el "detector de tramposos" (Fase 5 · Bloques C y E)
# MAGIC
# MAGIC Lee de Bronze los eventos del día N, los **limpia**, aplica las **reglas de calidad** y separa:
# MAGIC
# MAGIC ```
# MAGIC bronze.eventos_raw (día N)
# MAGIC         │  limpieza: aplanar `detalle`, tipos, normalizar texto, derivar fecha/hora
# MAGIC         │  R6: deduplicar por id_evento
# MAGIC         ▼
# MAGIC   Reglas de calidad R1–R5
# MAGIC         ├── válidos ───► silver.eventos  ──► silver.fact_partidas / silver.fact_compras
# MAGIC         └── inválidos ─► quality.rechazos (con el motivo)
# MAGIC                          quality.metricas_calidad (recuento por regla y día)
# MAGIC ```
# MAGIC
# MAGIC | Regla | Condición para ser válido | Qué detecta |
# MAGIC |---|---|---|
# MAGIC | R1 | `id_evento` e `id_jugador` no nulos | Registros incompletos o corruptos |
# MAGIC | R2 | `ts_evento` no está en el futuro | Relojes manipulados |
# MAGIC | R3 | `puntuacion <= duracion_seg * 5` y `bajas <= 60` | 🕹️ Puntuaciones imposibles (tramposos) |
# MAGIC | R4 | Compra con `importe_eur > 0` e igual al precio del artículo | 💰 Compras fraudulentas |
# MAGIC | R5 | `id_jugador` existe en el registro de jugadores | Jugadores fantasma |
# MAGIC | R6 | Un solo registro por `id_evento` | Duplicados por reconexión |
# MAGIC
# MAGIC **Idempotente**: si se ejecuta dos veces el mismo día, el resultado no cambia (MERGE por clave y sustitución de los rechazos del día).

# COMMAND ----------

dbutils.widgets.dropdown("dia", "1", ["1", "2", "3"], "Día de juego a procesar")
DIA = int(dbutils.widgets.get("dia"))
C = "respawn"
print(f"Procesando Silver del día {DIA}")

# COMMAND ----------

from pyspark.sql import functions as F, Window

def existe(tabla: str) -> bool:
    return spark.catalog.tableExists(tabla)

def merge_o_crear(df, tabla: str, claves: list[str], actualizar: bool = False) -> None:
    """Escritura incremental: crea la tabla la primera vez y después hace MERGE por la clave de negocio.
    WITH SCHEMA EVOLUTION: si el origen trae una columna nueva (schema drift, p. ej. version_juego), se añade a la tabla.
    Con actualizar=False solo inserta las filas nuevas (los eventos no cambian una vez registrados)."""
    if not existe(tabla):
        df.write.saveAsTable(tabla)
        return
    df.createOrReplaceTempView("_origen")
    condicion = " AND ".join(f"t.{c} <=> s.{c}" for c in claves)
    clausula_update = "WHEN MATCHED THEN UPDATE SET *" if actualizar else ""
    spark.sql(f"""
        MERGE WITH SCHEMA EVOLUTION INTO {tabla} t
        USING _origen s
        ON {condicion}
        {clausula_update}
        WHEN NOT MATCHED THEN INSERT *
    """)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Dimensión de artículos (SCD Tipo 1)
# MAGIC El catálogo de la tienda se sobrescribe si cambia un precio: no necesitamos historial.

# COMMAND ----------

dim_articulo = (spark.table(f"{C}.bronze.articulos_raw")
                .select(F.trim("id_articulo").alias("id_articulo"),
                        F.trim("nombre").alias("nombre"),
                        F.lower(F.trim("categoria")).alias("categoria"),
                        F.col("precio_eur").cast("decimal(10,2)").alias("precio_eur"))
                .dropDuplicates(["id_articulo"]))
merge_o_crear(dim_articulo, f"{C}.silver.dim_articulo", ["id_articulo"], actualizar=True)
display(spark.table(f"{C}.silver.dim_articulo"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Limpieza de los eventos del día

# COMMAND ----------

bronze = spark.table(f"{C}.bronze.eventos_raw").filter(F.col("_dia_carga") == DIA)
leidos = bronze.count()

eventos = (bronze.select(
        F.trim("id_evento").alias("id_evento"),
        F.trim("id_jugador").alias("id_jugador"),
        F.lower(F.trim("tipo_evento")).alias("tipo_evento"),                  # normalización
        F.try_to_timestamp(F.col("ts_evento").cast("string")).alias("ts_evento"),  # tipo correcto (null si no es válida)
        F.trim("id_sesion").alias("id_sesion"),
        F.trim("plataforma").alias("plataforma"),
        F.col("detalle.id_partida").alias("id_partida"),                       # aplanar el struct
        F.col("detalle.duracion_seg").cast("int").alias("duracion_seg"),
        F.col("detalle.puntuacion").cast("int").alias("puntuacion"),
        F.col("detalle.bajas").cast("int").alias("bajas"),
        F.col("detalle.id_articulo").alias("id_articulo"),
        F.col("detalle.importe_eur").cast("decimal(10,2)").alias("importe_eur"),
        F.col("detalle.nuevo_rango").alias("nuevo_rango"),
        # schema drift: version_juego solo existe desde el día 3 (en días anteriores queda NULL)
        (F.col("version_juego") if "version_juego" in bronze.columns else F.lit(None).cast("string")).alias("version_juego"),
        "_fichero_origen", "_fecha_ingesta", "_dia_carga")
    .withColumn("fecha_evento", F.to_date("ts_evento"))                        # columnas derivadas
    .withColumn("hora_evento", F.hour("ts_evento")))

# R6 · Deduplicación: nos quedamos con la primera aparición de cada id_evento
ventana = Window.partitionBy("id_evento").orderBy("_fecha_ingesta", "_fichero_origen")
eventos = eventos.withColumn("_n", F.row_number().over(ventana))
duplicados = eventos.filter("_n > 1 AND id_evento IS NOT NULL").count()
eventos = eventos.filter("_n = 1 OR id_evento IS NULL").drop("_n")
print(f"Leídos: {leidos} · duplicados eliminados (R6): {duplicados}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Reglas de calidad
# MAGIC Cada registro guarda **todas** las reglas que incumple y un **motivo principal** (la primera, en orden de prioridad).

# COMMAND ----------

# Las reglas viven en src/reglas_calidad.py (componente reutilizable y probado con pytest)
import os, sys
sys.path.append(os.path.dirname(os.getcwd()))          # raíz del repositorio (Git folder)
from src.reglas_calidad import evaluar_reglas, NOMBRES_REGLAS, DESCRIPCION_REGLAS
reglas = NOMBRES_REGLAS

# Jugadores conocidos hasta el día N (registro de jugadores en Bronze) y precios del catálogo
jugadores = (spark.table(f"{C}.bronze.jugadores_raw")
             .filter(F.col("_dia_carga") <= DIA)
             .select(F.trim("id_jugador").alias("id_jugador")))
precios = spark.table(f"{C}.silver.dim_articulo").select("id_articulo", "precio_eur")

evaluados = evaluar_reglas(eventos, jugadores, precios)

validos = evaluados.filter("motivo IS NULL").drop("reglas_incumplidas", "motivo")
invalidos = evaluados.filter("motivo IS NOT NULL")
print(f"Válidos: {validos.count()} · rechazados: {invalidos.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Escritura: válidos a Silver, inválidos a cuarentena

# COMMAND ----------

# Válidos → silver.eventos (MERGE por id_evento: un evento ya cargado no se duplica)
merge_o_crear(validos, f"{C}.silver.eventos", ["id_evento"])

# Inválidos → quality.rechazos (se sustituyen los del día para que sea idempotente)
rechazos = invalidos.select(
    "id_evento", "id_jugador", "tipo_evento", "motivo", "reglas_incumplidas",
    F.to_json(F.struct("ts_evento", "duracion_seg", "puntuacion", "bajas",
                       "id_articulo", "importe_eur")).alias("detalle_json"),
    "_fichero_origen", "_dia_carga", F.current_timestamp().alias("_fecha_rechazo"))
if existe(f"{C}.quality.rechazos"):
    spark.sql(f"DELETE FROM {C}.quality.rechazos WHERE _dia_carga = {DIA}")
rechazos.write.mode("append").saveAsTable(f"{C}.quality.rechazos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Tablas de hechos (desde los eventos válidos del día)

# COMMAND ----------

fact_partidas = (validos.filter("tipo_evento = 'fin_partida'")
                 .select("id_partida", "id_evento", "id_jugador", "ts_evento", "fecha_evento",
                         "plataforma", "duracion_seg", "puntuacion", "bajas", "_dia_carga"))
merge_o_crear(fact_partidas, f"{C}.silver.fact_partidas", ["id_evento"])

fact_compras = (validos.filter("tipo_evento = 'compra'")
                .join(spark.table(f"{C}.silver.dim_articulo").select("id_articulo", "categoria"),
                      "id_articulo", "left")                                    # join para enriquecer
                .select("id_evento", "id_jugador", "id_articulo", "categoria", "importe_eur",
                        "ts_evento", "fecha_evento", "plataforma", "_dia_carga"))
merge_o_crear(fact_compras, f"{C}.silver.fact_compras", ["id_evento"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Métricas de calidad del día

# COMMAND ----------

por_regla = {r.motivo: r["count"] for r in invalidos.groupBy("motivo").count().collect()}
filas = [(DIA, "leidos", leidos), (DIA, "R6_duplicados", duplicados),
         (DIA, "validos", validos.count()), (DIA, "rechazados", invalidos.count())]
filas += [(DIA, regla, por_regla.get(regla, 0)) for regla in reglas]

metricas = (spark.createDataFrame(filas, "_dia_carga int, metrica string, registros long")
            .withColumn("_fecha_ejecucion", F.current_timestamp()))
if existe(f"{C}.quality.metricas_calidad"):
    spark.sql(f"DELETE FROM {C}.quality.metricas_calidad WHERE _dia_carga = {DIA}")
metricas.write.mode("append").saveAsTable(f"{C}.quality.metricas_calidad")
display(metricas)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Validación frente a lo esperado
# MAGIC El generador de datos sabe exactamente cuántos errores sembró (`resumen_esperado.json`). Si el detector falla, el notebook falla.

# COMMAND ----------

import json
with open("/Volumes/respawn/bronze/raw_files/_staging/resumen_esperado.json", encoding="utf-8") as f:
    esperado = json.load(f)[f"dia_{DIA}"]

errores = esperado.get("errores", {})
comparacion = [("validos", esperado["eventos_validos"], validos.count()),
               ("R6_duplicados", errores.get("R6_duplicados", 0), duplicados)]
comparacion += [(r, errores.get(r, 0), por_regla.get(r, 0)) for r in reglas]

resultado = (spark.createDataFrame(comparacion, "metrica string, esperado long, obtenido long")
             .withColumn("resultado", F.when(F.col("esperado") == F.col("obtenido"), "✅ OK")
                                        .otherwise("❌ DIFERENCIA")))
display(resultado)
assert resultado.filter("resultado != '✅ OK'").count() == 0, "La calidad no coincide con lo esperado"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. 🕹️ Los tramposos detectados

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT _dia_carga, motivo, id_jugador, tipo_evento, detalle_json
# MAGIC FROM respawn.quality.rechazos
# MAGIC ORDER BY _dia_carga, motivo, id_jugador
