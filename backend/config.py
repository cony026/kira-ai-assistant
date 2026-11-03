"""
Configuración central de Kira IA.
Todas las rutas de carpetas, llaves de API y parámetros viven aquí,
para que ningún otro archivo tenga que leer el .env por su cuenta.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent   # carpeta kira/
ARCHIVO_ENV = RAIZ_PROYECTO / ".env"
if ARCHIVO_ENV.exists() and os.getenv("KIRA_PRUEBAS") != "1":
    # (las pruebas automáticas no leen el .env: usan SQLite y no tocan MySQL ni Gemini)
    load_dotenv(dotenv_path=ARCHIVO_ENV, encoding="utf-8-sig", override=True)
elif not os.getenv("JWT_SECRET"):
    # En Docker (o en las pruebas) las variables llegan por el entorno, sin archivo .env.
    raise FileNotFoundError(
        f"No existe el archivo .env en {RAIZ_PROYECTO}\n"
        "  Copia .env.example como .env (con ese nombre exacto) y completa tus valores ahí."
    )

CARPETA_DATA = RAIZ_PROYECTO / "data"
CARPETA_DOCS = CARPETA_DATA / "documentos"                # fichas .txt (fuente del RAG)
CARPETA_DB_VECTORIAL = str(CARPETA_DATA / "kira_db")      # ChromaDB
CARPETA_FRONTEND = RAIZ_PROYECTO / "frontend"

# ---------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------
PORT = int(os.getenv("PORT", "5000"))
DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"

# ---------------------------------------------------------------------
# Base de datos relacional (usuarios, perfiles, historial)
# Formato MySQL: mysql+pymysql://usuario:clave@localhost:3306/kira
# ---------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/kira")

# ---------------------------------------------------------------------
# Seguridad (JWT)
# ---------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRA_HORAS = int(os.getenv("JWT_EXPIRA_HORAS", "24"))
if not JWT_SECRET:
    # Sin secreto propio cualquiera podría firmar tokens válidos.
    raise ValueError("Falta JWT_SECRET en el archivo .env (ver .env.example)")

# ---------------------------------------------------------------------
# Verificación de correo (código de 6 dígitos enviado por email)
# Con Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587 y una "contraseña de
# aplicación" (no la contraseña normal). Ver INSTALACION.md.
# Si SMTP_USUARIO está vacío, el código se muestra en la consola del servidor
# (modo desarrollo, sirve para probar sin configurar el correo).
# ---------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "").strip()
SMTP_CLAVE = os.getenv("SMTP_CLAVE", "").replace(" ", "").strip()   # Google la muestra con espacios
SMTP_REMITENTE = os.getenv("SMTP_REMITENTE", "").strip() or SMTP_USUARIO
CORREO_MODO_CONSOLA = not SMTP_USUARIO

CODIGO_MINUTOS_VALIDEZ = 15     # el código vence a los 15 minutos
CODIGO_MAX_INTENTOS = 5         # después hay que pedir uno nuevo
CODIGO_SEGUNDOS_REENVIO = 60    # espera mínima entre reenvíos

# ---------------------------------------------------------------------
# APIs externas
# ---------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "").strip()
# IGDB (catálogo de juegos): gratis con una app en https://dev.twitch.tv/console/apps
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID", "").strip()
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET", "").strip()
# IsThereAnyDeal (precios e históricos, opcional): https://isthereanydeal.com/apps/my/
ITAD_API_KEY = os.getenv("ITAD_API_KEY", "").strip()
# País para los precios en vivo (código de 2 letras: CL, AR, MX, US...)
PAIS_PRECIOS = os.getenv("PAIS_PRECIOS", "CL").strip().upper()

# ---------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------
MODELO_GENERACION = os.getenv("MODELO_GENERACION", "gemini-3.5-flash-lite")
# Temperatura baja = respuestas más fieles al contexto recuperado (menos "creatividad" inventada).
TEMPERATURA = float(os.getenv("TEMPERATURA", "0.3"))
# Modelo de embeddings (debe ser el mismo en ingesta y consulta).
# multilingual-e5-small: entiende español e inglés en el mismo espacio vectorial
# (la base está 95% en inglés y los usuarios preguntan en español) y lee hasta
# 512 tokens por fragmento. Antes: all-MiniLM-L6-v2 (solo inglés, 256 tokens).
# Si lo cambias, reconstruye la base:  python -m backend.vectorDb.ingest
MODELO_EMBED = os.getenv("MODELO_EMBED", "intfloat/multilingual-e5-small")
NOMBRE_COLECCION = "kira_juegos"
# Recuperación en dos etapas (ver agent/reranking.py):
#   1. se traen TOP_K_CANDIDATOS fragmentos por similitud de vectores
#   2. el re-ranking híbrido (vectores + BM25) los reordena y solo pasan TOP_K al LLM
# Antes se mandaban 8 fragmentos sin reordenar; con 5 bien elegidos la respuesta es
# igual de buena y se gastan bastantes menos tokens de entrada.
TOP_K_CANDIDATOS = int(os.getenv("TOP_K_CANDIDATOS", "20"))
TOP_K = int(os.getenv("TOP_K", "5"))
PESO_SEMANTICO = float(os.getenv("PESO_SEMANTICO", "0.6"))   # el resto (0.4) es BM25
# Tope de caracteres de contexto que se envía a Gemini (~4 caracteres = 1 token).
MAX_CARACTERES_CONTEXTO = int(os.getenv("MAX_CARACTERES_CONTEXTO", "5000"))
# Tamaño de cada fragmento en caracteres. El modelo de embeddings tiene un máximo de
# tokens por fragmento y corta el resto (con all-MiniLM-L6-v2 y 1500 caracteres el 52%
# quedaba cortado). 1000 caracteres de texto limpio caben con holgura.
TAM_CHUNK = 1000
SOLAPE = 150
# Distancia coseno (0 = idéntico, 2 = opuesto). Los fragmentos más lejanos que esto
# se descartan por poco relevantes. Para calibrarlo con tu base:
#     python -m backend.vectorDb.calibrar
UMBRAL_DISTANCIA_MAXIMA = float(os.getenv("UMBRAL_DISTANCIA_MAXIMA", "0.30"))

# ---------------------------------------------------------------------
# Privacidad (Ley 19.628 y Ley 21.719 de Protección de Datos Personales)
# ---------------------------------------------------------------------
# Enmascara RUT, correos, teléfonos, tarjetas y nombres de personas antes de enviar
# el mensaje a Gemini (ver services/privacidad.py). Solo para pruebas se puede apagar.
ENMASCARAR_PII = os.getenv("ENMASCARAR_PII", "1") == "1"
# Modelo de spaCy para detectar nombres de personas (NER). Si no está instalado,
# se usan solo las expresiones regulares.
MODELO_SPACY = os.getenv("MODELO_SPACY", "es_core_news_sm")
# El historial de chat se borra solo después de estos días (minimización de datos).
RETENCION_HISTORIAL_DIAS = int(os.getenv("RETENCION_HISTORIAL_DIAS", "180"))

# ---------------------------------------------------------------------
# Costos (USD por 1 millón de tokens, plan pagado de la API de Gemini).
# Fuente: https://ai.google.dev/pricing  (gemini-3.5-flash-lite, revisado el 31-10-2026)
# ---------------------------------------------------------------------
PRECIO_ENTRADA_MTOK = float(os.getenv("PRECIO_ENTRADA_MTOK", "0.30"))
PRECIO_SALIDA_MTOK = float(os.getenv("PRECIO_SALIDA_MTOK", "2.50"))
