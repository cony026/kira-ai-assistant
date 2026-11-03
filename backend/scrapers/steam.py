"""
PARTE 1-A: Descargar fichas de juegos de PC (Steam).

Reemplaza a los antiguos 'descargar_canal_completo.py' y 'descargar_transcripciones.py'.
Ya NO se usan videos ni transcripciones de YouTube.

Qué hace:
    1. Pide a Steam la lista completa de apps (catálogo entero, decenas de miles de IDs).
    2. Para cada app, consulta la API oficial de la tienda (appdetails) para saber si es
       un juego de verdad (filtra DLC, software, soundtracks, demos, etc.).
    3. Si es un juego, arma un documento de texto plano con:
         - Descripción / reseña corta
         - Géneros, desarrollador, publisher, fecha de lanzamiento, precio
         - Nota de Metacritic (si Steam la tiene registrada)
         - Resumen de reseñas de usuarios de Steam (ej. "Extremadamente positivas 96%")
         - Requisitos mínimos y recomendados para Windows / Mac / Linux
    4. Guarda cada juego como documentos/steam_<appid>_<slug>.txt

Es reanudable: si se corta a mitad de camino, se puede volver a correr y sigue donde
quedó (no vuelve a pedir juegos que ya están guardados).

El catálogo completo de Steam son decenas de miles de apps. Con la API pública y una
sola conexión esto puede tardar VARIAS HORAS (incluso más de un día si se deja el
límite de velocidad conservador). Se puede:
    - Dejarlo corriendo en segundo plano y volver a ejecutarlo cuando se corte.
    - Ajustar LIMITE_JUEGOS abajo para probar primero con una muestra chica (ej. 50).
    - Subir HILOS si quieres más velocidad (con cuidado de no ser bloqueado por Steam).

Requiere: pip install requests
"""

import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from backend.config import CARPETA_DOCS, RAIZ_PROYECTO  # rutas centralizadas

# beautifulsoup4 se importa bajo demanda en obtener_lista_apps()
# para dar un mensaje de error claro si no está instalado

# =====================================================================
# CONFIGURACIÓN — ajusta esto a gusto
# =====================================================================
CARPETA = CARPETA_DOCS
CARPETA.mkdir(exist_ok=True)

ARCHIVO_LISTA_CACHE = Path("steam_applist_cache.json")   # cache de la lista completa de apps
ARCHIVO_PROGRESO = Path("steam_progreso.json")            # appids ya procesados (éxito o descarte)

IDIOMA = "spanish"          # idioma de la descripción/requisitos que pide a Steam
IDIOMA_FALLBACK = "english"  # si no hay versión en español, reintenta en inglés

LIMITE_JUEGOS = None   # None = catálogo completo. Pon un número (ej. 50) para probar primero.
HILOS = 4               # peticiones en paralelo. Súbelo con cuidado (ej. 6-8) si no te bloquean.
PAUSA_ENTRE_LOTES = 1.0  # segundos de pausa cada vez que se despachan HILOS peticiones

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Tipos de "app" de Steam que NO nos interesan (solo queremos type == "game")
# (esto se filtra igual con la respuesta de appdetails, aquí es solo referencia)


# =====================================================================
# Utilidades
# =====================================================================
def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto[:60] or "juego"


