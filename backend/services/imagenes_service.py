"""
Servicio de imágenes: índice de juegos (lee data/documentos/) y búsqueda de
portadas en Steam (directo) y RAWG (API). Antes estaba en extras_kira.py.
"""

import re
import unicodedata
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.config import CARPETA_DOCS, RAWG_API_KEY

# Estado interno
INDICE_JUEGOS = {}          # nombre_lower -> {nombre, plataforma, appid, fuente}
_cache_imagenes = {}        # nombre_lower -> url (o None)


# =====================================================================
# ÍNDICE DE JUEGOS (lee todos los .txt de documentos/)
# =====================================================================
def _extraer_titulo_ficha(path):
    """Lee la primera línea 'JUEGO: X' del archivo."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            primera = f.readline().strip()
        m = re.match(r"JUEGO:\s*(.+)", primera, re.IGNORECASE)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def _leer_campo(path, campo):
    """Lee el valor de una línea 'CAMPO: valor' de la ficha (solo la cabecera)."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for _ in range(30):
                linea = f.readline()
                if not linea:
                    break
                if linea.startswith(campo + ":"):
                    return linea.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def construir_indice_juegos():
    """
    Escanea documentos/ y arma un índice {nombre_lower: info}.
    Reconoce fichas de Steam, Metacritic y Pokémon a partir del nombre de archivo.
    """
    global INDICE_JUEGOS
    if not CARPETA_DOCS.exists():
        return {}

    indice = {}
    for fp in CARPETA_DOCS.glob("*.txt"):
        titulo = _extraer_titulo_ficha(fp)
        if not titulo:
            continue

        nombre_archivo = fp.stem
        info = {"nombre": titulo, "plataforma": None, "appid": None, "fuente": None, "portada": None}

        if nombre_archivo.startswith(("steam_", "steamresenas_")):
            partes = nombre_archivo.split("_", 2)
            if len(partes) >= 2 and partes[1].isdigit():
                info["appid"] = partes[1]
            info["plataforma"] = "PC"
            info["fuente"] = "steam"
        elif nombre_archivo.startswith("metacritic_"):
            partes = nombre_archivo.split("_", 2)
            if len(partes) >= 2:
                info["plataforma"] = partes[1]
            info["fuente"] = "metacritic"
        elif nombre_archivo.startswith("rawg_"):
            partes = nombre_archivo.split("_", 2)
            if len(partes) >= 2:
                info["plataforma"] = partes[1]
            info["fuente"] = "rawg"
        elif nombre_archivo.startswith("pokemon_"):
            partes = nombre_archivo.split("_", 2)
            if len(partes) >= 2:
                info["plataforma"] = partes[1]
            info["fuente"] = "pokemon"
        elif nombre_archivo.startswith("igdb_"):
            info["fuente"] = "igdb"
            info["plataforma"] = "multi"
            info["portada"] = _leer_campo(fp, "PORTADA")

        clave = titulo.lower().strip()
        anterior = indice.get(clave)
        # El mismo juego puede venir de varias fuentes: se conserva la que tiene imagen
        # (appid de Steam o portada de IGDB) y se le suma lo que falte.
        if anterior:
            for k in ("appid", "portada", "plataforma", "fuente"):
                if not anterior.get(k) and info.get(k):
                    anterior[k] = info[k]
            continue
        indice[clave] = info

    INDICE_JUEGOS = indice
    return indice


# =====================================================================
# DETECCIÓN DE JUEGOS MENCIONADOS EN UN TEXTO
# =====================================================================
def _normalizar(t):
    """
    Normaliza un título o un mensaje para compararlos sin importar cómo se escriban:
    minúsculas, sin tildes, sin apóstrofos ni puntuación, y sin la «s» final de cada
    palabra (plural). Así «Assassin's Creed Shadows» y «assassins creed shadow»
    quedan iguales: «assassin creed shadow».
    """
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    sin_apostrofos = re.sub(r"['’`´]", "", sin_tildes)
    palabras = re.sub(r"[^a-z0-9]+", " ", sin_apostrofos).split()
    palabras = [p[:-1] if len(p) > 3 and p.endswith("s") else p for p in palabras]
    # Números romanos como dígitos: «Dark Souls III» = «dark souls 3»
    return " ".join(_ROMANOS.get(p, p) for p in palabras)


