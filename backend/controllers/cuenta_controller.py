"""
Controlador de la cuenta: derechos ARCO de la Ley de Protección de Datos Personales.

    GET    /api/cuenta/datos   Acceso y portabilidad: descarga todos tus datos en JSON
    DELETE /api/cuenta         Cancelación: borra tu cuenta y todo tu historial
                               (pide la contraseña para confirmar)

La rectificación es PUT /api/perfil y el borrado del historial DELETE /api/chat/historial.
"""

from flask import request, jsonify, g

from backend.services import usuario_service
from backend.services.usuario_service import ErrorUsuario


def exportar_datos():
    try:
        datos = usuario_service.exportar_datos(g.usuario_id)
    except ErrorUsuario as e:
        return jsonify({"error": str(e)}), 404
    respuesta = jsonify(datos)
    respuesta.headers["Content-Disposition"] = "attachment; filename=mis_datos_kira.json"
    return respuesta


def eliminar_cuenta():
    data = request.get_json(silent=True) or {}
    try:
        usuario_service.eliminar_cuenta(g.usuario_id, data.get("password") or "")
    except ErrorUsuario as e:
        return jsonify({"error": str(e)}), 403 if "Contraseña" in str(e) else 404
    return jsonify({"ok": True, "mensaje": "Tu cuenta y tu historial fueron eliminados."})
