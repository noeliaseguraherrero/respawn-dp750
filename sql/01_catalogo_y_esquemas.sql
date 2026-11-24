-- =====================================================================
-- Respawn · Fase 3 · Bloque A: organización en Unity Catalog
-- Ejecutar en el SQL Editor (SQL warehouse serverless) o en un notebook SQL.
-- Es idempotente: se puede ejecutar varias veces sin errores.
-- =====================================================================

-- 1. Catálogo del proyecto
CREATE CATALOG IF NOT EXISTS respawn
COMMENT 'Lakehouse del videojuego ficticio Respawn (proyecto final DP-750)';

USE CATALOG respawn;

-- 2. Esquemas (capas de la arquitectura Medallion + calidad)
CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Datos en bruto tal y como llegan, con columnas de auditoría';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Datos limpios, deduplicados y modelados (dimensiones y hechos)';

CREATE SCHEMA IF NOT EXISTS quality
COMMENT 'Registros rechazados por las reglas de calidad y métricas de cada ejecución';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Data marts listos para el análisis: economía, retención y competitivo';

-- 3. Volumen gestionado para los ficheros de entrada
CREATE VOLUME IF NOT EXISTS bronze.raw_files
COMMENT 'Zona de aterrizaje: _staging (todos los días) y landing (lo que procesa el pipeline)';

-- 4. Comprobaciones
SHOW SCHEMAS IN respawn;
SHOW VOLUMES IN respawn.bronze;
DESCRIBE CATALOG EXTENDED respawn;
