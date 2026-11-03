"""
Evaluación automática de Kira con un Golden Dataset (fase 4: evaluación).

Métricas (las del marco Ragas / RAG Triad):

  RECUPERACIÓN (no gasta tokens, se calcula siempre)
  - Context Precision@K: ¿los fragmentos relevantes quedaron arriba? Fórmula de Ragas:
        CP@K = Σ_k (precisión@k · v_k) / (n.º de fragmentos relevantes en el top K)
    v_k = 1 si el fragmento k es relevante: es del juego esperado (preguntas de juego)
    o contiene alguna palabra clave del tema (preguntas de tema).
  - Hit Rate: % de preguntas con al menos un fragmento relevante.
  - Rechazo fuera de dominio: % de preguntas ajenas a juegos (cocina, geografía...)
    en que NO se recupera nada (el umbral de distancia funciona).

  GENERACIÓN (con --con-llm, llama a Gemini)
  - Faithfulness (fidelidad): Gemini, como juez, divide la respuesta en afirmaciones y
    marca cuáles están respaldadas por el contexto. Fidelidad = respaldadas / total.
  - Answer Relevance: similitud coseno entre la pregunta y la respuesta (embeddings e5).
  - Mención esperada: la respuesta contiene alguna de las palabras de "debe_mencionar".
  - Tokens de entrada y salida reales de cada respuesta (para el cálculo de costos).

Uso (desde la carpeta raíz kira/, con la base vectorial creada):
    python -m backend.evaluacion.evaluar_rag              # solo recuperación (gratis)
    python -m backend.evaluacion.evaluar_rag --con-llm    # todo (unas 60 llamadas a Gemini)
    python -m backend.evaluacion.evaluar_rag --con-llm --limite 10 --pausa 6

Resultados: data/evaluacion/resultados_<fecha>.json y .csv
"""

import argparse
import csv
import json
import statistics
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from backend.config import CARPETA_DATA, MODELO_GENERACION, TOP_K

CARPETA_RESULTADOS = CARPETA_DATA / "evaluacion"
DATASET = Path(__file__).with_name("golden_dataset.json")

# Metas de calidad (las mismas que los requisitos no funcionales del informe)
METAS = {"context_precision": 0.70, "hit_rate": 0.85, "rechazo_fuera_dominio": 0.90,
         "faithfulness": 0.85, "answer_relevance": 0.80}


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# Métricas de recuperación
# ---------------------------------------------------------------------------
def es_relevante(caso: dict, fragmento: dict) -> bool:
    from backend.services.imagenes_service import _normalizar
    if caso["tipo"] == "juego":
        esperado = _normalizar(caso["juego"])
        clave = fragmento["metadatos"].get("juego_clave", "")
        return bool(clave) and (esperado in clave or clave in esperado)
    texto = _norm(fragmento["documento"])
    return any(_norm(p) in texto for p in caso.get("palabras_clave", []))


def context_precision(relevancias: list[bool]) -> float:
    total_relevantes = sum(relevancias)
    if not total_relevantes:
        return 0.0
    acumulado, aciertos = 0.0, 0
    for k, relevante in enumerate(relevancias, start=1):
        if relevante:
            aciertos += 1
            acumulado += aciertos / k
    return acumulado / total_relevantes


# ---------------------------------------------------------------------------
# Métricas de generación
# ---------------------------------------------------------------------------
PROMPT_JUEZ = """Eres un evaluador estricto de sistemas RAG.
Divide la RESPUESTA en afirmaciones concretas y verificables (ignora saludos, preguntas
y opiniones de cortesía). Para cada afirmación indica si está respaldada por el CONTEXTO.
Devuelve SOLO un JSON con esta forma:
{"afirmaciones": [{"texto": "...", "respaldada": true}]}

CONTEXTO:
<<<CONTEXTO>>>

RESPUESTA:
<<<RESPUESTA>>>"""


