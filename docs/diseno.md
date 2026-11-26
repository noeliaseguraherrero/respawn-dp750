# Diseño del proyecto Respawn

## 1. Caso de negocio

*Respawn* es un videojuego online ficticio con jugadores en dos regiones (EU y NA). El estudio necesita saber cuánto se vende en la tienda, si los jugadores vuelven a jugar y quiénes son los mejores. Para eso necesita que los datos no estén contaminados por duplicados, errores ni tramposos.

## 2. Fuentes de datos (sintéticas, generadas con Python + Faker)

Cada "día de juego" (`dia_N`) deja varios ficheros en el volumen `/Volumes/respawn/bronze/raw_files/`.

| Fichero | Formato | Contenido | Frecuencia |
|---|---|---|---|
| `jugadores/jugadores_dia_N.csv` | CSV | Altas y cambios de jugadores | Diaria (incremental) |
| `eventos/eventos_dia_N.json` | JSON Lines | Eventos de juego | Diaria (incremental) |
| `articulos/articulos.csv` | CSV | Catálogo de la tienda | Estática (una vez) |

### jugadores_dia_N.csv
`id_jugador, nombre_usuario, email, pais, region, fecha_alta, rango, nivel, fecha_actualizacion`
(emails ficticios con el dominio `@example.com`)

### eventos_dia_N.json
```json
{"id_evento": "e-000123", "id_jugador": "p-0042", "tipo_evento": "fin_partida",
 "ts_evento": "2026-11-01T18:22:05Z", "id_sesion": "s-9981", "plataforma": "PC",
 "detalle": {"id_partida": "m-5531", "duracion_seg": 900, "puntuacion": 1450, "bajas": 12,
             "id_articulo": null, "importe_eur": null, "nuevo_rango": null}}
```
Tipos de evento: `inicio_sesion`, `fin_partida`, `compra`, `subida_rango`, `cierre_sesion`.

### articulos.csv
`id_articulo, nombre, categoria (skin, arma, pase_batalla, monedas), precio_eur`

## 3. Errores sembrados a propósito

| Día | Qué trae | Qué demuestra |
|---|---|---|
| Día 1 | 100 jugadores y 538 eventos limpios | Carga inicial |
| Día 2 | 12 jugadores nuevos, 5 que suben de rango, 15 eventos duplicados por reconexión y 11 eventos con errores (3 de ellos de **tramposos**) | MERGE, SCD2, reglas de calidad |
| Día 3 | 5 jugadores nuevos, 2 subidas de rango y una columna nueva `version_juego` en los eventos | Schema drift |
| Cualquier día | Con el parámetro `inyectar_error=si`, el Job deja además un JSON roto (`data/sample/errores/eventos_corrupto.json`) | Tratamiento de errores: cuarentena y Repair run |

## 4. Reglas de calidad ("detector de tramposos")

| Regla | Condición válida | Si falla |
|---|---|---|
| R1 Identificadores | `id_evento` e `id_jugador` no nulos | Rechazo |
| R2 Fecha coherente | `ts_evento` no está en el futuro | Rechazo |
| R3 Puntuación imposible | `puntuacion <= duracion_seg * 5` y `bajas <= 60` | Rechazo (tramposo) |
| R4 Compra válida | `importe_eur > 0` y coincide con el precio del artículo | Rechazo (tramposo) |
| R5 Jugador existente | `id_jugador` existe en `dim_jugador` | Rechazo (huérfano) |
| R6 Unicidad | Un solo registro por `id_evento` | Deduplicación (se cuenta en las métricas) |

Los rechazos van a `quality.rechazos` junto con el motivo, y los recuentos de cada ejecución a `quality.metricas_calidad`.

## 5. Unity Catalog: organización y nombres

```
respawn                          (catálogo)
├── bronze
│   ├── raw_files                (VOLUMEN gestionado: _staging/, landing/, _checkpoints/, _cuarentena/)
│   ├── jugadores_raw
│   ├── eventos_raw
│   └── articulos_raw
├── silver
│   ├── eventos                  (limpios y deduplicados)
│   ├── dim_jugador              (SCD Tipo 2: historial de rango, Change Data Feed activado)
│   ├── dim_articulo             (SCD Tipo 1)
│   ├── fact_partidas
│   ├── fact_compras
│   └── control_cargas           (versión Delta de cada día, para el time travel)
├── quality
│   ├── rechazos
│   ├── metricas_calidad
│   └── validaciones_pipeline    (historial de las validaciones de extremo a extremo)
└── gold
    ├── mart_economia            (ventas por día, región, categoría y rango del comprador)
    ├── mart_retencion           (jugadores activos, nuevos y retención de un día para otro)
    ├── mart_competitivo         (ranking global y por región)
    ├── v_jugadores_analistas    (vistas para analistas: filtro por región y email enmascarado)
    ├── v_economia_analistas
    └── v_competitivo_analistas
```

**Convenciones de nombres**
- Todo en `snake_case` y en español.
- Sufijo `_raw` para Bronze; prefijos `dim_` y `fact_` para el modelo dimensional; prefijo `mart_` para Gold; prefijo `v_` para vistas.
- Columnas de auditoría con guion bajo inicial: `_fecha_ingesta`, `_fichero_origen`, `_dia_carga`.
- SCD2: `fecha_inicio_vigencia`, `fecha_fin_vigencia`, `es_actual`.

**Managed frente a external:** todos los objetos son *managed*. Databricks Free Edition no permite configurar *external locations* propias, y las tablas gestionadas dejan a Unity Catalog el ciclo de vida, la optimización y la limpieza. Los ficheros de entrada se guardan en un volumen gestionado.

**Cómputo:** serverless, que es el que ofrece la Free Edition. Arranca en segundos, se factura por uso y no hay que administrar clústeres. Encaja con el caso: cargas pequeñas que se ejecutan una vez al día.

## 6. Modelo dimensional (Silver/Gold)

```
            dim_jugador (SCD2)            dim_articulo
                  │                            │
   fact_partidas ─┤                            ├─ fact_compras
                  │                            │
                  └───────────► gold.mart_* ◄──┘
```

## 7. Flujo (Lakeflow Job `respawn_simular_dia_de_juego`)

```
01_ingesta_bronze → 02_silver_calidad → 03_merge_scd2 → 04_gold_marts → 06_validaciones
```

- Parámetros: `dia` (1, 2, 3) e `inyectar_error` (no / si). Detalle completo en `jobs/configuracion.md`.
- Fuera del Job se ejecutan una sola vez: `05_seguridad_gobierno` (permisos, vistas y etiquetas) y, de forma opcional,
  `07_optimizacion` (medición de liquid clustering + OPTIMIZE) y `99_reiniciar_entorno` (empezar de cero).
