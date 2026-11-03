"""NODO 3 - Images: detecta juegos mencionados en la respuesta y trae sus portadas."""

from backend.agent.state import EstadoAgente
from backend.services.imagenes_service import obtener_imagenes_para_respuesta


def images(estado: EstadoAgente) -> EstadoAgente:
    estado.imagenes = obtener_imagenes_para_respuesta(estado.respuesta)
    return estado
