"""
NODO 1 - Retrieve: busca los fragmentos más relevantes en ChromaDB.

Búsqueda en dos partes (combina lo léxico con lo semántico):
  1. Si la pregunta nombra un juego (aunque esté mal escrito: «asassins creed shadow»),
     se traen primero los fragmentos de ESE juego, filtrando por el metadato "juego_clave".
  2. Se completa con la búsqueda semántica normal (vectores) sobre toda la base.
  3. Re-ranking híbrido (vectores + BM25) y compactación: de ~20 candidatos solo los
     5 mejores llegan al LLM (agent/reranking.py). Así se gastan menos tokens.
  4. Si la pregunta es sobre precios, se usa la herramienta de precios en vivo
     (agent/tools/precios.py): los precios no se guardan en la base porque cambian a diario.
"""

from backend.agent.state import EstadoAgente
from backend.agent.reranking import compactar_contexto, reordenar
from backend.agent.tools import invocar
from backend.agent.tools.precios import pregunta_por_precio
from backend.config import TOP_K, TOP_K_CANDIDATOS, UMBRAL_DISTANCIA_MAXIMA
from backend.vectorDb.store import obtener_coleccion, obtener_modelo_embeddings, vectorizar_consulta
from backend.services.imagenes_service import detectar_juegos_en_texto, _normalizar

# De los candidatos, cuántos pueden venir del juego nombrado
MAX_DEL_JUEGO = 8


def _consultar(coleccion, vector, n, filtro=None):
    """Devuelve [(id, documento, metadatos, distancia)]."""
    resultados = coleccion.query(
        query_embeddings=[vector],
        n_results=n,
        where=filtro,
        include=["documents", "metadatas", "distances"],
    )
    if not resultados["ids"] or not resultados["ids"][0]:
        return []
    return list(zip(resultados["ids"][0], resultados["documents"][0],
                    resultados["metadatas"][0], resultados["distances"][0]))


def recuperar_fragmentos(pregunta: str, top_k: int = TOP_K, juegos: list | None = None) -> list[dict]:
    """
    Recuperación en dos etapas: candidatos (vectores + filtro por juego) -> re-ranking
    híbrido -> compactación. Devuelve [{id, documento, metadatos, distancia, puntaje}].
    La usan el agente y la evaluación (backend/evaluacion/evaluar_rag.py).
    """
    coleccion = obtener_coleccion()
    modelo = obtener_modelo_embeddings()
    if not coleccion or not modelo:
        return []

    nombres = [j["nombre"] for j in (juegos or [])]
    # El nombre correcto se agrega a la consulta: el vector queda más cerca del juego real
    consulta = f"{pregunta} {' '.join(nombres)}" if nombres else pregunta
    vector = vectorizar_consulta(modelo, consulta)

    candidatos, ids = [], set()
    if nombres:
        claves = [_normalizar(n) for n in nombres]
        filtro = {"juego_clave": claves[0]} if len(claves) == 1 else {"juego_clave": {"$in": claves}}
        for id_, doc, meta, dist in _consultar(coleccion, vector, MAX_DEL_JUEGO, filtro):
            candidatos.append({"id": id_, "documento": doc, "metadatos": meta, "distancia": dist, "del_juego": True})
            ids.add(id_)

    for id_, doc, meta, dist in _consultar(coleccion, vector, TOP_K_CANDIDATOS):
        if id_ in ids or (dist is not None and dist > UMBRAL_DISTANCIA_MAXIMA):
            continue
        candidatos.append({"id": id_, "documento": doc, "metadatos": meta, "distancia": dist, "del_juego": False})
        ids.add(id_)

    mejores = compactar_contexto(reordenar(consulta, candidatos, top_k))
    for f in mejores:
        print(f"  [RAG] puntaje={f['puntaje']:.2f}  distancia={f['distancia']:.3f}  "
              f"fuente={f['metadatos'].get('fuente')}")
    print(f"  [RAG] {len(candidatos)} candidatos -> {len(mejores)} fragmentos al LLM "
          f"({sum(len(f['documento']) for f in mejores)} caracteres)")
    return mejores


def formatear_contexto(pregunta: str, fragmentos: list[dict], juegos: list | None = None) -> str:
    nombres = [j["nombre"] for j in (juegos or [])]
    contextos = []
    # Si el usuario escribió mal el nombre, se le avisa al LLM a qué juego se refiere
    mal_escritos = [n for n in nombres if f" {_normalizar(n)} " not in f" {_normalizar(pregunta)} "]
    if mal_escritos:
        contextos.append("Nota: el usuario escribió el nombre con errores; se refiere a: "
                         + ", ".join(f"«{n}»" for n in mal_escritos) + ".")
    for f in fragmentos:
        contextos.append(f"[{f['metadatos'].get('fuente', 'desconocido')}] {f['documento']}")
    return "\n\n".join(contextos)


def buscar_contexto(pregunta: str, top_k: int = TOP_K, juegos: list | None = None) -> str:
    """Los fragmentos relevantes como un solo texto para el prompt."""
    try:
        return formatear_contexto(pregunta, recuperar_fragmentos(pregunta, top_k, juegos), juegos)
    except Exception as e:
        print(f"Error en búsqueda vectorial: {e}")
        return ""


def consulta_de_busqueda(estado: EstadoAgente) -> str:
    """
    Si el mensaje es una respuesta corta de seguimiento que no nombra ningún juego
    («los requisitos», «y la nota?»), se busca junto con el último mensaje del usuario
    que sí nombró un juego.
    """
    if len(estado.mensaje.split()) > 6 or detectar_juegos_en_texto(estado.mensaje, 1, tolerar_errores=True):
        return estado.mensaje
    for turno in reversed(estado.historial):
        if detectar_juegos_en_texto(turno["mensaje"], 1, tolerar_errores=True):
            return f"{turno['mensaje']} {estado.mensaje}"
    return estado.mensaje


def retrieve(estado: EstadoAgente) -> EstadoAgente:
    consulta = consulta_de_busqueda(estado)
    juegos = detectar_juegos_en_texto(consulta, max_juegos=3, tolerar_errores=True)
    if juegos:
        print(f"  [RAG] juegos detectados: {[j['nombre'] for j in juegos]}")
    try:
        fragmentos = recuperar_fragmentos(consulta, juegos=juegos)
    except Exception as e:
        print(f"Error en búsqueda vectorial: {e}")
        fragmentos = []
    estado.fragmentos = [{"id": f["id"], "fuente": f["metadatos"].get("fuente"),
                          "juego_clave": f["metadatos"].get("juego_clave"), "puntaje": f["puntaje"]}
                         for f in fragmentos]
    estado.contexto_rag = formatear_contexto(consulta, fragmentos, juegos)

    # Herramienta: precios en vivo (solo si pregunta por precios y nombró un juego).
    # Se invoca por el registro de herramientas, que valida los argumentos contra su
    # esquema y deja registro de cada llamada (agent/tools/__init__.py).
    if juegos and pregunta_por_precio(estado.mensaje):
        bloques = []
        for juego in juegos[:2]:
            llamada = invocar("consultar_precios", {"nombre": juego["nombre"], "appid": juego.get("appid")})
            estado.herramientas.append({k: llamada[k] for k in ("nombre", "ok", "ms")})
            bloques.append(llamada["resultado"])
        bloque = "\n\n".join(b for b in bloques if b)
        if bloque:
            estado.contexto_rag = f"{bloque}\n\n{estado.contexto_rag}".strip()
    return estado
