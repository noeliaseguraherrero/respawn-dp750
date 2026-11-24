"""Configuración común de pytest: Spark local con el modo ANSI activado (igual que serverless)."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


@pytest.fixture(scope="session")
def spark():
    from pyspark.sql import SparkSession
    sesion = (SparkSession.builder.master("local[1]")
              .appName("respawn-tests")
              .config("spark.sql.ansi.enabled", "true")
              .config("spark.sql.shuffle.partitions", "1")
              .config("spark.ui.enabled", "false")
              .getOrCreate())
    sesion.sparkContext.setLogLevel("ERROR")
    yield sesion
    sesion.stop()


@pytest.fixture(scope="session")
def datos_generados(tmp_path_factory):
    """Genera los 3 días de datos con la semilla 42 en una carpeta temporal."""
    import subprocess
    salida = tmp_path_factory.mktemp("sample")
    subprocess.run([sys.executable, str(RAIZ / "src" / "generador_datos.py"),
                    "--salida", str(salida), "--semilla", "42"],
                   check=True, capture_output=True)
    return salida
