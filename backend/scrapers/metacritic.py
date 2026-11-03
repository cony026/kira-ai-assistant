"""
PARTE 1-B: Descargar fichas de reseñas de juegos de consola (PlayStation, Xbox, Switch)
desde Metacritic.

Para PC ya usamos la API oficial de Steam (descargar_steam.py), que es más completa,
rápida y no tiene bloqueos. Metacritic solo se usa aquí para las plataformas donde
Steam no aplica.

IMPORTANTE — Metacritic usa Cloudflare y bloqueo por velocidad de peticiones.
No es una API oficial, es scraping, así que:
    - Ve despacio (hay una pausa entre peticiones, no la bajes mucho).
    - Prueba primero con LIMITE_POR_PLATAFORMA chico (ej. 20) antes de lanzar todo.
    - Si Metacritic cambia el diseño de su página, el parseo puede dejar de
    funcionar; en ese caso hay que revisar las funciones extraer_* de abajo.
    - Si te empieza a bloquear (errores 403 seguidos), sube PAUSA_SEGUNDOS o
    instala 'cloudscraper' (pip install cloudscraper) que ayuda a pasar el
    desafío de Cloudflare; el script lo usa automáticamente si está instalado.

Requiere: pip install requests beautifulsoup4
Opcional (recomendado si te bloquea): pip install cloudscraper
"""

import json
import re
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from backend.config import CARPETA_DOCS, RAIZ_PROYECTO  # rutas centralizadas

try:
    import cloudscraper
    SESION = cloudscraper.create_scraper()
except ImportError:
    SESION = requests.Session()

# =====================================================================
# CONFIGURACIÓN
# =====================================================================
CARPETA = CARPETA_DOCS
CARPETA.mkdir(exist_ok=True)

ARCHIVO_PROGRESO = Path("metacritic_progreso.json")

# slug de plataforma en Metacritic -> nombre bonito para el documento
PLATAFORMAS = {
    "playstation-5": "PlayStation 5",
    "xbox-series-x": "Xbox Series X|S",
    "switch": "Nintendo Switch",
}

PAGINAS_POR_PLATAFORMA = 50    # cada página trae ~24 juegos; ajusta según cobertura deseada
LIMITE_POR_PLATAFORMA = None    # None = sin límite (usa PAGINAS_POR_PLATAFORMA como tope real)
PAUSA_SEGUNDOS = 2.0             # pausa entre cada request a Metacritic (no bajar de 1.5)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

BASE = "https://www.metacritic.com"


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto[:60] or "juego"


def cargar_progreso() -> set:
    if ARCHIVO_PROGRESO.exists():
        return set(json.loads(ARCHIVO_PROGRESO.read_text(encoding="utf-8")))
    return set()


def guardar_progreso(procesados: set):
    ARCHIVO_PROGRESO.write_text(json.dumps(sorted(procesados)), encoding="utf-8")


def pedir(url: str):
    for intento in range(3):
        try:
            r = SESION.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r
            if r.status_code == 403:
                print(f"    Bloqueado (403) en {url}, esperando más...")
                time.sleep(10 * (intento + 1))
                continue
            if r.status_code == 404:
                return None
        except requests.RequestException:
            time.sleep(3 * (intento + 1))
    return None


# =====================================================================
# Listado de juegos por plataforma
# =====================================================================
def listar_juegos_plataforma(slug_plataforma: str, paginas: int) -> list:
    """Devuelve una lista de URLs de fichas de juego para una plataforma,
    recorriendo el listado ordenado por nota (metascore)."""
    urls = []
    for pagina in range(paginas):
        url = f"{BASE}/browse/game/{slug_plataforma}/all/all-time/metascore/?page={pagina}"
        r = pedir(url)
        time.sleep(PAUSA_SEGUNDOS)
        if r is None:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        enlaces = soup.select('a[href*="/game/"]')
        encontrados_en_pagina = 0
        for a in enlaces:
            href = a.get("href", "")
            if "/game/" in href and href not in urls:
                if not href.startswith("http"):
                    href = BASE + href
                urls.append(href)
                encontrados_en_pagina += 1
        if encontrados_en_pagina == 0:
            break  # ya no hay más páginas con contenido
        print(f"    página {pagina}: {encontrados_en_pagina} juegos nuevos (total {len(urls)})")

    return urls


