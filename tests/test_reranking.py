"""Re-ranking híbrido (vectores + BM25) y compactación del contexto."""

from backend.agent.reranking import bm25, compactar_contexto, reordenar, terminos


def _c(id_, doc, dist, del_juego=False):
    return {"id": id_, "documento": doc, "metadatos": {"fuente": id_}, "distancia": dist, "del_juego": del_juego}


def test_terminos_aplica_limpieza_nlp():
    t = terminos("¿Cuáles son los Requisitos mínimos de Elden Ring?")
    assert "los" not in t and "son" not in t                     # stopwords fuera
    assert terminos("requisito") == terminos("requisitos")       # stemming


def test_bm25_premia_las_palabras_exactas():
    docs = [terminos("historia del juego y sus personajes"),
            terminos("requisitos mínimos: procesador i5, 8 GB de RAM, GTX 1060")]
    p = bm25(terminos("requisitos mínimos RAM"), docs)
    assert p[1] > p[0]


def test_el_reranking_sube_el_fragmento_que_responde():
    candidatos = [
        _c("a", "Elden Ring es un mundo abierto oscuro con una historia profunda.", 0.12),
        _c("b", "Juego: Elden Ring. REQUISITOS MÍNIMOS: Intel Core i5, 12 GB de RAM, GTX 1060.", 0.18),
        _c("c", "Dark Souls III comparte el estilo de combate exigente.", 0.15),
    ]
    mejores = reordenar("requisitos mínimos de Elden Ring", candidatos, top_k=2)
    assert mejores[0]["id"] == "b"
    assert len(mejores) == 2


def test_fragmentos_del_juego_nombrado_tienen_prioridad():
    candidatos = [_c("otro", "Un juego de terror muy parecido.", 0.10),
                  _c("juego", "Outlast es un juego de terror.", 0.20, del_juego=True)]
    assert reordenar("háblame de Outlast terror", candidatos, top_k=1)[0]["id"] == "juego"


def test_compactar_quita_repetidos_y_respeta_el_tope():
    base = "Esta es una oración suficientemente larga para contar. " * 5
    frags = [_c("1", base, 0.1), _c("2", base, 0.1), _c("3", "x" * 3000, 0.2), _c("4", "y" * 3000, 0.3)]
    for f in frags:
        f["puntaje"] = 1
    elegidos = compactar_contexto(frags, max_caracteres=4000)
    ids = [f["id"] for f in elegidos]
    assert "2" not in ids                                         # repetido
    assert sum(len(f["documento"]) for f in elegidos) <= 4000


def test_recuperacion_en_dos_etapas_con_base_simulada(monkeypatch):
    """Candidatos del juego + semánticos -> umbral -> re-ranking -> máximo TOP_K al LLM."""
    from backend.agent.nodes import retrieve
    from backend.config import TOP_K

    class ColeccionFalsa:
        def query(self, query_embeddings, n_results, where=None, include=None):
            if where:   # fragmentos filtrados por el juego nombrado
                filas = [("er_1", "Juego: Elden Ring. REQUISITOS MÍNIMOS: 12 GB de RAM.", {"fuente": "steam", "juego_clave": "elden ring"}, 0.20)]
            else:
                filas = [(f"otro_{i}", f"Otro juego de rol número {i}.", {"fuente": "rawg", "juego_clave": f"otro {i}"}, 0.10 + i / 100)
                         for i in range(12)]
                filas.append(("lejano", "Receta de cocina.", {"fuente": "x", "juego_clave": "x"}, 0.95))
            ids, docs, metas, dists = zip(*filas)
            return {"ids": [list(ids)], "documents": [list(docs)], "metadatas": [list(metas)], "distances": [list(dists)]}

    monkeypatch.setattr(retrieve, "obtener_coleccion", lambda: ColeccionFalsa())
    monkeypatch.setattr(retrieve, "obtener_modelo_embeddings", lambda: object())
    monkeypatch.setattr(retrieve, "vectorizar_consulta", lambda modelo, texto: [0.0])

    frags = retrieve.recuperar_fragmentos("requisitos de elden ring", juegos=[{"nombre": "Elden Ring"}])
    ids = [f["id"] for f in frags]
    assert len(frags) <= TOP_K
    assert ids[0] == "er_1"                 # el del juego nombrado queda primero
    assert "lejano" not in ids              # descartado por el umbral de distancia
