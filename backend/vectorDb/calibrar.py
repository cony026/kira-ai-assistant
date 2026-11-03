"""
Calibra UMBRAL_DISTANCIA_MAXIMA para el modelo de embeddings actual.

Hace preguntas que SÍ tienen respuesta en la base (sobre juegos y géneros) y preguntas
que NO tienen nada que ver (cocina, geografía...), mide la distancia del fragmento más
cercano en cada caso y sugiere un umbral entre ambos grupos.

Uso (desde la carpeta raíz kira/, después de correr la ingesta):
    python -m backend.vectorDb.calibrar
"""

import random
import statistics

from backend.config import UMBRAL_DISTANCIA_MAXIMA, MODELO_EMBED
from backend.vectorDb.store import obtener_coleccion, obtener_modelo_embeddings, vectorizar_consulta
from backend.services.imagenes_service import construir_indice_juegos

PREGUNTAS_TEMA = [
    "recomiéndame juegos de terror", "un rpg de mundo abierto con buena historia",
    "juegos de carreras para jugar con amigos", "shooter multijugador competitivo",
    "juegos de estrategia por turnos", "un juego de plataformas difícil",
    "juegos de supervivencia con crafteo", "juegos de peleas", "simulador de granja relajante",
    "juegos de fútbol",
]
PREGUNTAS_FUERA = [
    "receta de pan amasado", "cuál es la capital de Francia", "cómo cambiar la rueda de un auto",
    "horóscopo de hoy", "cómo resolver una ecuación de segundo grado", "precio del dólar hoy",
    "cómo plantar tomates en el jardín", "historia de la revolución francesa",
    "cómo hacer un currículum", "qué tiempo hará mañana en Santiago",
]


def mejor_distancia(coleccion, modelo, pregunta):
    r = coleccion.query(query_embeddings=[vectorizar_consulta(modelo, pregunta)], n_results=1,
                        include=["distances"])
    return r["distances"][0][0]


def main():
    coleccion, modelo = obtener_coleccion(), obtener_modelo_embeddings()
    if not coleccion or not modelo:
        return
    indice = construir_indice_juegos()
    random.seed(7)
    juegos = random.sample([i["nombre"] for i in indice.values()], 15)
    preguntas_juego = [random.choice(["¿qué dicen las reseñas de {}?", "requisitos de {}",
                                      "¿de qué trata {}?"]).format(j) for j in juegos]

    print(f"Modelo: {MODELO_EMBED}\n")
    relevantes = []
    for p in preguntas_juego + PREGUNTAS_TEMA:
        d = mejor_distancia(coleccion, modelo, p)
        relevantes.append(d)
        print(f"  [relevante] {d:.3f}  {p}")
    fuera = []
    for p in PREGUNTAS_FUERA:
        d = mejor_distancia(coleccion, modelo, p)
        fuera.append(d)
        print(f"  [fuera    ] {d:.3f}  {p}")

    relevantes.sort()
    fuera.sort()
    alto_relevante = relevantes[int(len(relevantes) * 0.9) - 1]   # percentil 90
    bajo_fuera = fuera[0]
    print(f"\nRelevantes: mediana {statistics.median(relevantes):.3f}, percentil 90 {alto_relevante:.3f}")
    print(f"Fuera de tema: mínima {bajo_fuera:.3f}, mediana {statistics.median(fuera):.3f}")
    if alto_relevante < bajo_fuera:
        sugerido = round((alto_relevante + bajo_fuera) / 2, 3)
        print(f"\n✓ Umbral sugerido: {sugerido}  (actual: {UMBRAL_DISTANCIA_MAXIMA})")
    else:
        sugerido = round(alto_relevante + 0.01, 3)
        print(f"\n~ Los grupos se mezclan un poco; umbral sugerido: {sugerido} (deja pasar las relevantes)")
    print(f"  Para usarlo, agrega al .env:  UMBRAL_DISTANCIA_MAXIMA={sugerido}")


if __name__ == "__main__":
    main()
