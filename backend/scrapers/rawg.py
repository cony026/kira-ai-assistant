"""
PARTE 1-C: Descargar fichas de juegos desde RAWG (todas las plataformas).

RAWG es una API con ~800.000 juegos que cubre PC, PlayStation, Xbox, Switch,
móviles y retro. Complementa Steam (solo PC) y Metacritic (bloquea seguido).

Requiere: RAWG_API_KEY en tu .env (gratis en https://rawg.io/apidocs)
Instalación: pip install requests python-dotenv
"""

import os
import re
import time
import unicodedata
import requests
from pathlib import Path
from dotenv import load_dotenv
from backend.config import CARPETA_DOCS, RAIZ_PROYECTO  # rutas centralizadas

# =====================================================================
# CONFIGURACIÓN
# =====================================================================
DIRECTORIO_ACTUAL = Path(__file__).parent.resolve()
load_dotenv(dotenv_path=RAIZ_PROYECTO / ".env")

API_KEY = os.getenv("RAWG_API_KEY", "").strip()
if not API_KEY:
    raise ValueError("Falta RAWG_API_KEY en tu .env. Obtén una gratis en https://rawg.io/apidocs")

CARPETA_DOCS.mkdir(exist_ok=True)

# IDs de plataformas en RAWG.
# Cada plataforma puede sobreescribir el filtro global (metacritic_min, orden)
# y opcionalmente exigir un mínimo de votos ("votos_min") para evitar juegos
# basura/desconocidos, algo clave en móvil donde hay muchísimo shovelware.
PLATAFORMAS = {
    "pc":       {"id": 4,   "slug": "pc",              "nombre": "PC"},
    "ps5":      {"id": 187, "slug": "playstation-5",   "nombre": "PlayStation 5"},
    "ps4":      {"id": 18,  "slug": "playstation-4",   "nombre": "PlayStation 4"},
    "xbox-sx":  {"id": 186, "slug": "xbox-series-x",   "nombre": "Xbox Series X/S"},
    "xbox-one": {"id": 1,   "slug": "xbox-one",        "nombre": "Xbox One"},
    "switch":   {"id": 7,   "slug": "nintendo-switch", "nombre": "Nintendo Switch"},
    # --- Móvil / tablet ---
    # La mayoría de juegos móviles NO tiene nota Metacritic, así que para estas
    # dos se ignora METACRITIC_MINIMO y en su lugar se pide rating de usuarios
    # alto + bastantes votos, para traer juegos móviles realmente conocidos.
        "ios": {
        "id": 3, "slug": "ios", "nombre": "iOS (iPhone/iPad)",
        "metacritic_min": None, "orden": "-added",
        "rating_min": 3.5, "votos_min": 50, "fecha_desde": None,
    },
    "android": {
        "id": 21, "slug": "android", "nombre": "Android",
        "metacritic_min": None, "orden": "-added",
        "rating_min": 3.5, "votos_min": 50, "fecha_desde": None,
    },
}

# ---- AJUSTABLES ----
# Qué plataformas quieres descargar. Quita las que no te interesen.
PLATAFORMAS_A_DESCARGAR = ["pc", "ps5", "ps4", "xbox-sx", "xbox-one", "switch", "ios", "android"]

# Cuántos juegos por plataforma. Puedes darle un número distinto a cada una en
# JUEGOS_POR_PLATAFORMA_OVERRIDE; si una plataforma no aparece ahí, se usa este
# valor por defecto.
JUEGOS_POR_PLATAFORMA = 100
JUEGOS_POR_PLATAFORMA_OVERRIDE = {
    "ios": 150,
    "android": 150,
}

# Nota mínima de Metacritic para filtrar solo juegos bien valorados.
# Pon None si quieres TODO (incluyendo juegos sin nota).
METACRITIC_MINIMO = 70

# '-metacritic' | '-rating' | '-added' | '-released'
ORDEN = "-metacritic"

# Rango de fechas. None = sin filtro.
FECHA_DESDE = "2015-01-01"
FECHA_HASTA = None

PAUSA_SEGUNDOS = 0.3


# =====================================================================
# HELPERS
# =====================================================================
def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode()
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    return re.sub(r"[-\s]+", "-", texto)[:80]


def obtener_lista(plataforma_id: int, pagina: int, page_size: int = 40,
                   metacritic_min=METACRITIC_MINIMO, orden: str = ORDEN,
                   fecha_desde=FECHA_DESDE, fecha_hasta=FECHA_HASTA) -> list:
    params = {
        "key": API_KEY,
        "platforms": plataforma_id,
        "page_size": page_size,
        "page": pagina,
        "ordering": orden,
    }
    if metacritic_min:
        params["metacritic"] = f"{metacritic_min},100"
    if fecha_desde or fecha_hasta:
        desde = fecha_desde or "1970-01-01"
        hasta = fecha_hasta or "2099-12-31"
        params["dates"] = f"{desde},{hasta}"
    try:
        r = requests.get("https://api.rawg.io/api/games", params=params, timeout=15)
        if r.status_code == 404:
            # RAWG ya no tiene más páginas para este filtro (fin del catálogo).
            return []
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        print(f"  ✗ Error listando página {pagina}: {e}")
        return []


