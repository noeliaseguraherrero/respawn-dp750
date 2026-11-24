"""
Generador de datos sintéticos del proyecto Respawn.

Crea 3 "días de juego" con errores sembrados a propósito para demostrar
la ingesta incremental, las reglas de calidad, el MERGE/SCD2 y el schema drift.

Uso:
    python src/generador_datos.py                 # escribe en data/sample
    python src/generador_datos.py --salida otra/carpeta --semilla 7

Todos los datos son ficticios (emails @example.com). Con la misma semilla,
el resultado es siempre el mismo (reproducible).
"""
import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

RANGOS = ["Bronce", "Plata", "Oro", "Diamante"]
PAISES = {"ES": "EU", "FR": "EU", "DE": "EU", "IT": "EU", "PT": "EU",
          "US": "NA", "CA": "NA", "MX": "NA"}
PLATAFORMAS = ["PC", "PlayStation", "Xbox", "Switch"]
FECHA_DIA_1 = datetime(2026, 11, 1, tzinfo=timezone.utc)

ARTICULOS = [
    ("a-001", "Skin Dragón Carmesí", "skin", 9.99),
    ("a-002", "Skin Ninja Neón", "skin", 7.99),
    ("a-003", "Skin Astronauta Retro", "skin", 12.99),
    ("a-004", "Espada de Plasma", "arma", 4.99),
    ("a-005", "Arco Glacial", "arma", 5.99),
    ("a-006", "Martillo Sísmico", "arma", 6.49),
    ("a-007", "Pase de Batalla T1", "pase_batalla", 14.99),
    ("a-008", "Pase de Batalla Premium T1", "pase_batalla", 24.99),
    ("a-009", "Pack 500 monedas", "monedas", 4.99),
    ("a-010", "Pack 1200 monedas", "monedas", 9.99),
    ("a-011", "Pack 3000 monedas", "monedas", 19.99),
    ("a-012", "Emote Baile Victoria", "skin", 2.99),
]
PRECIOS = {a[0]: a[3] for a in ARTICULOS}

CAMPOS_JUGADOR = ["id_jugador", "nombre_usuario", "email", "pais", "region",
                  "fecha_alta", "rango", "nivel", "fecha_actualizacion"]


