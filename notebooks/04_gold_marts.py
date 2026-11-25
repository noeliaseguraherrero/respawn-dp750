# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Gold: los 3 data marts (Fase 7)
# MAGIC
# MAGIC | Data mart | Pregunta de negocio | Grano (una fila por…) |
# MAGIC |---|---|---|
# MAGIC | `gold.mart_economia` | ¿Cuánto vendemos, de qué y a qué tipo de jugador? | día × región × categoría × rango del comprador |
# MAGIC | `gold.mart_retencion` | ¿Cuántos jugadores tenemos y cuántos vuelven? | día |
# MAGIC | `gold.mart_competitivo` | ¿Quiénes son los mejores jugadores? | jugador |
# MAGIC
# MAGIC **Join "point-in-time" con la SCD2**: cada compra se asocia al rango que tenía el jugador
# MAGIC **en la fecha de la compra**, no al rango actual. Por eso guardamos el historial en `dim_jugador`.
# MAGIC
# MAGIC ```sql
# MAGIC f.fecha_evento >= d.fecha_inicio_vigencia
# MAGIC AND (d.fecha_fin_vigencia IS NULL OR f.fecha_evento < d.fecha_fin_vigencia)
# MAGIC ```
# MAGIC
# MAGIC **Estrategia de carga**: los marts se **recalculan completos** (`CREATE OR REPLACE TABLE`) en cada ejecución.
# MAGIC Son agregados pequeños, así que recalcular es barato y garantiza que siempre cuadran con Silver
# MAGIC (no hay riesgo de sumar dos veces un día reprocesado). Delta guarda cada versión en el historial.
# MAGIC Con el modo ANSI de serverless, las divisiones usan `try_divide` para no fallar si el divisor es 0.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. mart_economia

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE respawn.gold.mart_economia
# MAGIC COMMENT 'Ventas de la tienda por día, región, categoría y rango del comprador en el momento de la compra'
# MAGIC AS
# MAGIC SELECT
# MAGIC   f.fecha_evento                                   AS fecha,
# MAGIC   d.region,
# MAGIC   f.categoria,
# MAGIC   d.rango                                          AS rango_comprador,
# MAGIC   count(*)                                         AS num_compras,
# MAGIC   count(DISTINCT f.id_jugador)                     AS compradores_unicos,
# MAGIC   sum(f.importe_eur)                               AS ingresos_eur,
# MAGIC   round(try_divide(sum(f.importe_eur), count(*)), 2) AS ticket_medio_eur
# MAGIC FROM respawn.silver.fact_compras f
# MAGIC JOIN respawn.silver.dim_jugador d
# MAGIC   ON  f.id_jugador = d.id_jugador
# MAGIC   AND f.fecha_evento >= d.fecha_inicio_vigencia
# MAGIC   AND (d.fecha_fin_vigencia IS NULL OR f.fecha_evento < d.fecha_fin_vigencia)
# MAGIC GROUP BY ALL;
# MAGIC
# MAGIC SELECT categoria, sum(num_compras) AS compras, sum(ingresos_eur) AS ingresos_eur
# MAGIC FROM respawn.gold.mart_economia GROUP BY categoria ORDER BY ingresos_eur DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. mart_retencion
# MAGIC **Retención D1** = de los jugadores activos el día anterior, qué porcentaje vuelve a jugar hoy.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE respawn.gold.mart_retencion
# MAGIC COMMENT 'Actividad diaria: jugadores activos, altas, sesiones, partidas y retención D1'
# MAGIC AS
# MAGIC WITH activos AS (
# MAGIC   SELECT DISTINCT fecha_evento AS fecha, id_jugador FROM respawn.silver.eventos
# MAGIC ),
# MAGIC diario AS (
# MAGIC   SELECT fecha_evento AS fecha,
# MAGIC          count(DISTINCT id_jugador)                                        AS jugadores_activos,
# MAGIC          count(DISTINCT id_sesion)                                         AS sesiones,
# MAGIC          count_if(tipo_evento = 'fin_partida')                             AS partidas,
# MAGIC          count_if(tipo_evento = 'compra')                                  AS compras,
# MAGIC          count_if(tipo_evento = 'subida_rango')                            AS subidas_rango
# MAGIC   FROM respawn.silver.eventos GROUP BY fecha_evento
# MAGIC ),
# MAGIC altas AS (
# MAGIC   SELECT fecha_alta AS fecha, count(*) AS jugadores_nuevos
# MAGIC   FROM respawn.silver.dim_jugador WHERE es_actual GROUP BY fecha_alta
# MAGIC ),
# MAGIC retencion AS (
# MAGIC   SELECT hoy.fecha,
# MAGIC          count(ayer.id_jugador)                         AS activos_dia_anterior,
# MAGIC          count(CASE WHEN volvio.id_jugador IS NOT NULL THEN 1 END) AS retenidos
# MAGIC   FROM (SELECT DISTINCT fecha FROM activos) hoy
# MAGIC   JOIN activos ayer ON ayer.fecha = date_sub(hoy.fecha, 1)
# MAGIC   LEFT JOIN activos volvio ON volvio.fecha = hoy.fecha AND volvio.id_jugador = ayer.id_jugador
# MAGIC   GROUP BY hoy.fecha
# MAGIC )
# MAGIC SELECT d.fecha, d.jugadores_activos, coalesce(a.jugadores_nuevos, 0) AS jugadores_nuevos,
# MAGIC        d.sesiones, d.partidas, d.compras, d.subidas_rango,
# MAGIC        r.activos_dia_anterior, r.retenidos,
# MAGIC        round(100 * try_divide(r.retenidos, r.activos_dia_anterior), 1) AS retencion_d1_pct
# MAGIC FROM diario d
# MAGIC LEFT JOIN altas a     ON a.fecha = d.fecha
# MAGIC LEFT JOIN retencion r ON r.fecha = d.fecha;
# MAGIC
# MAGIC SELECT * FROM respawn.gold.mart_retencion ORDER BY fecha;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. mart_competitivo

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE respawn.gold.mart_competitivo
# MAGIC COMMENT 'Estadísticas competitivas por jugador (versión actual) con ranking global y por región'
# MAGIC AS
# MAGIC WITH stats AS (
# MAGIC   SELECT id_jugador,
# MAGIC          count(*)                         AS partidas,
# MAGIC          sum(puntuacion)                  AS puntuacion_total,
# MAGIC          round(avg(puntuacion), 1)        AS puntuacion_media,
# MAGIC          max(puntuacion)                  AS mejor_puntuacion,
# MAGIC          sum(bajas)                       AS bajas_totales,
# MAGIC          round(sum(duracion_seg) / 60, 1) AS minutos_jugados
# MAGIC   FROM respawn.silver.fact_partidas GROUP BY id_jugador
# MAGIC )
# MAGIC SELECT j.id_jugador, j.nombre_usuario, j.region, j.rango AS rango_actual, j.nivel,
# MAGIC        s.partidas, s.puntuacion_total, s.puntuacion_media, s.mejor_puntuacion,
# MAGIC        s.bajas_totales, s.minutos_jugados,
# MAGIC        dense_rank() OVER (ORDER BY s.puntuacion_total DESC)                     AS ranking_global,
# MAGIC        dense_rank() OVER (PARTITION BY j.region ORDER BY s.puntuacion_total DESC) AS ranking_region
# MAGIC FROM stats s
# MAGIC JOIN respawn.silver.dim_jugador j ON j.id_jugador = s.id_jugador AND j.es_actual;
# MAGIC
# MAGIC SELECT ranking_global, id_jugador, nombre_usuario, region, rango_actual, partidas, puntuacion_total
# MAGIC FROM respawn.gold.mart_competitivo WHERE ranking_global <= 10 ORDER BY ranking_global;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Validaciones: Gold cuadra con Silver
# MAGIC Un data mart no debe "inventar" ni "perder" datos al agregar.