def obtener_detalle(juego_id: int) -> dict:
    try:
        r = requests.get(
            f"https://api.rawg.io/api/games/{juego_id}",
            params={"key": API_KEY},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ✗ Error detalle {juego_id}: {e}")
        return {}


def formatear_ficha(detalle: dict, plataforma_nombre: str) -> str:
    nombre = detalle.get("name", "").strip()
    if not nombre:
        return ""

    lineas = [f"JUEGO: {nombre}", "", "FUENTE: RAWG", f"PLATAFORMA PRINCIPAL: {plataforma_nombre}"]

    plats = detalle.get("platforms") or []
    if plats:
        nombres = [p.get("platform", {}).get("name") for p in plats if p.get("platform")]
        nombres = [n for n in nombres if n]
        if nombres:
            lineas.append(f"DISPONIBLE EN: {', '.join(nombres)}")

    if detalle.get("released"):
        lineas.append(f"FECHA DE LANZAMIENTO: {detalle['released']}")

    devs = detalle.get("developers") or []
    if devs:
        nombres = [d.get("name", "") for d in devs if d.get("name")]
        if nombres:
            lineas.append(f"DESARROLLADOR: {', '.join(nombres)}")

    pubs = detalle.get("publishers") or []
    if pubs:
        nombres = [p.get("name", "") for p in pubs if p.get("name")]
        if nombres:
            lineas.append(f"PUBLISHER: {', '.join(nombres)}")

    generos = detalle.get("genres") or []
    if generos:
        nombres = [g.get("name", "") for g in generos if g.get("name")]
        if nombres:
            lineas.append(f"GÉNEROS: {', '.join(nombres)}")

    if detalle.get("metacritic"):
        lineas.append(f"NOTA METACRITIC: {detalle['metacritic']}")

    if detalle.get("rating"):
        cnt = detalle.get("ratings_count", 0)
        lineas.append(f"RATING USUARIOS: {detalle['rating']}/5 ({cnt} votos)")

    if detalle.get("playtime"):
        lineas.append(f"TIEMPO DE JUEGO MEDIO: {detalle['playtime']} horas")

    tags = detalle.get("tags") or []
    if tags:
        tags_txt = [t.get("name") for t in tags[:15] if t.get("language") == "eng" and t.get("name")]
        if tags_txt:
            lineas.append(f"TAGS: {', '.join(tags_txt)}")

    lineas.append("")
    lineas.append("DESCRIPCIÓN:")
    desc = detalle.get("description_raw", "").strip()
    lineas.append(desc if desc else "(Sin descripción disponible)")

    return "\n".join(lineas) + "\n"


# =====================================================================
# MAIN
# =====================================================================
def descargar_plataforma(plataforma_key: str):
    p = PLATAFORMAS[plataforma_key]
    objetivo = JUEGOS_POR_PLATAFORMA_OVERRIDE.get(plataforma_key, JUEGOS_POR_PLATAFORMA)
    metacritic_min = p.get("metacritic_min", METACRITIC_MINIMO)
    orden = p.get("orden", ORDEN)
    rating_min = p.get("rating_min")
    votos_min = p.get("votos_min", 0)
    fecha_desde = p.get("fecha_desde", FECHA_DESDE)
    fecha_hasta = p.get("fecha_hasta", FECHA_HASTA)

    print(f"\n══════ {p['nombre']} (objetivo: {objetivo}) ══════")

    guardados = 0
    saltados = 0
    descartados_calidad = 0
    pagina = 1
    page_size = 40

    while guardados < objetivo:
        juegos =         juegos = obtener_lista(p["id"], pagina, page_size, metacritic_min, orden, fecha_desde, fecha_hasta)
        if not juegos:
            break

        for j in juegos:
            if guardados >= objetivo:
                break

            nombre = j.get("name", "").strip()
            juego_id = j.get("id")
            if not nombre or not juego_id:
                continue

            if votos_min and j.get("ratings_count", 0) < votos_min:
                descartados_calidad += 1
                continue
            if rating_min and j.get("rating", 0) < rating_min:
                descartados_calidad += 1
                continue

            slug = slugify(nombre)
            nombre_archivo = f"rawg_{p['slug']}_{slug}.txt"
            path = CARPETA_DOCS / nombre_archivo

            if path.exists():
                saltados += 1
                continue

            detalle = obtener_detalle(juego_id)
            time.sleep(PAUSA_SEGUNDOS)
            if not detalle:
                continue

            ficha = formatear_ficha(detalle, p["nombre"])
            if not ficha:
                continue

            path.write_text(ficha, encoding="utf-8")
            guardados += 1
            print(f"  ✓ {guardados}/{objetivo}: {nombre}")

        pagina += 1
        time.sleep(PAUSA_SEGUNDOS)

    print(f"  → Guardados: {guardados}, ya existían: {saltados}, descartados por calidad: {descartados_calidad}")


if __name__ == "__main__":
    print(f"Descargando desde RAWG a: {CARPETA_DOCS}")
    print(f"Plataformas: {', '.join(PLATAFORMAS_A_DESCARGAR)}")
    print(f"Filtro: Metacritic >= {METACRITIC_MINIMO}, desde {FECHA_DESDE}\n")

    for pk in PLATAFORMAS_A_DESCARGAR:
        if pk in PLATAFORMAS:
            descargar_plataforma(pk)
        else:
            print(f"✗ Plataforma desconocida: {pk}")

    print("\n══════════════════════════════════════")
    print("Listo. Ahora corre:")
    print("   python construir_base.py")
    print("para que Kira aprenda los nuevos juegos.")
    print("══════════════════════════════════════")