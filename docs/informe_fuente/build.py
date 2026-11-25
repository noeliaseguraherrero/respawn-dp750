"""Genera docs/proyecto.pdf (informe del proyecto Respawn) a partir de HTML + Chrome headless."""
import subprocess, pathlib, html

BASE = pathlib.Path(__file__).parent
FONTS = BASE / "node_modules/@fontsource"
IMG = BASE / "img"

# ---------- sprites pixel art ----------
SPRITES = {
    "invader": ["..X.....X..", "...X...X...", "..XXXXXXX..", ".XX.XXX.XX.", "XXXXXXXXXXX",
                "X.XXXXXXX.X", "X.X.....X.X", "...XX.XX..."],
    "heart": [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."],
    "coin": ["..XXXX..", ".XX..XX.", "XX.XX.XX", "XX.XX.XX", "XX.XX.XX", "XX.XX.XX", ".XX..XX.", "..XXXX.."],
    "pad": ["..XXXXXXXXXXXX..", ".XXXXXXXXXXXXXX.", "XXX.XXXXXXXX.XXX", "XX...XXXXXX.X.XX",
            "XXX.XXXXXXXX.XXX", "XXXXXXX..XXXXXXX", "XXXXX......XXXXX", ".XXX........XXX."],
    "star": ["...X...", "...X...", ".XXXXX.", "XXXXXXX", ".XXXXX.", ".XX.XX.", "X.....X"],
    "ghost": ["..XXXX..", ".XXXXXX.", "XX.XX.XX", "XX.XX.XX", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", "X.XX.XX."],
    "sword": [".......XX", "......XXX", ".....XXX.", "X...XXX..", ".X.XXX...", "..XXX....", "..XX.....",
              ".X..X....", "X........"],
    "trophy": ["XXXXXXXXX", "X.XXXXX.X", "X.XXXXX.X", ".XXXXXXX.", "...XXX...", "....X....", "...XXX...", "..XXXXX.."],
    "shield": ["XXXXXXX", "XX.X.XX", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."],
    "bug": ["X.....X", ".X...X.", "..XXX..", ".XXXXX.", "XX.X.XX", ".XXXXX.", "X.XXX.X", "..X.X.."],
}


def sprite(nombre, px=4, color="#a855f7", extra=""):
    filas = SPRITES[nombre]
    w, h = len(filas[0]), len(filas)
    rects = "".join(f'<rect x="{x}" y="{y}" width="1.02" height="1.02"/>'
                    for y, f in enumerate(filas) for x, c in enumerate(f) if c == "X")
    return (f'<svg class="sprite {extra}" width="{w*px}" height="{h*px}" viewBox="0 0 {w} {h}" '
            f'shape-rendering="crispEdges" fill="{color}">{rects}</svg>')


def img(nombre, pie, ancho="100%"):
    return (f'<figure class="shot" style="width:{ancho}"><div class="pantalla">'
            f'<img src="img/{nombre}"></div><figcaption>{pie}</figcaption></figure>')


TOTAL = 16
SECCIONES = []


def pagina(num, nivel, titulo, cuerpo, icono=None):
    xp = int(num / TOTAL * 100)
    return f'''
<section class="pagina">
  <header class="hud">
    <span class="px nivel">NIVEL {nivel}</span><span class="hud-tit">{titulo}</span>
  </header>
  <div class="contenido">{cuerpo}</div>
  <footer class="pie">
    <span>Respawn · Proyecto final DP-750</span>
    <div class="xp"><div style="width:{xp}%"></div></div>
    <span class="px">{num:02d}/{TOTAL}</span>
  </footer>
</section>'''


def tabla(cabecera, filas, clase=""):
    th = "".join(f"<th>{c}</th>" for c in cabecera)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f'<table class="{clase}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def codigo(txt, titulo):
    return f'<div class="code"><div class="code-tit"><span></span><span></span><span></span>{titulo}</div><pre>{html.escape(txt)}</pre></div>'


def stat(valor, etiqueta, icono="coin", color="#facc15"):
    return f'<div class="stat"><b>{valor}</b><small>{etiqueta}</small></div>'


def caja(titulo, texto, tipo="tip", icono="star"):
    colores = {"tip": "#a855f7", "boss": "#ec4899", "ok": "#22c55e"}
    return (f'<div class="caja {tipo}">'
            f'<div><span class="px">{titulo}</span><p>{texto}</p></div></div>')


# =====================================================================
# PORTADA
# =====================================================================
estrellas = "".join(
    f'<i style="left:{(i*37)%100}%;top:{(i*53)%100}%;opacity:{0.25+((i*7)%10)/14:.2f}"></i>' for i in range(46))
portada = f'''
<section class="portada">
  <div class="estrellas">{estrellas}</div>
  <div class="scan"></div>
  <div class="port-top"><span class="px">1UP  0001240</span><span class="px">HI-SCORE  849,18 €</span><span class="px">CRÉDITOS 03</span></div>
  <div class="port-sprites">{sprite("invader",9,"#c084fc")}{sprite("ghost",9,"#f472b6")}{sprite("invader",9,"#818cf8")}</div>
  <div class="port-centro">
    <p class="px port-pre">PROYECTO FINAL · DP-750</p>
    <h1 class="logo">RESPAWN</h1>
    <p class="port-sub">Lakehouse de un videojuego en Databricks</p>
    <p class="port-desc">Ingesta incremental · detector de tramposos · historial de rangos · data marts · seguridad · orquestación</p>
    <div class="press px">▶ PRESS START</div>
  </div>
  <div class="port-pad">{sprite("pad",10,"#7c3aed")}</div>
  <div class="port-foot">
    <div><span class="px">JUGADORA</span><b>Noelia Segura Herrero</b></div>
    <div><span class="px">PLATAFORMA</span><b>Databricks Free Edition</b></div>
    <div><span class="px">FECHA</span><b>Noviembre 2026</b></div>
  </div>
</section>'''

# =====================================================================
# 2 · ÍNDICE + OBJETIVO
# =====================================================================
niveles = [("01", "Objetivo", 2), ("02", "Caso de uso y fuentes de datos", 3), ("03", "Arquitectura", 4),
           ("04", "Modelo de datos", 5), ("05", "Bloques implementados", 6), ("06", "Código y configuraciones clave", 7),
           ("07", "Calidad y seguridad", 8), ("08", "Automatización y optimización", 9),
           ("09", "Capturas de las ejecuciones", 10), ("10", "Problemas y soluciones", 14), ("11", "Conclusiones", 15), ("++", "Cómo reproducirlo", 16)]
indice = "".join(f'<li><span class="px n">{n}</span><span class="t">{t}</span><span class="dots"></span>'
                 f'<span class="px p">{p:02d}</span></li>' for n, t, p in niveles)
p2 = pagina(2, "01", "OBJETIVO", f'''
<div class="dos-col">
  <div>
    <h2 class="px-tit">SELECCIONA NIVEL</h2>
    <ol class="indice">{indice}</ol>
  </div>
  <div>
    <h2>Objetivo del proyecto</h2>
    <p>El objetivo de este proyecto es aplicar lo que he aprendido en la DP-750 en una solución completa de ingeniería de
    datos, pequeña pero de principio a fin, y sobre todo <b>demostrar que funciona</b>: que cada número que sale al final se
    puede explicar y comprobar.</p>
    <p>Para que fuera algo más divertido que un ejemplo de ventas, elegí un videojuego online inventado, <b>Respawn</b>.
    Los videojuegos generan muchos eventos, tienen problemas de datos muy reconocibles (duplicados, tramposos, cambios de
    versión) y se entienden fácil al explicarlos.</p>
    <p>Me propuse llegar al <b>nivel 3 (avanzado)</b> del enunciado: varias capas, carga incremental, reglas de calidad,
    seguridad, un Job con tratamiento de errores, tests automáticos y una optimización medida.</p>
  </div>
</div>
<div class="stats">
  {stat("1.240", "eventos válidos", "coin")}
  {stat("11", "eventos rechazados", "ghost", "#f472b6")}
  {stat("117", "jugadores", "invader", "#c084fc")}
  {stat("10/10", "validaciones OK", "star", "#4ade80")}
  {stat("19", "tests en verde", "trophy", "#facc15")}
</div>
{caja("EN UNA FRASE", "Cargo cada día los ficheros del juego, separo lo que es basura o trampa, guardo el historial de cada jugador y dejo listos tres informes para negocio, todo automatizado y con permisos por región.")}
''', "star")

# =====================================================================
# 3 · CASO DE USO Y FUENTES
# =====================================================================
p3 = pagina(3, "02", "CASO DE USO Y FUENTES", f'''
<h2>El caso de uso</h2>
<p><b>Respawn</b> es un juego online con jugadores en dos regiones, Europa (EU) y Norteamérica (NA). El estudio quiere
responder tres preguntas: <i>¿cuánto vendemos en la tienda y a quién?</i>, <i>¿los jugadores vuelven a jugar?</i> y
<i>¿quiénes son los mejores?</i></p>
<p>El problema es que los datos no llegan limpios. Hay eventos repetidos por reconexiones, registros sin identificador,
fechas en el futuro, compras con precios que no existen y jugadores que hacen trampa. Si se calculan los informes sin
limpiar, las ventas y los rankings salen mal. Por eso la pieza central del proyecto es un <b>"detector de tramposos"</b>.</p>

<h2>Fuentes de datos</h2>
<p>Los datos son sintéticos. Los genero yo con un script de Python (<code>src/generador_datos.py</code>) usando Faker y
una semilla fija (42), así que cada vez salen exactamente iguales y cualquiera puede reproducirlos. Los emails son
ficticios (<code>@example.com</code>), así que no hay datos personales reales.</p>
{tabla(["Fichero", "Formato", "Qué contiene"], [
    ["<code>jugadores_dia_N.csv</code>", "CSV", "Altas y cambios de jugadores: país, región, rango, nivel…"],
    ["<code>eventos_dia_N.json</code>", "JSON Lines", "Inicios de sesión, partidas, compras y subidas de rango, con un campo anidado <code>detalle</code>"],
    ["<code>articulos.csv</code>", "CSV", "Catálogo de la tienda: 12 artículos con su precio"],
    ["<code>eventos_corrupto.json</code>", "JSON roto", "Un fichero mal formado para provocar un error en el Job"]])}

<h2>Los tres días de juego</h2>
<p>Simulo tres días. Cada uno trae algo nuevo para poder demostrar una parte distinta del temario. Lo que se mete a
propósito queda apuntado en <code>resumen_esperado.json</code>, que luego uso para validar.</p>
<div class="dias">
  <div class="dia"><span class="px">DÍA 1</span><b>Carga inicial</b><p>100 jugadores y 538 eventos limpios.</p></div>
  <div class="dia boss"><span class="px">DÍA 2</span><b>Llegan los problemas</b><p>12 jugadores nuevos, 5 suben de rango, 15 duplicados y 11 eventos con errores, 3 de ellos de tramposos.</p></div>
  <div class="dia"><span class="px">DÍA 3</span><b>Actualización del juego</b><p>5 jugadores nuevos, 2 subidas de rango y una columna nueva: <code>version_juego</code>.</p></div>
</div>
''', "pad")

# =====================================================================
# 4 · ARQUITECTURA
# =====================================================================
p4 = pagina(4, "03", "ARQUITECTURA", f'''
<h2>Arquitectura medallón en Unity Catalog</h2>
<figure class="diagrama"><img src="img/arquitectura.png"></figure>
<h3>Recorrido de los datos</h3>
<ol class="pasos">
  <li><b>Origen.</b> El notebook <code>00</code> copia los ficheros de <code>data/sample</code> (que vienen en el
  repositorio) al volumen <code>respawn.bronze.raw_files</code>, en la carpeta <code>_staging</code>.</li>
  <li><b>Llega el día.</b> La primera tarea del Job copia el día N a <code>landing/</code>, como si el juego acabara de
  dejar los ficheros. Si hay un JSON roto, lo mueve a <code>_cuarentena/</code> y para el Job.</li>
  <li><b>Bronze.</b> Auto Loader lee solo los ficheros nuevos y los guarda tal cual, con el fichero de origen y la hora de carga.</li>
  <li><b>Silver.</b> Limpio, quito duplicados, aplico las reglas y separo lo válido de lo rechazado. Los jugadores van a una dimensión con historial (SCD2).</li>
  <li><b>Gold.</b> Construyo los tres data marts. Los analistas los leen a través de vistas con filtro por región y el email enmascarado.</li>
  <li><b>Validación.</b> La última tarea compara cada capa con lo esperado y guarda el resultado.</li>
</ol>
{caja("POR QUÉ SERVERLESS", "En Free Edition solo hay cómputo serverless, pero además encaja con el caso: son cargas pequeñas que se ejecutan una vez al día, así que no tiene sentido tener un clúster encendido esperando.")}
''', "invader")

# =====================================================================
# 5 · MODELO DE DATOS
# =====================================================================
p5 = pagina(5, "04", "MODELO DE DATOS", f'''
<h2>Catálogo <code>respawn</code></h2>
<p>Uso un único catálogo con un esquema por capa, más uno de calidad. Los nombres están en español y en
<code>snake_case</code>: <code>_raw</code> para Bronze, <code>dim_</code> y <code>fact_</code> para el modelo
dimensional y <code>mart_</code> para Gold.</p>
<div class="capas">
  <div class="capa bronze"><span class="px">BRONZE</span>
    <p><code>jugadores_raw</code><br><code>eventos_raw</code><br><code>articulos_raw</code></p>
    <small>Datos tal cual + <code>_fichero_origen</code>, <code>_fecha_ingesta</code>, <code>_dia_carga</code>, <code>_rescued_data</code></small></div>
  <div class="capa silver"><span class="px">SILVER</span>
    <p><code>eventos</code><br><code>dim_jugador</code> (SCD2)<br><code>dim_articulo</code> (SCD1)<br><code>fact_partidas</code><br><code>fact_compras</code><br><code>control_cargas</code></p>
    <small>Datos limpios, tipados y sin duplicados</small></div>
  <div class="capa gold"><span class="px">GOLD</span>
    <p><code>mart_economia</code><br><code>mart_retencion</code><br><code>mart_competitivo</code><br><code>v_*_analistas</code> (vistas)</p>
    <small>Listo para negocio</small></div>
  <div class="capa quality"><span class="px">QUALITY</span>
    <p><code>rechazos</code><br><code>metricas_calidad</code><br><code>validaciones_pipeline</code></p>
    <small>Lo que falla y cuánto</small></div>
</div>
<h3>Los data marts</h3>
{tabla(["Data mart", "Pregunta", "Una fila por…"], [
    ["<code>mart_economia</code>", "¿Cuánto vendemos, de qué y a qué tipo de jugador?", "día × región × categoría × rango del comprador"],
    ["<code>mart_retencion</code>", "¿Cuántos jugadores hay y cuántos vuelven?", "día"],
    ["<code>mart_competitivo</code>", "¿Quiénes son los mejores?", "jugador"]])}
<h3>La dimensión de jugadores (SCD tipo 2)</h3>
<p>Cuando un jugador sube de rango no sobrescribo la fila: cierro la versión antigua y creo una nueva. Así sé qué rango
tenía en cada momento. Cada versión tiene <code>fecha_inicio_vigencia</code>, <code>fecha_fin_vigencia</code>,
<code>es_actual</code> y una clave sustituta <code>sk_jugador</code>.</p>
<div class="scd">
  <div><span class="px">v1</span>p-0033 · <b>Plata</b> · 01/11 → 02/11</div>
  <div><span class="px">v2</span>p-0033 · <b>Oro</b> · 02/11 → 03/11</div>
  <div class="act"><span class="px">v3</span>p-0033 · <b>Diamante</b> · 03/11 → actual</div>
</div>
{caja("MANAGED VS EXTERNAL", "Todas las tablas y el volumen son gestionados: Unity Catalog se encarga del almacenamiento y de borrar los ficheros cuando se borra la tabla. En Free Edition no tengo un almacenamiento externo propio, así que no había motivo para usar tablas externas.")}
''', "shield")

# =====================================================================
# 6 · BLOQUES IMPLEMENTADOS
# =====================================================================
bloques = [
    ("A", "Entorno y Unity Catalog", "Catálogo, 4 esquemas, volumen gestionado, convención de nombres, serverless justificado", 100),
    ("B", "Seguridad y gobierno", "Grupos, GRANT/REVOKE, filtro de filas, máscara de email, comentarios, etiquetas, linaje", 100),
    ("C", "Ingesta y transformación", "Auto Loader, tipos, nulos, duplicados, aplanado del JSON, validación contra el origen", 100),
    ("D", "Delta e incremental", "MERGE, SCD1 y SCD2, hechos y dimensiones, medallón, time travel, Change Data Feed", 100),
    ("E", "Calidad", "6 reglas, válidos y rechazados por separado, métricas, schema drift, tests", 100),
    ("F", "Orquestación", "Lakeflow Job de 5 tareas, parámetros, reintentos, email, programación, Repair run", 100),
    ("G", "Optimización (ligera)", "Liquid clustering + OPTIMIZE medido antes y después", 60),
    ("H", "SDLC (ligera)", "Git folder, código modular, tests con pytest, GitHub Actions, configuración separada", 60),
]
filas_b = "".join(f'''<div class="logro"><div class="letra px">{l}</div><div class="info"><b>{t}</b><small>{d}</small>
<div class="barra-l"><div style="width:{p}%"></div></div></div><span class="px estado">{"100%" if p == 100 else "LIGERO"}</span></div>'''
                  for l, t, d, p in bloques)
p6 = pagina(6, "05", "BLOQUES IMPLEMENTADOS", f'''
<h2>Logros desbloqueados</h2>
<p>El enunciado pide al menos un bloque. Yo he hecho los seis principales completos (A–F) y una versión ligera de
optimización (G) y de ciclo de vida del software (H), que es lo que necesita el nivel 3.</p>
<div class="logros">{filas_b}</div>
{tabla(["Nivel del enunciado", "Qué pide", "Dónde se ve"], [
    ["1 · Básico", "Flujo de principio a fin, limpieza, tabla Delta y validación", "Notebooks 01–02, validaciones"],
    ["2 · Intermedio", "Varias capas, carga incremental, reglas de calidad, Unity Catalog", "Medallón + Auto Loader + reglas R1–R6"],
    ["3 · Avanzado", "Jobs, monitorización y errores, seguridad, tests, optimización", "Job, cuarentena + Repair run, vistas, pytest, notebook 07"]])}
''', "trophy")

# =====================================================================
# 7 · CÓDIGO
# =====================================================================
c_auto = '''spark.readStream.format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.schemaLocation", f"{CHECKPOINTS}/eventos/esquema")
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns")   # schema drift
  .load(f"{LANDING}/eventos")
  .select("*", "_metadata.file_path")                          # de qué fichero viene
  .writeStream.trigger(availableNow=True)                      # procesa lo nuevo y para
  .toTable("respawn.bronze.eventos_raw")'''
c_scd = '''MERGE INTO respawn.silver.dim_jugador AS d
USING (
  SELECT o.id_jugador AS clave_merge, o.* FROM origen_jugadores o      -- para cerrar
  UNION ALL
  SELECT NULL AS clave_merge, o.* FROM origen_jugadores o              -- para insertar
  JOIN respawn.silver.dim_jugador d
    ON d.id_jugador = o.id_jugador AND d.es_actual AND d.hash_atributos <> o.hash_atributos
) AS s
ON d.id_jugador = s.clave_merge AND d.es_actual
WHEN MATCHED AND d.hash_atributos <> s.hash_atributos THEN
  UPDATE SET d.es_actual = false, d.fecha_fin_vigencia = s.fecha_actualizacion
WHEN NOT MATCHED THEN INSERT (...) VALUES (..., s.fecha_actualizacion, NULL, true, ...)'''
c_sec = '''CREATE FUNCTION respawn.gold.fn_region_visible(region STRING) RETURNS BOOLEAN
RETURN CASE
  WHEN is_account_group_member('respawn_analistas_eu') THEN region = 'EU'
  WHEN is_account_group_member('respawn_analistas_na') THEN region = 'NA'
  ELSE true END;'''
p7 = pagina(7, "06", "CÓDIGO Y CONFIGURACIÓN", f'''
<h2>Las piezas clave</h2>
<p>Aquí pongo solo lo más importante. El código completo está en el repositorio de GitHub.</p>
<h3>1 · Ingesta incremental con Auto Loader</h3>
<p>El checkpoint guarda qué ficheros ya se han leído, así que aunque ejecute el Job dos veces no se duplica nada. Con
<code>addNewColumns</code>, cuando el día 3 trae <code>version_juego</code> la columna se añade sola.</p>
{codigo(c_auto, "notebooks/01_ingesta_bronze.py (simplificado)")}
<h3>2 · SCD2 en un solo MERGE</h3>
<p>El truco es duplicar las filas que han cambiado: una con la clave, que cierra la versión vieja, y otra con clave
<code>NULL</code>, que nunca coincide y por eso se inserta como versión nueva. Para detectar cambios comparo un hash de
los atributos (<code>rango</code>, <code>nivel</code>, <code>region</code>).</p>
{codigo(c_scd, "notebooks/03_merge_scd2.py")}
<h3>3 · Filtro de filas por región</h3>
{codigo(c_sec, "notebooks/05_seguridad_gobierno.py")}
<h3>Configuración</h3>
<p>No hay ninguna contraseña ni token en el repositorio. La configuración (catálogo, esquemas, rutas) está separada del
código en <code>config/project_config.yaml</code>, y el Job se crea desde <code>jobs/crear_job.py</code> con el SDK de
Databricks: si ya existe, lo actualiza en lugar de crear otro.</p>
''', "sword")

# =====================================================================
# 8 · CALIDAD Y SEGURIDAD
# =====================================================================
p8 = pagina(8, "07", "CALIDAD Y SEGURIDAD", f'''
<h2>El detector de tramposos</h2>
<p>Cada evento pasa por seis reglas. Lo que no cumple no se borra: va a <code>quality.rechazos</code> con todas las
reglas que incumple y un motivo principal. Así puedo explicar por qué falta cada evento.</p>
{tabla(["Regla", "Qué comprueba", "Día 2"], [
    ["R1", "<code>id_evento</code> e <code>id_jugador</code> no nulos", "2"],
    ["R2", "La fecha no está en el futuro", "2"],
    ["R3", "Puntuación ≤ duración × 5 y bajas ≤ 60 → <b>tramposos</b> (p-0007, p-0022, p-0051)", "3"],
    ["R4", "Compra con importe positivo e igual al precio del artículo", "2"],
    ["R5", "El jugador existe", "2"],
    ["R6", "Un solo registro por <code>id_evento</code> (duplicados)", "15 quitados"]], "compacta")}
<p>Los recuentos de cada carga (leídos, válidos, rechazados por regla, duplicados) se guardan en
<code>quality.metricas_calidad</code>. Las reglas R1–R5 están en <code>src/reglas_calidad.py</code> para poder
probarlas con pytest fuera de Databricks.</p>

<h2>Seguridad y gobierno</h2>
<ul class="lista">
  <li><b>Mínimo privilegio:</b> los grupos de analistas solo tienen <code>SELECT</code> sobre las vistas de Gold, no sobre las tablas. Hice también un <code>REVOKE</code> de un permiso dado "por error" sobre Silver.</li>
  <li><b>Filtro de filas:</b> un analista de EU solo ve jugadores de EU (función <code>fn_region_visible</code>).</li>
  <li><b>Máscara de columna:</b> el email aparece como <code>a***@example.com</code> salvo para el grupo <code>respawn_pii</code>.</li>
  <li><b>Metadatos:</b> comentarios en tablas y columnas, etiquetas (<code>capa</code>, <code>dominio</code>, <code>pii</code>) y linaje automático de Unity Catalog.</li>
</ul>
{tabla(["Escenario", "Mis grupos", "Qué veo en la vista de jugadores"], [
    ["A", "Ninguno (soy la propietaria)", "Todas las regiones, email enmascarado"],
    ["B", "<code>respawn_analistas_eu</code>", "Solo EU, email enmascarado"],
    ["C", "<code>respawn_analistas_eu</code> + <code>respawn_pii</code>", "Solo EU, email completo"]], "compacta")}
{caja("UN SOLO JUGADOR", "Free Edition solo tiene un usuario, así que no podía probar con otra persona. Lo comprobé metiéndome y sacándome de los grupos y consultando la misma vista. Los cambios de grupo tardan unos minutos en aplicarse.", "boss", "ghost")}
''', "shield")

# =====================================================================
# 9 · AUTOMATIZACIÓN Y OPTIMIZACIÓN
# =====================================================================
p9 = pagina(9, "08", "AUTOMATIZACIÓN Y OPTIMIZACIÓN", f'''
<h2>Lakeflow Job: "simular un día de juego"</h2>
<div class="pipeline">
  <div class="px">01 BRONZE</div><i>▶</i><div class="px">02 SILVER</div><i>▶</i><div class="px">03 SCD2</div><i>▶</i>
  <div class="px">04 GOLD</div><i>▶</i><div class="px fin">06 VALIDA</div>
</div>
{tabla(["Opción", "Configuración"], [
    ["Parámetros", "<code>dia</code> (1, 2, 3) e <code>inyectar_error</code> (no / si)"],
    ["Reintentos", "1 por tarea (menos la de validación, que si falla debe fallar)"],
    ["Avisos", "Email a la propietaria si el Job falla"],
    ["Programación", "Todos los días a las 06:00 (Europe/Madrid), en pausa para no gastar"],
    ["Concurrencia", "Máximo 1 ejecución a la vez; 30 minutos de límite por tarea"]], "compacta")}
<p><b>Error y recuperación.</b> Con <code>inyectar_error=si</code> la tarea 01 encuentra un JSON roto, lo manda a
cuarentena y falla a propósito. Las demás tareas quedan en <i>Upstream failed</i>, así que no se carga nada a medias.
Con <b>Repair run</b> solo se repite lo que falló y el Job termina bien.</p>
<p><b>Monitorización.</b> Lo sigo desde el historial de ejecuciones del Job y con dos tablas: <code>metricas_calidad</code>
y <code>validaciones_pipeline</code> (10 comprobaciones de extremo a extremo; si una falla, falla el Job).</p>

<h2>Optimización medida</h2>
<p>Con 1.240 eventos todo tarda milisegundos y no se puede medir nada. Por eso creé una tabla de pruebas de
<b>10 millones de filas</b> escrita a propósito en 200 ficheros pequeños. Medí una consulta típica ("qué ha hecho el jugador X
entre dos fechas") antes y después de <code>CLUSTER BY (id_jugador, fecha_evento)</code> + <code>OPTIMIZE</code>.</p>
<div class="versus">
  <div><span class="px">ANTES</span><b>200</b><small>ficheros</small><b>73,8 MB</b><small>tamaño</small><b>0,91 s</b><small>consulta</small></div>
  <div class="vs px">VS</div>
  <div class="win"><span class="px">DESPUÉS</span><b>2</b><small>ficheros</small><b>67,8 MB</b><small>tamaño</small><b>1,0 s</b><small>consulta</small></div>
</div>
{caja("RESULTADO HONESTO", "La compactación funciona (200 → 2 ficheros), pero la consulta no va más rápida. Con 74 MB casi todo el tiempo es el arranque de la consulta en serverless, no la lectura. Esta mejora se nota con gigabytes. No hice VACUUM para no perder el time travel.", "boss", "bug")}
''', "pad")

# =====================================================================
# 10–13 · CAPTURAS
# =====================================================================
p10 = pagina(10, "09", "CAPTURAS · INGESTA Y CALIDAD", f'''
<h2>Ingesta incremental (Bronze)</h2>
{img("f4_03_bronze_incremental_por_fichero_c.jpg", "Cada ejecución carga solo el fichero nuevo: 538 eventos del día 1 y 424 del día 2.")}
{img("f5_01_metricas_calidad_dia2_c.jpg", "Métricas de calidad del día 2: 424 leídos, 15 duplicados, 398 válidos y 11 rechazados por regla.")}
{img("f5_03_tramposos_rechazados_c.jpg", "Los 11 eventos rechazados con su motivo, entre ellos los tramposos con puntuación 99999.")}
''', "ghost")

p11 = pagina(11, "09", "CAPTURAS · SCD2 Y GOLD", f'''
<h2>Historial de jugadores y data marts</h2>
{img("f6_04_historial_scd2_c.jpg", "SCD2 tras el día 2: cada jugador que sube de rango tiene su versión cerrada y la nueva activa.")}
{img("f6_05_time_travel_dia1_vs_dia2_c.jpg", "Time travel: comparo la versión de la tabla del día 1 con la del día 2 para ver quién es nuevo y quién ha subido.")}
{img("f7_05_gasto_por_rango_point_in_time_c.jpg", "Gasto por rango con el join point-in-time: cada compra cuenta con el rango que tenía el jugador ese día.")}
''', "trophy")

p12 = pagina(12, "09", "CAPTURAS · SEGURIDAD", f'''
<h2>Permisos y vistas para analistas</h2>
{img("f8_05_escenario_A_sin_grupos_c.jpg", "Escenario A, sin grupos: veo todas las regiones (75 EU, 37 NA) con el email enmascarado.")}
{img("f8_07_escenario_B_analista_eu_c.jpg", "Escenario B, en el grupo de analistas EU: la misma consulta solo devuelve jugadores de EU.")}
{img("f8_06_linaje_mart_economia_c.jpg", "Linaje de <code>mart_economia</code> en Unity Catalog: de qué tablas se alimenta y qué la usa.")}
''', "shield")

p13 = pagina(13, "09", "CAPTURAS · JOB Y TESTS", f'''
<h2>Ejecución, error y recuperación</h2>
{img("f9_03_ejecucion_fallida_grafo_c.jpg", "Ejecución con el fichero corrupto: falla la tarea 01 y el resto queda en Upstream failed.")}
{img("f9_06_validaciones_extremo_a_extremo_dia3_c.jpg", "Después del Repair run: las 10 validaciones de extremo a extremo salen OK.")}
<div class="fila-img">
{img("f10_03_comparacion_antes_despues_c.jpg", "Optimización: comparación antes y después.", "49%")}
{img("f10_05_github_actions_c.jpg", "Los tests pasan en GitHub Actions con cada push.", "49%")}
</div>
''', "star")

# =====================================================================
# 14 · PROBLEMAS Y SOLUCIONES
# =====================================================================
bugs = [
    ("Errores que en local no salían", "Serverless tiene activado el modo ANSI de SQL: acceder a una posición que no existe en un array o convertir una fecha mal escrita lanza un error en lugar de devolver NULL.",
     "Usé <code>try_to_timestamp</code> y <code>try_divide</code>, y compruebo el tamaño del array antes de <code>element_at</code>."),
    ("El Git folder no conectaba", "Con el repositorio privado, Databricks Free no conseguía autenticarse con GitHub.",
     "Hice el repositorio público. No pasa nada porque no contiene ningún secreto."),
    ("El pull borra las salidas", "Al actualizar el Git folder se borran los resultados de los notebooks.",
     "Hago las capturas antes de cada actualización."),
    ("La columna nueva paraba el stream", "Cuando llega <code>version_juego</code>, Auto Loader para el stream a propósito para guardar el nuevo esquema. Reintentarlo dentro del notebook no bastaba.",
     "Añadí un reintento a la tarea del Job: el segundo intento ya continúa con el esquema nuevo."),
    ("Solo tengo un usuario", "No podía probar los permisos con otra persona.",
     "Cambié mi pertenencia a los grupos en tres escenarios y esperé unos minutos a que se aplicara."),
    ("Datos de prueba que no servían", "En la prueba de optimización generé los valores con una fórmula que relacionaba unas columnas con otras: cada jugador tenía un solo tipo de evento y la consulta no devolvía filas.",
     "Lo cambié por un hash con una semilla distinta para cada columna."),
]
p14 = pagina(14, "10", "PROBLEMAS Y SOLUCIONES", '''
<h2>Bugs encontrados y parches</h2>
<p>No todo salió a la primera. Estos son los problemas más importantes y cómo los resolví.</p>
<div class="bugs">''' + "".join(
    f'<div class="bugc"><div><b>{t}</b><p>{p}</p><p class="fix"><span class="px">PARCHE</span> {s}</p></div></div>'
    for t, p, s in bugs) + '''</div>
<h3>Limitaciones que conozco</h3>
<ul class="lista">
  <li>El join <i>point-in-time</i> va por día: si un jugador sube de rango y compra el mismo día, se usa el rango del final del día.</li>
  <li>En serverless no se puede desactivar la caché, así que los tiempos medidos tienen algo de ruido.</li>
  <li>Los datos son pequeños: la optimización está medida, pero su beneficio real solo se vería con mucho más volumen.</li>
</ul>''', "bug")

# =====================================================================
# 15 · CONCLUSIONES
# =====================================================================
p15 = pagina(15, "11", "CONCLUSIONES", f'''
<h2>Lo que me llevo</h2>
<ul class="lista">
  <li><b>Auto Loader</b> facilita mucho la carga incremental: con el checkpoint no se repiten datos y las columnas nuevas se añaden solas.</li>
  <li>Hacer el <b>SCD2 con un solo MERGE</b> me costó entenderlo, pero tener el historial es lo que permite contar cada compra con el rango que tenía el jugador ese día.</li>
  <li>Es mejor <b>no borrar</b> los datos malos y guardarlos con su motivo. Así cada número se puede explicar.</li>
  <li>Validar contra lo esperado (<code>resumen_esperado.json</code>) da mucha tranquilidad: si algo cambia, el Job falla y me entero.</li>
  <li>Con <b>Unity Catalog</b> la seguridad se resuelve con funciones y vistas, sin duplicar datos por región.</li>
  <li>Medir es tan importante como optimizar: una mejora que no se nota con datos pequeños también es un resultado.</li>
</ul>
<h2>Posibles mejoras</h2>
<div class="mejoras">
  <div><b>Lakeflow Declarative Pipelines</b><small>con <i>expectations</i> para las reglas de calidad</small></div>
  <div><b>Asset Bundles</b><small>para desplegar en dev y prod</small></div>
  <div><b>Dashboard y alertas</b><small>sobre los data marts y las métricas de calidad</small></div>
  <div><b>Más volumen</b><small>para medir la optimización con datos realistas</small></div>
</div>
<div class="gameover">
  <p class="px go">LEVEL COMPLETE</p>
  <p>Todo el código, los datos de ejemplo, las instrucciones para reproducirlo y todas las capturas están en el repositorio:</p>
  <p class="px repo">github.com/noeliaseguraherrero/respawn-dp750</p>
</div>
''', "trophy")

# =====================================================================
# 16 · CONTRAPORTADA / REPRODUCIR
# =====================================================================
p16 = pagina(16, "++", "CÓMO REPRODUCIRLO", f'''
<h2>Guía de reproducción</h2>
<ol class="pasos grande">
  <li>Crear un <b>Git folder</b> en Databricks con la URL del repositorio.</li>
  <li>Ejecutar <code>sql/01_catalogo_y_esquemas.sql</code> (catálogo, esquemas y volumen).</li>
  <li>Ejecutar <code>notebooks/00_preparar_volumen.py</code> (copia los datos al volumen).</li>
  <li>Ejecutar <code>jobs/crear_job.py</code> (crea el Job).</li>
  <li>Lanzar el Job con <code>dia=1</code>, luego <code>dia=2</code> y luego <code>dia=3</code> con <code>inyectar_error=si</code> y hacer <b>Repair run</b>.</li>
  <li>Crear a mano los grupos <code>respawn_analistas_eu</code>, <code>respawn_analistas_na</code> y <code>respawn_pii</code>, y ejecutar <code>notebooks/05_seguridad_gobierno.py</code>.</li>
  <li>(Opcional) <code>notebooks/07_optimizacion.py</code>. Para empezar de cero: <code>notebooks/99_reiniciar_entorno.py</code>.</li>
</ol>
<h3>Resultado esperado tras el día 3</h3>
{tabla(["Comprobación", "Valor"], [
    ["Eventos válidos en Silver", "1.240"], ["Eventos rechazados", "11"], ["Duplicados eliminados", "15"],
    ["Jugadores (versión actual)", "117"], ["Versiones históricas", "7"], ["Partidas", "691"],
    ["Ingresos", "849,18 €"], ["Validaciones", "10/10 OK"], ["Tests", "19 passed"]], "compacta")}
<p class="nota">Lo único que no se puede guardar en Git es el Git folder y los grupos; todo lo demás se crea desde el
repositorio. No hace falta ninguna contraseña ni token.</p>
''', "pad")

paginas = [portada, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15, p16]

css = (BASE / "estilo.css").read_text(encoding="utf-8").replace("FONTS", str(FONTS))
doc = f'''<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Respawn · Proyecto DP-750</title>
<style>{css}</style></head><body>{"".join(paginas)}</body></html>'''
(BASE / "informe.html").write_text(doc, encoding="utf-8")
print("HTML generado,", len(paginas), "páginas")
