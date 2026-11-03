"""
Limpieza y preprocesamiento del texto ANTES de vectorizar (fase 1 del pipeline RAG:
ingesta y procesamiento).

Los .txt de data/documentos/ vienen de scrapers (Steam, Metacritic, RAWG, PokeAPI) y
traen "basura" de las páginas web que ensucia los embeddings:
  - prefijo "Summary " y colas tipo "... Read More Adventure Developer: ..." (Metacritic)
  - el mismo párrafo repetido en dos secciones (resumen y descripción)
  - entidades y etiquetas HTML (&quot;  &#39;  <br/>  [b]...[/b])
  - símbolos ® ™ ©, emojis, espacios invisibles
  - palabras pegadas al perder un salto de línea ("construirloConstruye")
  - URLs, espacios y líneas en blanco de sobra
  - secciones vacías (ej. "REQUISITOS MÍNIMOS (MAC): Mínimo:" sin nada más)

Aquí se limpia todo eso con expresiones regulares (re), igual que en el laboratorio,
y se separa cada documento en:
  - campos   : la ficha (JUEGO, PLATAFORMA, GÉNEROS, NOTA...) -> también metadatos
  - secciones: los textos largos (descripción, reseña, requisitos)

OJO: aquí NO se pasa a minúsculas, NI se quitan stopwords, NI se hace stemming.
El modelo de embeddings (multilingual-e5-small) entiende frases completas: "no me gustó"
y "me gustó" deben quedar distintas, y el texto que se guarda es el mismo que lee
Gemini para responder. Esas técnicas del laboratorio se usan en analisis_nlp.py
para estudiar el corpus (frecuencias, raíces), que es donde sí sirven.
"""

import html
import re
import unicodedata

# ---------------------------------------------------------------------------
# Estructura de los documentos
# ---------------------------------------------------------------------------
# Campos de la ficha (una línea "CAMPO: valor")
CAMPOS_FICHA = {
    "JUEGO", "PLATAFORMA", "PLATAFORMA PRINCIPAL", "DISPONIBLE EN", "GÉNEROS",
    "FECHA DE LANZAMIENTO", "DESARROLLADOR", "PUBLISHER", "PRECIO", "NOTA METACRITIC",
    "RATING USUARIOS", "TIEMPO DE JUEGO MEDIO", "TAGS", "RESEÑAS DE USUARIOS (STEAM)",
    "GENERACIÓN", "REGIÓN PRINCIPAL", "LANZADO JUNTO A", "FUENTE", "NOMBRE EN INGLÉS",
    # IGDB
    "TEMAS", "MODOS DE JUEGO", "PERSPECTIVA", "NOTA DE LA CRÍTICA (IGDB)", "NOTA DE USUARIOS (IGDB)",
    "FRANQUICIA", "TAMBIÉN CONOCIDO COMO", "PORTADA", "URL",
    # Reseñas de Steam
    "VALORACIÓN DE USUARIOS (STEAM)",
}
# Títulos de sección (una línea "TÍTULO:" y debajo el texto)
_RE_SECCION = re.compile(
    r"^(DESCRIPCIÓN(?: DETALLADA| / RESEÑA)?|RESEÑA / DESCRIPCIÓN|RESUMEN DE LA CRÍTICA"
    r"|REQUISITOS (?:MÍNIMOS|RECOMENDADOS)(?: \([A-Z]+\))?"
    r"|POKÉDEX|POKÉMON INICIALES|LEGENDARIOS Y SINGULARES"
    r"|RESUMEN|HISTORIA|JUEGOS PARECIDOS|RESEÑAS DE USUARIOS):\s*$"
)
_RE_CAMPO = re.compile(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ /()]{1,40}):\s*(.+)$")

# Nombres reales con mayúscula al medio (no son palabras pegadas)
_NO_SEPARAR = {"tinyBuild", "wipEout", "synchroniSing", "iPhone", "iPad", "eShop", "eSports"}


