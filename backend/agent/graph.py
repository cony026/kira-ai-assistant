"""
Flujo del agente RAG (equivale a graph.ts del ejemplo).

    mensaje ──► router ──┬──► (pregunta genérica sobre un juego) ──► pregunta qué quiere saber + opciones
                         │
                         └──► retrieve ──────────► generate ──► images ──► respuesta
                             (ChromaDB             (Gemini)    (Steam/IGDB/RAWG)
                              + tools/precios
                                si pregunta precio)
"""

from backend.agent.state import EstadoAgente
from backend.agent.nodes.router import router
from backend.agent.nodes.retrieve import retrieve
from backend.agent.nodes.generate import generate
from backend.agent.nodes.images import images

FLUJO = [retrieve, generate, images]


def ejecutar_agente(mensaje: str, perfil: dict, historial: list | None = None) -> EstadoAgente:
    estado = EstadoAgente(mensaje=mensaje, perfil=perfil or {}, historial=historial or [])
    estado = router(estado)
    if estado.aclaracion:          # el router ya respondió con una pregunta: no se llama al LLM
        return estado
    for nodo in FLUJO:
        estado = nodo(estado)
    return estado