def faithfulness(contexto: str, respuesta: str) -> tuple[float | None, int]:
    """Gemini como juez. Devuelve (fidelidad, n.º de afirmaciones)."""
    from google.genai import types
    from backend.agent.nodes.generate import _cliente

    prompt = PROMPT_JUEZ.replace("<<<CONTEXTO>>>", contexto or "(vacío)").replace("<<<RESPUESTA>>>", respuesta)
    r = _cliente().models.generate_content(
        model=MODELO_GENERACION, contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    try:
        afirmaciones = json.loads(r.text).get("afirmaciones", [])
    except (json.JSONDecodeError, AttributeError):
        return None, 0
    if not afirmaciones:
        return 1.0, 0            # sin afirmaciones verificables (por ejemplo, una pregunta de vuelta)
    respaldadas = sum(1 for a in afirmaciones if a.get("respaldada") is True)
    return respaldadas / len(afirmaciones), len(afirmaciones)


def answer_relevance(modelo, pregunta: str, respuesta: str) -> float:
    from backend.vectorDb.store import vectorizar_consulta
    a, b = vectorizar_consulta(modelo, pregunta), vectorizar_consulta(modelo, respuesta)
    return float(sum(x * y for x, y in zip(a, b)))          # vectores normalizados: coseno


# ---------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------
def evaluar(con_llm: bool, limite: int | None, pausa: float) -> dict:
    from backend.agent.graph import ejecutar_agente
    from backend.agent.nodes.retrieve import recuperar_fragmentos, consulta_de_busqueda
    from backend.agent.state import EstadoAgente
    from backend.services.imagenes_service import construir_indice_juegos, detectar_juegos_en_texto
    from backend.vectorDb.store import obtener_coleccion, obtener_modelo_embeddings

    construir_indice_juegos()
    if not obtener_coleccion():
        raise SystemExit("No hay base vectorial. Créala con:  python -m backend.vectorDb.ingest")
    modelo = obtener_modelo_embeddings()

    casos = json.loads(DATASET.read_text(encoding="utf-8"))[:limite]
    filas = []
    for i, caso in enumerate(casos, 1):
        pregunta = caso["pregunta"]
        consulta = consulta_de_busqueda(EstadoAgente(mensaje=pregunta))
        juegos = detectar_juegos_en_texto(consulta, max_juegos=3, tolerar_errores=True)
        inicio = time.perf_counter()
        fragmentos = recuperar_fragmentos(consulta, juegos=juegos)
        ms_recuperacion = int((time.perf_counter() - inicio) * 1000)

        fila = {"n": i, "tipo": caso["tipo"], "pregunta": pregunta, "fragmentos": len(fragmentos),
                "ms_recuperacion": ms_recuperacion,
                "caracteres_contexto": sum(len(f["documento"]) for f in fragmentos)}
        if caso["tipo"] == "fuera":
            fila["rechazo_correcto"] = len(fragmentos) == 0
        else:
            relevancias = [es_relevante(caso, f) for f in fragmentos]
            fila["context_precision"] = round(context_precision(relevancias), 3)
            fila["hit"] = any(relevancias)

        if con_llm and caso["tipo"] != "fuera":
            inicio = time.perf_counter()
            estado = ejecutar_agente(pregunta, perfil={}, historial=[])
            fila["ms_respuesta"] = int((time.perf_counter() - inicio) * 1000)
            fila["tokens_entrada"], fila["tokens_salida"] = estado.tokens_entrada, estado.tokens_salida
            fila["respuesta"] = estado.respuesta
            if estado.aclaracion:          # el router pidió aclarar: no hubo llamada al LLM
                fila["aclaracion"] = True
                filas.append(fila)
                print(f"[{i:02d}/{len(casos)}] {pregunta[:55]:<55} (el router pidió aclarar)")
                continue
            fila["menciona_esperado"] = any(_norm(p) in _norm(estado.respuesta) for p in caso.get("debe_mencionar", []))
            fila["answer_relevance"] = round(answer_relevance(modelo, pregunta, estado.respuesta), 3)
            time.sleep(pausa)
            fid, n_afirm = faithfulness(estado.contexto_rag, estado.respuesta)
            fila["faithfulness"] = None if fid is None else round(fid, 3)
            fila["afirmaciones"] = n_afirm
            time.sleep(pausa)

        filas.append(fila)
        resumen = " ".join(f"{k}={fila[k]}" for k in ("context_precision", "rechazo_correcto", "faithfulness") if k in fila)
        print(f"[{i:02d}/{len(casos)}] {pregunta[:55]:<55} {resumen}")

    return {"filas": filas, "resumen": resumir(filas)}


def _media(valores):
    valores = [v for v in valores if v is not None]
    return round(statistics.mean(valores), 3) if valores else None


def resumir(filas: list[dict]) -> dict:
    en_dominio = [f for f in filas if f["tipo"] != "fuera"]
    fuera = [f for f in filas if f["tipo"] == "fuera"]
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "preguntas": len(filas), "top_k": TOP_K, "modelo_generacion": MODELO_GENERACION,
        "context_precision": _media([f.get("context_precision") for f in en_dominio]),
        "hit_rate": _media([1.0 if f.get("hit") else 0.0 for f in en_dominio]),
        "rechazo_fuera_dominio": _media([1.0 if f.get("rechazo_correcto") else 0.0 for f in fuera]),
        "ms_recuperacion_media": _media([f["ms_recuperacion"] for f in filas]),
        "caracteres_contexto_medio": _media([f["caracteres_contexto"] for f in en_dominio]),
    }
    if any("faithfulness" in f for f in filas):
        resumen.update({
            "faithfulness": _media([f.get("faithfulness") for f in en_dominio]),
            "answer_relevance": _media([f.get("answer_relevance") for f in en_dominio]),
            "menciona_esperado": _media([1.0 if f.get("menciona_esperado") else 0.0 for f in en_dominio]),
            "tokens_entrada_medio": _media([f.get("tokens_entrada") for f in en_dominio]),
            "tokens_salida_medio": _media([f.get("tokens_salida") for f in en_dominio]),
            "ms_respuesta_media": _media([f.get("ms_respuesta") for f in en_dominio]),
        })
    return resumen


