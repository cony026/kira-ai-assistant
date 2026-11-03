"""
Definición de endpoints de la API (equivale a routes/index.ts del ejemplo).

  POST /api/auth/register     registrar cuenta
  POST /api/auth/verificar    confirmar el correo con el código de 6 dígitos (devuelve JWT)
  POST /api/auth/reenviar     enviar un código nuevo al correo
  POST /api/auth/login        iniciar sesión (devuelve JWT si el correo está verificado)
  GET  /api/auth/me           usuario actual                [login]
  PUT  /api/perfil            guardar perfil gamer          [login]
  POST /api/chat              consultar a Kira (RAG)        [login]
  GET  /api/chat/historial    últimas consultas             [login]
  DELETE /api/chat/historial  borrar mi historial           [login]  (derecho de cancelación)
  GET  /api/cuenta/datos      descargar mis datos (JSON)    [login]  (derecho de acceso)
  DELETE /api/cuenta          eliminar mi cuenta            [login]  (derecho de cancelación)
  GET  /api/noticias          noticias gaming (RSS)
  GET  /api/health            estado del servidor
"""

from flask import Blueprint

from backend.controllers import (auth_controller, perfil_controller, chat_controller,
                                 noticias_controller, cuenta_controller)
from backend.middleware.auth_middleware import login_requerido

api = Blueprint("api", __name__, url_prefix="/api")

api.post("/auth/register")(auth_controller.registrar)
api.post("/auth/verificar")(auth_controller.verificar)
api.post("/auth/reenviar")(auth_controller.reenviar)
api.post("/auth/login")(auth_controller.iniciar_sesion)
api.get("/auth/me")(login_requerido(auth_controller.usuario_actual))

api.put("/perfil")(login_requerido(perfil_controller.actualizar_perfil))

api.post("/chat")(login_requerido(chat_controller.chat))
api.get("/chat/historial")(login_requerido(chat_controller.historial))
api.delete("/chat/historial")(login_requerido(chat_controller.borrar_historial))

api.get("/cuenta/datos")(login_requerido(cuenta_controller.exportar_datos))
api.delete("/cuenta")(login_requerido(cuenta_controller.eliminar_cuenta))

api.get("/noticias")(noticias_controller.noticias)
api.get("/health")(noticias_controller.health)
