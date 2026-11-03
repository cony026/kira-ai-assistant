"""
Estimación de costos operativos de Kira (viabilidad financiera del MVP).

Calcula el costo mensual de:
  1. Inferencia del LLM (Gemini): tokens de entrada y salida por consulta × precio.
  2. Embeddings: Kira los calcula en su propio servidor (multilingual-e5-small), así
     que la API cuesta 0; se muestra cuánto costaría con una API pagada, para comparar.
  3. Infraestructura cloud: servidor para los contenedores Docker y respaldos.

¿De dónde salen los tokens por consulta? (en este orden de preferencia)
  --desde-bd          promedio REAL de las consultas guardadas en MySQL (historial_chat)
  --desde-evaluacion  promedio del último resultado de evaluar_rag.py --con-llm
  (por defecto)       estimación a partir del tamaño del prompt (~4 caracteres por token)

Uso (desde la carpeta raíz kira/):
    python -m backend.evaluacion.costos
    python -m backend.evaluacion.costos --desde-bd --usuarios 1000 --consultas-dia 10
"""

import argparse
import json
from pathlib import Path

from backend.config import (CARPETA_DATA, CARPETA_DOCS, MAX_CARACTERES_CONTEXTO, MODELO_GENERACION,
                            PRECIO_ENTRADA_MTOK, PRECIO_SALIDA_MTOK, TAM_CHUNK)

CARPETA_RESULTADOS = CARPETA_DATA / "evaluacion"
CARACTERES_POR_TOKEN = 4          # aproximación habitual para texto en español/inglés

# Infraestructura de referencia (USD/mes). Son valores de referencia de proveedores
# tipo Vultr, DigitalOcean o AWS Lightsail: cotizar antes de presentar cifras finales.
INFRA = {
    "Servidor (2 vCPU, 4 GB RAM): contenedores app + nginx + MariaDB": 24.00,
    "Disco adicional y respaldos diarios (object storage)": 5.00,
    "Dominio y certificado HTTPS (Let's Encrypt es gratis; dominio .cl prorrateado)": 1.00,
}
# Precio de referencia de una API de embeddings pagada (USD por 1M de tokens),
# solo para mostrar el ahorro de calcularlos en el propio servidor.
PRECIO_EMBEDDINGS_API_MTOK = 0.15


def tokens_estimados() -> dict:
    """Tamaño típico del prompt de Kira, antes y después del re-ranking."""
    from backend.agent.prompts import SYSTEM_INSTRUCTION
    sistema = len(SYSTEM_INSTRUCTION)
    perfil, mensaje, historial = 700, 120, 2 * 900          # perfil + pregunta + 2 turnos de memoria
    ahora = sistema + perfil + mensaje + historial + MAX_CARACTERES_CONTEXTO
    antes = sistema + perfil + mensaje + historial + 8 * TAM_CHUNK   # versión anterior: 8 fragmentos
    return {
        "fuente": "estimación por tamaño del prompt",
        "entrada": round(ahora / CARACTERES_POR_TOKEN),
        "entrada_version_anterior": round(antes / CARACTERES_POR_TOKEN),
        "salida": 220,                    # respuestas de ~120 palabras (límite del system prompt)
    }


def tokens_desde_bd() -> dict:
    from sqlalchemy import func, select
    from backend.database import SessionLocal
    from backend.models.chat import Chat
    with SessionLocal() as db:
        n, entrada, salida = db.execute(
            select(func.count(Chat.id), func.avg(Chat.tokens_entrada), func.avg(Chat.tokens_salida))
            .where(Chat.tokens_entrada > 0)
        ).one()
    if not n:
        raise SystemExit("Todavía no hay consultas con tokens registrados en historial_chat.")
    return {"fuente": f"promedio real de {n} consultas en MySQL", "entrada": round(entrada), "salida": round(salida)}


def tokens_desde_evaluacion() -> dict:
    archivos = sorted(CARPETA_RESULTADOS.glob("resultados_*.json"))
    for archivo in reversed(archivos):
        resumen = json.loads(archivo.read_text(encoding="utf-8"))["resumen"]
        if resumen.get("tokens_entrada_medio"):
            return {"fuente": f"evaluación {archivo.name}", "entrada": round(resumen["tokens_entrada_medio"]),
                    "salida": round(resumen["tokens_salida_medio"])}
    raise SystemExit("No hay evaluaciones con LLM. Corre:  python -m backend.evaluacion.evaluar_rag --con-llm")


def tokens_del_corpus() -> int:
    caracteres = sum(a.stat().st_size for a in Path(CARPETA_DOCS).glob("*.txt"))
    return round(caracteres / CARACTERES_POR_TOKEN)


