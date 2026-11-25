# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · Validaciones de extremo a extremo (Fase 9 · última tarea del Job)
# MAGIC
# MAGIC Comprueba que **todo el pipeline** cuadra después de procesar el día N, comparando cada capa con
# MAGIC lo que sembró el generador (`resumen_esperado.json`). Los resultados se guardan en
# MAGIC `quality.validaciones_pipeline` (historial de ejecuciones) y, si algo falla, **la tarea falla**
# MAGIC y el Job queda marcado como erróneo.

# COMMAND ----------

dbutils.widgets.dropdown("dia", "1", ["1", "2", "3"], "Último día procesado")
DIA = int(dbutils.widgets.get("dia"))

import json
from pyspark.sql import functions as F

with open("/Volumes/respawn/bronze/raw_files/_staging/resumen_esperado.json", encoding="utf-8") as f:
    R = json.load(f)
dias = [R[f"dia_{d}"] for d in range(1, DIA + 1)]

def n(sql: str):
    return spark.sql(sql).first()[0]

# COMMAND ----------

esperado_validos   = sum(d["eventos_validos"] for d in dias)
esperado_rechazos  = sum(sum(v for k, v in d.get("errores", {}).items() if k[:2] in ("R1", "R2", "R3", "R4", "R5")) for d in dias)
esperado_jugadores = sum(d["jugadores_nuevos"] for d in dias)
esperado_cambios   = sum(len(d.get("jugadores_suben_rango", [])) for d in dias)

comprobaciones = [
    ("bronze", "eventos cargados del día",
     R[f"dia_{DIA}"]["eventos_fichero"],
     n(f"SELECT count(*) FROM respawn.bronze.eventos_raw WHERE _dia_carga = {DIA}")),
    ("silver", "eventos válidos acumulados",
     esperado_validos, n("SELECT count(*) FROM respawn.silver.eventos")),
    ("silver", "sin id_evento duplicados",
     0, n("SELECT count(*) - count(DISTINCT id_evento) FROM respawn.silver.eventos")),
    ("quality", "rechazos acumulados (R1–R5)",
     esperado_rechazos, n("SELECT count(*) FROM respawn.quality.rechazos")),
    ("silver", "jugadores (versiones actuales SCD2)",
     esperado_jugadores, n("SELECT count(*) FROM respawn.silver.dim_jugador WHERE es_actual")),
    ("silver", "versiones históricas SCD2",
     esperado_cambios, n("SELECT count(*) FROM respawn.silver.dim_jugador WHERE NOT es_actual")),
    ("gold", "ingresos gold = ingresos silver",
     str(n("SELECT sum(importe_eur) FROM respawn.silver.fact_compras")),
     str(n("SELECT sum(ingresos_eur) FROM respawn.gold.mart_economia"))),
    ("gold", "partidas gold = partidas silver",
     n("SELECT count(*) FROM respawn.silver.fact_partidas"),
     n("SELECT sum(partidas) FROM respawn.gold.mart_competitivo")),
]
if DIA >= 3:
    comprobaciones += [
        ("silver", "schema drift: version_juego presente en el día 3",
         R["dia_3"]["eventos_validos"],
         n("SELECT count(*) FROM respawn.silver.eventos WHERE version_juego IS NOT NULL")),
        ("silver", "p-0033 tiene 3 versiones (Plata → Oro → Diamante)",
         3, n("SELECT count(*) FROM respawn.silver.dim_jugador WHERE id_jugador = 'p-0033'")),
    ]

resultado = (spark.createDataFrame([(c, t, str(e), str(o)) for c, t, e, o in comprobaciones],
                                   "capa string, comprobacion string, esperado string, obtenido string")
             .withColumn("resultado", F.when(F.col("esperado") == F.col("obtenido"), "OK").otherwise("ERROR"))
             .withColumn("dia", F.lit(DIA))
             .withColumn("fecha_validacion", F.current_timestamp()))
display(resultado)

# COMMAND ----------

# Historial de validaciones (útil para monitorizar el pipeline a lo largo del tiempo)
resultado.write.mode("append").saveAsTable("respawn.quality.validaciones_pipeline")

errores = resultado.filter("resultado != 'OK'").count()
assert errores == 0, f"{errores} validaciones fallidas: revise quality.validaciones_pipeline"
print(f"Pipeline validado hasta el día {DIA}: {len(comprobaciones)} comprobaciones correctas")