def limpiar_html(texto: str) -> str:
    """Quita etiquetas HTML de los campos de requisitos/descripción de Steam."""
    if not texto:
        return ""
    texto = re.sub(r"<br\s*/?>", "\n", texto)
    texto = re.sub(r"<li>", "\n- ", texto)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"&amp;", "&", texto)
    texto = re.sub(r"&nbsp;", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def cargar_progreso() -> set:
    if ARCHIVO_PROGRESO.exists():
        return set(json.loads(ARCHIVO_PROGRESO.read_text(encoding="utf-8")))
    return set()


def guardar_progreso(procesados: set):
    ARCHIVO_PROGRESO.write_text(json.dumps(sorted(procesados)), encoding="utf-8")


# =====================================================================
# Llamadas a la API oficial de Steam
# =====================================================================
def obtener_lista_apps() -> list:
    """Devuelve [{'appid':..., 'name':...}, ...] de los juegos más populares de Steam.

    En lugar de intentar descargar el catálogo completo (que está protegido por
    Valve), scrapea la página de juegos mejor valorados/populares de la tienda.
    Esto da cientos de juegos válidos con el que empezar.

    Si quieres más juegos después, puedes:
    - Aumentar PAGINAS_A_SCRAPEAR abajo
    - Cambiar el sorting (bestselling, recent, top_rated)
    """
    if ARCHIVO_LISTA_CACHE.exists():
        print("Usando lista de apps en caché (borra steam_applist_cache.json para refrescar).")
        return json.loads(ARCHIVO_LISTA_CACHE.read_text(encoding="utf-8"))

    print("Scrapiendo los juegos más populares de Steam...")
    apps = []
    PAGINAS_A_SCRAPEAR = 5  # cada página ≈ 40-50 juegos. Aumenta si quieres más.

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "Se requiere beautifulsoup4. Instala con:\n"
            "  pip install beautifulsoup4"
        )

    for pagina in range(PAGINAS_A_SCRAPEAR):
        url = f"https://store.steampowered.com/search/?os=win&page={pagina + 1}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        filas = soup.find_all("a", class_="search_result_row")

        if not filas:
            print(f"  Página {pagina + 1}: sin resultados, deteniendo.")
            break

        for fila in filas:
            href = fila.get("href", "")
            # Extraer app ID de URLs tipo: https://store.steampowered.com/app/730/...
            match = re.search(r"/app/(\d+)", href)
            if not match:
                continue

            appid = int(match.group(1))
            nombre = fila.find("span", class_="title")
            if nombre:
                nombre = nombre.get_text(strip=True)
                apps.append({"appid": appid, "name": nombre})

        print(f"  Página {pagina + 1}: {len(filas)} juegos (total: {len(apps)})")
        time.sleep(1)  # pausa entre páginas

    if not apps:
        raise RuntimeError(
            "No se pudieron scrapear juegos de Steam. "
            "¿Tiene conectividad? ¿Steam está bloqueando las peticiones?"
        )

    ARCHIVO_LISTA_CACHE.write_text(json.dumps(apps), encoding="utf-8")
    print(f"\n  Total: {len(apps)} apps descargados.\n")
    return apps


def pedir_appdetails(appid: int, idioma: str) -> dict | None:
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "l": idioma, "cc": "us"}
    for intento in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                time.sleep(5 * (intento + 1))
                continue
            r.raise_for_status()
            data = r.json().get(str(appid))
            if data and data.get("success"):
                return data["data"]
            return None
        except requests.RequestException:
            time.sleep(2 * (intento + 1))
    return None


def pedir_resumen_reseñas(appid: int) -> str:
    """Usa la API pública de reviews de Steam para sacar un resumen tipo
    'Extremadamente positivas (96% de 12.345 reseñas)'."""
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {"json": 1, "language": "all", "purchase_type": "all", "num_per_page": 0}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        qs = r.json().get("query_summary", {})
        desc = qs.get("review_score_desc")
        total = qs.get("total_reviews")
        if desc and total:
            return f"{desc} ({total} reseñas de usuarios en Steam)"
    except requests.RequestException:
        pass
    return ""


