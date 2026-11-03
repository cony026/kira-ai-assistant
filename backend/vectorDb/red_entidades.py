"""
Red de entidades del corpus de Kira (NER + grafo de enlaces, como en el laboratorio NLP-2).

En el laboratorio se detectaron los personajes del Quijote con spaCy (entidades PER) y
se armó una red con networkx: cada personaje es un nodo y dos personajes quedan
UNIDOS POR UN ENLACE cuando aparecen en el mismo párrafo (co-ocurrencia). El peso del
enlace es cuántas veces aparecen juntos.

Aquí se hace lo mismo con las descripciones y reseñas de los juegos:
  1. Limpieza (limpieza.py) y detección del idioma de cada documento
  2. NER con spaCy: personajes y personas (PER/PERSON) y estudios u organizaciones (ORG)
  3. Normalización: si en un documento aparece "Geralt of Rivia" y luego "Geralt",
     ambos se cuentan como "Geralt of Rivia" (igual que sancho -> sancho panza)
  4. Grafo: enlaces entre entidades que aparecen en el mismo documento
  5. Resultados: entidades más frecuentes, enlaces más fuertes, imagen PNG y archivo
     GEXF (se abre con Gephi)

Sirve para conocer la base de conocimiento: qué personajes y estudios dominan y qué
juegos quedan conectados entre sí (sagas, estudios compartidos).

Requisitos:  pip install spacy networkx matplotlib
             python -m spacy download es_core_news_sm
             python -m spacy download en_core_web_sm     (el 95 % del corpus está en inglés)
Uso (desde la carpeta raíz kira/):
    python -m backend.vectorDb.red_entidades              # 1.500 documentos
    python -m backend.vectorDb.red_entidades --max 0      # todos (tarda varios minutos)
"""

import argparse
import itertools
import re
from collections import Counter

from backend.config import CARPETA_DATA, CARPETA_DOCS
from backend.vectorDb.limpieza import limpiar_documento

CARPETA_SALIDA = CARPETA_DATA / "evaluacion"
ETIQUETAS = {"PER": "persona", "PERSON": "persona", "ORG": "organización"}
# Falsos positivos típicos del NER en fichas de juegos
IGNORAR = {"steam", "pc", "xbox", "playstation", "nintendo switch", "dlc", "rpg", "fps", "mac", "linux",
           "windows", "directx", "nvidia", "amd", "intel", "ram", "gb", "hd", "ai", "ui", "co-op", "mmo"}
STOP_EN = {"the", "and", "of", "to", "a", "in", "is", "you", "that", "it", "for", "with", "as", "on", "your"}
STOP_ES = {"de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por", "con", "una"}


def cargar_modelos():
    import spacy
    modelos = {}
    for idioma, nombre in (("es", "es_core_news_sm"), ("en", "en_core_web_sm")):
        try:
            modelos[idioma] = spacy.load(nombre, disable=["parser", "lemmatizer", "tagger"])
        except OSError:
            print(f"  (falta el modelo {nombre}: python -m spacy download {nombre})")
    if not modelos:
        raise SystemExit("No hay modelos de spaCy instalados.")
    return modelos


def idioma_de(texto: str) -> str:
    palabras = re.findall(r"[a-záéíóúñ]+", texto.lower())[:400]
    return "es" if sum(p in STOP_ES for p in palabras) >= sum(p in STOP_EN for p in palabras) else "en"


