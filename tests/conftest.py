"""
Configuración común de las pruebas.

Las pruebas NO necesitan el .env, MySQL, ChromaDB ni internet:
  - las variables se ponen aquí (antes de importar backend.config)
  - la base relacional es SQLite en un archivo temporal
  - las APIs externas se simulan (mocks)

Uso (desde la carpeta raíz kira/):
    python -m pytest -v
"""

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

_db = Path(tempfile.gettempdir()) / "kira_pruebas.sqlite"
if _db.exists():
    _db.unlink()

os.environ["KIRA_PRUEBAS"] = "1"          # no leer el .env real
os.environ.setdefault("JWT_SECRET", "secreto-solo-para-pruebas-0123456789abcdef")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["SMTP_USUARIO"] = ""          # modo consola: no envía correos
os.environ["GEMINI_API_KEY"] = ""
os.environ["ENMASCARAR_PII"] = "1"
