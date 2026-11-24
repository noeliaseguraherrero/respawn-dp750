"""Tests de las reglas de calidad (src/reglas_calidad.py) con Spark local en modo ANSI."""
import json
from datetime import datetime
from decimal import Decimal

import pytest
from pyspark.sql import functions as F

from src.reglas_calidad import NOMBRES_REGLAS, evaluar_reglas

ESQUEMA = ("id_evento string, id_jugador string, tipo_evento string, ts_evento timestamp, "
           "duracion_seg int, puntuacion int, bajas int, id_articulo string, importe_eur decimal(10,2)")
AYER = datetime(2026, 11, 1, 18, 0, 0)
FUTURO = datetime(2031, 1, 1, 12, 0, 0)


@pytest.fixture(scope="module")
def contexto(spark):
    jugadores = spark.createDataFrame([("p-0001",), ("p-0002",)], "id_jugador string")
    precios = spark.createDataFrame([("a-001", Decimal("9.99"))], "id_articulo string, precio_eur decimal(10,2)")
    return jugadores, precios


def motivo(spark, contexto, *fila):
    df = spark.createDataFrame([fila], ESQUEMA)
    return evaluar_reglas(df, *contexto).first()["motivo"]


def test_evento_valido_no_tiene_motivo(spark, contexto):
    assert motivo(spark, contexto, "e1", "p-0001", "fin_partida", AYER, 600, 1200, 10, None, None) is None


def test_compra_valida(spark, contexto):
    assert motivo(spark, contexto, "e2", "p-0001", "compra", AYER, None, None, None, "a-001", Decimal("9.99")) is None


@pytest.mark.parametrize("fila, esperado", [
    (("e3", None, "fin_partida", AYER, 600, 900, 5, None, None), "R1_id_nulo"),
    (("e4", "p-0001", "fin_partida", FUTURO, 600, 900, 5, None, None), "R2_fecha_futura"),
    (("e5", "p-0001", "fin_partida", AYER, 45, 99999, 187, None, None), "R3_puntuacion_imposible"),
    (("e6", "p-0001", "fin_partida", AYER, 600, 900, 61, None, None), "R3_puntuacion_imposible"),
    (("e7", "p-0001", "compra", AYER, None, None, None, "a-001", Decimal("-9.99")), "R4_compra_invalida"),
    (("e8", "p-0001", "compra", AYER, None, None, None, "a-001", Decimal("0.01")), "R4_compra_invalida"),
    (("e9", "p-0001", "compra", AYER, None, None, None, "a-999", Decimal("9.99")), "R4_compra_invalida"),
    (("e10", "p-9999", "fin_partida", AYER, 600, 900, 5, None, None), "R5_jugador_inexistente"),
])
def test_cada_regla_detecta_su_error(spark, contexto, fila, esperado):
    assert motivo(spark, contexto, *fila) == esperado


def test_limite_exacto_de_puntuacion_es_valido(spark, contexto):
    """puntuacion == duracion_seg * 5 sigue siendo válida (la regla es estrictamente mayor)."""
    assert motivo(spark, contexto, "e11", "p-0001", "fin_partida", AYER, 100, 500, 60, None, None) is None


def test_varias_reglas_y_prioridad(spark, contexto):
    """Un tramposo inexistente con fecha futura incumple R2, R3 y R5; el motivo principal es R2."""
    df = spark.createDataFrame([("e12", "p-9999", "fin_partida", FUTURO, 45, 99999, 187, None, None)], ESQUEMA)
    fila = evaluar_reglas(df, *contexto).first()
    assert fila["reglas_incumplidas"] == ["R2_fecha_futura", "R3_puntuacion_imposible", "R5_jugador_inexistente"]
    assert fila["motivo"] == "R2_fecha_futura"


def test_detector_sobre_el_dia_2_generado(spark, datos_generados):
    """Prueba de integración: sobre los datos reales del día 2 se detecta exactamente lo sembrado."""
    resumen = json.loads((datos_generados / "resumen_esperado.json").read_text(encoding="utf-8"))["dia_2"]
    crudos = spark.read.json(str(datos_generados / "dia_2" / "eventos_dia_2.json"))
    eventos = (crudos.dropDuplicates(["id_evento"]).select(
        "id_evento", "id_jugador", "tipo_evento",
        F.to_timestamp("ts_evento").alias("ts_evento"),
        F.col("detalle.duracion_seg").cast("int").alias("duracion_seg"),
        F.col("detalle.puntuacion").cast("int").alias("puntuacion"),
        F.col("detalle.bajas").cast("int").alias("bajas"),
        F.col("detalle.id_articulo").alias("id_articulo"),
        F.col("detalle.importe_eur").cast("decimal(10,2)").alias("importe_eur")))
    jugadores = spark.read.option("header", True).csv(
        [str(datos_generados / f"dia_{d}" / f"jugadores_dia_{d}.csv") for d in (1, 2)]).select("id_jugador")
    precios = (spark.read.option("header", True).csv(str(datos_generados / "articulos" / "articulos.csv"))
               .select("id_articulo", F.col("precio_eur").cast("decimal(10,2)").alias("precio_eur")))

    evaluados = evaluar_reglas(eventos, jugadores, precios)
    por_regla = {r["motivo"]: r["count"] for r in evaluados.groupBy("motivo").count().collect()}
    assert por_regla.pop(None) == resumen["eventos_validos"]
    for regla in NOMBRES_REGLAS:
        assert por_regla.get(regla, 0) == resumen["errores"][regla]
