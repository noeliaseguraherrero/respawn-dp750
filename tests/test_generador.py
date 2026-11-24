"""Tests del generador de datos sintéticos: reproducibilidad y errores sembrados."""
import csv
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def leer_eventos(ruta: Path) -> list[dict]:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_es_reproducible(datos_generados, tmp_path):
    """Con la misma semilla se generan exactamente los mismos ficheros."""
    subprocess.run([sys.executable, str(RAIZ / "src" / "generador_datos.py"),
                    "--salida", str(tmp_path), "--semilla", "42"], check=True, capture_output=True)
    for rel in ["dia_1/eventos_dia_1.json", "dia_2/eventos_dia_2.json", "dia_3/jugadores_dia_3.csv"]:
        assert (datos_generados / rel).read_bytes() == (tmp_path / rel).read_bytes()


def test_recuentos_coinciden_con_resumen(datos_generados):
    resumen = json.loads((datos_generados / "resumen_esperado.json").read_text(encoding="utf-8"))
    for dia in (1, 2, 3):
        eventos = leer_eventos(datos_generados / f"dia_{dia}" / f"eventos_dia_{dia}.json")
        with open(datos_generados / f"dia_{dia}" / f"jugadores_dia_{dia}.csv", encoding="utf-8") as f:
            jugadores = list(csv.DictReader(f))
        assert len(eventos) == resumen[f"dia_{dia}"]["eventos_fichero"]
        assert len(jugadores) == resumen[f"dia_{dia}"]["jugadores_fichero"]


def test_dia_2_tiene_los_errores_sembrados(datos_generados):
    resumen = json.loads((datos_generados / "resumen_esperado.json").read_text(encoding="utf-8"))
    eventos = leer_eventos(datos_generados / "dia_2" / "eventos_dia_2.json")
    ids = [e["id_evento"] for e in eventos if e["id_evento"]]
    assert len(ids) - len(set(ids)) == resumen["dia_2"]["errores"]["R6_duplicados"] == 15
    assert sum(e["id_jugador"] is None for e in eventos) == 2                       # R1
    assert sum(e["ts_evento"].startswith("2031") for e in eventos) == 2             # R2
    assert sum(e["detalle"]["puntuacion"] == 99999 for e in eventos) == 3           # R3
    assert sorted(resumen["dia_2"]["errores"]["tramposos"]) == ["p-0007", "p-0022", "p-0051"]


def test_eventos_validos_del_dia_1_cumplen_las_reglas(datos_generados):
    precios = {}
    with open(datos_generados / "articulos" / "articulos.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            precios[fila["id_articulo"]] = float(fila["precio_eur"])
    for e in leer_eventos(datos_generados / "dia_1" / "eventos_dia_1.json"):
        d = e["detalle"]
        if e["tipo_evento"] == "fin_partida":
            assert d["puntuacion"] <= d["duracion_seg"] * 5 and d["bajas"] <= 60
        if e["tipo_evento"] == "compra":
            assert d["importe_eur"] == precios[d["id_articulo"]]


def test_dia_3_trae_columna_nueva(datos_generados):
    eventos = leer_eventos(datos_generados / "dia_3" / "eventos_dia_3.json")
    assert all(e.get("version_juego") == "1.4.0" for e in eventos)


def test_fichero_corrupto_tiene_lineas_no_validas(datos_generados):
    malas = 0
    for linea in (datos_generados / "errores" / "eventos_corrupto.json").read_text(encoding="utf-8").splitlines():
        try:
            json.loads(linea)
        except json.JSONDecodeError:
            malas += 1
    assert malas == 2
