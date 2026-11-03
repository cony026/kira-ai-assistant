"""Controlador del chat: recibe la pregunta, ejecuta el agente RAG y guarda el historial."""

import time

from flask import request, jsonify, g

from backend.agent.graph import ejecutar_agente
from backend.services import usuario_service

MAX_LARGO_MENSAJE = 2000


def chat():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or "").strip()
    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400
    if len(mensaje) > MAX_LARGO_MENSAJE:
        return jsonify({"error": f"Máximo {MAX_LARGO_MENSAJE} caracteres."}), 400

    usuario = usuario_service.obtener_por_id(g.usuario_id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado."}), 404

    # El perfil sale de la base de datos, no del navegador (no se puede falsear).
    perfil = usuario.a_dict()

    # Memoria corta: últimos 2 turnos de los últimos 30 minutos
    turnos = usuario_service.ultimos_turnos(usuario.id)

    inicio = time.perf_counter()
    try:
        estado = ejecutar_agente(mensaje, perfil, turnos)
    except Exception as e:
        print(f"Error en el agente: {e.__class__.__name__}")   # sin el mensaje: podría traer datos personales
        return jsonify({"error": "Kira no pudo responder en este momento. Intenta de nuevo."}), 500
    latencia = int((time.perf_counter() - inicio) * 1000)

    usuario_service.guardar_chat(usuario.id, mensaje, estado.respuesta,
                                 estado.tokens_entrada, estado.tokens_salida, latencia)
    return jsonify({
        "respuesta": estado.respuesta, "imagenes": estado.imagenes, "opciones": estado.opciones,
        # trazabilidad (útil para la evaluación y la estimación de costos)
        "meta": {"tokens_entrada": estado.tokens_entrada, "tokens_salida": estado.tokens_salida,
                 "latencia_ms": latencia, "fragmentos": len(estado.fragmentos),
                 "herramientas": estado.herramientas},
    })


def historial():
    return jsonify({"historial": usuario_service.historial(g.usuario_id)})


def borrar_historial():
    """Derecho de cancelación u oposición sobre el historial de conversaciones."""
    borradas = usuario_service.borrar_historial(g.usuario_id)
    return jsonify({"ok": True, "borradas": borradas})
