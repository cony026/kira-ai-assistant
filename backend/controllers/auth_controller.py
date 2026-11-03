"""
Controlador de autenticación: registrar, verificar correo, reenviar código,
iniciar sesión y usuario actual.

Flujo: registro → se envía un código de 6 dígitos al correo → el usuario lo
ingresa → recién ahí recibe su token y puede usar Kira. Así se confirma que
el correo existe y que pertenece a quien se registra.
"""

from flask import request, jsonify, g

from backend.middleware.auth_middleware import crear_token
from backend.middleware.validacion import validar_nombre, validar_email, validar_password, validar_codigo
from backend.services import usuario_service
from backend.services.usuario_service import ErrorUsuario
from backend.services.email_service import enviar_codigo, ErrorCorreo, CorreoInexistente
from backend.config import CORREO_MODO_CONSOLA


def _enviar(usuario):
    """Genera un código nuevo y lo envía. Devuelve (ok, mensaje_error).
    Si el servidor dice que la casilla no existe, deja pasar CorreoInexistente."""
    usuario, codigo = usuario_service.nuevo_codigo(usuario.id)
    try:
        enviar_codigo(usuario.email, usuario.nombre, codigo)
        return True, None
    except CorreoInexistente:
        usuario_service.anular_envio(usuario.id)
        raise
    except ErrorCorreo as e:
        usuario_service.anular_envio(usuario.id)
        return False, str(e)


def _pendiente(usuario, enviado: bool, error_envio: str | None, status: int):
    cuerpo = {
        "pendiente_verificacion": True,
        "email": usuario.email,
        "envio_ok": enviado,
        "mensaje": (f"Te enviamos un código de 6 dígitos a {usuario.email}."
                    if enviado else error_envio),
    }
    if CORREO_MODO_CONSOLA:
        cuerpo["modo_desarrollo"] = "SMTP no configurado: el código aparece en la consola del servidor."
    return jsonify(cuerpo), status


def registrar():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    acepta = data.get("acepta_privacidad") is True

    error = validar_nombre(nombre) or validar_email(email) or validar_password(password)
    if error:
        return jsonify({"error": error}), 400
    if not acepta:
        return jsonify({"error": "Para crear la cuenta debes aceptar la política de privacidad.",
                        "campo": "acepta_privacidad"}), 400

    try:
        usuario = usuario_service.registrar(nombre, email, password, acepta_privacidad=True)
    except ErrorUsuario as e:
        return jsonify({"error": str(e)}), 409
    try:
        enviado, error_envio = _enviar(usuario)
    except CorreoInexistente as e:
        # El correo no existe: no se deja la cuenta creada.
        usuario_service.eliminar_no_verificado(usuario.id)
        return jsonify({"error": str(e)}), 400
    except ErrorUsuario as e:          # se registró de nuevo antes de 60 s
        return _pendiente(usuario, True, None, 201)

    # Sin token todavía: primero hay que confirmar el correo.
    return _pendiente(usuario, enviado, error_envio, 201)


def verificar():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    codigo = (data.get("codigo") or "").strip()

    error = validar_email(email) or validar_codigo(codigo)
    if error:
        return jsonify({"error": error}), 400

    try:
        usuario = usuario_service.verificar_codigo(email, codigo)
    except ErrorUsuario as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"token": crear_token(usuario.id), "usuario": usuario.a_dict()})


def reenviar():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if validar_email(email):
        return jsonify({"error": "Correo inválido."}), 400

    usuario = usuario_service.obtener_por_email(email)
    if not usuario or usuario.email_verificado:
        # Respuesta neutra: no revela si el correo está registrado.
        return jsonify({"mensaje": "Si el correo tiene una cuenta pendiente, te enviamos un código nuevo."})
    try:
        enviado, error_envio = _enviar(usuario)
    except ErrorUsuario as e:          # esperar antes de reenviar
        return jsonify({"error": str(e)}), 429
    except CorreoInexistente as e:
        return jsonify({"error": str(e)}), 400
    return _pendiente(usuario, enviado, error_envio, 200)


def iniciar_sesion():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Ingresa correo y contraseña."}), 400

    usuario = usuario_service.autenticar(email, password)
    if not usuario:
        # Mensaje genérico: no revela si el correo existe.
        return jsonify({"error": "Correo o contraseña incorrectos."}), 401

    if not usuario.email_verificado:
        # Contraseña correcta pero correo sin confirmar: se manda un código nuevo.
        try:
            enviado, error_envio = _enviar(usuario)
        except ErrorUsuario:               # ya se envió uno hace poco: sirve el mismo
            enviado, error_envio = True, None
        except CorreoInexistente as e:
            enviado, error_envio = False, str(e)
        resp, _ = _pendiente(usuario, enviado, error_envio, 403)
        cuerpo = resp.get_json()
        cuerpo["error"] = "Debes verificar tu correo antes de entrar."
        return jsonify(cuerpo), 403

    return jsonify({"token": crear_token(usuario.id), "usuario": usuario.a_dict()})


def usuario_actual():
    usuario = usuario_service.obtener_por_id(g.usuario_id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado."}), 404
    return jsonify({"usuario": usuario.a_dict()})
