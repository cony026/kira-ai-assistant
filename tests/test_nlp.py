"""Técnicas del laboratorio NLP aplicadas al corpus (red_entidades.py)."""

from backend.vectorDb.red_entidades import idioma_de, normalizar_entidades


def test_normaliza_variantes_como_sancho_panza():
    entidades = ["Geralt", "Geralt of Rivia", "Ciri", "Geralt"]
    assert normalizar_entidades(entidades) == ["Geralt of Rivia", "Geralt of Rivia", "Ciri", "Geralt of Rivia"]


def test_detecta_el_idioma_del_documento():
    assert idioma_de("El juego de la temporada que todos los fans esperaban con una historia") == "es"
    assert idioma_de("The game of the year that you and your friends will love to play in the dark") == "en"
