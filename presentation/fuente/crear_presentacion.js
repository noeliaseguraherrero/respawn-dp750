// Genera presentation/respawn_dp750.pptx (8 diapositivas) con pptxgenjs
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/2bda2c70-50d3-4a08-ad31-63c8e40ff307_78bd9719-b31e-478c-8276-c45f159eda5f/pptx/scripts/apply_theme.js");

const THEME = {
  name: "Respawn",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "241338", lt1: "FFFFFF", dk2: "3B0A6B", lt2: "F5F0FF",
    accent1: "7C3AED", accent2: "EC4899", accent3: "A855F7", accent4: "FACC15",
    accent5: "16A34A", accent6: "6B5A85", hlink: "7C3AED", folHlink: "A855F7",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Respawn · Proyecto final DP-750";
pres.author = "Noelia Segura Herrero";
const C = pres.SchemeColor;
const MONO = "Courier New";

// ---------------- layouts ----------------
pres.defineSlideMaster({
  title: "PORTADA",
  background: { path: "fondo.png" },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENIDO",
  background: { color: "FFFFFF" },
  margin: [0.5, 0.5, 0.55, 0.5],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.62, w: 9, h: 0.6,
        fontSize: 26, bold: true, color: C.text2, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: "Respawn · Proyecto final DP-750", options: { x: 0.5, y: 5.2, w: 4, h: 0.25, fontSize: 9, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.25, fontFace: MONO, fontSize: 9, color: C.accent1, bold: true, align: "right" },
});

let n = 0;
function etiqueta(slide, nivel, seccion) {
  slide.addText(`NIVEL ${nivel}`, { x: 0.5, y: 0.25, w: 1.05, h: 0.26, fontFace: MONO, bold: true, fontSize: 9,
    color: C.accent1, align: "center", valign: "middle", margin: 0, isTextBox: true,
    line: { color: THEME.colors.accent1, width: 1 }, objectName: "Etiqueta nivel" });
  slide.addText(seccion.toUpperCase(), { x: 1.68, y: 0.25, w: 6, h: 0.26, fontSize: 9.5, bold: true, charSpacing: 2,
    color: C.text2, valign: "middle", margin: 0, isTextBox: true, objectName: "Sección" });
  // barra de experiencia (progreso de la presentación)
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 5.29, w: 3.5, h: 0.06, fill: { color: C.background2 }, line: { type: "none" }, objectName: "XP fondo" });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 5.29, w: 3.5 * nivel / 8, h: 0.06, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "XP progreso" });
  slide.addText("XP", { x: 4.85, y: 5.2, w: 0.3, h: 0.25, fontFace: MONO, bold: true, fontSize: 8, color: C.accent1, margin: 0, isTextBox: true });
}
const tarjeta = (slide, x, y, w, h, nombre) =>
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.background2 }, line: { type: "none" }, objectName: nombre });

// =============== 1 · TÍTULO Y OBJETIVO ===============
pres.addSection({ title: "Inicio" });
let s = pres.addSlide({ masterName: "PORTADA", sectionTitle: "Inicio" });
s.addImage({ path: "inv1.png", x: 3.2, y: 0.55, w: 0.62, h: 0.45, objectName: "Sprite 1" });
s.addImage({ path: "ghost.png", x: 4.69, y: 0.5, w: 0.62, h: 0.62, objectName: "Sprite 2" });
s.addImage({ path: "inv2.png", x: 6.18, y: 0.55, w: 0.62, h: 0.45, objectName: "Sprite 3" });
s.addText("PROYECTO FINAL · DP-750", { x: 1, y: 1.4, w: 8, h: 0.3, fontFace: MONO, bold: true, fontSize: 12, color: "E9D5FF",
  align: "center", charSpacing: 4, margin: 0, isTextBox: true });
s.addImage({ path: "logo.png", x: 2.0, y: 1.82, w: 6.0, h: 6.0 * 152 / 1052, altText: "RESPAWN", objectName: "Logo" });
s.addText("Lakehouse de un videojuego en Databricks", { x: 1, y: 2.85, w: 8, h: 0.5, fontSize: 24, bold: true, color: "F3E8FF",
  align: "center", margin: 0, isTextBox: true });
s.addText("Objetivo: cargar cada día los datos del juego, detectar a los tramposos, guardar el historial de los jugadores y dejar informes fiables para negocio, todo automatizado y con permisos por región.",
  { x: 1.4, y: 3.4, w: 7.2, h: 0.7, fontSize: 13, color: "D8B4FE", align: "center", margin: 0, isTextBox: true });
