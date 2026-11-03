"""Estado que viaja entre los nodos del agente (equivale a state.ts del ejemplo)."""

from dataclasses import dataclass, field


@dataclass
class EstadoAgente:
    mensaje: str                                  # pregunta del usuario
    perfil: dict = field(default_factory=dict)    # nombre, edad, consolas, generos
    historial: list = field(default_factory=list) # últimos turnos [{mensaje, respuesta}] (memoria corta)
    contexto_rag: str = ""                        # fragmentos recuperados de ChromaDB
    respuesta: str = ""                           # texto final para el usuario
    imagenes: list = field(default_factory=list)  # portadas de juegos mencionados
    opciones: list = field(default_factory=list)  # botones sugeridos [{etiqueta, mensaje}]
    aclaracion: bool = False                      # True si el router respondió con una pregunta
    # Privacidad: enmascarador de datos personales de esta petición (services/privacidad.py)
    privacidad: object = None
    # Trazabilidad y costos: lo que informa Gemini en usage_metadata
    tokens_entrada: int = 0
    tokens_salida: int = 0
    fragmentos: list = field(default_factory=list)   # fragmentos usados [{id, fuente, juego_clave, puntaje}]
    herramientas: list = field(default_factory=list) # herramientas invocadas [{nombre, ok, ms}]
