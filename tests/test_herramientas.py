"""
Validación del Tool Calling: la herramienta de precios se invoca con un esquema
validado, maneja las caídas de las APIs externas y respeta el privilegio mínimo.
Las APIs se simulan con mocks: las pruebas no salen a internet.
"""

import pytest
import requests

from backend.agent import tools
from backend.agent.tools import ErrorHerramienta, describir_herramientas, invocar, validar_argumentos
from backend.agent.tools import precios


class RespuestaFalsa:
    def __init__(self, datos, status=200):
        self._datos, self.status_code = datos, status

    def json(self):
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error")


@pytest.fixture(autouse=True)
def sin_cache(monkeypatch):
    precios._cache.clear()
    precios._tiendas.clear()
    monkeypatch.setattr(precios, "ITAD_API_KEY", "")


def _api_falsa(url, params=None, **kwargs):
    if url.endswith("/stores"):
        return RespuestaFalsa([{"storeID": "1", "storeName": "Steam"}, {"storeID": "7", "storeName": "GOG"}])
    if "cheapshark" in url and params and "title" in params:
        return RespuestaFalsa([{"gameID": "99", "external": "Hollow Knight", "steamAppID": "367520"}])
    if "cheapshark" in url and params and "id" in params:
        return RespuestaFalsa({"info": {"title": "Hollow Knight", "steamAppID": "367520"},
                               "deals": [{"storeID": "7", "price": "7.49", "retailPrice": "14.99", "savings": "50"}],
                               "cheapestPriceEver": {"price": "4.99", "date": 1700000000}})
    if "steampowered" in url:
        return RespuestaFalsa({"367520": {"success": True, "data": {"price_overview": {
            "final_formatted": "CLP 5.375", "initial_formatted": "CLP 10.750", "discount_percent": 50,
            "currency": "CLP"}}}})
    raise AssertionError(f"URL inesperada: {url}")


# ---------------------------------------------------------------- esquema
def test_la_herramienta_se_declara_como_en_mcp():
    lista = describir_herramientas()
    assert lista[0]["name"] == "consultar_precios"
    assert lista[0]["inputSchema"]["required"] == ["nombre"]


@pytest.mark.parametrize("argumentos, error", [
    ({}, "falta el parámetro obligatorio"),
    ({"nombre": ""}, "vacío"),
    ({"nombre": 123}, "debe ser string"),
    ({"nombre": "Hades", "appid": "abc"}, "formato"),
    ({"nombre": "Hades", "borrar_todo": True}, "no permitido"),
    ({"nombre": "x" * 500}, "demasiado largo"),
])
def test_argumentos_invalidos_se_rechazan_sin_ejecutar(argumentos, error, monkeypatch):
    monkeypatch.setattr(precios.requests, "get", lambda *a, **k: pytest.fail("no debía llamar a la API"))
    with pytest.raises(ErrorHerramienta, match=error):
        invocar("consultar_precios", argumentos)


def test_herramienta_desconocida_se_rechaza():
    with pytest.raises(ErrorHerramienta):
        invocar("ejecutar_comando", {"cmd": "rm -rf /"})


def test_argumentos_validos_pasan_el_esquema():
    esquema = tools.HERRAMIENTAS["consultar_precios"]["inputSchema"]
    assert validar_argumentos(esquema, {"nombre": "Hades", "appid": "1145360"}) == []
    assert validar_argumentos(esquema, {"nombre": "Hades", "appid": 1145360}) == []


# ---------------------------------------------------------------- ejecución
def test_llamada_correcta_devuelve_precios(monkeypatch):
    monkeypatch.setattr(precios.requests, "get", _api_falsa)
    r = invocar("consultar_precios", {"nombre": "Hollow Knight", "appid": None})
    assert r["ok"] is True
    assert "CLP 5.375" in r["resultado"] and "GOG" in r["resultado"] and "US$ 4.99" in r["resultado"]


def test_si_la_api_responde_500_kira_sigue(monkeypatch):
    monkeypatch.setattr(precios.requests, "get", lambda *a, **k: RespuestaFalsa({}, status=500))
    r = invocar("consultar_precios", {"nombre": "Hollow Knight"})
    assert r["ok"] is True                       # la herramienta se degrada, no se cae
    assert "no se encontraron precios" in r["resultado"]


def test_si_la_api_no_responde_kira_sigue(monkeypatch):
    def timeout(*a, **k):
        raise requests.Timeout("tiempo agotado")
    monkeypatch.setattr(precios.requests, "get", timeout)
    r = invocar("consultar_precios", {"nombre": "Hollow Knight"})
    assert "no se encontraron precios" in r["resultado"]


def test_error_inesperado_de_la_herramienta_no_rompe_el_chat(monkeypatch):
    def explota(**kwargs):
        raise RuntimeError("bug")
    monkeypatch.setitem(tools.HERRAMIENTAS["consultar_precios"], "funcion", explota)
    r = invocar("consultar_precios", {"nombre": "Hades"})
    assert r["ok"] is False and r["resultado"] == "" and "RuntimeError" in r["error"]


# ---------------------------------------------------------------- privilegio mínimo
def test_solo_puede_conectarse_a_dominios_permitidos():
    with pytest.raises(PermissionError):
        precios._get("https://sitio-malicioso.com/robar")


@pytest.mark.parametrize("mensaje, esperado", [
    ("¿cuánto cuesta Hades?", True),
    ("precio de Elden Ring", True),
    ("está en oferta Celeste?", True),
    ("¿vale la pena Hollow Knight?", False),
    ("requisitos de Cyberpunk 2077", False),
])
def test_la_herramienta_solo_se_usa_cuando_preguntan_precio(mensaje, esperado):
    assert precios.pregunta_por_precio(mensaje) is esperado