def normalizar_entidades(entidades: list[str]) -> list[str]:
    """Une variantes dentro de un mismo documento: "Geralt" -> "Geralt of Rivia"."""
    largas = sorted(set(entidades), key=len, reverse=True)
    mapa = {}
    for e in largas:
        destino = next((l for l in largas if l != e and len(l) > len(e)
                        and re.search(rf"\b{re.escape(e)}\b", l)), e)
        mapa[e] = mapa.get(destino, destino)
    return [mapa[e] for e in entidades]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=1500, help="documentos a procesar (0 = todos)")
    parser.add_argument("--min-peso", type=int, default=2, help="enlaces con menos co-ocurrencias se descartan")
    args = parser.parse_args()

    import networkx as nx
    modelos = cargar_modelos()
    archivos = sorted(CARPETA_DOCS.glob("*.txt"))
    if args.max:
        archivos = archivos[:args.max]

    frecuencia, tipo, juegos_de = Counter(), {}, {}
    G = nx.Graph()
    for i, archivo in enumerate(archivos, 1):
        campos, secciones = limpiar_documento(archivo.read_text(encoding="utf-8"))
        texto = " ".join(c for _, c in secciones)[:6000]
        if not texto:
            continue
        idioma = idioma_de(texto)
        nlp = modelos.get(idioma) or next(iter(modelos.values()))
        encontradas = []
        for ent in nlp(texto).ents:
            nombre = re.sub(r"\s+", " ", ent.text).strip(" .,:;'\"")
            if ent.label_ in ETIQUETAS and len(nombre) > 2 and nombre.lower() not in IGNORAR:
                encontradas.append(nombre)
                tipo.setdefault(nombre, ETIQUETAS[ent.label_])
        presentes = set(normalizar_entidades(encontradas))
        juego = campos.get("JUEGO", archivo.stem)
        for e in presentes:
            frecuencia[e] += 1
            juegos_de.setdefault(e, set()).add(juego)
        for a, b in itertools.combinations(sorted(presentes), 2):        # enlaces por co-ocurrencia
            peso = G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1
            G.add_edge(a, b, weight=peso)
        if i % 250 == 0:
            print(f"  [{i}/{len(archivos)}] documentos procesados")

    # Quitar enlaces débiles y nodos aislados para que la red se pueda leer
    G.remove_edges_from([(a, b) for a, b, d in G.edges(data=True) if d["weight"] < args.min_peso])
    G.remove_nodes_from(list(nx.isolates(G)))
    for n in G.nodes:
        G.nodes[n]["frecuencia"] = frecuencia[n]
        G.nodes[n]["tipo"] = tipo.get(n, "")
        G.nodes[n]["juegos"] = len(juegos_de.get(n, ()))

    print("\n" + "=" * 60)
    print("RED DE ENTIDADES DEL CORPUS DE KIRA")
    print("=" * 60)
    print(f"Documentos: {len(archivos)}   Entidades distintas: {len(frecuencia)}   "
          f"En la red: {G.number_of_nodes()} nodos, {G.number_of_edges()} enlaces")
    print("\n15 entidades más frecuentes (documentos en que aparecen):")
    for e, n in frecuencia.most_common(15):
        print(f"  {e:<32}{n:>5}   ({tipo.get(e, '')})")
    print("\n15 enlaces más fuertes (aparecen juntas):")
    for a, b, d in sorted(G.edges(data=True), key=lambda x: -x[2]["weight"])[:15]:
        print(f"  {a} ↔ {b}: {d['weight']}")
    if G.number_of_nodes():
        centrales = sorted(nx.degree_centrality(G).items(), key=lambda x: -x[1])[:10]
        print("\nEntidades más conectadas (centralidad de grado):")
        for e, c in centrales:
            print(f"  {e:<32}{c:.3f}")

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    nx.write_gexf(G, CARPETA_SALIDA / "red_entidades.gexf")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        principales = [n for n, _ in sorted(G.degree, key=lambda x: -x[1])[:60]]
        H = G.subgraph(principales)
        pos = nx.spring_layout(H, k=0.6, seed=7, weight="weight")
        plt.figure(figsize=(14, 10))
        nx.draw_networkx_edges(H, pos, alpha=0.25, width=[0.4 + d["weight"] / 3 for *_, d in H.edges(data=True)])
        nx.draw_networkx_nodes(H, pos, node_size=[60 + 25 * H.nodes[n]["frecuencia"] for n in H],
                               node_color=["#4cd7f0" if H.nodes[n]["tipo"] == "persona" else "#c77dff" for n in H],
                               alpha=0.85)
        nx.draw_networkx_labels(H, pos, font_size=8)
        plt.title("Kira IA: red de personajes (celeste) y organizaciones (morado) por co-ocurrencia")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(CARPETA_SALIDA / "red_entidades.png", dpi=150)
        print(f"\nImagen: {CARPETA_SALIDA / 'red_entidades.png'}")
    except ImportError:
        print("\n(instala matplotlib para generar la imagen)")
    print(f"Red para Gephi: {CARPETA_SALIDA / 'red_entidades.gexf'}")


if __name__ == "__main__":
    main()