_ROMANOS = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8",
            "ix": "9", "x": "10", "xi": "11", "xii": "12", "xiii": "13", "xv": "15", "xvi": "16"}


_SUBTITULO_GENERICO = re.compile(
    r"\b(edition|edicion|remaster|remastered|cut|collection|coleccion|deluxe|goty|year|bundle|"
    r"pack|season|dlc|expansion|complete|ultimate|anniversary|version|hd|definitive)\b")

_indice_normalizado = {"n": -1, "claves": []}   # caché: [(clave_normalizada, info)] de mayor a menor largo


def _claves_normalizadas():
    if _indice_normalizado["n"] != len(INDICE_JUEGOS):
        pares = {}
        for info in INDICE_JUEGOS.values():
            clave = _normalizar(info["nombre"])
            if len(clave) >= 4:            # ignorar nombres muy cortos (evita falsos positivos)
                pares.setdefault(clave, info)
        # Alias sin subtítulo: «The Witcher 3: Wild Hunt» también se reconoce como «the witcher 3»
        # Solo si el alias es único y lleva número de entrega (evita que «the legend of zelda»
        # apunte a un juego cualquiera de la saga).
        prefijos = {}
        for info in INDICE_JUEGOS.values():
            if ":" in info["nombre"]:
                corto = _normalizar(info["nombre"].split(":")[0])
                prefijos.setdefault(corto, []).append(info)
        for corto, infos in prefijos.items():
            if len(infos) == 1 and re.search(r"\d", corto) and len(corto.split()) >= 2:
                pares.setdefault(corto, infos[0])
        # Alias por subtítulo: «The Legend of Zelda: Breath of the Wild» también se reconoce
        # como «breath of the wild». Solo subtítulos únicos, de 3+ palabras y que no sean
        # genéricos («Definitive Edition», «Director's Cut»...).
        subtitulos = {}
        for info in INDICE_JUEGOS.values():
            if ":" in info["nombre"]:
                sub = _normalizar(info["nombre"].split(":", 1)[1])
                minimo = 4 if sub.split()[0] in ("the", "a", "an") else 3   # «the new world»: muy genérico
                if len(sub.split()) >= minimo and len(sub) >= 12 and not _SUBTITULO_GENERICO.search(sub):
                    subtitulos.setdefault(sub, set()).add(info["nombre"])
        for sub, nombres in subtitulos.items():
            if len(nombres) == 1:
                nombre = next(iter(nombres))
                pares.setdefault(sub, next(i for i in INDICE_JUEGOS.values() if i["nombre"] == nombre))
        _indice_normalizado["claves"] = sorted(pares.items(), key=lambda kv: len(kv[0]), reverse=True)
        _indice_normalizado["n"] = len(INDICE_JUEGOS)
    return _indice_normalizado["claves"]


# ---------------------------------------------------------------------
# Tolerancia a errores de escritura («asassins creed shadow»)
# ---------------------------------------------------------------------
# Similitud mínima (0 a 100) entre lo que escribió la persona y el título.
# Con 1 o 2 letras mal en un título largo la similitud queda sobre 88.
SIMILITUD_MINIMA = 88
SIMILITUD_MINIMA_CORTOS = 92   # títulos de una palabra: un error pesa más
# Palabras que solas nunca forman un título (evita falsos positivos)
_PALABRAS_COMUNES = {
    "juego", "juegos", "videojuego", "de", "del", "la", "el", "los", "las", "un", "una", "y", "o",
    "para", "con", "que", "como", "mejor", "mejores", "requisito", "requisitos", "minimo", "minimos",
    "recomendado", "pc", "ps5", "ps4", "xbox", "switch", "nintendo", "playstation", "precio", "nota",
    "resena", "parecido", "parecidos", "a", "en", "me", "mi", "tu", "kira", "the", "of", "and",
}