def guardar(resultado: dict) -> Path:
    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M")
    ruta = CARPETA_RESULTADOS / f"resultados_{sello}.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    columnas = sorted({k for f in resultado["filas"] for k in f if k != "respuesta"}, key=lambda c: (c != "n", c))
    with open(ruta.with_suffix(".csv"), "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, extrasaction="ignore", delimiter=";")
        escritor.writeheader()
        escritor.writerows(resultado["filas"])
    return ruta


def mostrar(resumen: dict) -> None:
    print("\n" + "=" * 62)
    print("RESULTADOS DE LA EVALUACIÓN")
    print("=" * 62)
    for clave, valor in resumen.items():
        meta = METAS.get(clave)
        estado = "" if meta is None or valor is None else ("  ✓ cumple" if valor >= meta else f"  ✗ meta {meta}")
        print(f"  {clave:<28}{valor}{estado}")


def main():
    parser = argparse.ArgumentParser(description="Evalúa la recuperación y las respuestas de Kira.")
    parser.add_argument("--con-llm", action="store_true", help="también evalúa las respuestas (usa Gemini)")
    parser.add_argument("--limite", type=int, default=None, help="evaluar solo las primeras N preguntas")
    parser.add_argument("--pausa", type=float, default=4.0, help="segundos entre llamadas (cuota del plan gratis)")
    args = parser.parse_args()

    resultado = evaluar(args.con_llm, args.limite, args.pausa)
    ruta = guardar(resultado)
    mostrar(resultado["resumen"])
    print(f"\nDetalle guardado en: {ruta}  (y .csv para Excel)")


if __name__ == "__main__":
    main()