# ---------------------------------------------------------------------------
# Limpiezas con expresiones regulares
# ---------------------------------------------------------------------------
def normalizar_unicode(texto: str) -> str:
    """Unifica la forma de las tildes y quita caracteres invisibles."""
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace(" ", " ")                       # espacio duro
    texto = re.sub(r"[​-‏⁠﻿]", "", texto)   # espacios de ancho cero
    texto = texto.replace("’", "'").replace("‘", "'")
    texto = texto.replace("“", '"').replace("”", '"')
    return texto


def quitar_html(texto: str) -> str:
    """Decodifica entidades (&quot; -> ") y borra etiquetas HTML y BBCode."""
    texto = html.unescape(html.unescape(texto))                 # a veces vienen dobles
    texto = re.sub(r"<br\s*/?>", "\n", texto, flags=re.I)
    texto = re.sub(r"</?[a-zA-Z][^>]{0,80}>", " ", texto)
    texto = re.sub(r"\[/?(?:b|i|u|h\d|list|url|img|\*)(?:=[^\]]*)?\]", " ", texto, flags=re.I)
    return texto


def quitar_simbolos(texto: str) -> str:
    """Borra ® ™ ©, emojis y otros símbolos que no aportan significado."""
    texto = re.sub(r"[®™©℠]", "", texto)
    texto = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", texto)
    return texto


def quitar_urls(texto: str) -> str:
    return re.sub(r"https?://\S+|www\.\S+", "", texto)


def separar_palabras_pegadas(texto: str) -> str:
    """'construirloConstruye' -> 'construirlo. Construye' (se perdió un salto de línea).
    Solo si la primera parte empieza en minúscula: así no rompe 'PlayStation'."""
    def _separar(m):
        palabra = m.group(0)
        if palabra in _NO_SEPARAR:
            return palabra
        return f"{m.group(1)}. {m.group(2)}"
    return re.sub(r"\b([a-záéíóúñü]{4,})([A-ZÁÉÍÓÚÑ][a-záéíóúñü]{2,})\b", _separar, texto)


def quitar_ruido_metacritic(texto: str) -> str:
    """Quita 'Summary ' del inicio y la cola '... Read More <géneros> Developer: ...'."""
    texto = re.sub(r"^Summary\s+", "", texto)
    corte = re.search(r"(?:\s*\.\.\.)?\s*Read More\b|\s+Rated [A-Z0-9+]{1,5} for |\s+Developer:\s", texto)
    if corte:
        texto = texto[:corte.start()]
        # si quedó un resto suelto tras el último punto (ej. "Adventure"), se corta
        ultimo = max(texto.rfind("."), texto.rfind("!"), texto.rfind("?"))
        if ultimo != -1 and len(texto) - ultimo < 40:
            texto = texto[:ultimo + 1]
    return texto.strip()


def normalizar_espacios(texto: str) -> str:
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def limpiar_texto(texto: str) -> str:
    """Aplica todas las limpiezas a un texto libre (descripción, reseña...)."""
    texto = normalizar_unicode(texto)
    texto = quitar_html(texto)
    texto = quitar_simbolos(texto)
    texto = quitar_urls(texto)
    texto = separar_palabras_pegadas(texto)
    return normalizar_espacios(texto)


