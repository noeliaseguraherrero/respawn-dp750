# Fase 10 · Tests y optimización

## 1. Reglas de calidad como componente reutilizable

Las reglas R1–R5 estaban escritas dentro del notebook `02_silver_calidad`. Se han extraído a
`src/reglas_calidad.py` para poder probarlas fuera de Databricks:

| Elemento | Qué hace |
|---|---|
| `NOMBRES_REGLAS` / `DESCRIPCION_REGLAS` | Lista ordenada de reglas y su descripción (se usa en métricas y rechazos) |
| `evaluar_reglas(eventos, jugadores, precios)` | Añade `reglas_incumplidas` (array) y `motivo` (primera regla incumplida, `null` si es válido) |

El notebook `02` lo importa desde el Git folder (`sys.path` → raíz del repositorio). El Job completo se
volvió a ejecutar tras el cambio y terminó en verde (`docs/capturas/f10_01_job_con_modulo_reglas.png`).

## 2. Tests (pytest)

```bash
pip install -r requirements.txt   # necesita Java 17 para PySpark
python -m pytest tests -v
```

Spark local se arranca con `spark.sql.ansi.enabled=true`, igual que serverless, para detectar los mismos errores.

| Fichero | Tests | Qué comprueba |
|---|---|---|
| `tests/test_generador.py` | 6 | Reproducibilidad con semilla 42, recuentos = `resumen_esperado.json`, errores sembrados del día 2, eventos válidos cumplen las reglas, columna nueva del día 3, fichero corrupto |
| `tests/test_reglas_calidad.py` | 13 | Evento y compra válidos, cada regla R1–R5 detecta su caso, límite exacto de puntuación, varias reglas a la vez y prioridad del motivo, integración con los datos reales del día 2 |

Resultado: **19 passed** (`docs/evidencias/pytest_resultado.txt`).
Integración continua: `.github/workflows/tests.yml` ejecuta los tests en cada push a `main` (pestaña *Actions* de GitHub).

## 3. Optimización medida (`notebooks/07_optimizacion.py`)

Tabla de pruebas `silver.eventos_bench`: 10 M filas sintéticas escritas en 200 ficheros, con
`optimizeWrite` y `autoCompact` desactivados. Consulta: eventos de un jugador entre dos fechas.
Optimización aplicada: `ALTER TABLE ... CLUSTER BY (id_jugador, fecha_evento)` + `OPTIMIZE`.

| Métrica | Antes | Después |
|---|---|---|
| Ficheros de la tabla | 200 | 2 (−99 %) |
| Ficheros que contienen al jugador | 190 | 2 |
| Tamaño | 73,8 MB | 67,8 MB |
| Tiempo de la consulta (mediana de 3) | 0,91 s | 1,0 s |

**Interpretación**
- La compactación funciona: el historial registra `numRemovedFiles = 200`, `numAddedFiles = 2`.
- El tiempo no mejora: con 74 MB domina la sobrecarga fija de serverless, no la lectura. Se documenta tal cual;
  la optimización se nota a partir de gigabytes, cuando la tabla tiene muchos ficheros grandes y el clustering
  permite descartar la mayoría (data skipping).
- En el proyecto real (≈1.240 eventos) no compensa aplicarla; si creciera, se aplicaría a `silver.eventos` y
  `silver.fact_partidas` con mantenimiento por *predictive optimization*.
- No se ejecuta `VACUUM` para no perder el *time travel*.

Captura de CI: `f10_05_github_actions.png` (2 ejecuciones en verde).

Capturas: `f10_02_benchmark_antes.png`, `f10_03_comparacion_antes_despues.png`, `f10_04_historial_optimize.png`.
