import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
ax.set_xlim(0, 160); ax.set_ylim(0, 90); ax.axis("off")
fig.patch.set_facecolor("white")
T = "#1f2937"; G = "#6b7280"

def caja(x, y, w, h, titulo, lineas, color, borde, tit_size=12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5",
                                fc=color, ec=borde, lw=1.6))
    ax.text(x + w/2, y + h - 3.2, titulo, ha="center", va="center", fontsize=tit_size, weight="bold", color=T)
    for i, l in enumerate(lineas):
        ax.text(x + w/2, y + h - 7.6 - i*3.1, l, ha="center", va="center", fontsize=8.6, color=T)

def flecha(x1, y1, x2, y2, texto=None, color="#374151", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                                 color=color, lw=1.6, linestyle=ls))
    if texto:
        ax.text((x1+x2)/2, (y1+y2)/2 + 1.8, texto, ha="center", fontsize=7.8, color=G, style="italic")

ax.text(80, 87, "Respawn · arquitectura del lakehouse", ha="center", fontsize=17, weight="bold", color=T)
ax.text(80, 83.2, "Databricks Free Edition · Unity Catalog (catálogo respawn) · cómputo serverless",
        ha="center", fontsize=10, color=G)

# Lakeflow Job band
ax.add_patch(FancyBboxPatch((24, 68), 132, 10, boxstyle="round,pad=0.4,rounding_size=1.5",
                            fc="#eef2ff", ec="#6366f1", lw=1.4, ls="--"))
ax.text(26, 75.6, "Lakeflow Job  respawn_simular_dia_de_juego", fontsize=10.5, weight="bold", color="#3730a3")
ax.text(26, 71.2, "01_ingesta_bronze ► 02_silver_calidad ► 03_merge_scd2 ► 04_gold_marts ► 06_validaciones",
        fontsize=9, color="#3730a3", family="monospace")
ax.text(154, 75.6, "parámetros: dia, inyectar_error", fontsize=8.3, color="#4338ca", ha="right")
ax.text(154, 71.2, "1 reintento/tarea · email si falla · 06:00 (pausa)", fontsize=8.3, color="#4338ca", ha="right")

# Source
caja(2, 32, 20, 30, "Origen", ["generador_datos.py", "(Python + Faker,", "semilla 42)", "", "data/sample/", "días 1, 2 y 3"],
     "#f3f4f6", "#9ca3af")
# Volume
caja(27, 32, 24, 30, "Volumen UC", ["bronze.raw_files", "", "_staging/  (00)", "landing/   (día N)", "_cuarentena/", "_checkpoints/"],
     "#fff7ed", "#f59e0b")
# Bronze
caja(56, 32, 24, 30, "Bronze", ["Auto Loader", "(incremental,", "schema drift)", "", "jugadores_raw", "eventos_raw", "articulos_raw"],
     "#fde7d9", "#c2410c")
# Silver
caja(85, 32, 28, 30, "Silver", ["limpieza + dedup (R6)", "reglas R1–R5", "eventos (MERGE)", "dim_jugador (SCD2, CDF)", "dim_articulo (SCD1)",
     "fact_partidas · fact_compras"], "#e5e7eb", "#6b7280")
# Gold
caja(118, 32, 22, 30, "Gold", ["join point-in-time", "", "mart_economia", "mart_retencion", "mart_competitivo"],
     "#fef3c7", "#ca8a04")
# Analysts
caja(144, 32, 14, 30, "Analistas", ["vistas", "v_*_analistas", "", "filtro por", "región", "email", "enmascarado"],
     "#dcfce7", "#16a34a", tit_size=10.5)

# Quality
caja(85, 8, 28, 18, "Quality", ["rechazos (con motivo)", "metricas_calidad", "validaciones_pipeline"], "#fee2e2", "#dc2626")
# Governance
caja(118, 8, 40, 18, "Gobierno (Unity Catalog)", ["grupos: analistas_eu / _na / pii", "GRANT · REVOKE · comentarios · etiquetas", "linaje automático"],
     "#ecfeff", "#0891b2")
# Repo
caja(2, 8, 49, 18, "Repositorio GitHub → Git folder", ["notebooks · sql · src · jobs/crear_job.py (SDK)", "tests con pytest + GitHub Actions",
     "config sin secretos"], "#f5f3ff", "#7c3aed")
caja(56, 8, 24, 18, "Optimización", ["silver.eventos_bench", "CLUSTER BY + OPTIMIZE", "200 → 2 ficheros"], "#f3f4f6", "#9ca3af")

y = 47
flecha(22.6, y, 26.6, y, "")
flecha(51.6, y, 55.6, y, "")
flecha(80.6, y, 84.6, y, "")
flecha(113.6, y, 117.6, y, "")
flecha(140.6, y, 143.6, y, "")
ax.text(24.6, y + 2, "00", fontsize=7.8, color=G, ha="center")
flecha(99, 31.6, 99, 26.6, color="#dc2626")
ax.text(100.5, 28.8, "inválidos", fontsize=7.8, color="#dc2626", style="italic")
ax.text(39, 29, "corrupto → cuarentena (falla el Job)", fontsize=7.6, color="#b45309", ha="center", style="italic")
flecha(26.5, 26.6, 26.5, 31.6, color="#7c3aed", ls="--")
plt.savefig("arquitectura.png", bbox_inches="tight", facecolor="white")