def _detectar_con_errores(texto, max_juegos, ya_normalizado=False):
    """Busca títulos parecidos (no idénticos) a partes del texto, con rapidfuzz."""
    try:
        from rapidfuzz import fuzz, process
    except ImportError:                    # sin rapidfuzz: no se corrigen errores
        return []

    claves = [c for c, _ in _claves_normalizadas() if len(c) >= 8]
    # títulos cortos de una palabra («Celeste», «Hades»): solo con una palabra y más parecido
    cortas = [c for c, _ in _claves_normalizadas() if 5 <= len(c) < 8 and " " not in c]
    info_de = dict(_claves_normalizadas())
    palabras = (texto if ya_normalizado else _normalizar(texto)).split()

    # 1. Todos los trozos del mensaje (de 1 a 8 palabras) parecidos a algún título
    candidatos = []
    for n in range(1, min(8, len(palabras)) + 1):
        for i in range(len(palabras) - n + 1):
            trozo = palabras[i:i + n]
            frase = " ".join(trozo)
            if all(p in _PALABRAS_COMUNES for p in trozo):
                continue
            if len(frase) >= 8:
                match = process.extractOne(frase, claves, scorer=fuzz.ratio, score_cutoff=SIMILITUD_MINIMA)
                if match and match[1] < 100:   # los idénticos ya los encuentra la búsqueda exacta
                    candidatos.append((match[1], n, i, match[0]))
            if n == 1 and 5 <= len(frase) <= 9:
                match = process.extractOne(frase, cortas, scorer=fuzz.ratio, score_cutoff=SIMILITUD_MINIMA_CORTOS)
                if match and match[1] < 100:
                    candidatos.append((match[1], n, i, match[0]))

    # 2. Gana el más parecido (y a igual parecido, el más largo), sin que se pisen:
    #    «god of war ragnarock vale la pena» -> «God of War: Ragnarok» (97) y no
    #    «God of War: Ragnarok - Valhalla» (que solo se parece porque «vale» ~ «valhalla»)
    candidatos.sort(key=lambda c: (-c[0], -c[1]))
    usadas, encontrados, vistos = set(), [], set()
    for _, n, i, clave in candidatos:
        tramo = set(range(i, i + n))
        info = info_de[clave]
        if tramo & usadas or info["nombre"] in vistos:
            continue
        encontrados.append(info)
        vistos.add(info["nombre"])
        usadas |= tramo
        if len(encontrados) >= max_juegos:
            break
    return encontrados


def detectar_juegos_en_texto(texto, max_juegos=4, tolerar_errores=False):
    """
    Detecta qué juegos del índice aparecen mencionados en el texto.
    Con tolerar_errores=True (mensajes del usuario), si no hay coincidencia exacta
    busca títulos parecidos: «asassins creed shadow» -> Assassin's Creed Shadows.
    """
    if not INDICE_JUEGOS or not texto:
        return []
    exactos = _detectar_exactos(texto, max_juegos)
    if not tolerar_errores:
        return exactos
    parecidos = _detectar_con_errores(texto, max_juegos)
    if not exactos:
        return parecidos
    # «god of war ragnarock»: el exacto «God of War» es parte de un título más largo
    # escrito con un error («God of War: Ragnarok»). Gana el título más completo.
    resultado, usados = [], set()
    for e in exactos:
        clave_e = f" {_normalizar(e['nombre'])} "
        mejor = next((p for p in parecidos
                      if clave_e in f" {_normalizar(p['nombre'])} " and p["nombre"] != e["nombre"]), e)
        if mejor["nombre"] not in {r["nombre"] for r in resultado}:
            resultado.append(mejor)
            usados.add(mejor["nombre"])
    # «elden rign o dark souls 3»: otro juego mal escrito junto a uno bien escrito.
    # Se busca solo en lo que queda del mensaje sin los juegos ya reconocidos (así
    # «final fantasy vii remake» no suma también «Final Fantasy IX»).
    resto = f" {_normalizar(texto)} "
    for r in resultado + exactos:
        resto = resto.replace(f" {_normalizar(r['nombre'])} ", " | ")
    otros = []
    for segmento in resto.split("|"):
        otros += _detectar_con_errores(segmento, max_juegos, ya_normalizado=True)
    for p in otros:
        clave_p = f" {_normalizar(p['nombre'])} "
        if p["nombre"] not in usados and not any(
                f" {_normalizar(r['nombre'])} " in clave_p or clave_p in f" {_normalizar(r['nombre'])} "
                for r in resultado):
            resultado.append(p)
    return resultado[:max_juegos]


