# Databricks notebook source
# MAGIC %md
# MAGIC # Crear (o actualizar) el Lakeflow Job `respawn_simular_dia_de_juego` (Fase 9 · Bloque F)
# MAGIC
# MAGIC El Job se define **como código** con el SDK de Databricks, así que se puede reproducir desde el repositorio
# MAGIC (si ya existe un Job con ese nombre, se actualiza en lugar de duplicarse).
# MAGIC
# MAGIC ```
# MAGIC 01_ingesta_bronze ─► 02_silver_calidad ─► 03_merge_scd2 ─► 04_gold_marts ─► 06_validaciones
# MAGIC ```
# MAGIC
# MAGIC | Configuración | Valor | Motivo |
# MAGIC |---|---|---|
# MAGIC | Cómputo | Serverless | Único disponible en Free Edition; arranca en segundos y se paga por uso |
# MAGIC | Parámetros | `dia` (1–3), `inyectar_error` (no/si) | Simular cada día de juego y la demo de error |
# MAGIC | Reintentos | 1 reintento en ingesta, Silver, SCD2 y Gold | Fallos transitorios y *schema drift*: Auto Loader detiene el stream al ver una columna nueva y el reintento continúa con el esquema actualizado (práctica recomendada por Databricks) |
# MAGIC | Timeout | 30 min por tarea | Evita ejecuciones colgadas |
# MAGIC | Programación | Diaria 06:00 (Europe/Madrid), **en pausa** | Lista para producción sin consumir recursos |
# MAGIC | Notificaciones | Email al propietario si falla | Monitorización |
# MAGIC | Concurrencia | 1 ejecución a la vez | Evita dos cargas del mismo día en paralelo |

# COMMAND ----------

import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs

w = WorkspaceClient()
NOMBRE = "respawn_simular_dia_de_juego"
yo = w.current_user.me().user_name

# Ruta del repositorio en el workspace: este notebook está en <repo>/jobs
ruta_nb = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
REPO = os.path.dirname(os.path.dirname(ruta_nb))
print("Repositorio:", REPO)

# COMMAND ----------

def tarea(clave: str, depende_de: str | None = None, reintentos: int = 1) -> jobs.Task:
    return jobs.Task(
        task_key=clave,
        description=f"Notebook notebooks/{clave}",
        notebook_task=jobs.NotebookTask(notebook_path=f"{REPO}/notebooks/{clave}",
                                        source=jobs.Source.WORKSPACE),
        depends_on=[jobs.TaskDependency(task_key=depende_de)] if depende_de else None,
        max_retries=reintentos,
        min_retry_interval_millis=30_000,
        timeout_seconds=1800,
    )

configuracion = dict(
    name=NOMBRE,
    description="Simula un día de juego de Respawn: ingesta Bronze → calidad Silver → SCD2 → marts Gold → validaciones",
    tasks=[
        tarea("01_ingesta_bronze", reintentos=1),   # el reintento completa el schema drift de Auto Loader
        tarea("02_silver_calidad", "01_ingesta_bronze"),
        tarea("03_merge_scd2", "02_silver_calidad"),
        tarea("04_gold_marts", "03_merge_scd2"),
        tarea("06_validaciones", "04_gold_marts", reintentos=0),
    ],
    parameters=[
        jobs.JobParameterDefinition(name="dia", default="3"),
        jobs.JobParameterDefinition(name="inyectar_error", default="no"),
    ],
    schedule=jobs.CronSchedule(quartz_cron_expression="0 0 6 * * ?", timezone_id="Europe/Madrid",
                               pause_status=jobs.PauseStatus.PAUSED),
    email_notifications=jobs.JobEmailNotifications(on_failure=[yo]),
    max_concurrent_runs=1,
    tags={"proyecto": "respawn", "certificacion": "dp-750"},
)

# COMMAND ----------

existentes = [j for j in w.jobs.list(name=NOMBRE)]
if existentes:
    job_id = existentes[0].job_id
    w.jobs.reset(job_id=job_id, new_settings=jobs.JobSettings(**configuracion))
    print(f"Job actualizado: {job_id}")
else:
    job_id = w.jobs.create(**configuracion).job_id
    print(f"Job creado: {job_id}")

displayHTML(f'<a href="/jobs/{job_id}" target="_blank">Abrir el Job {NOMBRE}</a>')
