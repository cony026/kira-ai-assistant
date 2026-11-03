"""
Descarga fichas de juegos desde IGDB (Internet Game Database, de Twitch) a data/documentos/.

IGDB es el catálogo más completo: juegos de todas las plataformas (PC, PlayStation,
Xbox, Nintendo, móviles, retro) con resumen, historia, géneros, temas, modos de juego,
desarrolladora, fecha, nota de la crítica, nota de usuarios, juegos parecidos y portada.

Requiere en el .env (gratis):
    IGDB_CLIENT_ID=...
    IGDB_CLIENT_SECRET=...
  1. Entra a https://dev.twitch.tv/console/apps con tu cuenta de Twitch
     (Twitch pide activar la verificación en dos pasos con tu teléfono).
  2. "Registrar tu aplicación": nombre "Kira IA", URL de redirección http://localhost,
     categoría "Application Integration", tipo de cliente "Confidencial".
  3. Copia el "ID de cliente" y genera un "Secreto de cliente".

Uso (desde la carpeta raíz kira/):
    python -m backend.scrapers.igdb                 # los 5000 juegos más votados
    python -m backend.scrapers.igdb 1000            # una muestra más chica para probar
    python -m backend.vectorDb.ingest               # después, para cargarlos en la base

Los juegos ya descargados se saltan, así que se puede cortar y volver a correr.
"""

import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

import requests

from backend.config import CARPETA_DOCS, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET

URL_TOKEN = "https://id.twitch.tv/oauth2/token"
URL_API = "https://api.igdb.com/v4"

MAX_JUEGOS = 5000          # cuántos juegos bajar (los más votados primero)
MIN_VOTOS = 10             # ignora juegos casi desconocidos (sin reseñas suficientes)
POR_PAGINA = 500           # máximo que permite IGDB por consulta
PAUSA = 0.3                # IGDB permite ~4 consultas por segundo

CAMPOS = ", ".join([
    "name", "slug", "summary", "storyline", "url",
    "rating", "rating_count", "aggregated_rating", "aggregated_rating_count",
    "first_release_date", "genres.name", "themes.name", "game_modes.name",
    "player_perspectives.name", "platforms.name", "franchises.name",
    "involved_companies.company.name", "involved_companies.developer", "involved_companies.publisher",
    "similar_games.name", "alternative_names.name", "cover.image_id",
])

# Traducción de los géneros y modos más comunes (IGDB los entrega en inglés)
TRADUCCIONES = {
    "Role-playing (RPG)": "RPG", "Shooter": "Shooter", "Adventure": "Aventura", "Platform": "Plataformas",
    "Puzzle": "Puzle", "Racing": "Carreras", "Sport": "Deportes", "Strategy": "Estrategia",
    "Real Time Strategy (RTS)": "Estrategia en tiempo real", "Turn-based strategy (TBS)": "Estrategia por turnos",
    "Simulator": "Simulación", "Fighting": "Peleas", "Indie": "Indie", "Arcade": "Arcade",
    "Hack and slash/Beat 'em up": "Hack and slash", "Tactical": "Táctico", "Music": "Música",
    "Point-and-click": "Point and click", "Visual Novel": "Novela visual", "Card & Board Game": "Cartas y tablero",
    "MOBA": "MOBA", "Quiz/Trivia": "Trivia", "Pinball": "Pinball",
    "Single player": "Un jugador", "Multiplayer": "Multijugador", "Co-operative": "Cooperativo",
    "Split screen": "Pantalla dividida", "Massively Multiplayer Online (MMO)": "MMO", "Battle Royale": "Battle Royale",
    "Action": "Acción", "Fantasy": "Fantasía", "Science fiction": "Ciencia ficción", "Horror": "Terror",
    "Thriller": "Suspenso", "Survival": "Supervivencia", "Historical": "Histórico", "Stealth": "Sigilo",
    "Comedy": "Comedia", "Open world": "Mundo abierto", "Sandbox": "Sandbox", "Warfare": "Bélico",
    "Mystery": "Misterio", "Drama": "Drama", "Kids": "Infantil", "Educational": "Educativo",
    "Romance": "Romance", "Party": "Party", "Business": "Gestión", "Erotic": "Erótico",
    "First person": "Primera persona", "Third person": "Tercera persona", "Side view": "Vista lateral",
    "Bird view / Isometric": "Isométrica", "Virtual Reality": "Realidad virtual", "Text": "Texto",
    "Auditory": "Auditiva",
}