class Generador:
    def __init__(self, semilla: int):
        self.rnd = random.Random(semilla)
        self.fake = Faker("es_ES")
        self.fake.seed_instance(semilla)
        self.jugadores = {}      # estado actual de cada jugador
        self.contador_evento = 0
        self.contador_sesion = 0
        self.contador_partida = 0

    # ---------- utilidades ----------
    def _fecha(self, dia: int) -> datetime:
        return FECHA_DIA_1 + timedelta(days=dia - 1)

    def _ts(self, dia: int) -> str:
        base = self._fecha(dia) + timedelta(hours=16)
        ts = base + timedelta(seconds=self.rnd.randint(0, 8 * 3600 - 1))
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _id_evento(self, dia: int) -> str:
        self.contador_evento += 1
        return f"e-d{dia}-{self.contador_evento:06d}"

    def _detalle_vacio(self) -> dict:
        return {"id_partida": None, "duracion_seg": None, "puntuacion": None,
                "bajas": None, "id_articulo": None, "importe_eur": None,
                "nuevo_rango": None}

    def _evento(self, dia, id_jugador, tipo, id_sesion, plataforma, **detalle):
        d = self._detalle_vacio()
        d.update(detalle)
        return {"id_evento": self._id_evento(dia), "id_jugador": id_jugador,
                "tipo_evento": tipo, "ts_evento": self._ts(dia),
                "id_sesion": id_sesion, "plataforma": plataforma, "detalle": d}

    # ---------- jugadores ----------
    def nuevo_jugador(self, num: int, dia: int) -> dict:
        nombre = f"{self.fake.user_name()}{num}"
        pais = self.rnd.choice(list(PAISES))
        fecha = self._fecha(dia).strftime("%Y-%m-%d")
        j = {"id_jugador": f"p-{num:04d}", "nombre_usuario": nombre,
             "email": f"{nombre}@example.com", "pais": pais,
             "region": PAISES[pais], "fecha_alta": fecha,
             "rango": self.rnd.choices(RANGOS, weights=[50, 30, 15, 5])[0],
             "nivel": self.rnd.randint(1, 60), "fecha_actualizacion": fecha}
        self.jugadores[j["id_jugador"]] = j
        return j

    def subir_rango(self, id_jugador: str, dia: int) -> dict | None:
        j = self.jugadores[id_jugador]
        pos = RANGOS.index(j["rango"])
        if pos == len(RANGOS) - 1:
            return None
        j = dict(j, rango=RANGOS[pos + 1], nivel=j["nivel"] + self.rnd.randint(3, 10),
                 fecha_actualizacion=self._fecha(dia).strftime("%Y-%m-%d"))
        self.jugadores[id_jugador] = j
        return j

    # ---------- eventos válidos ----------
    def sesion(self, dia: int, id_jugador: str) -> list[dict]:
        self.contador_sesion += 1
        sid = f"s-{self.contador_sesion:06d}"
        plat = self.rnd.choice(PLATAFORMAS)
        eventos = [self._evento(dia, id_jugador, "inicio_sesion", sid, plat)]
        for _ in range(self.rnd.randint(1, 5)):
            self.contador_partida += 1
            dur = self.rnd.randint(300, 1800)
            eventos.append(self._evento(
                dia, id_jugador, "fin_partida", sid, plat,
                id_partida=f"m-{self.contador_partida:06d}", duracion_seg=dur,
                puntuacion=self.rnd.randint(50, dur * 4), bajas=self.rnd.randint(0, 40)))
        if self.rnd.random() < 0.35:
            art = self.rnd.choice(ARTICULOS)
            eventos.append(self._evento(dia, id_jugador, "compra", sid, plat,
                                        id_articulo=art[0], importe_eur=art[3]))
        eventos.append(self._evento(dia, id_jugador, "cierre_sesion", sid, plat))
        return eventos

    def evento_subida_rango(self, dia, id_jugador, nuevo_rango) -> dict:
        self.contador_sesion += 1
        return self._evento(dia, id_jugador, "subida_rango",
                            f"s-{self.contador_sesion:06d}",
                            self.rnd.choice(PLATAFORMAS), nuevo_rango=nuevo_rango)

    # ---------- eventos con errores (los "tramposos") ----------
    def errores(self, dia: int, validos: list[dict]) -> tuple[list[dict], dict]:
        ids = list(self.jugadores)
        malos, resumen = [], {}

        def base(tipo="fin_partida", jugador=None):
            return self._evento(dia, jugador or self.rnd.choice(ids), tipo,
                                f"s-x{self.rnd.randint(1, 999):03d}", "PC")

        # R1 identificador nulo
        for _ in range(2):
            e = base(); e["id_jugador"] = None; e["detalle"].update(
                id_partida="m-x", duracion_seg=600, puntuacion=900, bajas=5)
            malos.append(e)
        resumen["R1_id_nulo"] = 2
        # R2 fecha en el futuro
        for _ in range(2):
            e = base(); e["ts_evento"] = "2031-01-01T12:00:00Z"
            e["detalle"].update(id_partida="m-x", duracion_seg=600, puntuacion=800, bajas=3)
            malos.append(e)
        resumen["R2_fecha_futura"] = 2
        # R3 puntuación imposible (tramposos)
        tramposos = self.rnd.sample(ids, 3)
        for jid in tramposos:
            e = base(jugador=jid)
            e["detalle"].update(id_partida="m-hack", duracion_seg=45,
                                puntuacion=99999, bajas=187)
            malos.append(e)
        resumen["R3_puntuacion_imposible"] = 3
        resumen["tramposos"] = tramposos
        # R4 compra fraudulenta
        e = base("compra"); e["detalle"].update(id_articulo="a-008", importe_eur=-24.99)
        malos.append(e)
        e = base("compra"); e["detalle"].update(id_articulo="a-008", importe_eur=0.01)
        malos.append(e)
        resumen["R4_compra_invalida"] = 2
        # R5 jugador inexistente
        for _ in range(2):
            e = base(jugador="p-9999")
            e["detalle"].update(id_partida="m-x", duracion_seg=700, puntuacion=1000, bajas=8)
            malos.append(e)
        resumen["R5_jugador_inexistente"] = 2
        # R6 duplicados por reconexión (mismo id_evento repetido)
        duplicados = [json.loads(json.dumps(e)) for e in self.rnd.sample(validos, 15)]
        resumen["R6_duplicados"] = 15
        return malos + duplicados, resumen


def escribir_csv(ruta: Path, filas: list[dict]):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_JUGADOR)
        w.writeheader()
        w.writerows(filas)


