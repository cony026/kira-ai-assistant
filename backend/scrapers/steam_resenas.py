"""
Descarga reseñas de usuarios de Steam (opiniones reales, no descripciones) para los
juegos de Steam que ya están en data/documentos/ (archivos steam_<appid>_*.txt).

Por cada juego guarda un archivo steamresenas_<appid>_<juego>.txt con:
  - la valoración general ("Muy positivas", % positivo y cantidad de reseñas)
  - las reseñas más útiles en español e inglés, con horas jugadas

No necesita API key. Usa el endpoint actual de Steam (IUserReviewsService/GetAppReviews)
y, si falla, el antiguo (/appreviews), que Steam marcó como obsoleto.

Uso (desde la carpeta raíz kira/):
    python -m backend.scrapers.steam_resenas
    python -m backend.vectorDb.ingest        # después, para cargarlas en la base
"""

import json
import re
import time

import requests

from backend.config import CARPETA_DOCS

URL_NUEVA = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
URL_ANTIGUA = "https://store.steampowered.com/appreviews/{appid}"

RESENAS_POR_JUEGO = 8      # cuántas reseñas guardar por juego
LARGO_MINIMO = 80          # ignora reseñas de una línea ("10/10", "buen juego")
LARGO_MAXIMO = 700         # recorta reseñas muy largas
PAUSA = 1.0                # segundos entre juegos (Steam limita consultas anónimas)
IDIOMAS = ["spanish", "latam", "english"]   # español de España, latino e inglés


def pedir_nueva(appid: int, idioma: list[str]) -> dict | None:
    entrada = {
        "appid": appid, "num_per_page": 40, "filter": 0,   # 0 = más útiles
        "review_type": 0, "purchase_type": 1,               # 0 = todas, 1 = todas las compras
        "languages": idioma, "filter_offtopic_activity": True, "display_language": "spanish",
    }
    r = requests.get(URL_NUEVA, params={"input_json": json.dumps(entrada)}, timeout=20)
    if r.status_code != 200:
        return None
    datos = r.json()
    return datos.get("response", datos)      # la Web API de Steam suele envolver en "response"


def pedir_antigua(appid: int, idioma: str) -> dict | None:
    r = requests.get(URL_ANTIGUA.format(appid=appid), timeout=20, params={
        "json": 1, "language": idioma, "num_per_page": 40, "filter": "all",
        "purchase_type": "all", "filter_offtopic_activity": 1,
    })
    if r.status_code != 200:
        return None
    datos = r.json()
    return datos if datos.get("success", 1) else None


def obtener_resenas(appid: int) -> tuple[dict, list[dict]]:
    """Devuelve (resumen, reseñas). Prueba el endpoint nuevo y luego el antiguo."""
    resumen, resenas = {}, []
    for idioma in (IDIOMAS[:2], IDIOMAS[2:]):          # primero en español, luego en inglés
        datos = None
        try:
            datos = pedir_nueva(appid, idioma)
        except (requests.RequestException, ValueError):
            pass
        if not datos or "reviews" not in datos:
            try:
                datos = pedir_antigua(appid, idioma[0])   # el antiguo acepta un solo idioma
            except (requests.RequestException, ValueError):
                datos = None
        if not datos:
            continue
        if not resumen and datos.get("query_summary", {}).get("total_reviews"):
            resumen = datos["query_summary"]
        resenas += datos.get("reviews", [])
        if len(resenas) >= RESENAS_POR_JUEGO * 2:
            break
    return resumen, resenas


def limpiar_resena(texto: str) -> str:
    texto = re.sub(r"\[/?[a-z0-9*]+(=[^\]]*)?\]", " ", texto)   # BBCode de Steam: [b], [h1], [url=...]
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) > LARGO_MAXIMO:
        texto = texto[:LARGO_MAXIMO].rsplit(" ", 1)[0] + "…"
    return texto


def formatear(juego: str, appid: int, resumen: dict, resenas: list[dict]) -> str | None:
    elegidas, vistas = [], set()
    for r in resenas:
        original = r.get("review", "")
        # reseñas "plantilla" con casillas (☐ Malo ☑ Bueno...): no aportan opinión real
        if sum(original.count(c) for c in "☐☑☒✓✔✅") >= 3:
            continue
        texto = limpiar_resena(original)
        if len(texto) < LARGO_MINIMO or texto[:60] in vistas:
            continue
        vistas.add(texto[:60])
        horas = round((r.get("author", {}).get("playtime_at_review")
                       or r.get("author", {}).get("playtime_forever") or 0) / 60)
        veredicto = "Recomendado" if r.get("voted_up") else "No recomendado"
        elegidas.append(f"[{veredicto} · {horas} h jugadas] {texto}")
        if len(elegidas) >= RESENAS_POR_JUEGO:
            break
    if not elegidas and not resumen:
        return None

    lineas = [f"JUEGO: {juego}", "", "FUENTE: Reseñas de usuarios de Steam", "PLATAFORMA: PC (Steam)"]
    total = resumen.get("total_reviews") or 0
    if total:
        positivas = resumen.get("total_positive") or 0
        porcentaje = round(100 * positivas / total)
        desc = resumen.get("review_score_desc") or ""
        lineas.append(f"VALORACIÓN DE USUARIOS (STEAM): {desc} ({porcentaje}% positivas de {total} reseñas)".replace(" ()", ""))
    lineas.append(f"URL: https://store.steampowered.com/app/{appid}/")
    if elegidas:
        lineas += ["", "RESEÑAS DE USUARIOS:", *elegidas]
    return "\n".join(lineas) + "\n"


def main():
    fichas = sorted(CARPETA_DOCS.glob("steam_*.txt"))
    print(f"Descargando reseñas de usuarios para {len(fichas)} juegos de Steam...")
    guardados = 0
    for i, ficha in enumerate(fichas, 1):
        partes = ficha.stem.split("_", 2)
        if len(partes) < 3 or not partes[1].isdigit():
            continue
        appid, slug = int(partes[1]), partes[2]
        destino = CARPETA_DOCS / f"steamresenas_{appid}_{slug}.txt"
        if destino.exists():
            continue
        primera = ficha.read_text(encoding="utf-8", errors="ignore").split("\n", 1)[0]
        juego = primera.split(":", 1)[1].strip() if primera.upper().startswith("JUEGO:") else slug
        try:
            resumen, resenas = obtener_resenas(appid)
        except Exception as e:
            print(f"  ✗ {juego}: {e}")
            continue
        contenido = formatear(juego, appid, resumen, resenas)
        if contenido:
            destino.write_text(contenido, encoding="utf-8")
            guardados += 1
            print(f"  [{i}/{len(fichas)}] ✓ {juego}")
        time.sleep(PAUSA)
    print(f"\nListo: reseñas de {guardados} juegos.")
    print("Ahora reconstruye la base:  python -m backend.vectorDb.ingest")


if __name__ == "__main__":
    main()
