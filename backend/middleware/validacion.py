"""Validación de datos de entrada (se repite en backend por si alguien manipula el frontend)."""

import re
import unicodedata
from datetime import date

PALABRAS_PROHIBIDAS = {
    'puto', 'puta', 'mierda', 'verga', 'cabron', 'pendejo', 'culero', 'marica', 'maricon',
    'coño', 'joder', 'polla', 'ctm', 'hdp', 'conchesumadre',
    'fuck', 'shit', 'bitch', 'asshole', 'dick', 'cunt', 'nigger', 'faggot', 'retard',
    'porn', 'porno', 'xxx'
}

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RE_NOMBRE = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'-]+$")


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def nombre_apropiado(nombre: str) -> bool:
    limpio = nombre.lower().strip()
    palabras = re.split(r"[\s\-_.]+", limpio) + re.split(r"[\s\-_.]+", _sin_tildes(limpio))
    return not any(p in PALABRAS_PROHIBIDAS for p in palabras)


def validar_nombre(nombre: str) -> str | None:
    n = (nombre or "").strip()
    if len(n) < 2:
        return "El nombre debe tener al menos 2 letras."
    if len(n) > 30:
        return "Máximo 30 caracteres."
    if not RE_NOMBRE.match(n):
        return "Solo letras, espacios, guiones y apóstrofes."
    if not nombre_apropiado(n):
        return "Por favor usa un nombre apropiado."
    return None


def validar_email(email: str) -> str | None:
    if not email or len(email) > 120 or not RE_EMAIL.match(email):
        return "Correo electrónico inválido."
    return None


def validar_password(password: str) -> str | None:
    if not password or len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if len(password) > 128:
        return "La contraseña es demasiado larga."
    return None


def validar_codigo(codigo: str) -> str | None:
    if not codigo or not re.fullmatch(r"\d{6}", codigo):
        return "El código tiene 6 dígitos."
    return None


def validar_fecha_nacimiento(texto: str) -> tuple[date | None, str | None]:
    """Devuelve (fecha, error). Texto vacío = sin fecha."""
    if not texto:
        return None, None
    try:
        f = date.fromisoformat(texto)
    except ValueError:
        return None, "Fecha inválida."
    hoy = date.today()
    edad = hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day))
    if edad < 6 or edad > 120:
        return None, "¿Seguro que esa es tu fecha?"
    return f, None


def validar_lista(valores, permitidos: list[str]) -> list[str]:
    """Filtra una lista para dejar solo opciones conocidas."""
    if not isinstance(valores, list):
        return []
    return [v for v in valores if isinstance(v, str) and v in permitidos]
