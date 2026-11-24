# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Seguridad y gobierno con Unity Catalog (Fase 8 · Bloque B)
# MAGIC
# MAGIC | Medida | Cómo se implementa |
# MAGIC |---|---|
# MAGIC | 1. **Privilegios mínimos** | Los analistas solo tienen `SELECT` sobre vistas de Gold. `GRANT` / `REVOKE` por grupos. |
# MAGIC | 2. **Filtro de filas por región** | Función `fn_region_visible`: un analista de EU solo ve jugadores de EU. |
# MAGIC | 3. **Máscara de columna (PII)** | Función `fn_enmascarar_email`: el email solo se ve completo si se pertenece a `respawn_pii`. |
# MAGIC | 4. **Metadatos** | Comentarios en tablas y columnas, **etiquetas** (`pii`, `capa`, `dominio`), propietario. |
# MAGIC | 5. **Linaje** | Unity Catalog registra el linaje automáticamente (Catalog Explorer → pestaña *Lineage*). |
# MAGIC
# MAGIC ```
# MAGIC Unity Catalog · catálogo respawn
# MAGIC   ├── propietario (ingeniería) ─► todo: bronze, silver, quality, gold
# MAGIC   ├── respawn_analistas_eu ────► SELECT en gold.v_*  → solo filas de EU, email enmascarado
# MAGIC   ├── respawn_analistas_na ────► SELECT en gold.v_*  → solo filas de NA, email enmascarado
# MAGIC   └── respawn_pii ─────────────► además ve el email completo
# MAGIC ```
# MAGIC
# MAGIC **Decisión de diseño — vistas dinámicas en lugar de `ROW FILTER` / `MASK` sobre las tablas**:
# MAGIC las tablas de Silver las escribe el pipeline con `MERGE` (un filtro de filas interferiría con la carga)
# MAGIC y los marts de Gold se recrean en cada ejecución. Las vistas dinámicas aplican las mismas funciones
# MAGIC sin afectar al pipeline y, además, ocultan Bronze y Silver a los analistas.
# MAGIC
# MAGIC **Requisito previo**: crear los grupos `respawn_analistas_eu`, `respawn_analistas_na` y `respawn_pii`
# MAGIC (Settings → Identity and access → Groups).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Funciones de seguridad (filtro de filas y máscara)
# MAGIC `is_account_group_member` comprueba grupos de cuenta y `is_member` grupos del workspace: se usan ambas para que funcione en los dos casos.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION respawn.gold.fn_region_visible(region STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC COMMENT 'Filtro de filas: los analistas regionales solo ven su región; el resto de identidades autorizadas ven todo'
# MAGIC RETURN CASE
# MAGIC   WHEN is_account_group_member('respawn_analistas_eu') OR is_member('respawn_analistas_eu') THEN region = 'EU'
# MAGIC   WHEN is_account_group_member('respawn_analistas_na') OR is_member('respawn_analistas_na') THEN region = 'NA'
# MAGIC   ELSE true
# MAGIC END;
# MAGIC
# MAGIC CREATE OR REPLACE FUNCTION respawn.gold.fn_enmascarar_email(email STRING)
# MAGIC RETURNS STRING
# MAGIC COMMENT 'Máscara de PII: email completo solo para el grupo respawn_pii'
# MAGIC RETURN CASE
# MAGIC   WHEN is_account_group_member('respawn_pii') OR is_member('respawn_pii') THEN email
# MAGIC   ELSE concat(left(email, 1), '***@', split_part(email, '@', 2))
# MAGIC END;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vistas dinámicas para analistas (capa de consumo)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW respawn.gold.v_jugadores_analistas
# MAGIC COMMENT 'Jugadores actuales para analistas: filtrado por región y email enmascarado'
# MAGIC AS SELECT id_jugador, nombre_usuario,
# MAGIC           respawn.gold.fn_enmascarar_email(email) AS email,
# MAGIC           pais, region, rango, nivel, fecha_alta
# MAGIC    FROM respawn.silver.dim_jugador
# MAGIC    WHERE es_actual AND respawn.gold.fn_region_visible(region);
# MAGIC
# MAGIC CREATE OR REPLACE VIEW respawn.gold.v_competitivo_analistas
# MAGIC COMMENT 'Ranking competitivo filtrado por la región del analista'
# MAGIC AS SELECT * FROM respawn.gold.mart_competitivo WHERE respawn.gold.fn_region_visible(region);
# MAGIC
# MAGIC CREATE OR REPLACE VIEW respawn.gold.v_economia_analistas
# MAGIC COMMENT 'Ventas filtradas por la región del analista'
# MAGIC AS SELECT * FROM respawn.gold.mart_economia WHERE respawn.gold.fn_region_visible(region);

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Privilegios: GRANT y REVOKE
# MAGIC Principio de **mínimo privilegio**: para leer una vista hacen falta `USE CATALOG` + `USE SCHEMA` + `SELECT` sobre la vista.
# MAGIC Las vistas leen las tablas con los permisos de su propietario, así que los analistas **no** necesitan acceso a Silver.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Acceso de lectura a la capa de consumo para los dos grupos regionales
# MAGIC GRANT USE CATALOG ON CATALOG respawn TO `respawn_analistas_eu`;
# MAGIC GRANT USE CATALOG ON CATALOG respawn TO `respawn_analistas_na`;
# MAGIC GRANT USE SCHEMA  ON SCHEMA respawn.gold TO `respawn_analistas_eu`;
# MAGIC GRANT USE SCHEMA  ON SCHEMA respawn.gold TO `respawn_analistas_na`;
# MAGIC GRANT SELECT ON VIEW respawn.gold.v_jugadores_analistas   TO `respawn_analistas_eu`;
# MAGIC GRANT SELECT ON VIEW respawn.gold.v_jugadores_analistas   TO `respawn_analistas_na`;
# MAGIC GRANT SELECT ON VIEW respawn.gold.v_competitivo_analistas TO `respawn_analistas_eu`;
# MAGIC GRANT SELECT ON VIEW respawn.gold.v_competitivo_analistas TO `respawn_analistas_na`;
# MAGIC GRANT SELECT ON VIEW respawn.gold.v_economia_analistas    TO `respawn_analistas_eu`;
# MAGIC GRANT SELECT ON VIEW respawn.gold.v_economia_analistas    TO `respawn_analistas_na`;
# MAGIC GRANT EXECUTE ON FUNCTION respawn.gold.fn_region_visible   TO `respawn_analistas_eu`;
# MAGIC GRANT EXECUTE ON FUNCTION respawn.gold.fn_region_visible   TO `respawn_analistas_na`;
# MAGIC GRANT EXECUTE ON FUNCTION respawn.gold.fn_enmascarar_email TO `respawn_analistas_eu`;
# MAGIC GRANT EXECUTE ON FUNCTION respawn.gold.fn_enmascarar_email TO `respawn_analistas_na`;
# MAGIC
# MAGIC -- Demostración de REVOKE: se concede por error SELECT sobre todo el esquema silver y se retira
# MAGIC GRANT  SELECT ON SCHEMA respawn.silver TO `respawn_analistas_eu`;
# MAGIC REVOKE SELECT ON SCHEMA respawn.silver FROM `respawn_analistas_eu`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Permisos efectivos sobre las vistas de consumo
# MAGIC SHOW GRANTS ON VIEW respawn.gold.v_jugadores_analistas;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- El esquema silver no tiene permisos para los analistas (el REVOKE ha funcionado)
# MAGIC SHOW GRANTS ON SCHEMA respawn.silver;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Metadatos: comentarios y etiquetas

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Comentarios de columnas clave
# MAGIC ALTER TABLE respawn.silver.dim_jugador ALTER COLUMN email  COMMENT 'Email del jugador (PII: se expone enmascarado en v_jugadores_analistas)';
# MAGIC ALTER TABLE respawn.silver.dim_jugador ALTER COLUMN region COMMENT 'Región de juego (EU / NA): se usa en el filtro de filas';
# MAGIC ALTER TABLE respawn.silver.eventos     ALTER COLUMN id_evento COMMENT 'Clave de negocio del evento (deduplicación R6)';
# MAGIC ALTER TABLE respawn.quality.rechazos  ALTER COLUMN motivo COMMENT 'Primera regla de calidad incumplida (R1–R5)';
# MAGIC COMMENT ON TABLE respawn.silver.eventos      IS 'Eventos de juego limpios, deduplicados y validados (R1–R6)';
# MAGIC COMMENT ON TABLE respawn.quality.rechazos    IS 'Cuarentena: eventos que incumplen alguna regla de calidad, con el motivo';
# MAGIC COMMENT ON TABLE respawn.bronze.eventos_raw  IS 'Eventos tal y como llegan (JSON) + columnas de auditoría. Ingesta con Auto Loader';
# MAGIC
# MAGIC -- Etiquetas de gobierno (clasificación de datos)
# MAGIC ALTER TABLE respawn.silver.dim_jugador SET TAGS ('dominio' = 'jugadores', 'capa' = 'silver', 'contiene_pii' = 'si');
# MAGIC ALTER TABLE respawn.silver.dim_jugador ALTER COLUMN email SET TAGS ('pii' = 'email');
# MAGIC ALTER TABLE respawn.gold.mart_economia SET TAGS ('dominio' = 'economia', 'capa' = 'gold');
# MAGIC ALTER TABLE respawn.quality.rechazos   SET TAGS ('dominio' = 'calidad', 'capa' = 'quality');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Consultar las etiquetas desde information_schema
# MAGIC SELECT 'tabla' AS nivel, schema_name, table_name, NULL AS column_name, tag_name, tag_value
# MAGIC FROM respawn.information_schema.table_tags
# MAGIC UNION ALL
# MAGIC SELECT 'columna', schema_name, table_name, column_name, tag_name, tag_value
# MAGIC FROM respawn.information_schema.column_tags
# MAGIC ORDER BY nivel DESC, schema_name, table_name

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Propietario, comentario y propiedades de una tabla
# MAGIC DESCRIBE TABLE EXTENDED respawn.silver.dim_jugador

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Demostración del efecto con una sola identidad
# MAGIC
# MAGIC La Free Edition tiene un único usuario, así que la demostración se hace **cambiando la pertenencia a grupos**
# MAGIC del propio usuario y volviendo a ejecutar estas celdas:
# MAGIC
# MAGIC | Escenario | Pertenencia | Resultado esperado |
# MAGIC |---|---|---|
# MAGIC | A | ningún grupo respawn | todas las regiones, email enmascarado |
# MAGIC | B | `respawn_analistas_eu` | solo EU, email enmascarado |
# MAGIC | C | `respawn_analistas_eu` + `respawn_pii` | solo EU, email completo |
# MAGIC
# MAGIC ⚠️ Los cambios de grupo pueden tardar unos minutos en reflejarse.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT current_user() AS usuario,
# MAGIC        is_account_group_member('respawn_analistas_eu') OR is_member('respawn_analistas_eu') AS en_analistas_eu,
# MAGIC        is_account_group_member('respawn_analistas_na') OR is_member('respawn_analistas_na') AS en_analistas_na,
# MAGIC        is_account_group_member('respawn_pii')          OR is_member('respawn_pii')          AS en_pii

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT region, count(*) AS jugadores_visibles
# MAGIC FROM respawn.gold.v_jugadores_analistas
# MAGIC GROUP BY region ORDER BY region

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_jugador, nombre_usuario, email, region, rango
# MAGIC FROM respawn.gold.v_jugadores_analistas
# MAGIC ORDER BY id_jugador LIMIT 5