s.addText("Noelia Segura Herrero  ·  Databricks Free Edition  ·  Noviembre 2026", { x: 1, y: 4.95, w: 8, h: 0.3, fontFace: MONO,
  bold: true, fontSize: 10, color: "F0ABFC", align: "center", margin: 0, isTextBox: true });
s.addNotes("Presento Respawn, mi proyecto final de la DP-750. Es un lakehouse en Databricks para un videojuego online inventado. El objetivo es demostrar de principio a fin cómo cargar los datos de cada día, limpiarlos, detectar tramposos, guardar el historial de los jugadores y dejar tres informes listos para negocio, todo automatizado con un Job y con seguridad por región.");

// =============== 2 · PROBLEMA ===============
pres.addSection({ title: "Contexto" });
s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Contexto" });
etiqueta(s, 2, "El problema");
s.addText("Los datos del juego no llegan limpios", { placeholder: "title" });
s.addText([
  { text: "Respawn es un juego online con jugadores en Europa y Norteamérica. Cada día deja ficheros con sesiones, partidas, compras y subidas de rango.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 6 } },
  { text: "Si se analizan tal cual, las ventas y los rankings salen mal. Por eso la pieza central del proyecto es un ", options: {} },
  { text: "detector de tramposos.", options: { bold: true, color: C.accent1 } },
], { x: 0.5, y: 1.45, w: 3.7, h: 2.6, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
const problemas = [
  ["15", "eventos duplicados", "por reconexiones"],
  ["4", "datos imposibles", "sin identificador o con fecha futura"],
  ["4", "compras falsas", "precio incorrecto o jugador que no existe"],
  ["3", "tramposos", "puntuaciones imposibles para la duración"],
];
problemas.forEach(([num, tit, desc], i) => {
  const x = 4.6 + (i % 2) * 2.5, y = 1.45 + Math.floor(i / 2) * 1.65;
  tarjeta(s, x, y, 2.3, 1.45, `Problema ${i + 1}`);
  s.addText(num, { x: x + 0.2, y: y + 0.15, w: 1.9, h: 0.6, fontSize: 34, bold: true, color: i === 3 ? C.accent2 : C.accent1, margin: 0, isTextBox: true });
  s.addText(tit, { x: x + 0.2, y: y + 0.75, w: 1.9, h: 0.28, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(desc, { x: x + 0.2, y: y + 1.03, w: 1.95, h: 0.35, fontSize: 10.5, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
});
s.addText("Errores metidos a propósito en el día 2 y apuntados en resumen_esperado.json para poder validarlos.",
  { x: 0.5, y: 4.35, w: 3.7, h: 0.5, fontSize: 10.5, italic: true, color: C.accent6, margin: 0, isTextBox: true });
s.addNotes("Los datos son sintéticos: los genero con Python y una semilla fija, así que siempre salen iguales. En el día 2 meto a propósito los problemas típicos de un juego: duplicados por reconexiones, registros sin identificador, fechas futuras, compras con precios que no existen y tres tramposos con puntuaciones imposibles. Todo queda apuntado en un fichero de resumen que luego uso para comprobar que el pipeline detecta exactamente eso.");

// =============== 3 · ARQUITECTURA ===============
pres.addSection({ title: "Solución" });
s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Solución" });
etiqueta(s, 3, "Arquitectura");
s.addText("Arquitectura medallón en Unity Catalog", { placeholder: "title" });
const ah = 3.75, aw = ah * 1890 / 1069;
s.addImage({ path: "arquitectura.png", x: (10 - aw) / 2, y: 1.3, w: aw, h: ah, altText: "Diagrama de arquitectura del lakehouse Respawn", objectName: "Diagrama" });
s.addNotes("Los ficheros de cada día llegan a un volumen de Unity Catalog. Auto Loader los carga de forma incremental en Bronze. En Silver limpio, quito duplicados, aplico las reglas de calidad y separo lo válido de lo rechazado, que va al esquema quality con su motivo. Los jugadores van a una dimensión SCD2 con historial. En Gold construyo tres data marts, y los analistas los leen a través de vistas con filtro por región y el email enmascarado. Todo lo orquesta un Lakeflow Job y el código está en GitHub, conectado con un Git folder.");

// =============== 4 · FUENTES, TABLAS Y PROCESAMIENTO ===============
s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Solución" });
etiqueta(s, 4, "Fuentes, tablas y procesamiento");
s.addText("Tres días de juego, cuatro capas de datos", { placeholder: "title" });
const dias = [["DÍA 1", "Carga inicial", "100 jugadores y 538 eventos limpios"],
  ["DÍA 2", "Llegan los problemas", "Duplicados, errores, tramposos y 5 subidas de rango"],
  ["DÍA 3", "Actualización del juego", "Columna nueva version_juego (schema drift)"]];
dias.forEach(([d, t, desc], i) => {
  const x = 0.5 + i * 3.05;
  tarjeta(s, x, 1.4, 2.85, 1.15, `Día ${i + 1}`);
  s.addText(d, { x: x + 0.2, y: 1.52, w: 2.4, h: 0.22, fontFace: MONO, bold: true, fontSize: 10, color: i === 1 ? C.accent2 : C.accent1, margin: 0, isTextBox: true });
  s.addText(t, { x: x + 0.2, y: 1.76, w: 2.5, h: 0.28, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(desc, { x: x + 0.2, y: 2.05, w: 2.5, h: 0.42, fontSize: 10.5, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
});
const capas = [["BRONZE", "C2410C", "jugadores_raw · eventos_raw · articulos_raw", "Auto Loader incremental, datos tal cual + fichero de origen"],
  ["SILVER", "475569", "eventos · dim_jugador (SCD2) · dim_articulo · fact_partidas · fact_compras", "Limpieza, tipos, duplicados, reglas y MERGE"],
  ["GOLD", "A16207", "mart_economia · mart_retencion · mart_competitivo", "Join point-in-time con la SCD2 y vistas para analistas"],
  ["QUALITY", "EC4899", "rechazos · metricas_calidad · validaciones_pipeline", "Lo que falla, por qué y cuánto"]];
capas.forEach(([c, col, tablas, proc], i) => {
  const y = 2.8 + i * 0.58;
  s.addText(c, { x: 0.5, y, w: 1.1, h: 0.42, fontFace: MONO, bold: true, fontSize: 10, color: col, valign: "middle", margin: 0, isTextBox: true });
  s.addText(tablas, { x: 1.65, y, w: 4.6, h: 0.42, fontSize: 11.5, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  s.addText(proc, { x: 6.35, y, w: 3.15, h: 0.42, fontSize: 10.5, color: C.accent6, valign: "middle", margin: 0, isTextBox: true });
  if (i < 3) s.addShape(pres.shapes.LINE, { x: 0.5, y: y + 0.5, w: 9, h: 0, line: { color: "EEE7F8", width: 0.75 }, objectName: `Separador ${i + 1}` });
});
s.addNotes("Simulo tres días. El primero es la carga inicial. El segundo trae todos los problemas y cambios de rango, para demostrar el MERGE, la SCD2 y las reglas de calidad. El tercero trae una columna nueva para demostrar la evolución del esquema. Abajo están las cuatro capas: Bronze guarda los datos tal cual llegan, Silver los limpia y modela, Gold tiene los informes y Quality guarda lo que falla, el motivo y las métricas. Todas las tablas son gestionadas.");

// =============== 5 · FUNCIONALIDADES DP-750 ===============
s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Solución" });
etiqueta(s, 5, "Funcionalidades DP-750");
s.addText("Los 8 bloques del enunciado", { placeholder: "title" });
const bloques = [
  ["A", "Unity Catalog", "Catálogo, 4 esquemas, volumen, nombres, serverless"],
  ["B", "Seguridad", "Grupos, GRANT/REVOKE, filtro de filas, máscara, etiquetas"],
  ["C", "Ingesta", "Auto Loader, tipos, nulos, duplicados, JSON anidado"],
  ["D", "Delta incremental", "MERGE, SCD1 y SCD2, time travel, Change Data Feed"],
  ["E", "Calidad", "6 reglas, rechazos con motivo, métricas, schema drift"],
  ["F", "Orquestación", "Job de 5 tareas, reintentos, email, Repair run"],
  ["G", "Optimización", "Liquid clustering + OPTIMIZE, medido antes y después"],
  ["H", "SDLC", "Git, código modular, 19 tests, GitHub Actions"],
];
bloques.forEach(([l, t, d], i) => {
  const x = 0.5 + (i % 4) * 2.3, y = 1.4 + Math.floor(i / 4) * 1.78;
  tarjeta(s, x, y, 2.1, 1.6, `Bloque ${l}`);
  s.addText(l, { x: x + 0.2, y: y + 0.18, w: 0.42, h: 0.42, fontFace: MONO, bold: true, fontSize: 16, color: "FFFFFF",
    fill: { color: i >= 6 ? THEME.colors.accent3 : THEME.colors.accent1 }, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(i >= 6 ? "LIGERO" : "COMPLETO", { x: x + 0.75, y: y + 0.26, w: 1.2, h: 0.26, fontFace: MONO, bold: true, fontSize: 8,
    color: i >= 6 ? C.accent3 : C.accent5, margin: 0, isTextBox: true });
  s.addText(t, { x: x + 0.2, y: y + 0.72, w: 1.8, h: 0.28, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(d, { x: x + 0.2, y: y + 1.0, w: 1.75, h: 0.5, fontSize: 10, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("El enunciado pide al menos un bloque. Yo he hecho completos los seis principales, de la A a la F, y una versión ligera de optimización y de ciclo de vida del software, que es lo que pide el nivel 3: Jobs, tratamiento de errores, seguridad, tests automáticos y una optimización medida.");

// =============== 6 · DEMOSTRACIÓN ===============
pres.addSection({ title: "Demostración" });
s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Demostración" });
etiqueta(s, 6, "Demostración");
s.addText("Un día de juego con error y recuperación", { placeholder: "title" });
const pasos = [["1", "Run now", "dia=3, inyectar_error=si"], ["2", "Falla la ingesta", "JSON roto → cuarentena"],
  ["3", "Repair run", "solo se repite lo que falló"], ["4", "Validación", "10/10 comprobaciones OK"]];
pasos.forEach(([num, t, d], i) => {
  const x = 0.5 + i * 2.3;
  s.addText(num, { x, y: 1.4, w: 0.4, h: 0.4, fontFace: MONO, bold: true, fontSize: 14, color: "FFFFFF",
    fill: { color: i === 1 ? THEME.colors.accent2 : (i === 3 ? THEME.colors.accent5 : THEME.colors.accent1) },
    align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(t, { x: x + 0.5, y: 1.36, w: 1.7, h: 0.25, fontSize: 13, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(d, { x: x + 0.5, y: 1.6, w: 1.75, h: 0.25, fontSize: 10, color: C.accent6, margin: 0, isTextBox: true });
});
const w1 = 4.4, h1 = w1 * 470 / 1250, h2 = w1 * 607 / 1250;
s.addImage({ path: "f9_03_ejecucion_fallida_grafo_c.jpg", x: 0.5, y: 2.2, w: w1, h: h1, altText: "Job con la tarea de ingesta fallida", objectName: "Captura fallo" });
s.addText("La tarea 01 falla y el resto queda en Upstream failed: no se carga nada a medias.",
  { x: 0.5, y: 2.25 + h1, w: w1, h: 0.4, fontSize: 10, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
s.addImage({ path: "f9_06_validaciones_extremo_a_extremo_dia3_c.jpg", x: 5.1, y: 2.2, w: w1, h: h2, altText: "Validaciones de extremo a extremo correctas", objectName: "Captura validaciones" });
s.addText("Después del Repair run, las 10 validaciones salen OK.",
  { x: 5.1, y: 2.25 + h2, w: w1, h: 0.3, fontSize: 10, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
s.addNotes("Si puedo, lo hago en directo: lanzo el Job con dia=3 e inyectar_error=si. La primera tarea encuentra un JSON roto, lo mueve a cuarentena y falla a propósito, así que el resto de tareas no se ejecuta y no se carga nada a medias. Después hago Repair run con inyectar_error=no: solo se repite lo que falló, el Job termina bien y la última tarea comprueba diez cosas de extremo a extremo. Si no hay tiempo o conexión, enseño estas capturas.");

// =============== 7 · RESULTADOS Y VALIDACIONES ===============
s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Demostración" });
etiqueta(s, 7, "Resultados y validaciones");
s.addText("Todo cuadra con lo esperado", { placeholder: "title" });
const stats = [["1.240", "eventos válidos"], ["11", "rechazados con motivo"], ["117", "jugadores · 7 versiones"],
  ["849,18 €", "en ventas"], ["10/10", "validaciones OK"], ["19", "tests en verde"]];
stats.forEach(([v, l], i) => {
  const x = 0.5 + (i % 3) * 1.9, y = 1.4 + Math.floor(i / 3) * 1.45;
  tarjeta(s, x, y, 1.75, 1.28, `Resultado ${i + 1}`);
  s.addText(v, { x: x + 0.15, y: y + 0.2, w: 1.5, h: 0.5, fontSize: v.length > 6 ? 20 : 26, bold: true, color: i === 1 ? C.accent2 : C.accent1, margin: 0, isTextBox: true });
  s.addText(l, { x: x + 0.15, y: y + 0.75, w: 1.5, h: 0.42, fontSize: 10.5, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
});
s.addText("OPTIMIZACIÓN", { x: 6.4, y: 1.4, w: 3.1, h: 0.25, fontFace: MONO, bold: true, fontSize: 10, color: C.accent1, margin: 0, isTextBox: true });
s.addText("10 millones de filas · CLUSTER BY + OPTIMIZE", { x: 6.4, y: 1.68, w: 3.1, h: 0.25, fontSize: 10.5, color: C.accent6, margin: 0, isTextBox: true });
s.addTable([
  [{ text: "", options: { bold: true } }, { text: "Antes", options: { bold: true, color: C.text2 } }, { text: "Después", options: { bold: true, color: C.text2 } }],
  ["Ficheros", "200", { text: "2", options: { bold: true, color: C.accent1 } }],
  ["Tamaño", "73,8 MB", "67,8 MB"],
  ["Consulta", "0,91 s", "1,0 s"],
], { x: 6.4, y: 2.05, w: 3.1, colW: [1.1, 1.0, 1.0], fontSize: 11, color: C.text1, rowH: 0.34,
  border: { type: "solid", pt: 0.75, color: "E3D5FF" }, objectName: "Tabla optimización" });
s.addText("La compactación funciona, pero con 74 MB manda el arranque de serverless: el tiempo no baja.",
  { x: 6.4, y: 3.55, w: 3.1, h: 0.8, fontSize: 10.5, italic: true, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
s.addNotes("Después de los tres días, Silver tiene 1.240 eventos válidos, 11 rechazados cada uno con su motivo, 117 jugadores con 7 cambios de rango en el historial y 849,18 euros en ventas. Una tarea del Job compara cada capa con lo esperado y las diez comprobaciones salen bien. Además hay 19 tests con pytest que se ejecutan en GitHub Actions en cada push. En la optimización, la compactación pasa de 200 a 2 ficheros, pero el tiempo no mejora porque con 74 megas lo que pesa es el arranque de la consulta. Lo dejo documentado tal cual.");

// =============== 8 · CONCLUSIONES Y MEJORAS ===============
pres.addSection({ title: "Cierre" });
s = pres.addSlide({ masterName: "PORTADA", sectionTitle: "Cierre" });
s.addImage({ path: "lc.png", x: 2.5, y: 0.45, w: 5.0, h: 5.0 * 63 / 887, altText: "LEVEL COMPLETE", objectName: "Level complete" });
s.addText("Conclusiones y mejoras", { x: 1, y: 0.95, w: 8, h: 0.45, fontSize: 22, bold: true, color: "F3E8FF", align: "center", margin: 0, isTextBox: true });
const col = (x, titulo, items) => {
  s.addShape(pres.shapes.RECTANGLE, { x, y: 1.65, w: 4.3, h: 2.55, fill: { color: "14072B", transparency: 25 }, line: { color: "A855F7", width: 1 }, objectName: titulo });
  s.addText(titulo, { x: x + 0.25, y: 1.8, w: 3.8, h: 0.28, fontFace: MONO, bold: true, fontSize: 11, color: "FDE047", margin: 0, isTextBox: true });
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 12 }, breakLine: i < items.length - 1 } })),
    { x: x + 0.25, y: 2.2, w: 3.85, h: 2.2, fontSize: 12.5, color: "F3E8FF", valign: "top", margin: 0, paraSpaceAfter: 5, isTextBox: true });
};
col(0.5, "LO QUE ME LLEVO", [
  "Auto Loader resuelve la carga incremental y el schema drift",
  "La SCD2 permite contar cada compra con el rango de ese día",
  "No borrar los datos malos: guardarlos con su motivo",
  "Medir también cuando la mejora no se nota",
]);
col(5.2, "SIGUIENTE PARTIDA", [
  "Lakeflow Declarative Pipelines con expectations",
  "Asset Bundles para desplegar en dev y prod",
  "Dashboard y alertas sobre la calidad",
  "Más volumen para medir la optimización",
]);
s.addText("github.com/noeliaseguraherrero/respawn-dp750", { x: 1, y: 4.62, w: 8, h: 0.3, fontFace: MONO, bold: true, fontSize: 11,
  color: "F0ABFC", align: "center", margin: 0, isTextBox: true });
s.addNotes("Me llevo que Auto Loader facilita mucho la carga incremental, que la SCD2 es lo que permite contar cada compra con el rango que tenía el jugador ese día, que es mejor guardar los datos malos con su motivo que borrarlos, y que medir es importante aunque la mejora no se note. Como mejoras, pasaría el pipeline a Lakeflow Declarative Pipelines con expectations, usaría Asset Bundles para desplegar en varios entornos y montaría un dashboard con alertas. Todo el código y las instrucciones para reproducirlo están en el repositorio de GitHub.");

(async () => {
  const out = "respawn_dp750.pptx";
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("ok", out);
})();
