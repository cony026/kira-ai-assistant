"""
HERRAMIENTA - Precios en vivo.

Los precios cambian todos los días (ofertas, rebajas), así que NO se guardan en la base
vectorial: se consultan en el momento en que el usuario pregunta "¿cuánto cuesta X?".
Así la respuesta nunca queda desactualizada (fase 4 de la arquitectura RAG:
obsolescencia de los datos).

Fuentes:
  - Steam (tienda oficial)  precio en la moneda del país configurado (PAIS_PRECIOS, ej. CL)
                            Sin API key.
  - CheapShark              precio en distintas tiendas de PC (Steam, GOG, Epic, Humble...)
                            en dólares, y el precio más bajo de la historia. Sin API key.
  - IsThereAnyDeal          precios por tienda en tu país y mínimo histórico.
                            Opcional: solo si hay ITAD_API_KEY en el .env.

Las consolas (PlayStation Store, Nintendo eShop, Microsoft Store) no tienen API pública
de precios, así que para ellas Kira indica revisar la tienda oficial.
"""

import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse

import requests

from backend.config import ITAD_API_KEY, PAIS_PRECIOS

CHEAPSHARK = "https://www.cheapshark.com/api/1.0"
STEAM_APPDETAILS = "https://store.steampowered.com/api/appdetails"
ITAD = "https://api.isthereanydeal.com"
# Privilegio mínimo: la herramienta solo puede conectarse a estos dominios.
DOMINIOS_PERMITIDOS = {"www.cheapshark.com", "store.steampowered.com", "api.isthereanydeal.com"}
TIMEOUT = 6                     # segundos máximos por consulta (el chat no debe quedarse pegado)
CACHE_SEGUNDOS = 30 * 60        # un mismo juego no se vuelve a consultar en 30 minutos

_cache: dict = {}
_tiendas: dict = {}

# ---------------------------------------------------------------------------
# ¿La pregunta es sobre precios?
# ---------------------------------------------------------------------------
_RE_PRECIO = re.compile(
    r"\b(precios?|cuesta|cuestan|costo|coste|cuanto (sale|vale|esta)|valor|ofertas?|descuentos?|"
    r"rebajas?|baratos?|barata|comprar|compro|comprarlo|gratis|free|sale en|dolares|pesos|clp|usd)\b"
)


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def pregunta_por_precio(mensaje: str) -> bool:
    texto = _normalizar(mensaje).replace("vale la pena", "")     # «vale la pena» no es precio
    return bool(_RE_PRECIO.search(texto))


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------
def _revisar_dominio(url: str) -> None:
    if urlparse(url).hostname not in DOMINIOS_PERMITIDOS:
        raise PermissionError(f"Dominio no permitido para la herramienta de precios: {urlparse(url).hostname}")


def _get(url, **kwargs):
    _revisar_dominio(url)
    r = requests.get(url, timeout=TIMEOUT, **kwargs)
    r.raise_for_status()
    return r.json()


def _post(url, **kwargs):
    _revisar_dominio(url)
    return requests.post(url, timeout=TIMEOUT, **kwargs)


def _tiendas_cheapshark() -> dict:
    if not _tiendas:
        try:
            for t in _get(f"{CHEAPSHARK}/stores"):
                _tiendas[str(t["storeID"])] = t["storeName"]
        except Exception:
            pass
    return _tiendas


