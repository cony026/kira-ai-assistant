"""
Re-ranking híbrido y compactación del contexto (fase 3 del pipeline RAG).

La búsqueda por vectores a veces trae fragmentos que "suenan parecido" pero no
responden lo que se preguntó. Por eso la recuperación se hace en dos etapas:

  1. ChromaDB trae TOP_K_CANDIDATOS fragmentos por similitud coseno (semántica).
  2. Aquí se reordenan combinando dos puntajes y solo pasan los TOP_K mejores:

        puntaje = PESO_SEMANTICO * semantico  +  (1 - PESO_SEMANTICO) * BM25

     semantico = 1 - distancia / UMBRAL  (1 = idéntico, 0 = en el límite del umbral)

     BM25 es la búsqueda léxica clásica (la de los buscadores): premia los fragmentos
     que contienen las palabras exactas de la pregunta ("requisitos", "mínimos",
     "multijugador"). Para calcularlo se usan las técnicas del laboratorio de NLP:
     minúsculas, tokenización, eliminación de stopwords y stemming (raíz de la palabra,
     así "requisito" y "requisitos" cuentan como la misma).

Después, compactar_contexto() quita fragmentos repetidos (el solapamiento del chunking
hace que dos fragmentos seguidos compartan oraciones) y corta el total a
MAX_CARACTERES_CONTEXTO. Menos texto al LLM = menos tokens de entrada = menos costo.
"""

import math
import re
import unicodedata
from collections import Counter

from backend.config import MAX_CARACTERES_CONTEXTO, PESO_SEMANTICO, TOP_K, UMBRAL_DISTANCIA_MAXIMA

# Stopwords español + inglés (el corpus mezcla ambos). Lista propia para no depender
# de descargar los recursos de nltk en el servidor.
STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales cuando
de del desde donde durante e el ella ellas ellos en entre era eran es esa esas ese eso esos esta
estas este esto estos fue fueron ha han hay la las le les lo los mas me mi mis mucho muy nada ni
no nos o otra otro para pero poco por porque que quien se ser si sin sobre su sus tambien tan te
tiene tienen todo todos tu tus un una unas uno unos y ya yo cual cuanto cuanta dame dime quiero
puedes sabes saber hablame cuentame necesito juego juegos son soy eres esta estan estoy
cuales cuantos cuantas hola gracias favor algun recomiendame recomienda
the and or of to in on for with is are was were be been it its this that these those as at by
an from about what which who how can i you me my your do does did game games
""".split())

_stemmer = None


def _raiz(palabra: str) -> str:
    global _stemmer
    if _stemmer is None:
        try:
            from nltk.stem import SnowballStemmer
            _stemmer = SnowballStemmer("spanish").stem
        except Exception:                       # sin nltk: raíz aproximada
            _stemmer = lambda p: re.sub(r"(es|s)$", "", p) if len(p) > 4 else p
    return _stemmer(palabra)


def terminos(texto: str) -> list[str]:
    """Limpieza NLP: minúsculas, sin tildes, tokens, sin stopwords, raíces."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    tokens = re.findall(r"[a-z0-9ñ]+", texto)
    return [_raiz(t) for t in tokens if t not in STOPWORDS and len(t) > 1]


def bm25(consulta: list[str], documentos: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Puntaje BM25 de cada documento (ya tokenizado) para la consulta."""
    n = len(documentos)
    if n == 0 or not consulta:
        return [0.0] * n
    largo_medio = sum(len(d) for d in documentos) / n or 1
    df = Counter(t for d in documentos for t in set(d))
    puntajes = []
    for doc in documentos:
        tf = Counter(doc)
        total = 0.0
        for t in set(consulta):
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            total += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(doc) / largo_medio))
        puntajes.append(total)
    return puntajes


def _normalizar_0_1(valores: list[float]) -> list[float]:
    if not valores:
        return []
    bajo, alto = min(valores), max(valores)
    if alto - bajo < 1e-9:
        return [1.0 if alto > 0 else 0.0 for _ in valores]
    return [(v - bajo) / (alto - bajo) for v in valores]


def reordenar(pregunta: str, candidatos: list[dict], top_k: int = TOP_K,
              peso_semantico: float = PESO_SEMANTICO) -> list[dict]:
    """
    candidatos: [{id, documento, metadatos, distancia, del_juego}] (distancia coseno).
    Devuelve los top_k mejores con su "puntaje" agregado.
    del_juego=True (fragmento del juego que la persona nombró) recibe un bono, porque
    ese filtro por metadato es la señal más confiable que tenemos.
    """
    if not candidatos:
        return []
    # Semántico: se mide respecto del umbral (no min-max) para no exagerar diferencias
    # pequeñas de distancia entre candidatos que son casi igual de parecidos.
    sem = [max(0.0, min(1.0, 1 - (c["distancia"] if c.get("distancia") is not None else 1)
                        / UMBRAL_DISTANCIA_MAXIMA)) for c in candidatos]
    lex = _normalizar_0_1(bm25(terminos(pregunta), [terminos(c["documento"]) for c in candidatos]))
    for c, s, l in zip(candidatos, sem, lex):
        c["puntaje"] = round(peso_semantico * s + (1 - peso_semantico) * l + (0.25 if c.get("del_juego") else 0), 4)
    return sorted(candidatos, key=lambda c: c["puntaje"], reverse=True)[:top_k]


def _oraciones(texto: str) -> set[str]:
    return {o.strip().lower() for o in re.split(r"(?<=[.!?])\s+|\n", texto) if len(o.strip()) > 25}


def compactar_contexto(fragmentos: list[dict], max_caracteres: int = MAX_CARACTERES_CONTEXTO) -> list[dict]:
    """
    Quita fragmentos casi repetidos (>60 % de sus oraciones ya están en otro elegido)
    y se detiene antes de pasar el tope de caracteres. Mantiene el orden del re-ranking.
    """
    elegidos, vistas, total = [], set(), 0
    for f in fragmentos:
        oraciones = _oraciones(f["documento"])
        if oraciones and len(oraciones & vistas) / len(oraciones) > 0.6:
            continue
        largo = len(f["documento"])
        if elegidos and total + largo > max_caracteres:
            continue
        elegidos.append(f)
        vistas |= oraciones
        total += largo
    return elegidos
