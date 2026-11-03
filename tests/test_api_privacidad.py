"""
API: consentimiento, derechos ARCO (acceso, rectificación, cancelación) y registro de
tokens por consulta. Usa SQLite temporal y un agente simulado (no llama a Gemini).
"""

import pytest
from flask import Flask

from backend.agent.state import EstadoAgente
from backend.controllers import auth_controller, chat_controller
from backend.database import crear_tablas
from backend.routes import api

CODIGOS = {}


@pytest.fixture(scope="module")
def cliente():
    crear_tablas()
    app = Flask(__name__)
    app.register_blueprint(api)
    return app.test_client()


@pytest.fixture(autouse=True)
def simulaciones(monkeypatch):
    monkeypatch.setattr(auth_controller, "enviar_codigo",
                        lambda email, nombre, codigo: CODIGOS.__setitem__(email, codigo))

    def agente_falso(mensaje, perfil, historial=None):
        return EstadoAgente(mensaje=mensaje, perfil=perfil, respuesta="Te recomiendo Hades.",
                            tokens_entrada=1200, tokens_salida=80)
    monkeypatch.setattr(chat_controller, "ejecutar_agente", agente_falso)


def _registrar(cliente, nombre, email, password="clave-segura-123", acepta=True):
    return cliente.post("/api/auth/register", json={"nombre": nombre, "email": email,
                                                     "password": password, "acepta_privacidad": acepta})


def _cuenta_lista(cliente, nombre, email, password="clave-segura-123"):
    assert _registrar(cliente, nombre, email, password).status_code == 201
    r = cliente.post("/api/auth/verificar", json={"email": email, "codigo": CODIGOS[email]})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def test_sin_aceptar_la_politica_no_se_crea_la_cuenta(cliente):
    r = _registrar(cliente, "Sin Consentimiento", "sin@prueba.cl", acepta=False)
    assert r.status_code == 400 and r.get_json()["campo"] == "acepta_privacidad"


def test_chat_guarda_los_tokens_informados_por_gemini(cliente):
    h = _cuenta_lista(cliente, "Tokens", "tokens@prueba.cl")
    r = cliente.post("/api/chat", json={"mensaje": "un roguelike"}, headers=h)
    meta = r.get_json()["meta"]
    assert meta["tokens_entrada"] == 1200 and meta["tokens_salida"] == 80
    datos = cliente.get("/api/cuenta/datos", headers=h).get_json()
    assert datos["historial_chat"][0]["respuesta"] == "Te recomiendo Hades."


def test_derecho_de_acceso_exporta_todo_sin_secretos(cliente):
    h = _cuenta_lista(cliente, "Acceso", "acceso@prueba.cl")
    r = cliente.get("/api/cuenta/datos", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers["Content-Disposition"]
    datos = r.get_json()
    assert datos["usuario"]["email"] == "acceso@prueba.cl"
    assert datos["usuario"]["acepta_privacidad_en"]               # consentimiento registrado
    texto = r.get_data(as_text=True)
    assert "password" not in texto and "codigo_hash" not in texto


def test_derecho_de_cancelacion_del_historial(cliente):
    h = _cuenta_lista(cliente, "Historial", "historial@prueba.cl")
    cliente.post("/api/chat", json={"mensaje": "hola"}, headers=h)
    r = cliente.delete("/api/chat/historial", headers=h)
    assert r.get_json()["borradas"] == 1
    assert cliente.get("/api/chat/historial", headers=h).get_json()["historial"] == []


def test_eliminar_cuenta_pide_la_contrasena_y_borra_todo(cliente):
    h = _cuenta_lista(cliente, "Eliminar", "eliminar@prueba.cl")
    cliente.post("/api/chat", json={"mensaje": "hola"}, headers=h)
    assert cliente.delete("/api/cuenta", json={"password": "otra"}, headers=h).status_code == 403
    assert cliente.delete("/api/cuenta", json={"password": "clave-segura-123"}, headers=h).status_code == 200
    # el token ya no sirve y el login falla
    assert cliente.get("/api/auth/me", headers=h).status_code in (401, 404)
    r = cliente.post("/api/auth/login", json={"email": "eliminar@prueba.cl", "password": "clave-segura-123"})
    assert r.status_code == 401


def test_las_rutas_arco_exigen_sesion(cliente):
    assert cliente.get("/api/cuenta/datos").status_code == 401
    assert cliente.delete("/api/cuenta").status_code == 401
    assert cliente.delete("/api/chat/historial").status_code == 401
