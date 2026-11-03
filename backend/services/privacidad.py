"""
Privacidad por diseño (Ley 19.628 y Ley 21.719 de Protección de Datos Personales de Chile).

Antes de enviar cualquier texto a Gemini (un proveedor externo) se ENMASCARAN los
datos personales (PII) y se reemplazan por etiquetas genéricas:

    "me llamo Constanza Navarro, mi rut es 12.345.678-5"
        -> "me llamo [PERSONA_1], mi rut es [RUT_1]"

Qué se detecta:
  - RUT chileno, correos, teléfonos, tarjetas de crédito, direcciones IP  (expresiones regulares)
  - nombres de personas                                                    (NER de spaCy, como en el
                                                                            laboratorio de NLP)
  - el nombre con que la persona se registró en Kira

Para no romper las preguntas sobre juegos, un nombre que aparece en la base de
conocimiento (Mario, Kratos, Geralt, Max Payne...) NO se enmascara: es un personaje
público, no un dato personal.

El enmascaramiento es reversible SOLO dentro de Kira: la tabla de reemplazos vive en
memoria durante la petición, y al recibir la respuesta se restauran los valores
originales para mostrárselos a su dueño. Gemini nunca ve los datos reales.
"""

import re
import unicodedata

from backend.config import CARPETA_DOCS, ENMASCARAR_PII, MODELO_SPACY

