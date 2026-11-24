"""
Reglas de calidad del proyecto Respawn (componente reutilizable).

Se usan desde el notebook 02_silver_calidad y desde los tests automáticos (tests/test_reglas_calidad.py),
de modo que la lógica que se prueba es exactamente la misma que se ejecuta en el pipeline.

Columnas que necesita el DataFrame de eventos (ya limpio y aplanado):
    id_evento, id_jugador, tipo_evento, ts_evento, duracion_seg, puntuacion, bajas, id_articulo, importe_eur
"""
from pyspark.sql import DataFrame, functions as F

# Orden = prioridad del motivo principal
DESCRIPCION_REGLAS = {
    "R1_id_nulo": "id_evento o id_jugador nulo",
    "R2_fecha_futura": "ts_evento nulo o en el futuro",
    "R3_puntuacion_imposible": "partida con puntuacion > duracion_seg * 5 o más de 60 bajas",
    "R4_compra_invalida": "compra con artículo desconocido, importe <= 0 o distinto del precio",
    "R5_jugador_inexistente": "id_jugador que no existe en el registro de jugadores",
}
NOMBRES_REGLAS = list(DESCRIPCION_REGLAS)

PUNTOS_MAX_POR_SEGUNDO = 5
BAJAS_MAX = 60


def _condiciones() -> dict:
    return {
        "R1_id_nulo": F.col("id_evento").isNull() | F.col("id_jugador").isNull(),
        "R2_fecha_futura": F.col("ts_evento").isNull() | (F.col("ts_evento") > F.current_timestamp()),
        "R3_puntuacion_imposible": (F.col("tipo_evento") == "fin_partida") & (
            (F.col("puntuacion") > F.col("duracion_seg") * PUNTOS_MAX_POR_SEGUNDO)
            | (F.col("bajas") > BAJAS_MAX)),
        "R4_compra_invalida": (F.col("tipo_evento") == "compra") & (
            F.col("_precio").isNull() | (F.col("importe_eur") <= 0)
            | (F.col("importe_eur") != F.col("_precio"))),
        "R5_jugador_inexistente": F.col("id_jugador").isNotNull() & F.col("_jugador_conocido").isNull(),
    }


def evaluar_reglas(eventos: DataFrame, jugadores_conocidos: DataFrame, precios: DataFrame) -> DataFrame:
    """Añade `reglas_incumplidas` (array con todas las reglas que falla el evento) y
    `motivo` (la primera por prioridad, o NULL si el evento es válido).

    jugadores_conocidos: DataFrame con la columna id_jugador.
    precios: DataFrame con las columnas id_articulo y precio_eur.
    """
    jug = jugadores_conocidos.select(F.col("id_jugador").alias("_jugador_conocido")).distinct()
    pre = precios.select(F.col("id_articulo").alias("_articulo"), F.col("precio_eur").alias("_precio"))

    evaluados = (eventos
                 .join(F.broadcast(jug), eventos.id_jugador == jug._jugador_conocido, "left")
                 .join(F.broadcast(pre), eventos.id_articulo == pre._articulo, "left"))

    incumplidas = F.array_compact(F.array(*[F.when(c, F.lit(n)) for n, c in _condiciones().items()]))
    return (evaluados
            .withColumn("reglas_incumplidas", incumplidas)
            # Con ANSI activado (serverless), element_at falla con un array vacío → se protege con when
            .withColumn("motivo", F.when(F.size("reglas_incumplidas") > 0,
                                         F.element_at("reglas_incumplidas", 1)))
            .drop("_jugador_conocido", "_articulo", "_precio"))
