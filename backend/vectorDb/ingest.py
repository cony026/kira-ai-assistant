"""
Ingesta: construye la base de conocimiento vectorial de Kira (antes construir_base.py).

Pipeline (igual que en la teoría de RAG):
  1. Ingesta y LIMPIEZA   -> lee data/documentos/*.txt y les quita el ruido (limpieza.py)
  2. Chunking             -> fragmentos por secciones, cada uno con la cabecera del juego
  3. Vectorización        -> embeddings multilingües con sentence-transformers (local, gratis)
  4. Almacenamiento       -> ChromaDB (data/kira_db/) con metadatos por fragmento

Uso (desde la carpeta raíz kira/):
    python -m backend.vectorDb.ingest            # limpia, vectoriza y guarda
    python -m backend.vectorDb.ingest --revisar  # solo muestra la limpieza (no vectoriza)
"""

import re
import sys

from backend.config import (
    CARPETA_DOCS, CARPETA_DB_VECTORIAL, NOMBRE_COLECCION,
    MODELO_EMBED, TAM_CHUNK, SOLAPE,
)
from backend.vectorDb.limpieza import limpiar_documento, metadatos_de
from backend.services.imagenes_service import _normalizar


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def trocear(texto: str, tam: int = TAM_CHUNK, solape: int = SOLAPE) -> list[str]:
    """
    Divide un texto largo en fragmentos de hasta `tam` caracteres respetando
    párrafos y oraciones (no corta palabras a la mitad). Entre un fragmento y el
    siguiente se repiten las últimas oraciones (~`solape` caracteres) para no
    perder el contexto en el corte.
    """
    if len(texto) <= tam:
        return [texto] if texto.strip() else []

    # unidades: oraciones (o líneas, en listas como los requisitos)
    unidades = []
    for parrafo in re.split(r"\n\s*\n", texto):
        partes = re.split(r"(?<=[.!?])\s+|\n", parrafo.strip())
        for parte in partes:
            parte = parte.strip()
            while len(parte) > tam:                  # oración gigante: corte duro
                corte = parte.rfind(" ", 0, tam)
                corte = corte if corte > tam // 2 else tam
                unidades.append(parte[:corte])
                parte = parte[corte:].strip()
            if parte:
                unidades.append(parte)

    fragmentos, actual = [], []
    for unidad in unidades:
        if actual and len(" ".join(actual + [unidad])) > tam:
            fragmentos.append(" ".join(actual))
            # solapamiento: arrastra las últimas oraciones al siguiente fragmento
            arrastre = []
            for u in reversed(actual):
                if len(" ".join([u] + arrastre)) > solape:
                    break
                arrastre.insert(0, u)
            actual = arrastre
        actual.append(unidad)
    if actual:
        fragmentos.append(" ".join(actual))
    return fragmentos


def cabecera(campos: dict) -> str:
    """Identifica el juego en cada fragmento (si no, un trozo del medio de una
    descripción no dice de qué juego habla y la búsqueda no lo encuentra)."""
    partes = [f"Juego: {campos.get('JUEGO', '?')}"]
    plataforma = campos.get("PLATAFORMA") or campos.get("PLATAFORMA PRINCIPAL")
    if plataforma:
        partes.append(f"Plataforma: {plataforma}")
    return " | ".join(partes)


def fragmentar_documento(campos: dict, secciones: list[tuple[str, str]]) -> list[str]:
    """Fragmento 1 = ficha completa. Luego, cada sección troceada con la cabecera."""
    ficha = "\n".join(f"{k}: {v}" for k, v in campos.items() if k not in ("URL", "PORTADA"))
    fragmentos = [ficha] if ficha else []
    cab = cabecera(campos)
    espacio = max(300, TAM_CHUNK - len(cab) - 60)
    for titulo, contenido in secciones:
        for trozo in trocear(contenido, espacio, SOLAPE):
            fragmentos.append(f"{cab}\n{titulo}:\n{trozo}")
    return fragmentos


