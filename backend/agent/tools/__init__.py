"""
Herramientas que el agente puede usar (equivale a agent/tools/ del ejemplo).

A diferencia de la base vectorial (información que cambia poco y se carga una vez con
la ingesta), las herramientas consultan datos que cambian todo el tiempo, en el
momento en que el usuario pregunta:

    precios.py   precios actuales de un juego (Steam en tu país, tiendas de PC, históricos)

Cada herramienta se declara como en MCP (Model Context Protocol): nombre, descripción
y un esquema JSON de sus parámetros (inputSchema). Toda llamada pasa por invocar(),
que:
  1. valida los argumentos contra el esquema (si no cumplen, NO se ejecuta),
  2. ejecuta la herramienta con un tiempo máximo y atrapa cualquier error
     (si la API externa se cae, Kira responde igual, sin precios),
  3. deja un registro auditable de la llamada (nombre, argumentos, resultado, ms).

Privilegio mínimo: las herramientas solo LEEN datos públicos. No reciben datos del
usuario (solo el nombre del juego), no tienen acceso a MySQL ni a la clave de Gemini,
y solo pueden conectarse a los dominios de su lista blanca (precios.DOMINIOS_PERMITIDOS).
"""

import json
import re
import time

from backend.agent.tools.precios import consultar_precios


class ErrorHerramienta(Exception):
    """Llamada rechazada: herramienta desconocida o argumentos fuera del esquema."""


HERRAMIENTAS = {
    "consultar_precios": {
        "descripcion": "Precios actuales de un videojuego en Steam (moneda del país) y tiendas de PC, "
                       "con el precio más bajo histórico. Solo lectura.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "minLength": 1, "maxLength": 120,
                           "description": "Título del juego tal como aparece en la base"},
                "appid": {"type": ["string", "integer", "null"], "pattern": r"^\d{1,10}$",
                          "description": "Id de Steam, si se conoce"},
            },
            "required": ["nombre"],
            "additionalProperties": False,
        },
        "funcion": consultar_precios,
        "permisos": "lectura de APIs públicas de precios; sin datos del usuario ni acceso a la base",
    },
}

_TIPOS = {"string": str, "integer": int, "null": type(None), "object": dict}


def validar_argumentos(esquema: dict, argumentos) -> list[str]:
    """Validación simple de JSON Schema (los casos que usan nuestras herramientas)."""
    if not isinstance(argumentos, dict):
        return ["los argumentos deben ser un objeto JSON"]
    errores = []
    props = esquema.get("properties", {})
    for campo in esquema.get("required", []):
        if campo not in argumentos:
            errores.append(f"falta el parámetro obligatorio «{campo}»")
    if esquema.get("additionalProperties") is False:
        for campo in argumentos:
            if campo not in props:
                errores.append(f"parámetro no permitido «{campo}»")
    for campo, valor in argumentos.items():
        regla = props.get(campo)
        if not regla:
            continue
        tipos = regla["type"] if isinstance(regla["type"], list) else [regla["type"]]
        if not any(isinstance(valor, _TIPOS[t]) and not (t == "integer" and isinstance(valor, bool))
                   for t in tipos):
            errores.append(f"«{campo}» debe ser {' o '.join(tipos)}")
            continue
        if isinstance(valor, str):
            if len(valor.strip()) < regla.get("minLength", 0):
                errores.append(f"«{campo}» está vacío")
            if len(valor) > regla.get("maxLength", 10**6):
                errores.append(f"«{campo}» es demasiado largo")
        if valor is not None and "pattern" in regla and not re.match(regla["pattern"], str(valor)):
            errores.append(f"«{campo}» no tiene el formato esperado")
    return errores


def describir_herramientas() -> list[dict]:
    """Lista en formato MCP (tools/list): lo que se le mostraría a un LLM o a un cliente MCP."""
    return [{"name": n, "description": h["descripcion"], "inputSchema": h["inputSchema"]}
            for n, h in HERRAMIENTAS.items()]


def invocar(nombre: str, argumentos: dict) -> dict:
    """
    Ejecuta una herramienta. Nunca lanza errores de la API externa: devuelve
    {nombre, ok, resultado, error, ms}. Solo lanza ErrorHerramienta si la llamada
    misma es inválida (herramienta inexistente o argumentos que no cumplen el esquema).
    """
    herramienta = HERRAMIENTAS.get(nombre)
    if not herramienta:
        raise ErrorHerramienta(f"Herramienta desconocida: {nombre}")
    argumentos = {k: v for k, v in (argumentos or {}).items() if not (k != "nombre" and v is None)}
    errores = validar_argumentos(herramienta["inputSchema"], argumentos)
    if errores:
        raise ErrorHerramienta(f"Argumentos inválidos para {nombre}: " + "; ".join(errores))

    inicio = time.perf_counter()
    try:
        resultado, ok, error = herramienta["funcion"](**argumentos), True, None
    except Exception as e:                       # la API externa falló: se sigue sin herramienta
        resultado, ok, error = "", False, f"{e.__class__.__name__}: {e}"
    ms = int((time.perf_counter() - inicio) * 1000)
    print(f"  [herramienta] {json.dumps({'nombre': nombre, 'argumentos': argumentos, 'ok': ok, 'ms': ms, 'error': error}, ensure_ascii=False)}")
    return {"nombre": nombre, "ok": ok, "resultado": resultado or "", "error": error, "ms": ms}