# =====================================================================
# Armar el documento de texto por juego
# =====================================================================
def armar_documento(app: dict, resumen_reseñas: str) -> str:
    partes = []
    nombre = app.get("name", "Desconocido")
    partes.append(f"JUEGO: {nombre}")
    partes.append("PLATAFORMA: PC (Steam)")

    generos = ", ".join(g["description"] for g in app.get("genres", []) or [])
    if generos:
        partes.append(f"GÉNEROS: {generos}")

    desarrolladores = ", ".join(app.get("developers", []) or [])
    publishers = ", ".join(app.get("publishers", []) or [])
    if desarrolladores:
        partes.append(f"DESARROLLADOR: {desarrolladores}")
    if publishers:
        partes.append(f"PUBLISHER: {publishers}")

    fecha = (app.get("release_date") or {}).get("date")
    if fecha:
        partes.append(f"FECHA DE LANZAMIENTO: {fecha}")

    precio = app.get("price_overview")
    if precio:
        partes.append(f"PRECIO: {precio.get('final_formatted')}")
    elif app.get("is_free"):
        partes.append("PRECIO: Gratis")

    metacritic = app.get("metacritic")
    if metacritic:
        partes.append(f"NOTA METACRITIC: {metacritic.get('score')}/100")

    if resumen_reseñas:
        partes.append(f"RESEÑAS DE USUARIOS (STEAM): {resumen_reseñas}")

    corta = limpiar_html(app.get("short_description", ""))
    larga = limpiar_html(app.get("about_the_game", ""))
    if corta:
        partes.append(f"\nRESEÑA / DESCRIPCIÓN:\n{corta}")
    if larga and larga != corta:
        partes.append(f"\nDESCRIPCIÓN DETALLADA:\n{larga}")

    for plataforma, campo in (("WINDOWS", "pc_requirements"),
                              ("MAC", "mac_requirements"),
                              ("LINUX", "linux_requirements")):
        req = app.get(campo)
        if isinstance(req, dict):
            minimo = limpiar_html(req.get("minimum", ""))
            recomendado = limpiar_html(req.get("recommended", ""))
            if minimo:
                partes.append(f"\nREQUISITOS MÍNIMOS ({plataforma}):\n{minimo}")
            if recomendado:
                partes.append(f"\nREQUISITOS RECOMENDADOS ({plataforma}):\n{recomendado}")

    return "\n".join(partes).strip()


# =====================================================================
# Procesar un juego
# =====================================================================
def procesar_app(app: dict) -> str:
    appid = app["appid"]
    nombre = app.get("name", str(appid))

    data = pedir_appdetails(appid, IDIOMA)
    if data is None:
        data = pedir_appdetails(appid, IDIOMA_FALLBACK)
    if data is None:
        return f"SIN_DATOS {appid} {nombre}"

    if data.get("type") != "game":
        return f"OMITIDO(no-es-juego) {appid} {nombre}"

    resumen = pedir_resumen_reseñas(appid)
    documento = armar_documento(data, resumen)

    slug = slugify(nombre)
    destino = CARPETA / f"steam_{appid}_{slug}.txt"
    destino.write_text(documento, encoding="utf-8")
    return f"OK {appid} {nombre}"


# =====================================================================
# Main
# =====================================================================
def main():
    apps = obtener_lista_apps()
    if LIMITE_JUEGOS:
        apps = apps[:LIMITE_JUEGOS]

    procesados = cargar_progreso()
    pendientes = [a for a in apps if a["appid"] not in procesados]

    print(f"Total en catálogo: {len(apps)}")
    print(f"Ya procesados antes: {len(procesados)}")
    print(f"Pendientes ahora: {len(pendientes)}\n")

    if not pendientes:
        print("No hay nada pendiente. ¡Listo!")
        return

    exito = 0
    omitidos = 0
    fallos = 0

    with ThreadPoolExecutor(max_workers=HILOS) as pool:
        futuros = {}
        for i, app in enumerate(pendientes, 1):
            futuros[pool.submit(procesar_app, app)] = app
            # Despachamos en lotes de a HILOS para no saturar la API
            if i % HILOS == 0 or i == len(pendientes):
                for fut in as_completed(list(futuros.keys())):
                    app_terminada = futuros.pop(fut)
                    try:
                        resultado = fut.result()
                    except Exception as e:
                        resultado = f"ERROR {app_terminada['appid']} {e}"

                    procesados.add(app_terminada["appid"])
                    if resultado.startswith("OK"):
                        exito += 1
                    elif resultado.startswith("OMITIDO"):
                        omitidos += 1
                    else:
                        fallos += 1

                    print(f"  [{exito + omitidos + fallos}/{len(pendientes)}] {resultado}")

                guardar_progreso(procesados)
                time.sleep(PAUSA_ENTRE_LOTES)

    print("\nResultado de esta corrida:")
    print(f"  Juegos guardados: {exito}")
    print(f"  Omitidos (no eran juegos / DLC / software): {omitidos}")
    print(f"  Fallos: {fallos}")
    print(f"  Guardados en: {CARPETA.resolve()}")
    print("\nSi se cortó o quieres seguir otro día, vuelve a correr este mismo script:")
    print("continuará donde quedó gracias a steam_progreso.json")


if __name__ == "__main__":
    main()