def escribir_jsonl(ruta: Path, eventos: list[dict]):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        for e in eventos:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser(description="Genera los datos sintéticos de Respawn")
    p.add_argument("--salida", default="data/sample")
    p.add_argument("--semilla", type=int, default=42)
    args = p.parse_args()
    out = Path(args.salida)
    g = Generador(args.semilla)
    resumen = {"semilla": args.semilla}

    # Catálogo de la tienda (estático)
    out.joinpath("articulos").mkdir(parents=True, exist_ok=True)
    with out.joinpath("articulos", "articulos.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id_articulo", "nombre", "categoria", "precio_eur"])
        w.writerows(ARTICULOS)
    resumen["articulos"] = len(ARTICULOS)

    # ---------------- DÍA 1: carga inicial limpia ----------------
    jug_d1 = [g.nuevo_jugador(n, 1) for n in range(1, 101)]
    ev_d1 = [e for jid in g.jugadores for e in g.sesion(1, jid)]
    escribir_csv(out / "dia_1" / "jugadores_dia_1.csv", jug_d1)
    escribir_jsonl(out / "dia_1" / "eventos_dia_1.json", ev_d1)
    resumen["dia_1"] = {"jugadores_fichero": len(jug_d1), "jugadores_nuevos": 100,
                        "eventos_fichero": len(ev_d1), "eventos_validos": len(ev_d1),
                        "rechazos": 0, "duplicados": 0}

    # ---------------- DÍA 2: incremental + tramposos ----------------
    nuevos = [g.nuevo_jugador(n, 2) for n in range(101, 113)]
    candidatos = [j for j in g.jugadores.values()
                  if j["rango"] != "Diamante" and j["fecha_alta"] == "2026-11-01"]
    suben = [g.subir_rango(j["id_jugador"], 2) for j in g.rnd.sample(candidatos, 5)]
    sin_cambios = g.rnd.sample([g.jugadores[f"p-{n:04d}"] for n in range(1, 101)
                                if g.jugadores[f"p-{n:04d}"] not in suben], 3)
    jug_d2 = nuevos + suben + sin_cambios
    activos = g.rnd.sample(list(g.jugadores), 70)
    ev_validos = [e for jid in activos for e in g.sesion(2, jid)]
    ev_validos += [g.evento_subida_rango(2, j["id_jugador"], j["rango"]) for j in suben]
    ev_malos, errores_d2 = g.errores(2, ev_validos)
    ev_d2 = ev_validos + ev_malos
    g.rnd.shuffle(ev_d2)
    escribir_csv(out / "dia_2" / "jugadores_dia_2.csv", jug_d2)
    escribir_jsonl(out / "dia_2" / "eventos_dia_2.json", ev_d2)
    resumen["dia_2"] = {"jugadores_fichero": len(jug_d2), "jugadores_nuevos": 12,
                        "jugadores_suben_rango": [j["id_jugador"] for j in suben],
                        "jugadores_sin_cambios_repetidos": 3,
                        "eventos_fichero": len(ev_d2), "eventos_validos": len(ev_validos),
                        "errores": errores_d2}

    # ---------------- DÍA 3: schema drift (nueva columna) ----------------
    nuevos3 = [g.nuevo_jugador(n, 3) for n in range(113, 118)]
    # sube por segunda vez → 3 versiones en la SCD2
    repetidor = next(j["id_jugador"] for j in suben if j["rango"] != "Diamante")
    otro = g.rnd.choice([j for j in g.jugadores.values()
                         if j["rango"] in ("Bronce", "Plata") and j not in suben])
    suben3 = [s for s in (g.subir_rango(repetidor, 3), g.subir_rango(otro["id_jugador"], 3)) if s]
    jug_d3 = nuevos3 + suben3
    activos3 = g.rnd.sample(list(g.jugadores), 60)
    ev_d3 = [e for jid in activos3 for e in g.sesion(3, jid)]
    ev_d3 += [g.evento_subida_rango(3, j["id_jugador"], j["rango"]) for j in suben3]
    for e in ev_d3:                          # columna nueva: schema drift
        e["version_juego"] = "1.4.0"
    escribir_csv(out / "dia_3" / "jugadores_dia_3.csv", jug_d3)
    escribir_jsonl(out / "dia_3" / "eventos_dia_3.json", ev_d3)
    resumen["dia_3"] = {"jugadores_fichero": len(jug_d3), "jugadores_nuevos": 5,
                        "jugadores_suben_rango": [j["id_jugador"] for j in suben3],
                        "jugador_con_3_versiones_scd2": repetidor,
                        "eventos_fichero": len(ev_d3), "eventos_validos": len(ev_d3),
                        "columna_nueva": "version_juego"}

    # ---------------- Fichero corrupto (para la demo de errores del Job) ----------------
    corrupto = out / "errores" / "eventos_corrupto.json"
    corrupto.parent.mkdir(parents=True, exist_ok=True)
    corrupto.write_text(
        '{"id_evento": "e-bad-1", "id_jugador": "p-0001", "tipo_evento": "fin_partida"\n'
        'esto no es json\n'
        '{"id_evento": "e-bad-2", "id_jugador": "p-0002", "tipo_evento": "fin_partida", '
        '"ts_evento": "2026-11-03T18:00:00Z", "detalle": {"puntuacion": "mil"}}\n',
        encoding="utf-8")

    with (out / "resumen_esperado.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