# ---------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------
def preparar_fragmentos():
    """Lee, limpia y trocea todos los documentos. Devuelve (fragmentos, metadatos, stats)."""
    fragmentos, metadatos = [], []
    stats = {"documentos": 0, "chars_antes": 0, "chars_despues": 0, "secciones_descartadas": 0}
    for archivo in sorted(CARPETA_DOCS.glob("*.txt")):
        texto = archivo.read_text(encoding="utf-8")
        campos, secciones = limpiar_documento(texto)
        meta_base = metadatos_de(campos, archivo.stem)
        # clave normalizada del título (sin mayúsculas, tildes, apóstrofos ni símbolos):
        # permite filtrar por juego aunque el usuario lo escriba distinto
        meta_base["juego_clave"] = _normalizar(campos.get("JUEGO", ""))

        stats["documentos"] += 1
        stats["chars_antes"] += len(texto)
        stats["chars_despues"] += sum(len(c) for _, c in secciones) + sum(len(v) for v in campos.values())
        stats["secciones_descartadas"] += len(re.findall(r"^[A-ZÁÉÍÓÚÑ /()]+:\s*$", texto, re.M)) - len(secciones)

        for i, frag in enumerate(fragmentar_documento(campos, secciones)):
            fragmentos.append(frag)
            metadatos.append({**meta_base, "parte": i})
    return fragmentos, metadatos, stats


def mostrar_resumen(fragmentos, stats):
    reduccion = 100 * (1 - stats["chars_despues"] / max(1, stats["chars_antes"]))
    print(f"Documentos leídos:        {stats['documentos']}")
    print(f"Texto antes de limpiar:   {stats['chars_antes']:,} caracteres")
    print(f"Texto después de limpiar: {stats['chars_despues']:,} caracteres ({reduccion:.1f}% menos ruido)")
    print(f"Secciones vacías o repetidas descartadas: {max(0, stats['secciones_descartadas'])}")
    print(f"Fragmentos (chunks):      {len(fragmentos)}  (tamaño máx. {TAM_CHUNK}, solape {SOLAPE})\n")


def main():
    fragmentos, metadatos, stats = preparar_fragmentos()
    if not fragmentos:
        print(f"No hay documentos en '{CARPETA_DOCS}'.")
        print("Corre primero algún scraper, ej:  python -m backend.scrapers.steam")
        return

    print("1. LIMPIEZA Y CHUNKING")
    mostrar_resumen(fragmentos, stats)

    if "--revisar" in sys.argv:
        print("Ejemplos de fragmentos limpios:\n")
        for i in (0, 1, len(fragmentos) // 2):
            print(f"--- [{metadatos[i]['fuente']} #{metadatos[i]['parte']}]")
            print(fragmentos[i][:600], "\n")
        return

    import chromadb
    from backend.vectorDb.store import cargar_modelo, vectorizar_documentos

    print(f"2. VECTORIZACIÓN con {MODELO_EMBED}")
    print("   (la primera vez descarga el modelo, ~470 MB; luego queda guardado)")
    modelo = cargar_modelo()
    vectores = vectorizar_documentos(modelo, fragmentos)

    print("\n3. ALMACENAMIENTO en ChromaDB (se recrea desde cero)")
    db = chromadb.PersistentClient(path=CARPETA_DB_VECTORIAL)
    try:
        db.delete_collection(NOMBRE_COLECCION)
    except Exception:
        pass
    # distancia coseno (la estándar para embeddings normalizados) y el modelo usado,
    # para avisar si después se consulta con otro modelo
    col = db.create_collection(NOMBRE_COLECCION, metadata={"hnsw:space": "cosine", "modelo": MODELO_EMBED})

    LOTE = 500
    for i in range(0, len(fragmentos), LOTE):
        col.add(
            ids=[f"{m['fuente']}_{m['parte']}" for m in metadatos[i:i + LOTE]],
            documents=fragmentos[i:i + LOTE],
            embeddings=[v.tolist() for v in vectores[i:i + LOTE]],
            metadatas=metadatos[i:i + LOTE],
        )
        print(f"  [{min(i + LOTE, len(fragmentos))}/{len(fragmentos)}] guardado")

    print(f"\n✓ Base de conocimiento lista en: {CARPETA_DB_VECTORIAL}")
    print(f"  Fragmentos totales guardados: {col.count()}")


if __name__ == "__main__":
    main()
