"""
Descarga TODOS los juegos de Pokémon desde PokeAPI (https://pokeapi.co/docs/v2)
y los guarda como fichas .txt en data/documentos/ para la base de conocimiento.

PokeAPI es pública: no necesita API key ni cuenta.

Por cada versión (Rojo, Azul, Oro, ..., Escarlata, Púrpura y sus DLC) la ficha incluye:
  - nombre en español y en inglés, plataforma real, generación y región
  - versiones hermanas (lanzadas juntas)
  - sus Pokédex regionales y cuántos Pokémon tiene cada una
  - Pokémon iniciales
  - Pokémon legendarios y singulares que aparecen en su Pokédex

Uso (desde la carpeta raíz kira/):
    python -m backend.scrapers.pokeapi
    python -m backend.vectorDb.ingest          # después, para cargarlo en la base

Las respuestas de la API se guardan en data/cache_pokeapi/: si se vuelve a correr
no se repiten las consultas (PokeAPI pide no saturarla). Se puede borrar sin problema.
"""

import json
import os
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import requests

from backend.config import CARPETA_DOCS, RAIZ_PROYECTO

API = "https://pokeapi.co"
# Copia exacta de PokeAPI en GitHub (por si pokeapi.co no responde): POKEAPI_ESPEJO=1
ESPEJO = "https://raw.githubusercontent.com/PokeAPI/api-data/master/data"
USAR_ESPEJO = os.getenv("POKEAPI_ESPEJO") == "1"

CARPETA_CACHE = RAIZ_PROYECTO / "data" / "cache_pokeapi"
HILOS = 4            # consultas en paralelo (moderado, por respeto a la API)
PAUSA = 0.05         # segundos entre consultas de cada hilo

# ---------------------------------------------------------------------------
# Datos que PokeAPI no trae
# ---------------------------------------------------------------------------
PLATAFORMAS = {
    "red-blue": "Game Boy", "yellow": "Game Boy", "red-green-japan": "Game Boy", "blue-japan": "Game Boy",
    "gold-silver": "Game Boy Color", "crystal": "Game Boy Color",
    "ruby-sapphire": "Game Boy Advance", "emerald": "Game Boy Advance", "firered-leafgreen": "Game Boy Advance",
    "colosseum": "Nintendo GameCube", "xd": "Nintendo GameCube",
    "diamond-pearl": "Nintendo DS", "platinum": "Nintendo DS", "heartgold-soulsilver": "Nintendo DS",
    "black-white": "Nintendo DS", "black-2-white-2": "Nintendo DS",
    "x-y": "Nintendo 3DS", "omega-ruby-alpha-sapphire": "Nintendo 3DS", "sun-moon": "Nintendo 3DS",
    "ultra-sun-ultra-moon": "Nintendo 3DS",
    "lets-go-pikachu-lets-go-eevee": "Nintendo Switch", "sword-shield": "Nintendo Switch",
    "the-isle-of-armor": "Nintendo Switch", "the-crown-tundra": "Nintendo Switch",
    "brilliant-diamond-shining-pearl": "Nintendo Switch", "legends-arceus": "Nintendo Switch",
    "scarlet-violet": "Nintendo Switch", "the-teal-mask": "Nintendo Switch", "the-indigo-disk": "Nintendo Switch",
    "legends-za": "Nintendo Switch y Nintendo Switch 2", "mega-dimension": "Nintendo Switch y Nintendo Switch 2",
}
# Expansiones descargables -> juego base
DLC = {
    "the-isle-of-armor": "sword-shield", "the-crown-tundra": "sword-shield",
    "the-teal-mask": "scarlet-violet", "the-indigo-disk": "scarlet-violet",
    "mega-dimension": "legends-za",
}
SPIN_OFF = {"colosseum", "xd"}
INICIALES = {
    "bulbasaur", "charmander", "squirtle", "chikorita", "cyndaquil", "totodile", "treecko", "torchic",
    "mudkip", "turtwig", "chimchar", "piplup", "snivy", "tepig", "oshawott", "chespin", "fennekin",
    "froakie", "rowlet", "litten", "popplio", "grookey", "scorbunny", "sobble", "sprigatito", "fuecoco",
    "quaxly", "pikachu", "eevee",
}


# ---------------------------------------------------------------------------
# Acceso a la API (con caché en disco)
# ---------------------------------------------------------------------------
_sesion = requests.Session()


