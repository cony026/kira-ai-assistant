"""Controlador de perfil: guardar nombre, fecha de nacimiento, consolas y géneros."""

from flask import request, jsonify, g

from backend.middleware.validacion import validar_nombre, validar_fecha_nacimiento, validar_lista
from backend.services import usuario_service
from backend.services.usuario_service import ErrorUsuario

CONSOLAS_OPCIONES = ['PC', 'PlayStation 5', 'PlayStation 4', 'Xbox Series X/S', 'Xbox One',
                     'Nintendo Switch', 'Móvil', 'Retro']
GENEROS_OPCIONES = ['Acción', 'Aventura', 'RPG', 'Shooter', 'Plataformas', 'Estrategia', 'Deportes',
                    'Carreras', 'Simulación', 'Puzzle', 'Terror', 'Indie', 'Sandbox', 'MMO']


def actualizar_perfil():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()

    error = validar_nombre(nombre)
    if error:
        return jsonify({"error": error, "campo": "nombre"}), 400

    fecha, error = validar_fecha_nacimiento(data.get("fecha_nacimiento") or "")
    if error:
        return jsonify({"error": error, "campo": "fecha_nacimiento"}), 400

    try:
        usuario = usuario_service.actualizar_perfil(
            g.usuario_id,
            nombre=nombre,
            fecha_nacimiento=fecha,
            consolas=validar_lista(data.get("consolas"), CONSOLAS_OPCIONES),
            generos=validar_lista(data.get("generos"), GENEROS_OPCIONES),
        )
    except ErrorUsuario as e:
        return jsonify({"error": str(e), "campo": "nombre"}), 409
    return jsonify({"usuario": usuario.a_dict()})