def traducir(nombres):
    return [TRADUCCIONES.get(n, n) for n in nombres]


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode()
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    return re.sub(r"[-\s]+", "-", texto)[:80]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def obtener_token() -> str:
    r = requests.post(URL_TOKEN, params={
        "client_id": IGDB_CLIENT_ID, "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }, timeout=20)
    if r.status_code != 200:
        sys.exit(f"Twitch rechazó las credenciales ({r.status_code}): {r.text[:200]}\n"
                 "Revisa IGDB_CLIENT_ID e IGDB_CLIENT_SECRET en el .env")
    return r.json()["access_token"]


def consultar(token: str, consulta: str) -> list:
    """Consulta en lenguaje Apicalypse (el de IGDB). Reintenta si se pasa del límite."""
    for intento in range(5):
        r = requests.post(f"{URL_API}/games", data=consulta, timeout=30, headers={
            "Client-ID": IGDB_CLIENT_ID, "Authorization": f"Bearer {token}",
        })
        if r.status_code == 429:
            time.sleep(1 + intento)
            continue
        r.raise_for_status()
        time.sleep(PAUSA)
        return r.json()
    raise RuntimeError("IGDB sigue respondiendo 429 (demasiadas consultas)")


# ---------------------------------------------------------------------------
# Ficha
# ---------------------------------------------------------------------------
def formatear_ficha(j: dict) -> str:
    nombres = lambda clave: [x["name"] for x in j.get(clave, []) if x.get("name")]
    empresas = j.get("involved_companies", [])
    devs = [e["company"]["name"] for e in empresas if e.get("developer") and e.get("company")]
    pubs = [e["company"]["name"] for e in empresas if e.get("publisher") and e.get("company")]
    plataformas = nombres("platforms")

    lineas = [f"JUEGO: {j['name']}", "", "FUENTE: IGDB"]
    if plataformas:
        lineas.append(f"PLATAFORMA: {', '.join(plataformas[:4])}")
        lineas.append(f"DISPONIBLE EN: {', '.join(plataformas)}")
    if j.get("genres"):
        lineas.append(f"GÉNEROS: {', '.join(traducir(nombres('genres')))}")
    if j.get("themes"):
        lineas.append(f"TEMAS: {', '.join(traducir(nombres('themes')))}")
    if j.get("game_modes"):
        lineas.append(f"MODOS DE JUEGO: {', '.join(traducir(nombres('game_modes')))}")
    if j.get("player_perspectives"):
        lineas.append(f"PERSPECTIVA: {', '.join(traducir(nombres('player_perspectives')))}")
    if devs:
        lineas.append(f"DESARROLLADOR: {', '.join(dict.fromkeys(devs))}")
    if pubs:
        lineas.append(f"PUBLISHER: {', '.join(dict.fromkeys(pubs))}")
    if j.get("first_release_date"):
        fecha = datetime.fromtimestamp(j["first_release_date"], tz=timezone.utc).strftime("%Y-%m-%d")
        lineas.append(f"FECHA DE LANZAMIENTO: {fecha}")
    if j.get("aggregated_rating"):
        lineas.append(f"NOTA DE LA CRÍTICA (IGDB): {round(j['aggregated_rating'])}/100 "
                      f"({j.get('aggregated_rating_count', 0)} críticas)")
    if j.get("rating"):
        lineas.append(f"NOTA DE USUARIOS (IGDB): {round(j['rating'])}/100 ({j.get('rating_count', 0)} votos)")
    if j.get("franchises"):
        lineas.append(f"FRANQUICIA: {', '.join(nombres('franchises'))}")
    if j.get("alternative_names"):
        lineas.append(f"TAMBIÉN CONOCIDO COMO: {', '.join(nombres('alternative_names')[:5])}")
    if j.get("cover", {}).get("image_id"):
        lineas.append(f"PORTADA: https://images.igdb.com/igdb/image/upload/t_cover_big/{j['cover']['image_id']}.jpg")
    if j.get("url"):
        lineas.append(f"URL: {j['url']}")

    lineas += ["", "RESUMEN:", j.get("summary", "").strip()]
    if j.get("storyline"):
        lineas += ["", "HISTORIA:", j["storyline"].strip()]
    parecidos = nombres("similar_games")
    if parecidos:
        lineas += ["", "JUEGOS PARECIDOS:",
                   f"Si te gusta {j['name']}, también podrían gustarte: {', '.join(parecidos[:10])}."]
    return "\n".join(lineas) + "\n"


# ---------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------
def main():
    if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
        sys.exit("Faltan IGDB_CLIENT_ID e IGDB_CLIENT_SECRET en el .env (ver instrucciones arriba en igdb.py).")
    maximo = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else MAX_JUEGOS

    CARPETA_DOCS.mkdir(parents=True, exist_ok=True)
    token = obtener_token()
    print(f"✓ Conectado a IGDB. Descargando hasta {maximo} juegos (los más votados primero)...")

    guardados = saltados = 0
    for offset in range(0, maximo, POR_PAGINA):
        consulta = (f"fields {CAMPOS};"
                    f" where total_rating_count >= {MIN_VOTOS} & summary != null & version_parent = null;"
                    f" sort total_rating_count desc; limit {min(POR_PAGINA, maximo - offset)}; offset {offset};")
        juegos = consultar(token, consulta)
        if not juegos:
            break
        for j in juegos:
            archivo = CARPETA_DOCS / f"igdb_{slugify(j.get('slug') or j['name'])}.txt"
            if archivo.exists():
                saltados += 1
                continue
            archivo.write_text(formatear_ficha(j), encoding="utf-8")
            guardados += 1
        print(f"  [{offset + len(juegos)}/{maximo}] {guardados} nuevos, {saltados} ya existían")

    print(f"\nListo: {guardados} juegos nuevos de IGDB.")
    print("Ahora reconstruye la base:  python -m backend.vectorDb.ingest")


if __name__ == "__main__":
    main()