def _detectar_exactos(texto, max_juegos):

    texto_norm = f" {_normalizar(texto)} "
    encontrados = []
    vistos = set()

    # De mayor a menor largo para que "God of War Ragnarok" pegue antes que "God of War"
    for clave, info in _claves_normalizadas():
        patron = f" {clave} "
        if patron in texto_norm and info["nombre"] not in vistos:
            encontrados.append(info)
            vistos.add(info["nombre"])
            # Quitar la coincidencia para no re-detectar substrings
            texto_norm = texto_norm.replace(patron, " | ")
            if len(encontrados) >= max_juegos:
                break
    return encontrados


# =====================================================================
# BÚSQUEDA DE IMÁGENES (Steam directo + RAWG)
# =====================================================================
def imagen_de_steam(appid):
    """URL directa del header de Steam. Sin API key."""
    if not appid:
        return None
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"


def imagen_de_rawg(nombre):
    """Busca la portada del juego en RAWG. Requiere RAWG_API_KEY."""
    if not RAWG_API_KEY or not nombre:
        return None
    key = nombre.lower().strip()
    if key in _cache_imagenes:
        return _cache_imagenes[key]
    try:
        r = requests.get(
            "https://api.rawg.io/api/games",
            params={"key": RAWG_API_KEY, "search": nombre, "page_size": 1},
            timeout=6,
        )
        if r.status_code == 200:
            resultados = r.json().get("results", [])
            if resultados:
                url = resultados[0].get("background_image")
                _cache_imagenes[key] = url
                return url
    except Exception as e:
        print(f"RAWG error para '{nombre}': {e}")

    _cache_imagenes[key] = None
    return None


def obtener_imagenes_para_respuesta(respuesta):
    """
    Detecta juegos en el texto y devuelve sus imágenes.

    Las URLs de Steam son directas (no requieren red aquí, el navegador las
    carga solas). Las de RAWG sí requieren un request HTTP: antes se hacían
    una por una de forma secuencial (hasta 4 llamadas x 6s de timeout = hasta
    24s de bloqueo). Ahora se lanzan en paralelo para que el peor caso sea
    ~6s en vez de ~24s.
    """
    juegos = detectar_juegos_en_texto(respuesta)

    resultado = []
    pendientes_rawg = []  # juegos que necesitan ir a buscar a RAWG

    for j in juegos:
        if j["appid"]:
            resultado.append({
                "nombre": j["nombre"],
                "plataforma": j["plataforma"] or "PC",
                "url": imagen_de_steam(j["appid"]),
            })
        elif j.get("portada"):                     # portada de IGDB: directa, sin API key
            resultado.append({
                "nombre": j["nombre"],
                "plataforma": "Multiplataforma",
                "url": j["portada"],
            })
        elif j["plataforma"] and j["plataforma"] != "PC":
            pendientes_rawg.append(j)

    if pendientes_rawg:
        with ThreadPoolExecutor(max_workers=min(4, len(pendientes_rawg))) as pool:
            futuros = {
                pool.submit(imagen_de_rawg, j["nombre"]): j
                for j in pendientes_rawg
            }
            for futuro in as_completed(futuros):
                j = futuros[futuro]
                try:
                    url = futuro.result()
                except Exception as e:
                    print(f"RAWG error paralelo para '{j['nombre']}': {e}")
                    url = None
                if url:
                    resultado.append({
                        "nombre": j["nombre"],
                        "plataforma": j["plataforma"] or "PC",
                        "url": url,
                    })

    return resultado