def obtener(ruta: str) -> dict:
    """ruta: '/api/v2/version-group/4/' (o una URL completa de PokeAPI)."""
    ruta = "/" + ruta.split("pokeapi.co/", 1)[-1].lstrip("/")
    if not ruta.endswith("/") and "?" not in ruta:
        ruta += "/"
    # nombre de archivo válido también en Windows (sin ? ni =)
    archivo_cache = CARPETA_CACHE / (re.sub(r"[^\w-]+", "_", ruta.strip("/")) + ".json")
    if archivo_cache.exists():
        return json.loads(archivo_cache.read_text(encoding="utf-8"))

    if USAR_ESPEJO:   # el espejo no acepta parámetros (?limit=): su índice ya trae todo
        url = f"{ESPEJO}{ruta.split('?')[0].rstrip('/')}/index.json"
    else:
        url = f"{API}{ruta}"
    for intento in range(4):
        try:
            r = _sesion.get(url, timeout=20)
            if r.status_code == 429:                    # demasiadas consultas: esperar
                time.sleep(5 * (intento + 1))
                continue
            r.raise_for_status()
            datos = r.json()
            archivo_cache.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
            time.sleep(PAUSA)
            return datos
        except requests.RequestException:
            if intento == 3:
                raise
            time.sleep(2 * (intento + 1))
    raise RuntimeError(f"No se pudo obtener {url}")


def nombre_es(datos: dict, respaldo: str = "") -> str:
    """Nombre en español (o en inglés si no hay)."""
    nombres = {n["language"]["name"]: n["name"] for n in datos.get("names", [])}
    return nombres.get("es") or nombres.get("es-419") or nombres.get("en") or respaldo


def nombre_en(datos: dict, respaldo: str = "") -> str:
    nombres = {n["language"]["name"]: n["name"] for n in datos.get("names", [])}
    return nombres.get("en") or respaldo


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode()
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    return re.sub(r"[-\s]+", "-", texto)[:80]


def lista(nombres: list[str]) -> str:
    """['A', 'B', 'C'] -> 'A, B y C'."""
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


# ---------------------------------------------------------------------------
# Ficha de cada versión
# ---------------------------------------------------------------------------
def describir(grupo: dict, version: dict, especies: dict, pokedexes: list[dict],
              versiones_es: dict, grupos: dict) -> str:
    vg = grupo["name"]
    juego = f"Pokémon {nombre_es(version, version['name'].title())}"
    juego_en = f"Pokémon {nombre_en(version, version['name'].title())}"
    if version["name"].endswith("-japan"):          # Rojo/Verde/Azul originales de Japón (1996)
        juego += " (Japón)"
        juego_en += " (Japan)"
    plataforma = PLATAFORMAS.get(vg, "")
    generacion = nombre_es(obtener(grupo["generation"]["url"]), grupo["generation"]["name"])
    regiones = [r["name"].title() for r in grupo.get("regions", [])]
    hermanas = [f"Pokémon {versiones_es[v['name']]}" + (" (Japón)" if v["name"].endswith("-japan") else "")
                for v in grupo["versions"] if v["name"] != version["name"]]

    # Pokédex de esta versión
    detalle_dex = []
    especies_juego = []
    for dex in pokedexes:
        entradas = dex["pokemon_entries"]
        detalle_dex.append(f"- {nombre_es(dex, dex['name'].title())}: {len(entradas)} Pokémon")
        especies_juego += [e["pokemon_species"]["name"] for e in entradas]

    # Iniciales: entradas 1, 4 y 7 de la Pokédex regional principal (si de verdad son iniciales)
    iniciales = []
    if vg == "lets-go-pikachu-lets-go-eevee":
        iniciales = ["Pikachu" if "pikachu" in version["name"] else "Eevee"]
    elif pokedexes and vg not in DLC:
        por_numero = {e["entry_number"]: e["pokemon_species"]["name"] for e in pokedexes[0]["pokemon_entries"]}
        candidatos = [por_numero.get(n) for n in (1, 4, 7)]
        if all(c in INICIALES for c in candidatos):
            iniciales = [especies[c]["es"] for c in candidatos]

    legendarios, singulares, vistos = [], [], set()
    for nombre in especies_juego:
        if nombre in vistos or nombre not in especies:
            continue
        vistos.add(nombre)
        if especies[nombre]["legendario"]:
            legendarios.append(especies[nombre]["es"])
        elif especies[nombre]["singular"]:
            singulares.append(especies[nombre]["es"])

    # --- ficha ---
    lineas = [f"JUEGO: {juego}", "", "FUENTE: PokeAPI"]
    if juego_en != juego:
        lineas.append(f"NOMBRE EN INGLÉS: {juego_en}")
    if plataforma:
        lineas.append(f"PLATAFORMA: {plataforma}")
    conocido = vg in PLATAFORMAS or vg in SPIN_OFF      # juegos nuevos que aún no están en las tablas
    if conocido:
        lineas.append("GÉNEROS: " + ("Expansión (DLC), RPG, Aventura" if vg in DLC else "RPG, Aventura"))
    lineas.append(f"GENERACIÓN: {generacion}")
    if regiones:
        lineas.append(f"REGIÓN PRINCIPAL: {', '.join(regiones)}")
    if hermanas:
        lineas.append(f"LANZADO JUNTO A: {', '.join(hermanas)}")

    # --- descripción en prosa (es lo que mejor entiende la búsqueda semántica) ---
    if vg in DLC:
        base = grupos[DLC[vg]]
        base_es = lista([f"Pokémon {versiones_es[v['name']]}" for v in base["versions"]])
        frase = f"{juego} es una expansión descargable (DLC) de {base_es}"
    elif vg in SPIN_OFF:
        frase = f"{juego} es un juego derivado (spin-off) de rol y combates de Pokémon"
    elif conocido:
        frase = f"{juego} es un juego de rol de la saga principal de Pokémon"
    else:
        frase = f"{juego} es un juego de la franquicia Pokémon"
    frase += f", de la {generacion}" if generacion else ""
    frase += f", para {plataforma}." if plataforma else "."
    texto = [frase]
    if regiones:
        texto.append(f"La aventura transcurre en la región de {regiones[0]}." if len(regiones) == 1
                     else f"La aventura transcurre en las regiones de {lista(regiones)}.")
    if hermanas:
        texto.append(f"Se lanzó junto a {lista(hermanas)}; cada versión tiene algunos Pokémon exclusivos.")
    if iniciales:
        texto.append(f"Los Pokémon iniciales que se pueden elegir al comenzar son {lista(iniciales)}."
                     if len(iniciales) > 1 else f"El Pokémon inicial es {iniciales[0]}.")
    if especies_juego:
        texto.append(f"Su Pokédex regional reúne {len(set(especies_juego))} especies de Pokémon distintas.")
    if legendarios:
        texto.append(f"Incluye Pokémon legendarios como {lista(legendarios[:6])}.")

    lineas += ["", "DESCRIPCIÓN:", " ".join(texto)]
    if detalle_dex:
        lineas += ["", "POKÉDEX:", *detalle_dex]
    if iniciales:
        lineas += ["", "POKÉMON INICIALES:", ", ".join(iniciales)]
    if legendarios or singulares:
        lineas += ["", "LEGENDARIOS Y SINGULARES:"]
        if legendarios:
            lineas.append(f"Legendarios: {', '.join(legendarios)}")
        if singulares:
            lineas.append(f"Singulares (míticos): {', '.join(singulares)}")
    return juego, plataforma, "\n".join(lineas) + "\n"


