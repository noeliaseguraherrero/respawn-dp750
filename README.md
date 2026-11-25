# Respawn — Lakehouse de un videojuego en Databricks

> Proyecto final de la certificación **Microsoft DP-750: Azure Databricks Data Engineer Associate**.

## 1. Descripción

**Problema:** *Respawn* es un videojuego online ficticio. Cada día genera miles de eventos (inicios de sesión, partidas, compras en la tienda, subidas de rango). Esos datos llegan en bruto, con duplicados por reconexiones, errores y jugadores tramposos que falsean las métricas.

**Solución:** un lakehouse en Databricks que ingiere los datos de forma incremental, detecta y separa los registros inválidos (el "detector de tramposos"), mantiene el historial de rangos de cada jugador y publica 3 data marts listos para analizar.

**Resultado esperado:** tablas fiables y gobernadas en Unity Catalog, actualizadas automáticamente por un Lakeflow Job.

## 2. Arquitectura

_(Pendiente: diagrama en `docs/arquitectura.png`)_

```
Ficheros JSON/CSV (día N) → Volumen UC → Bronze → Silver (+ rechazos) → Gold (3 data marts)
                                       └──────── Lakeflow Job "Simular día de juego" ────────┘
```

## 3. Tecnologías

Databricks Free Edition · Unity Catalog · Delta Lake · PySpark · SQL · Lakeflow Jobs · Python · Git/GitHub

## 4. Instalación y configuración

_(Pendiente)_

## 5. Datos y modelo

_(Pendiente)_

| Capa | Tablas |
|---|---|
| Bronze | eventos y jugadores en bruto |
| Silver | eventos limpios, dimensión jugador (SCD2) |
| Gold | `mart_economia`, `mart_retencion`, `mart_competitivo` |
| Quality | rechazos y métricas de calidad |

## 6. Ejemplos de ejecución

_(Pendiente)_

## 7. Conclusiones

_(Pendiente)_

---

## Estructura del repositorio

```
├── config/          Configuración del proyecto (sin secretos)
├── data/sample/     Datos sintéticos de ejemplo (día 1, 2, 3)
├── docs/            Arquitectura, informe técnico (MD y PDF), capturas
├── notebooks/       Notebooks de Databricks (ingesta, limpieza, MERGE, gold)
├── sql/             Catálogo, seguridad y consultas de validación
├── src/             Funciones reutilizables y generador de datos
├── jobs/            Definición y configuración del Lakeflow Job
├── tests/           Pruebas de calidad
└── presentation/    Presentación del proyecto
```
