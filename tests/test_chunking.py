"""Ingesta y chunking: los fragmentos respetan el tamaño y el solapamiento configurados."""

from backend.config import TAM_CHUNK, SOLAPE
from backend.vectorDb.ingest import trocear, fragmentar_documento

ORACION = "Hollow Knight es un metroidvania exigente con un mundo enorme para explorar. "


def test_texto_corto_queda_en_un_fragmento():
    assert trocear("Un texto corto.") == ["Un texto corto."]


def test_texto_vacio_no_genera_fragmentos():
    assert trocear("   ") == []


def test_ningun_fragmento_supera_el_tamano():
    texto = ORACION * 60
    fragmentos = trocear(texto, TAM_CHUNK, SOLAPE)
    assert len(fragmentos) > 1
    assert all(len(f) <= TAM_CHUNK for f in fragmentos)


def test_hay_solapamiento_entre_fragmentos_seguidos():
    texto = " ".join(f"Oración número {i} del documento de prueba." for i in range(120))
    fragmentos = trocear(texto, 400, 100)
    for anterior, siguiente in zip(fragmentos, fragmentos[1:]):
        ultima = anterior.split(". ")[-1].rstrip(".")
        assert ultima in siguiente, "la última oración debe repetirse al inicio del siguiente"


def test_no_corta_palabras_a_la_mitad():
    texto = ("palabra " * 400).strip()            # una "oración" gigante sin puntos
    for f in trocear(texto, 300, 50):
        assert all(p == "palabra" for p in f.split())


def test_cada_fragmento_lleva_la_cabecera_del_juego():
    campos = {"JUEGO": "Hollow Knight", "PLATAFORMA": "PC"}
    secciones = [("DESCRIPCIÓN", ORACION * 40)]
    fragmentos = fragmentar_documento(campos, secciones)
    assert fragmentos[0].startswith("JUEGO: Hollow Knight")         # ficha
    assert all(f.startswith("Juego: Hollow Knight") for f in fragmentos[1:])
    assert all(len(f) <= TAM_CHUNK + 80 for f in fragmentos[1:])
