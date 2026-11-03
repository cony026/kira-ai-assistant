"""
Análisis NLP del corpus de Kira (las técnicas del laboratorio NLP aplicadas a los
documentos del RAG):

  1. Limpieza con re (la misma de limpieza.py)
  2. Minúsculas
  3. Tokenización (nltk.word_tokenize)
  4. Eliminación de stopwords (español + inglés: el corpus mezcla ambos idiomas)
  5. Frecuencia de palabras (collections.Counter)
  6. Stemming: raíz de cada palabra (SnowballStemmer)

Sirve para conocer y justificar la base de conocimiento (qué palabras dominan,
cuánto ruido se quitó). Estos pasos NO se aplican al texto que se vectoriza:
el modelo de embeddings necesita las frases completas (ver limpieza.py).

Uso (desde la carpeta raíz kira/):
    python -m backend.vectorDb.analisis_nlp
"""

import re
import unicodedata
from collections import Counter

from backend.config import CARPETA_DOCS
from backend.vectorDb.limpieza import limpiar_documento


def preparar_nltk():
    import nltk
    for recurso, ruta in (("punkt", "tokenizers/punkt"), ("punkt_tab", "tokenizers/punkt_tab"),
                          ("stopwords", "corpora/stopwords")):
        try:
            nltk.data.find(ruta)
        except LookupError:
            nltk.download(recurso, quiet=True)


def sin_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def main():
    preparar_nltk()
    from nltk.corpus import stopwords
    from nltk.stem import SnowballStemmer
    from nltk.tokenize import word_tokenize

    stop_es = {sin_tildes(p) for p in stopwords.words("spanish")}
    stop_en = set(stopwords.words("english"))
    stop_words = stop_es | stop_en
    stem_es, stem_en = SnowballStemmer("spanish"), SnowballStemmer("english")

    crudo_total = limpio_total = 0
    tokens_total = 0
    frecuencia = Counter()
    raices = Counter()
    idiomas = Counter()

    archivos = sorted(CARPETA_DOCS.glob("*.txt"))
    for archivo in archivos:
        crudo = archivo.read_text(encoding="utf-8")
        _, secciones = limpiar_documento(crudo)                       # 1. limpieza (re)
        texto = " ".join(contenido for _, contenido in secciones)
        crudo_total += len(crudo)
        limpio_total += len(texto)

        texto = sin_tildes(texto.lower())                              # 2. minúsculas
        texto = re.sub(r"[^a-z0-9ñ\s]", " ", texto)                    #    sin puntuación
        tokens = word_tokenize(texto)                                  # 3. tokenización
        tokens_total += len(tokens)

        # idioma del documento: el que tenga más stopwords
        es = sum(t in stop_es for t in tokens)
        en = sum(t in stop_en for t in tokens)
        idioma = "español" if es >= en else "inglés"
        idiomas[idioma] += 1
        stemmer = stem_es if idioma == "español" else stem_en

        palabras = [t for t in tokens if t not in stop_words and len(t) > 2 and not t.isdigit()]  # 4.
        frecuencia.update(palabras)                                    # 5. frecuencia
        raices.update(stemmer.stem(p) for p in palabras)               # 6. stemming

    print("=" * 60)
    print("ANÁLISIS NLP DE LA BASE DE CONOCIMIENTO DE KIRA")
    print("=" * 60)
    print(f"Documentos:               {len(archivos)}  ({idiomas['español']} en español, {idiomas['inglés']} en inglés)")
    print(f"Caracteres crudos:        {crudo_total:,}")
    print(f"Caracteres tras limpieza: {limpio_total:,}  (textos largos, sin la ficha)")
    print(f"Tokens:                   {tokens_total:,}")
    print(f"Tokens sin stopwords:     {sum(frecuencia.values()):,}")
    print(f"Vocabulario:              {len(frecuencia):,} palabras distintas -> {len(raices):,} raíces (stemming)")

    print("\n20 palabras más frecuentes (sin stopwords):")
    for palabra, n in frecuencia.most_common(20):
        print(f"  {palabra:<18}{n:>7}")

    print("\nEjemplos de stemming (palabra -> raíz):")
    for palabra, _ in frecuencia.most_common(60)[::6]:
        print(f"  {palabra:<18}-> {stem_en.stem(palabra) if palabra.isascii() else stem_es.stem(palabra)}")


if __name__ == "__main__":
    main()
