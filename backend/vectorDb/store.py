"""
Conexión a la base vectorial (ChromaDB) y al modelo de embeddings.
Se cargan una sola vez (perezosamente) y se reutilizan en cada consulta.
"""

from backend.config import CARPETA_DB_VECTORIAL, NOMBRE_COLECCION, MODELO_EMBED

_coleccion = None
_modelo = None
_cargado = False


def cargar_modelo():
    """Carga el modelo de embeddings (lo usan la ingesta y las consultas)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO_EMBED)


def _prefijo(tipo: str) -> str:
    # Los modelos E5 se entrenaron con "query: " para preguntas y "passage: " para
    # documentos; sin ese prefijo la búsqueda empeora.
    return f"{tipo}: " if "e5" in MODELO_EMBED.lower() else ""


def vectorizar_documentos(modelo, textos: list[str]):
    return modelo.encode([_prefijo("passage") + t for t in textos],
                         normalize_embeddings=True, show_progress_bar=True, batch_size=32)


def vectorizar_consulta(modelo, texto: str) -> list[float]:
    return modelo.encode(_prefijo("query") + texto, normalize_embeddings=True).tolist()


def _cargar():
    global _coleccion, _modelo, _cargado
    if _cargado:
        return
    _cargado = True
    try:
        import chromadb
        db = chromadb.PersistentClient(path=CARPETA_DB_VECTORIAL)
        _coleccion = db.get_collection(NOMBRE_COLECCION)
        print(f"✓ Base de conocimiento cargada: {_coleccion.count()} fragmentos")
        modelo_base = (_coleccion.metadata or {}).get("modelo")
        if modelo_base != MODELO_EMBED:
            print(f"✗ OJO: la base vectorial se creó con el modelo '{modelo_base or 'all-MiniLM-L6-v2 (antiguo)'}'")
            print(f"  pero ahora se usa '{MODELO_EMBED}'. Las búsquedas no funcionarán bien.")
            print("  Reconstrúyela con:  python -m backend.vectorDb.ingest")
    except Exception as e:
        print(f"✗ Error cargando ChromaDB: {e}")
        print("  Falta la base de conocimiento en data/kira_db. Créala con:")
        print("  python -m backend.vectorDb.ingest")
    try:
        _modelo = cargar_modelo()
        print(f"✓ Modelo de embeddings cargado: {MODELO_EMBED}")
    except Exception as e:
        print(f"✗ Error cargando modelo de embeddings: {e}")


def obtener_coleccion():
    _cargar()
    return _coleccion


def obtener_modelo_embeddings():
    _cargar()
    return _modelo
