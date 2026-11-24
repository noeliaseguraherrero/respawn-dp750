# Databricks notebook source
# MAGIC %md
# MAGIC # 99 · Reiniciar el entorno
# MAGIC
# MAGIC Borra las tablas del proyecto, los checkpoints de Auto Loader y la carpeta `landing/` para
# MAGIC **volver a ejecutar la simulación desde el día 1**. No borra el catálogo, los esquemas ni `_staging`.
# MAGIC
# MAGIC ⚠️ Usar solo para repetir la demostración desde cero.

# COMMAND ----------

dbutils.widgets.dropdown("confirmar", "no", ["no", "si"], "¿Borrar tablas y checkpoints?")
assert dbutils.widgets.get("confirmar") == "si", "Cambia el widget 'confirmar' a 'si' para ejecutar"

# COMMAND ----------

import shutil, os

VOLUMEN = "/Volumes/respawn/bronze/raw_files"

for esquema in ("bronze", "silver", "quality", "gold"):
    for fila in spark.sql(f"SHOW TABLES IN respawn.{esquema}").collect():
        if not fila.isTemporary:
            spark.sql(f"DROP TABLE IF EXISTS respawn.{esquema}.{fila.tableName}")
            print("Borrada:", f"respawn.{esquema}.{fila.tableName}")

for carpeta in ("_checkpoints", "landing"):
    ruta = f"{VOLUMEN}/{carpeta}"
    if os.path.exists(ruta):
        shutil.rmtree(ruta)
        print("Borrada carpeta:", ruta)

for carpeta in ("articulos", "jugadores", "eventos"):
    os.makedirs(f"{VOLUMEN}/landing/{carpeta}", exist_ok=True)
print("Entorno reiniciado")
