# Lakeflow Job `respawn_simular_dia_de_juego`

El Job se crea desde el repositorio ejecutando el notebook **`jobs/crear_job.py`** en el Git folder de Databricks
(usa el SDK de Databricks; si el Job ya existe, lo actualiza).

## Tareas y dependencias

```
01_ingesta_bronze ─► 02_silver_calidad ─► 03_merge_scd2 ─► 04_gold_marts ─► 06_validaciones
```

| Tarea | Notebook | Reintentos |
|---|---|---|
| 01_ingesta_bronze | Publica el día N, control de ficheros corruptos (cuarentena) y Auto Loader | 0 |
| 02_silver_calidad | Limpieza, reglas R1–R6, rechazos y métricas | 1 |
| 03_merge_scd2 | Dimensión de jugadores SCD2 | 1 |
| 04_gold_marts | Data marts de economía, retención y competitivo | 1 |
| 06_validaciones | Validaciones de extremo a extremo → `quality.validaciones_pipeline` | 0 |

## Parámetros

| Parámetro | Valores | Uso |
|---|---|---|
| `dia` | 1, 2, 3 | Día de juego que se simula |
| `inyectar_error` | no / si | Deja un fichero corrupto en `landing/` para demostrar el tratamiento de errores |

## Otras opciones

- **Cómputo**: serverless.
- **Programación**: diaria a las 06:00 (Europe/Madrid), en pausa.
- **Notificaciones**: email al propietario si el Job falla.
- **Concurrencia máxima**: 1. **Timeout**: 30 minutos por tarea.

## Demostración de error y recuperación

1. Ejecutar con `dia=3` e `inyectar_error=si` → la tarea 01 detecta el fichero corrupto, lo mueve a
   `/Volumes/respawn/bronze/raw_files/_cuarentena/` y falla. Las tareas siguientes no se ejecutan.
2. Pulsar **Repair run** → la tarea 01 ya no encuentra el fichero (está en cuarentena) y el pipeline termina correctamente,
   procesando además el *schema drift* del día 3 (`version_juego`).

## Pasos manuales previos

1. Ejecutar `sql/01_catalogo_y_esquemas.sql` y `notebooks/00_preparar_volumen.py`.
2. Ejecutar `jobs/crear_job.py`.
