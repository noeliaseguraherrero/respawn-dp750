# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Preparar el volumen de entrada (Fase 3 · Bloque A)
# MAGIC
# MAGIC Copia los datos sintéticos de `data/sample` (incluidos en este Git folder) al volumen
# MAGIC gestionado de Unity Catalog `respawn.bronze.raw_files`.
# MAGIC
# MAGIC Estructura del volumen:
# MAGIC ```
# MAGIC /Volumes/respawn/bronze/raw_files/
# MAGIC ├── _staging/     ← todos los días generados (dia_1, dia_2, dia_3, articulos, errores)
# MAGIC └── landing/      ← lo que el pipeline procesa: cada "día de juego" se publica aquí
# MAGIC     ├── articulos/
# MAGIC     ├── jugadores/
# MAGIC     └── eventos/
# MAGIC ```
# MAGIC Separar `_staging` de `landing` nos permite **simular la llegada diaria** de ficheros:
# MAGIC el Job publica el día N en `landing` y la ingesta incremental solo procesa lo nuevo.
# MAGIC
# MAGIC Requisito previo: haber ejecutado `sql/01_catalogo_y_esquemas.sql`.

# COMMAND ----------

import os
import shutil

VOLUMEN = "/Volumes/respawn/bronze/raw_files"
STAGING = f"{VOLUMEN}/_staging"
LANDING = f"{VOLUMEN}/landing"

# El notebook está en <repo>/notebooks → la raíz del repositorio es la carpeta padre
raiz_repo = os.path.dirname(os.getcwd())
origen = os.path.join(raiz_repo, "data", "sample")
print("Origen :", origen)
print("Destino:", STAGING)
assert os.path.isdir(origen), "No se encuentra data/sample. ¿Has hecho pull del repositorio?"

# COMMAND ----------

# Copia idempotente: si ya existía, se sustituye por la versión del repositorio
if os.path.exists(STAGING):
    shutil.rmtree(STAGING)
shutil.copytree(origen, STAGING, ignore=shutil.ignore_patterns(".gitkeep"))

for carpeta in ("articulos", "jugadores", "eventos"):
    os.makedirs(f"{LANDING}/{carpeta}", exist_ok=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Comprobación: ficheros copiados al volumen

# COMMAND ----------

filas = []
for raiz, _, ficheros in os.walk(VOLUMEN):
    for f in ficheros:
        ruta = os.path.join(raiz, f)
        filas.append((ruta.replace(VOLUMEN + "/", ""), os.path.getsize(ruta)))

display(spark.createDataFrame(sorted(filas), "fichero string, bytes long"))

# COMMAND ----------

# MAGIC %sql
# MAGIC -- También se puede consultar el volumen directamente con SQL
# MAGIC LIST '/Volumes/respawn/bronze/raw_files/_staging/dia_1/'