# =====================================================================
# Extraer datos de la ficha de un juego
# =====================================================================
def extraer_ficha(url: str) -> dict | None:
    r = pedir(url)
    if r is None:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    ficha = {"url": url}

    # 1) Intentar primero con el JSON-LD estructurado (más estable que el CSS)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") in ("VideoGame", "Product"):
            ficha["nombre"] = data.get("name")
            ficha["descripcion"] = data.get("description")
            rating = data.get("aggregateRating") or {}
            if rating:
                ficha["nota"] = rating.get("ratingValue")
                ficha["cantidad_resenas"] = rating.get("reviewCount") or rating.get("ratingCount")
            genero = data.get("genre")
            if genero:
                ficha["generos"] = genero if isinstance(genero, str) else ", ".join(genero)
            ficha["fecha"] = data.get("datePublished")

    # 2) Respaldo: metaetiquetas y título si no vino por JSON-LD
    if not ficha.get("nombre"):
        titulo = soup.find("title")
        if titulo:
            ficha["nombre"] = titulo.text.split(" - ")[0].strip()

    if not ficha.get("descripcion"):
        meta_desc = soup.find("meta", attrs={"name": "description"}) or \
                    soup.find("meta", attrs={"property": "og:description"})
        if meta_desc:
            ficha["descripcion"] = meta_desc.get("content", "").strip()

    # 3) Resumen crítico ("blurb") que Metacritic suele mostrar bajo la nota
    blurb = soup.select_one('[class*="summary"], [class*="deck"]')
    if blurb:
        texto = blurb.get_text(" ", strip=True)
        if texto and len(texto) > 20:
            ficha["resumen_critica"] = texto

    if not ficha.get("nombre"):
        return None

    return ficha


def armar_documento(ficha: dict, plataforma_bonita: str) -> str:
    partes = [f"JUEGO: {ficha['nombre']}", f"PLATAFORMA: {plataforma_bonita}"]

    if ficha.get("generos"):
        partes.append(f"GÉNEROS: {ficha['generos']}")
    if ficha.get("fecha"):
        partes.append(f"FECHA DE LANZAMIENTO: {ficha['fecha']}")
    if ficha.get("nota"):
        extra = f" ({ficha['cantidad_resenas']} reseñas)" if ficha.get("cantidad_resenas") else ""
        partes.append(f"NOTA METACRITIC: {ficha['nota']}{extra}")

    if ficha.get("resumen_critica"):
        partes.append(f"\nRESUMEN DE LA CRÍTICA:\n{ficha['resumen_critica']}")
    if ficha.get("descripcion"):
        partes.append(f"\nDESCRIPCIÓN / RESEÑA:\n{ficha['descripcion']}")

    partes.append(f"\nFUENTE: {ficha['url']}")
    return "\n".join(partes).strip()


# =====================================================================
# Main
# =====================================================================
def main():
    procesados = cargar_progreso()

    for slug_plataforma, nombre_bonito in PLATAFORMAS.items():
        print(f"\n=== {nombre_bonito} ===")
        urls = listar_juegos_plataforma(slug_plataforma, PAGINAS_POR_PLATAFORMA)
        if LIMITE_POR_PLATAFORMA:
            urls = urls[:LIMITE_POR_PLATAFORMA]

        pendientes = [u for u in urls if u not in procesados]
        print(f"  {len(urls)} juegos listados, {len(pendientes)} pendientes de descargar")

        for i, url in enumerate(pendientes, 1):
            ficha = extraer_ficha(url)
            time.sleep(PAUSA_SEGUNDOS)

            if ficha is None:
                print(f"  [{i}/{len(pendientes)}] ✗ no se pudo leer {url}")
                procesados.add(url)
                continue

            slug = slugify(ficha["nombre"])
            destino = CARPETA / f"metacritic_{slug_plataforma}_{slug}.txt"
            destino.write_text(armar_documento(ficha, nombre_bonito), encoding="utf-8")
            procesados.add(url)
            print(f"  [{i}/{len(pendientes)}] ✓ {ficha['nombre']}")

            if i % 20 == 0:
                guardar_progreso(procesados)

        guardar_progreso(procesados)

    print(f"\nListo. Fichas guardadas en: {CARPETA.resolve()}")
    print("Si Metacritic te bloqueó a mitad de camino, vuelve a correr el script más tarde:")
    print("continuará donde quedó gracias a metacritic_progreso.json")


if __name__ == "__main__":
    main()