"""
Middleware de autenticación con JWT.
Uso:  @login_requerido  sobre cualquier controlador que necesite sesión.
El id del usuario queda disponible en  g.usuario_id
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify, g

from backend.config import JWT_SECRET, JWT_EXPIRA_HORAS


def crear_token(usuario_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {"sub": str(usuario_id), "iat": ahora, "exp": ahora + timedelta(hours=JWT_EXPIRA_HORAS)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def login_requerido(f):
    @wraps(f)
    def envoltura(*args, **kwargs):
        cabecera = request.headers.get("Authorization", "")
        if not cabecera.startswith("Bearer "):
            return jsonify({"error": "Debes iniciar sesión."}), 401
        token = cabecera.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            g.usuario_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Tu sesión expiró, vuelve a iniciar sesión."}), 401
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return jsonify({"error": "Sesión inválida."}), 401
        # Tokens emitidos antes de exigir verificación no sirven si el correo no está confirmado.
        from backend.services.usuario_service import obtener_por_id
        usuario = obtener_por_id(g.usuario_id)
        if not usuario:
            return jsonify({"error": "Sesión inválida."}), 401
        if not usuario.email_verificado:
            return jsonify({"error": "Debes verificar tu correo.", "pendiente_verificacion": True,
                            "email": usuario.email}), 403
        return f(*args, **kwargs)
    return envoltura
