"""Ley de Protección de Datos: enmascaramiento de PII antes de enviar a Gemini."""

import pytest

from backend.services import privacidad
from backend.services.privacidad import Enmascarador, tramo_de_edad


@pytest.fixture(autouse=True)
def corpus_de_prueba(monkeypatch):
    # En vez de leer los 9.000 documentos, un corpus pequeño con personajes públicos
    monkeypatch.setattr(privacidad, "_corpus", " mario kratos geralt de rivia max payne link zelda ")


def test_rut_correo_telefono_y_tarjeta_se_enmascaran():
    e = Enmascarador()
    texto = ("mi rut es 12.345.678-5, mi correo cony@gmail.com, "
             "mi fono +56 9 8765 4321 y mi tarjeta 4111 1111 1111 1111")
    oculto = e.enmascarar(texto)
    for dato in ("12.345.678-5", "cony@gmail.com", "8765 4321", "4111 1111 1111 1111"):
        assert dato not in oculto
    for etiqueta in ("[RUT_1]", "[CORREO_1]", "[TELEFONO_1]", "[TARJETA_1]"):
        assert etiqueta in oculto


def test_el_nombre_registrado_se_reemplaza_y_se_restaura():
    e = Enmascarador(nombre_usuario="Constanza")
    oculto = e.enmascarar("Hola, soy constanza y quiero un juego de terror")
    assert "onstanza" not in oculto and "[USUARIO]" in oculto
    assert e.restaurar("¡Claro, [USUARIO]! Te recomiendo Outlast.") == "¡Claro, Constanza! Te recomiendo Outlast."


def test_presentacion_me_llamo_se_enmascara():
    e = Enmascarador()
    oculto = e.enmascarar("me llamo Javiera Rojas y tengo una PS5")
    assert "Javiera" not in oculto and "[PERSONA_1]" in oculto
    assert e.restaurar(oculto) == "me llamo Javiera Rojas y tengo una PS5"


def test_personajes_de_juegos_no_se_enmascaran():
    e = Enmascarador(nombre_usuario="Link")         # nombre que también es un personaje
    texto = "juegos parecidos a Max Payne o con Kratos y Link"
    assert e.enmascarar(texto) == texto


def test_mismo_dato_misma_etiqueta():
    e = Enmascarador()
    oculto = e.enmascarar("escríbeme a a@b.cl o a a@b.cl")
    assert oculto.count("[CORREO_1]") == 2 and "[CORREO_2]" not in oculto


def test_se_puede_desactivar():
    e = Enmascarador(nombre_usuario="Cony", activo=False)
    assert e.enmascarar("mi rut es 12.345.678-5") == "mi rut es 12.345.678-5"


def test_la_edad_exacta_no_se_envia():
    assert tramo_de_edad(None) is None
    assert tramo_de_edad(10) == "menor de 13 años"
    assert tramo_de_edad(15) == "entre 13 y 17 años"
    assert tramo_de_edad(22) == "18 años o más"


def test_el_prompt_a_gemini_no_lleva_datos_personales():
    """Lo que realmente sale hacia el LLM (sin llamarlo)."""
    from backend.agent.state import EstadoAgente
    from backend.agent.nodes.generate import armar_contenidos

    perfil = {"nombre": "Constanza", "email": "cony@gmail.com", "edad": 21,
              "fecha_nacimiento": "2004-05-02", "consolas": ["PC"], "generos": ["RPG"]}
    estado = EstadoAgente(
        mensaje="soy Constanza, mi rut es 12.345.678-5, ¿qué rpg me recomiendas?",
        perfil=perfil,
        historial=[{"mensaje": "mi correo es cony@gmail.com", "respuesta": "Anotado."}],
        contexto_rag="[rawg_elden-ring] Juego: Elden Ring",
    )
    e = Enmascarador(nombre_usuario="Constanza")
    enviado = "\n".join(texto for _, texto in armar_contenidos(estado, e))
    for dato in ("Constanza", "12.345.678-5", "cony@gmail.com", "2004-05-02", "21 años"):
        assert dato not in enviado, f"se filtró: {dato}"
    assert "[USUARIO]" in enviado and "18 años o más" in enviado and "Elden Ring" in enviado


def test_ner_con_spacy_si_esta_instalado():
    if privacidad._modelo_ner() is None:
        pytest.skip("modelo de spaCy no instalado (python -m spacy download es_core_news_sm)")
    e = Enmascarador()
    oculto = e.enmascarar("Ayer jugué Zelda con Fernanda Valenzuela en su casa")
    assert "Fernanda" not in oculto and "Zelda" in oculto


# ---------------------------------------------------------------- NER (simulado, sin descargar spaCy)
class _Tok:
    def __init__(self, text, pos):
        self.text, self.pos_ = text, pos


class _Ent(list):
    def __init__(self, tokens, label="PER"):
        super().__init__(tokens)
        self.label_ = label
        self.text = " ".join(t.text for t in tokens)


class _Doc:
    def __init__(self, ents):
        self.ents = ents


def test_ner_no_rompe_las_etiquetas_ya_puestas():
    """spaCy a veces marca «CORREO_1» como persona: no debe volver a enmascararse."""
    doc = _Doc([_Ent([_Tok("CORREO_1", "PROPN")]), _Ent([_Tok("TARJETA_1", "PROPN")])])
    assert privacidad.nombres_detectados(doc) == []


def test_ner_toma_solo_los_nombres_propios_no_publicos():
    doc = _Doc([_Ent([_Tok("Zelda", "PROPN"), _Tok("con", "ADP"),
                      _Tok("Fernanda", "PROPN"), _Tok("Valenzuela", "PROPN")]),
                _Ent([_Tok("Ayer", "ADV")])])
    assert privacidad.nombres_detectados(doc) == ["Fernanda Valenzuela"]


def test_enmascarar_con_ner_simulado(monkeypatch):
    def nlp_falso(texto):
        ents = []
        if "CORREO_1" in texto:
            ents.append(_Ent([_Tok("CORREO_1", "PROPN")]))
        if "Fernanda" in texto:
            ents.append(_Ent([_Tok("Zelda", "PROPN"), _Tok("con", "ADP"),
                              _Tok("Fernanda", "PROPN"), _Tok("Valenzuela", "PROPN")]))
        return _Doc(ents)
    monkeypatch.setattr(privacidad, "_modelo_ner", lambda: nlp_falso)
    e = Enmascarador()
    oculto = e.enmascarar("jugué Zelda con Fernanda Valenzuela, su correo es f@v.cl")
    assert oculto == "jugué Zelda con [PERSONA_1], su correo es [CORREO_1]"
    assert e.restaurar(oculto) == "jugué Zelda con Fernanda Valenzuela, su correo es f@v.cl"