def calcular(tokens: dict, usuarios: int, consultas_dia: int, dias: int, pct_sin_llm: float) -> dict:
    consultas = usuarios * consultas_dia * dias
    con_llm = round(consultas * (1 - pct_sin_llm))
    m_entrada = con_llm * tokens["entrada"] / 1e6
    m_salida = con_llm * tokens["salida"] / 1e6
    costo_entrada = m_entrada * PRECIO_ENTRADA_MTOK
    costo_salida = m_salida * PRECIO_SALIDA_MTOK
    llm = costo_entrada + costo_salida

    corpus = tokens_del_corpus()
    consultas_tokens = consultas * 30            # cada pregunta se vectoriza (~30 tokens)
    embeddings_api = (corpus + consultas_tokens) / 1e6 * PRECIO_EMBEDDINGS_API_MTOK

    infra = sum(INFRA.values())
    resultado = {
        "supuestos": {"usuarios_activos_mes": usuarios, "consultas_por_dia": consultas_dia, "dias": dias,
                      "consultas_mes": consultas, "consultas_que_llaman_al_llm": con_llm,
                      "modelo": MODELO_GENERACION, "precio_entrada_mtok": PRECIO_ENTRADA_MTOK,
                      "precio_salida_mtok": PRECIO_SALIDA_MTOK, "tokens_por_consulta": tokens},
        "llm": {"millones_tokens_entrada": round(m_entrada, 2), "millones_tokens_salida": round(m_salida, 2),
                "costo_entrada": round(costo_entrada, 2), "costo_salida": round(costo_salida, 2),
                "subtotal": round(llm, 2)},
        "embeddings": {"tokens_corpus": corpus, "costo_kira": 0.0,
                       "costo_si_fuera_api": round(embeddings_api, 2)},
        "infraestructura": {**INFRA, "subtotal": round(infra, 2)},
        "total_mensual": round(llm + infra, 2),
        "costo_por_consulta": round((llm + infra) / max(1, consultas), 5),
    }
    if "entrada_version_anterior" in tokens:
        antes = con_llm * tokens["entrada_version_anterior"] / 1e6 * PRECIO_ENTRADA_MTOK
        resultado["ahorro_reranking"] = {
            "costo_entrada_version_anterior": round(antes, 2),
            "ahorro_mensual": round(antes - costo_entrada, 2),
            "porcentaje_menos_tokens_entrada": round(100 * (1 - tokens["entrada"] / tokens["entrada_version_anterior"]), 1),
        }
    return resultado


def mostrar(r: dict) -> None:
    s, t = r["supuestos"], r["supuestos"]["tokens_por_consulta"]
    usd = lambda v: f"US$ {v:,.2f}"
    print("=" * 66)
    print("COSTOS OPERATIVOS ESTIMADOS DE KIRA IA (MVP)")
    print("=" * 66)
    print(f"Volumen: {s['usuarios_activos_mes']:,} usuarios × {s['consultas_por_dia']} consultas/día × {s['dias']} días"
          f" = {s['consultas_mes']:,} consultas/mes")
    print(f"Tokens por consulta ({t['fuente']}): {t['entrada']:,} de entrada y {t['salida']:,} de salida")
    print(f"\n1. LLM ({s['modelo']}, US$ {s['precio_entrada_mtok']} entrada / US$ {s['precio_salida_mtok']} salida por 1M)")
    print(f"   Entrada: {r['llm']['millones_tokens_entrada']:,} M tokens × {s['precio_entrada_mtok']} = {usd(r['llm']['costo_entrada'])}")
    print(f"   Salida:  {r['llm']['millones_tokens_salida']:,} M tokens × {s['precio_salida_mtok']} = {usd(r['llm']['costo_salida'])}")
    print(f"   Subtotal LLM: {usd(r['llm']['subtotal'])}")
    print("\n2. Embeddings (multilingual-e5-small en el propio servidor)")
    print(f"   Corpus: {r['embeddings']['tokens_corpus']:,} tokens. Costo de API: US$ 0.00 "
          f"(con una API pagada serían {usd(r['embeddings']['costo_si_fuera_api'])}/mes)")
    print("\n3. Infraestructura (Docker)")
    for nombre, valor in r["infraestructura"].items():
        if nombre != "subtotal":
            print(f"   {nombre}: {usd(valor)}")
    print(f"   Subtotal infraestructura: {usd(r['infraestructura']['subtotal'])}")
    print(f"\nTOTAL MENSUAL ESTIMADO: {usd(r['total_mensual'])}  (US$ {r['costo_por_consulta']:.4f} por consulta)")
    if "ahorro_reranking" in r:
        a = r["ahorro_reranking"]
        print(f"\nAhorro del re-ranking + compactación: {a['porcentaje_menos_tokens_entrada']}% menos tokens de entrada,"
              f" {usd(a['ahorro_mensual'])}/mes (antes {usd(a['costo_entrada_version_anterior'])} solo en entrada)")


def main():
    parser = argparse.ArgumentParser(description="Estima el costo mensual de operar Kira.")
    parser.add_argument("--usuarios", type=int, default=1000)
    parser.add_argument("--consultas-dia", type=int, default=10)
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--sin-llm", type=float, default=0.0,
                        help="fracción de consultas que responde el router sin LLM (ej. 0.1)")
    origen = parser.add_mutually_exclusive_group()
    origen.add_argument("--desde-bd", action="store_true")
    origen.add_argument("--desde-evaluacion", action="store_true")
    args = parser.parse_args()

    tokens = tokens_desde_bd() if args.desde_bd else tokens_desde_evaluacion() if args.desde_evaluacion \
        else tokens_estimados()
    resultado = calcular(tokens, args.usuarios, args.consultas_dia, args.dias, args.sin_llm)
    mostrar(resultado)
    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA_RESULTADOS / "costos.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en: {ruta}")


if __name__ == "__main__":
    main()