# ---------------------------------------------------------------------------
# Patrones (el orden importa: primero los más específicos)
# ---------------------------------------------------------------------------
PATRONES = [
    ("CORREO", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("RUT", re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")),
    ("TARJETA", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    # +56 9 1234 5678, 912345678, (2) 2345 6789 ...
    ("TELEFONO", re.compile(r"(?<![\w.])(?:\+?56[ -]?)?(?:\(?\d{1,2}\)?[ -]?)?\d{4}[ -]?\d{4}\b")),
]

# Frases con las que alguien se presenta: lo que viene después siempre es un nombre
_RE_PRESENTACION = re.compile(
    r"\b(?:me llamo|mi nombre es|mi nombre:|soy|my name is|i am|i'm)\s+"
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})"
)


def _sin_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# Recursos que se cargan una sola vez
# ---------------------------------------------------------------------------
_nlp = None
_nlp_cargado = False
_corpus = None


def _modelo_ner():
    """spaCy es opcional: si no está instalado, Kira sigue funcionando solo con regex."""
    global _nlp, _nlp_cargado
    if not _nlp_cargado:
        _nlp_cargado = True
        try:
            import spacy
            _nlp = spacy.load(MODELO_SPACY, disable=["parser", "lemmatizer"])
            print(f"✓ Detector de nombres (spaCy {MODELO_SPACY}) cargado")
        except Exception as e:
            print(f"✗ spaCy no disponible ({e.__class__.__name__}): la privacidad usa solo expresiones regulares.")
            print(f"  Para activarlo:  python -m spacy download {MODELO_SPACY}")
    return _nlp


def _texto_corpus() -> str:
    """Todo el corpus en minúsculas y sin tildes, para saber si un nombre es público."""
    global _corpus
    if _corpus is None:
        partes = []
        try:
            for archivo in CARPETA_DOCS.glob("*.txt"):
                partes.append(archivo.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass
        _corpus = " " + re.sub(r"\s+", " ", _sin_tildes(" ".join(partes))) + " "
    return _corpus


def es_nombre_publico(nombre: str) -> bool:
    """True si el nombre aparece en la base de juegos (personaje, estudio, título)."""
    clave = re.sub(r"\s+", " ", _sin_tildes(nombre)).strip()
    if len(clave) < 3:
        return True                    # "Al", "Yo": demasiado corto para ser un dato personal
    return f" {clave} " in _texto_corpus() or f" {clave}," in _texto_corpus()


_RE_ETIQUETA = re.compile(r"[A-Z]+_\d+|USUARIO")


def nombres_detectados(doc) -> list[str]:
    """
    Nombres de personas que hay que ocultar, a partir de las entidades de spaCy.

    El NER del modelo pequeño a veces se equivoca, así que de cada entidad PER solo
    se toman las palabras que son nombres propios (PROPN) y que no son personajes
    públicos de la base de juegos:
        "Zelda con Fernanda Valenzuela"  ->  "Fernanda Valenzuela"
    También se ignoran las etiquetas que ya se pusieron ([CORREO_1], [USUARIO]...).
    """
    nombres = []
    for ent in doc.ents:
        if ent.label_ not in ("PER", "PERSON"):
            continue
        tramo = []
        for token in list(ent) + [None]:          # None cierra el último tramo
            es_nombre = (
                token is not None
                and not _RE_ETIQUETA.search(token.text)
                and token.text not in "[]"
                and (token.pos_ == "PROPN" if token.pos_ else token.text[:1].isupper())
            )
            if es_nombre:
                tramo.append(token.text)
                continue
            if tramo:
                candidato = " ".join(tramo)
                if not es_nombre_publico(candidato):
                    nombres.append(candidato)
                tramo = []
    # primero los más largos: "Fernanda Valenzuela" antes que "Fernanda"
    return sorted(set(nombres), key=len, reverse=True)


# ---------------------------------------------------------------------------
# Enmascarador
# ---------------------------------------------------------------------------
class Enmascarador:
    """
    Un enmascarador por petición. Guarda la tabla etiqueta -> valor original para
    poder restaurar la respuesta. Un mismo valor siempre recibe la misma etiqueta.
    """

    def __init__(self, nombre_usuario: str = "", activo: bool = ENMASCARAR_PII):
        self.activo = activo
        self.tabla: dict[str, str] = {}          # "[RUT_1]" -> "12.345.678-5"
        self._inversa: dict[str, str] = {}       # valor -> etiqueta
        self._contador: dict[str, int] = {}
        self.nombre_usuario = (nombre_usuario or "").strip()
        if self.activo and self.nombre_usuario:
            self.tabla["[USUARIO]"] = self.nombre_usuario
            self._inversa[self.nombre_usuario.lower()] = "[USUARIO]"

    # ------------------------------------------------------------------
    def _etiqueta(self, tipo: str, valor: str) -> str:
        clave = valor.strip().lower()
        if clave in self._inversa:
            return self._inversa[clave]
        self._contador[tipo] = self._contador.get(tipo, 0) + 1
        etiqueta = f"[{tipo}_{self._contador[tipo]}]"
        self.tabla[etiqueta] = valor.strip()
        self._inversa[clave] = etiqueta
        return etiqueta

    def _reemplazar_nombre(self, texto: str, nombre: str, etiqueta: str | None = None) -> str:
        etiqueta = etiqueta or self._etiqueta("PERSONA", nombre)
        return re.sub(rf"(?<!\w){re.escape(nombre)}(?!\w)", etiqueta, texto, flags=re.IGNORECASE)

    # ------------------------------------------------------------------
    def enmascarar(self, texto: str) -> str:
        if not self.activo or not texto:
            return texto

        # 1. Datos con formato fijo (regex)
        for tipo, patron in PATRONES:
            texto = patron.sub(lambda m, t=tipo: self._etiqueta(t, m.group(0)), texto)

        # 2. El nombre con que se registró (salvo que sea también un juego o personaje)
        if self.nombre_usuario and not es_nombre_publico(self.nombre_usuario):
            texto = self._reemplazar_nombre(texto, self.nombre_usuario, "[USUARIO]")

        # 3. "me llamo X", "soy X": siempre es un nombre propio
        for m in list(_RE_PRESENTACION.finditer(texto)):
            nombre = m.group(1)
            if "[" not in nombre:
                texto = self._reemplazar_nombre(texto, nombre)

        # 4. Otros nombres de personas (NER), si no son personajes públicos
        nlp = _modelo_ner()
        if nlp is not None:
            for nombre in nombres_detectados(nlp(texto)):
                texto = self._reemplazar_nombre(texto, nombre)
        return texto

    def restaurar(self, texto: str) -> str:
        """Devuelve los valores originales en la respuesta (solo la ve su dueño)."""
        if not self.activo or not texto:
            return texto
        for etiqueta, valor in sorted(self.tabla.items(), key=lambda kv: -len(kv[0])):
            texto = texto.replace(etiqueta, valor)
        return texto

    @property
    def cantidad(self) -> int:
        """Cuántos datos personales distintos se ocultaron (sin contar el nombre registrado)."""
        return len([e for e in self.tabla if e != "[USUARIO]"])


# ---------------------------------------------------------------------------
# Minimización: el LLM no necesita la fecha de nacimiento, solo el tramo de edad
# ---------------------------------------------------------------------------
def tramo_de_edad(edad: int | None) -> str | None:
    if edad is None:
        return None
    if edad < 13:
        return "menor de 13 años"
    if edad < 18:
        return "entre 13 y 17 años"
    return "18 años o más"