def _parecido(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    limpia = lambda s: re.sub(r"[^a-z0-9]+", " ", _normalizar(s)).strip()
    return SequenceMatcher(None, limpia(a), limpia(b)).ratio()


def precios_cheapshark(nombre: str) -> dict | None:
    """Precios en tiendas de PC (USD) y mínimo histórico."""
    candidatos = _get(f"{CHEAPSHARK}/games", params={"title": nombre, "limit": 10})
    if not candidatos:
        return None
    mejor = max(candidatos, key=lambda c: _parecido(c.get("external", ""), nombre))
    if _parecido(mejor.get("external", ""), nombre) < 0.8:      # no es el mismo juego
        return None
    detalle = _get(f"{CHEAPSHARK}/games", params={"id": mejor["gameID"]})
    tiendas = _tiendas_cheapshark()
    ofertas = []
    for d in detalle.get("deals", []):
        precio, normal = float(d["price"]), float(d["retailPrice"])
        ofertas.append({
            "tienda": tiendas.get(str(d["storeID"]), f"tienda {d['storeID']}"),
            "precio": precio, "normal": normal,
            "descuento": round(float(d.get("savings", 0))),
        })
    ofertas.sort(key=lambda o: o["precio"])
    minimo = detalle.get("cheapestPriceEver", {})
    return {
        "titulo": detalle.get("info", {}).get("title", mejor.get("external")),
        "steam_appid": detalle.get("info", {}).get("steamAppID") or mejor.get("steamAppID"),
        "ofertas": ofertas,
        "minimo_historico": float(minimo["price"]) if minimo.get("price") else None,
        "fecha_minimo": datetime.fromtimestamp(minimo["date"]).strftime("%Y-%m-%d") if minimo.get("date") else None,
    }


def precio_steam(appid) -> dict | None:
    """Precio oficial en Steam en la moneda del país configurado."""
    params = {"appids": appid, "cc": PAIS_PRECIOS.lower(), "l": "spanish"}
    info = _get(STEAM_APPDETAILS, params={**params, "filters": "price_overview"}).get(str(appid), {})
    if not info.get("success"):
        return None
    precio = (info.get("data") or {}).get("price_overview") if isinstance(info.get("data"), dict) else None
    if not precio:
        # sin precio: puede ser gratuito (Steam no manda price_overview) -> ficha completa
        completo = _get(STEAM_APPDETAILS, params=params).get(str(appid), {})
        if (completo.get("data") or {}).get("is_free"):
            return {"gratis": True}
        return None
    return {
        "gratis": False,
        "final": precio.get("final_formatted"),
        "normal": precio.get("initial_formatted") or precio.get("final_formatted"),
        "descuento": precio.get("discount_percent", 0),
        "moneda": precio.get("currency"),
    }


def precios_itad(nombre: str, appid=None) -> dict | None:
    """Precios por tienda en el país configurado y mínimo histórico (requiere ITAD_API_KEY)."""
    if not ITAD_API_KEY:
        return None
    clave = {"key": ITAD_API_KEY}
    buscar = {"appid": appid} if appid else {"title": nombre}
    encontrado = _get(f"{ITAD}/games/lookup/v1", params={**clave, **buscar})
    if not encontrado.get("found"):
        return None
    id_juego = encontrado["game"]["id"]
    for pais in dict.fromkeys([PAIS_PRECIOS, "US"]):              # si el país no está, se usa EE.UU.
        r = _post(f"{ITAD}/games/prices/v3", params={**clave, "country": pais, "capacity": 6},
                  json=[id_juego])
        if r.status_code == 200 and r.json():
            juego = r.json()[0]
            ofertas = [{
                "tienda": d["shop"]["name"], "precio": d["price"]["amount"], "normal": d["regular"]["amount"],
                "moneda": d["price"]["currency"], "descuento": d.get("cut", 0),
            } for d in juego.get("deals", [])]
            minimo = (juego.get("historyLow") or {}).get("all") or {}
            return {"pais": pais, "ofertas": sorted(ofertas, key=lambda o: o["precio"]),
                    "minimo": minimo.get("amount"), "moneda_minimo": minimo.get("currency")}
    return None


# ---------------------------------------------------------------------------
# Texto para el contexto del LLM
# ---------------------------------------------------------------------------
def _usd(v: float) -> str:
    return f"US$ {v:.2f}"


def _monto(v: float, moneda: str) -> str:
    """5375 CLP -> 'CLP 5.375'; 9.99 USD -> 'USD 9.99'."""
    if float(v).is_integer():
        return f"{moneda} {int(v):,}".replace(",", ".")
    return f"{moneda} {v:.2f}"


def consultar_precios(nombre: str, appid=None) -> str:
    """Devuelve un bloque de texto con los precios actuales del juego (o "" si no hay)."""
    clave_cache = (nombre.lower(), appid)
    if clave_cache in _cache and time.time() - _cache[clave_cache][0] < CACHE_SEGUNDOS:
        return _cache[clave_cache][1]

    cheap = None
    try:
        cheap = precios_cheapshark(nombre)
    except Exception as e:
        print(f"  [precios] CheapShark no respondió: {e}")
    appid = appid or (cheap or {}).get("steam_appid")

    steam = itad = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_steam = pool.submit(precio_steam, appid) if appid else None
        f_itad = pool.submit(precios_itad, nombre, appid)
        for nombre_fuente, futuro in (("Steam", f_steam), ("IsThereAnyDeal", f_itad)):
            if not futuro:
                continue
            try:
                if nombre_fuente == "Steam":
                    steam = futuro.result()
                else:
                    itad = futuro.result()
            except Exception as e:
                print(f"  [precios] {nombre_fuente} no respondió: {e}")

    lineas = []
    if steam:
        if steam["gratis"]:
            lineas.append("- Steam: el juego es gratuito (free to play).")
        elif steam["descuento"]:
            lineas.append(f"- Steam ({PAIS_PRECIOS}): {steam['final']} con {steam['descuento']}% de descuento "
                          f"(precio normal {steam['normal']}).")
        else:
            lineas.append(f"- Steam ({PAIS_PRECIOS}): {steam['final']}.")
    if itad and itad["ofertas"]:
        partes = [f"{o['tienda']} {_monto(o['precio'], o['moneda'])}" + (f" (-{o['descuento']}%)" if o["descuento"] else "")
                  for o in itad["ofertas"][:5]]
        lineas.append(f"- Tiendas de PC ({itad['pais']}, vía IsThereAnyDeal): " + "; ".join(partes) + ".")
        if itad.get("minimo"):
            lineas.append(f"- Precio más bajo de la historia: {_monto(itad['minimo'], itad['moneda_minimo'])}.")
    if cheap and cheap["ofertas"]:
        partes = [f"{o['tienda']} {_usd(o['precio'])}" + (f" (-{o['descuento']}%, normal {_usd(o['normal'])})"
                                                        if o["descuento"] else "")
                  for o in cheap["ofertas"][:5]]
        lineas.append("- Tiendas de PC en dólares (vía CheapShark): " + "; ".join(partes) + ".")
        if cheap["minimo_historico"] is not None and not (itad and itad.get("minimo")):
            fecha = f" ({cheap['fecha_minimo']})" if cheap["fecha_minimo"] else ""
            lineas.append(f"- Precio más bajo de la historia en PC: {_usd(cheap['minimo_historico'])}{fecha}.")

    if lineas:
        hora = datetime.now().strftime("%Y-%m-%d %H:%M")
        texto = f"PRECIOS ACTUALES DE {nombre.upper()} (consultados en vivo el {hora}):\n" + "\n".join(lineas)
    else:
        texto = (f"PRECIOS DE {nombre.upper()}: no se encontraron precios en tiendas de PC. Si es un juego de "
                 "consola, no hay una API pública de precios: hay que revisar PlayStation Store, "
                 "Nintendo eShop o Microsoft Store.")
    _cache[clave_cache] = (time.time(), texto)
    return texto


def precios_para_contexto(juegos: list[dict]) -> str:
    """juegos: los detectados en la pregunta ({nombre, appid, ...}). Máximo 2 para no demorar."""
    bloques = [consultar_precios(j["nombre"], j.get("appid")) for j in juegos[:2]]
    return "\n\n".join(b for b in bloques if b)