# ---------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------
def main():
    CARPETA_DOCS.mkdir(parents=True, exist_ok=True)
    CARPETA_CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Descargando juegos de Pokémon desde {'el espejo de GitHub' if USAR_ESPEJO else 'pokeapi.co'}...")

    indice = obtener("/api/v2/version-group/?limit=100")
    grupos = {g["name"]: obtener(g["url"]) for g in indice["results"]}
    print(f"  {len(grupos)} grupos de versiones")

    versiones = {v["name"]: obtener(v["url"]) for g in grupos.values() for v in g["versions"]}
    versiones_es = {n: nombre_es(d, n.title()) for n, d in versiones.items()}
    print(f"  {len(versiones)} versiones (juegos y DLC)")

    pokedex_de = {}
    for g in grupos.values():
        pokedex_de[g["name"]] = [obtener(p["url"]) for p in g["pokedexes"]]

    # Datos de cada especie (legendario / singular / nombre en español), una sola vez
    urls = {e["pokemon_species"]["name"]: e["pokemon_species"]["url"]
            for dexes in pokedex_de.values() for d in dexes for e in d["pokemon_entries"]}
    print(f"  Leyendo {len(urls)} especies de Pokémon (la primera vez tarda unos minutos)...")
    especies = {}

    def leer(par):
        nombre, url = par
        d = obtener(url)
        return nombre, {"es": nombre_es(d, nombre.title()), "legendario": d["is_legendary"],
                        "singular": d["is_mythical"]}

    with ThreadPoolExecutor(max_workers=HILOS) as pool:
        for i, (nombre, info) in enumerate(pool.map(leer, urls.items()), 1):
            especies[nombre] = info
            if i % 200 == 0:
                print(f"    {i}/{len(urls)}")

    # Borrar las fichas antiguas de PokeAPI (las nuevas las reemplazan)
    borradas = 0
    for archivo in CARPETA_DOCS.glob("pokemon_*.txt"):
        if "FUENTE: PokeAPI" in archivo.read_text(encoding="utf-8", errors="ignore"):
            archivo.unlink()
            borradas += 1

    guardados = 0
    for g in grupos.values():
        for v in g["versions"]:
            juego, plataforma, contenido = describir(g, versiones[v["name"]], especies,
                                                     pokedex_de[g["name"]], versiones_es, grupos)
            archivo = CARPETA_DOCS / f"pokemon_{slugify(plataforma or 'nintendo')}_{slugify(juego)}.txt"
            archivo.write_text(contenido, encoding="utf-8")
            guardados += 1
            print(f"  ✓ {juego} ({plataforma or 'plataforma no informada'})")

    print(f"\nListo: {guardados} juegos de Pokémon guardados ({borradas} fichas antiguas reemplazadas).")
    print("Ahora reconstruye la base:  python -m backend.vectorDb.ingest")


if __name__ == "__main__":
    main()
