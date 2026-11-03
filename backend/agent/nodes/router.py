"""
NODO 0 - Router: decide si la pregunta necesita una aclaración antes de responder.

Si la persona nombra un juego sin decir qué quiere saber («háblame de Elden Ring»,
«qué sabes de Hollow Knight», o solo «Hades»), Kira no responde con un párrafo
largo: pregunta qué le interesa y ofrece botones con las opciones. Esto se
resuelve sin llamar al LLM (más rápido y no gasta cuota).

Si la pregunta ya es específica («requisitos de Elden Ring», «Hades vs Celeste»),
el router no hace nada y el flujo sigue a retrieve → generate.
"""

import re

from backend.agent.state import EstadoAgente
from backend.services.imagenes_service import detectar_juegos_en_texto, obtener_imagenes_para_respuesta, _normalizar

# Palabras que no indican qué se quiere saber. Si, quitando el nombre del juego,
# solo quedan estas palabras, la pregunta es genérica.
PALABRAS_GENERICAS = {
    "que", "q", "sabes", "sabe", "de", "del", "sobre", "acerca", "hablame", "habla", "hablas",
    "cuentame", "cuenta", "dime", "decir", "puedes", "podrias", "me", "te", "info", "informacion",
    "datos", "el", "la", "los", "las", "un", "una", "juego", "videojuego", "conoces", "conoce",
    "y", "a", "hola", "kira", "quiero", "saber", "conocer", "por", "favor", "porfa", "algo",
    "explicame", "explica", "mas", "todo", "es", "esta", "eso", "ese", "tal", "tienes", "hay",
}

OPCIONES = [
    ("Reseña y nota", "¿Qué dicen las reseñas de {j} y qué nota tiene?"),
    ("Requisitos técnicos", "¿Cuáles son los requisitos técnicos de {j}?"),
    ("Plataformas y precio", "¿En qué plataformas está {j} y cuánto cuesta?"),
    ("Juegos parecidos", "Recomiéndame juegos parecidos a {j}"),
    ("¿Es para mí?", "¿{j} es una buena opción para mí según mi perfil?"),
]


def _palabras(texto: str) -> list[str]:
    # Misma normalización que la detección de juegos (sin tildes, apóstrofos ni plurales)
    return _normalizar(texto).split()


GENERICAS_NORM = {w for p in PALABRAS_GENERICAS for w in _palabras(p)}


def _parecidas(a: str, b: str) -> bool:
    """«rign» ~ «ring»: misma palabra con un error de tipeo."""
    if a == b:
        return True
    if min(len(a), len(b)) < 4:
        return False
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() >= 0.75


def es_pregunta_generica(mensaje: str, nombre_juego: str) -> bool:
    restantes = list(_palabras(mensaje))
    for p in _palabras(nombre_juego):
        igual = next((r for r in restantes if _parecidas(r, p)), None)
        if igual:
            restantes.remove(igual)
    return all(p in GENERICAS_NORM for p in restantes)


# «háblame de X», «qué sabes de X», «cuéntame sobre X»... para juegos que NO están en la base
RE_PEDIDO_GENERAL = re.compile(
    r"^\s*(?:hola\s*,?\s*)?(?:kira\s*,?\s*)?"
    r"(?:h[aá]blame|cu[eé]ntame|dime algo|qu[eé] sabes|que me puedes decir|info(?:rmaci[oó]n)?)"
    r"\s+(?:de|del|sobre|acerca de)\s+(?:el\s+|la\s+|los\s+|las\s+)?(?:juego\s+|videojuego\s+)?"
    r"(?P<juego>.+?)\s*[?!.¿¡]*\s*$",
    re.IGNORECASE,
)
# Si el "nombre" contiene estas palabras, no es un juego puntual (ej. «juegos de terror»)
NO_ES_UN_JUEGO = {"juego", "videojuego", "algun", "alguno", "mejor", "nuevo", "genero", "tipo",
                  "consola", "plataforma", "recomendacion", "lanzamiento", "noticia", "requisito",
                  "nota", "precio", "estreno", "saga"}


def juego_no_indexado(mensaje: str) -> str | None:
    m = RE_PEDIDO_GENERAL.match(mensaje)
    if not m:
        return None
    nombre = m.group("juego").strip(" \"'«»")
    palabras = _palabras(nombre)
    if not palabras or len(palabras) > 7 or any(p in NO_ES_UN_JUEGO for p in palabras):
        return None
    return nombre.title() if nombre.islower() else nombre


def router(estado: EstadoAgente) -> EstadoAgente:
    juegos = detectar_juegos_en_texto(estado.mensaje, max_juegos=2, tolerar_errores=True)
    if len(juegos) == 1:
        juego = juegos[0]["nombre"]
        if not es_pregunta_generica(estado.mensaje, juego):
            return estado                   # ya dijo qué quiere saber
    elif not juegos:
        juego = juego_no_indexado(estado.mensaje)   # «háblame de X» con un juego que no está en la base
        if not juego:
            return estado
    else:
        return estado                       # varios juegos (comparación): sigue el flujo normal

    nombre = (estado.perfil.get("nombre") or "").strip()
    saludo = f"¡Buena elección, {nombre}!" if nombre else "¡Buena elección!"
    estado.respuesta = (
        f"{saludo} Antes de contarte sobre {juego}, ¿qué te gustaría saber?\n\n"
        "Puedo hablarte de su reseña y nota, sus requisitos técnicos, en qué plataformas está "
        "y cuánto cuesta, juegos parecidos, o si es una buena opción para ti según tu perfil."
    )
    estado.opciones = [{"etiqueta": e, "mensaje": m.format(j=juego)} for e, m in OPCIONES]
    estado.imagenes = obtener_imagenes_para_respuesta(juego)
    estado.aclaracion = True
    return estado