def limpiar_requisitos(texto: str) -> str:
    """Requisitos de Steam: una línea por ítem, sin 'Mínimo:'/'Recomendado:' sueltos."""
    lineas = []
    for linea in limpiar_texto(texto).split("\n"):
        linea = linea.strip()
        if not linea or re.fullmatch(r"(Mínimo|Recomendado|Minimum|Recommended):?", linea, re.I):
            continue
        lineas.append(linea)
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Documento completo
# ---------------------------------------------------------------------------
def _clave_comparacion(texto: str) -> str:
    """Versión simplificada para detectar párrafos repetidos."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def separar_documento(texto: str) -> tuple[dict, list[tuple[str, str]]]:
    """Separa el .txt en campos de la ficha y secciones de texto (sin limpiar aún)."""
    campos, secciones = {}, []
    titulo, buffer = None, []

    def cerrar():
        if titulo is not None:
            secciones.append((titulo, "\n".join(buffer)))

    for linea in normalizar_unicode(texto).split("\n"):
        m_sec = _RE_SECCION.match(linea.strip())
        if m_sec:
            cerrar()
            titulo, buffer = m_sec.group(1), []
            continue
        m_campo = _RE_CAMPO.match(linea.strip())
        if m_campo and m_campo.group(1) in CAMPOS_FICHA and (titulo is None or m_campo.group(1) == "FUENTE"):
            campos.setdefault(m_campo.group(1), m_campo.group(2).strip())
            if m_campo.group(1) in ("FUENTE", "URL") and m_campo.group(2).startswith("http"):
                campos["URL"] = m_campo.group(2).strip()
            continue
        if titulo is not None:
            buffer.append(linea)
    cerrar()
    return campos, secciones


def limpiar_documento(texto: str) -> tuple[dict, list[tuple[str, str]]]:
    """
    Devuelve (campos, secciones) ya limpios:
      - campos: dict de la ficha (sin URLs, sin símbolos)
      - secciones: [(título, texto limpio)] sin secciones vacías ni repetidas
    """
    campos_crudos, secciones_crudas = separar_documento(texto)

    campos = {}
    for clave, valor in campos_crudos.items():
        if clave in ("URL", "PORTADA"):          # enlaces: se guardan como metadato, no se vectorizan
            campos[clave] = valor
            continue
        valor = normalizar_espacios(quitar_simbolos(quitar_html(valor)))
        if valor and not valor.startswith("http"):
            campos[clave] = valor

    secciones = []
    for titulo, contenido in secciones_crudas:
        if titulo.startswith("REQUISITOS"):
            contenido = limpiar_requisitos(contenido)
        else:
            if titulo == "RESUMEN DE LA CRÍTICA":
                contenido = quitar_ruido_metacritic(contenido.strip())
            contenido = limpiar_texto(contenido)
        if len(contenido) >= 15:            # sección vacía o casi vacía: fuera
            secciones.append((titulo, contenido))

    # Secciones repetidas: si el inicio de una ya aparece dentro de otra, se descarta
    # la más corta (ej. "RESUMEN DE LA CRÍTICA" que repite la descripción de Metacritic).
    claves = [_clave_comparacion(c) for _, c in secciones]
    sin_repetir = []
    for i, (titulo, contenido) in enumerate(secciones):
        inicio = claves[i][:120]
        repetida = any(
            j != i and inicio in claves[j] and (len(claves[j]) > len(claves[i]) or (len(claves[j]) == len(claves[i]) and j < i))
            for j in range(len(secciones))
        )
        if not repetida:
            sin_repetir.append((titulo, contenido))

    # Párrafos repetidos dentro de una misma sección
    resultado = []
    for titulo, contenido in sin_repetir:
        vistos, parrafos = set(), []
        for p in re.split(r"\n\s*\n", contenido):
            k = _clave_comparacion(p)
            if k and k not in vistos:
                vistos.add(k)
                parrafos.append(p.strip())
        resultado.append((titulo, "\n\n".join(parrafos)))
    return campos, resultado


def _a_numero(valor: str | None):
    if not valor:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", valor)
    return float(m.group(0).replace(",", ".")) if m else None


def metadatos_de(campos: dict, nombre_archivo: str) -> dict:
    """Metadatos para ChromaDB (permiten filtrar antes de buscar). Solo str/int/float."""
    meta = {
        "fuente": nombre_archivo,                                  # lo usa retrieve.py
        "origen": nombre_archivo.split("_", 1)[0],                 # steam / rawg / metacritic / pokemon
        "juego": campos.get("JUEGO", ""),
        "plataforma": campos.get("PLATAFORMA") or campos.get("PLATAFORMA PRINCIPAL", ""),
        "generos": campos.get("GÉNEROS", ""),
        "fecha": campos.get("FECHA DE LANZAMIENTO", ""),
        "url": campos.get("URL", ""),
    }
    if campos.get("PORTADA"):
        meta["portada"] = campos["PORTADA"]
    nota = _a_numero(campos.get("NOTA METACRITIC"))
    if nota is not None:
        meta["nota_metacritic"] = nota
    return meta