# COMMAND ----------

from pyspark.sql import functions as F

def escalar(sql: str):
    return spark.sql(sql).first()[0]

comprobaciones = [
    ("economía: ingresos = suma de fact_compras",
     escalar("SELECT sum(importe_eur) FROM respawn.silver.fact_compras"),
     escalar("SELECT sum(ingresos_eur) FROM respawn.gold.mart_economia")),
    ("economía: cada compra casa con UNA versión del jugador (point-in-time)",
     escalar("SELECT count(*) FROM respawn.silver.fact_compras"),
     escalar("SELECT sum(num_compras) FROM respawn.gold.mart_economia")),
    ("retención: partidas = filas de fact_partidas",
     escalar("SELECT count(*) FROM respawn.silver.fact_partidas"),
     escalar("SELECT sum(partidas) FROM respawn.gold.mart_retencion")),
    ("competitivo: partidas = filas de fact_partidas",
     escalar("SELECT count(*) FROM respawn.silver.fact_partidas"),
     escalar("SELECT sum(partidas) FROM respawn.gold.mart_competitivo")),
    ("competitivo: un jugador por fila",
     escalar("SELECT count(DISTINCT id_jugador) FROM respawn.gold.mart_competitivo"),
     escalar("SELECT count(*) FROM respawn.gold.mart_competitivo")),
]
resultado = (spark.createDataFrame([(n, str(e), str(o)) for n, e, o in comprobaciones],
                                   "comprobacion string, silver string, gold string")
             .withColumn("resultado", F.when(F.col("silver") == F.col("gold"), "OK")
                                        .otherwise("DIFERENCIA")))
display(resultado)
assert resultado.filter("resultado != 'OK'").count() == 0, "Gold no cuadra con Silver"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Consulta de análisis: ¿qué rangos gastan más?
# MAGIC Gracias al join point-in-time, una compra hecha siendo "Plata" cuenta como Plata aunque hoy el jugador sea "Oro".

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT rango_comprador,
# MAGIC        sum(num_compras)                                         AS compras,
# MAGIC        sum(ingresos_eur)                                        AS ingresos_eur,
# MAGIC        round(try_divide(sum(ingresos_eur), sum(num_compras)), 2) AS ticket_medio_eur
# MAGIC FROM respawn.gold.mart_economia
# MAGIC GROUP BY rango_comprador
# MAGIC ORDER BY ingresos_eur DESC
