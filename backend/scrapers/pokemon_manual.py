"""
Crea archivos .txt para juegos de Pokémon populares.
Información basada en Metacritic y bases de datos públicas.
"""

from pathlib import Path
from backend.config import CARPETA_DOCS, RAIZ_PROYECTO  # rutas centralizadas

CARPETA = CARPETA_DOCS
CARPETA.mkdir(exist_ok=True)

JUEGOS_POKEMON = [
    {
        "nombre": "Pokémon Scarlet",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "84",
        "descripcion": "Pokémon Scarlet es un juego de rol de acción que permite explorar libremente el mundo de Paldea. Atrapa, entrena y evoluciona Pokémon mientras compites en batallas contra otros entrenadores. Características de mundo abierto con gráficos en tiempo real. Incluye pokémon nuevos y clásicos con nuevas formas Terastalizadas.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Violet",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "84",
        "descripcion": "Pokémon Violet es el juego hermano de Scarlet con el mismo mundo abierto de Paldea pero diferente versión exclusiva de Pokémon. Explora libremente, realiza misiones en cualquier orden y personaliza tu aventura. Características de batalla dinámica y cooperativa multijugador.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Legends: Arceus",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Acción",
        "score": "82",
        "descripcion": "Pokémon Legends: Arceus es un juego de acción-aventura ambientado en los antiguos tiempos de la región de Sinnoh. Atrapa Pokémon de forma más directa con mecánicas de tiempo real. Crea equipos únicos y participa en batallas dinámicas contra otros entrenadores y Pokémon salvajes.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Sword",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "80",
        "descripcion": "Pokémon Sword es la versión del juego que explora la región de Galar. Participa en emocionantes batallas gimnasia, atrapa Pokémon Gigantamax y compite en torneos. Incluye el Poké Ball Plus compatible y opciones de multijugador en línea.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Shield",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "80",
        "descripcion": "Pokémon Shield es la versión hermana de Sword con Pokémon exclusivos diferentes. Explora Galar, atrapa Pokémon raros y participa en batallas contra gimnasios y rivales. Incluye contenido descargable con nuevas regiones y Pokémon.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Brilliant Diamond",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "79",
        "descripcion": "Remake del clásico Pokémon Diamond para Nintendo Switch. Explora la región de Sinnoh con gráficos modernos e híbridos. Atrapa más de 150 Pokémon diferentes, participa en batallas y completa la Pokédex. Incluye Pokémon Legendarios y característica de unión con otros jugadores.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Shining Pearl",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "79",
        "descripcion": "Remake del clásico Pokémon Pearl con actualizaciones visuales para Nintendo Switch. Viaja por Sinnoh, captura Pokémon únicos de esta versión y compite en la Liga Pokémon. Características de multijugador y compatibilidad con Pokémon Home.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Let's Go Pikachu",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "79",
        "descripcion": "Pokémon Let's Go Pikachu es el remake del juego original Rojo/Azul con Pikachu como tu compañero principal. Explora Kanto, atrapa Pokémon en la región original y participa en batallas contra Gimnasios y rivales clásicos.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Let's Go Eevee",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Aventura",
        "score": "79",
        "descripcion": "Pokémon Let's Go Eevee es la versión hermana con Eevee como tu compañero principal. Recorre la región de Kanto con gráficos modernos, atrapa los 151 Pokémon originales y desafía a los 8 gimnasios.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Legends: Z-A",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Acción",
        "score": "TBA",
        "descripcion": "Pokémon Legends: Z-A es la próxima entrega en desarrollo ambientada en la región de Kalos. Continuación de la serie Legends con mecánicas de acción mejoradas. Características de combate dinámico y exploración del mundo de Kalos.",
        "requisitos": "Nintendo Switch (Próximo lanzamiento)"
    },
    {
        "nombre": "Pokémon GO",
        "plataforma": "Móvil",
        "generos": "RPG, Aventura, Realidad Aumentada",
        "score": "76",
        "descripcion": "Pokémon GO es un juego de realidad aumentada para dispositivos móviles. Camina por tu ciudad, atrapa Pokémon en tiempo real usando tu teléfono y participa en batallas con otros entrenadores. Eventos especiales y raids cooperativos.",
        "requisitos": "Dispositivo iOS o Android, GPS"
    },
    {
        "nombre": "Pokémon Legends: Giratina",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Acción",
        "score": "81",
        "descripcion": "Expansión de Pokémon Legends: Arceus enfocada en Giratina. Explora el Mundo Distorsionado, atrapa nuevos Pokémon y participa en desafíos únicos. Nuevas mecánicas de captura y batalla.",
        "requisitos": "Nintendo Switch, Pokémon Legends: Arceus"
    },
    {
        "nombre": "Pokémon Mystery Dungeon: Red Rescue Team DX",
        "plataforma": "Nintendo Switch",
        "generos": "RPG, Dungeon Crawler",
        "score": "73",
        "descripcion": "Remake del clásico Pokémon Mystery Dungeon. Forma un equipo de rescate, explora cuevas y ayuda a Pokémon en peligro. Sistema de roguelike con permadeath. Gráficos mejorados y nuevas características.",
        "requisitos": "Nintendo Switch"
    },
    {
        "nombre": "Pokémon Unite",
        "plataforma": "Nintendo Switch, Móvil",
        "generos": "MOBA",
        "score": "68",
        "descripcion": "Pokémon Unite es un juego MOBA donde seleccionas un Pokémon y compites en batallas 5v5. Participa en eventos competitivos, sube de nivel tus Pokémon y domina el campo de batalla. Juego gratuito con compras opcionales.",
        "requisitos": "Nintendo Switch o dispositivo móvil"
    },
    {
        "nombre": "Pokkén Tournament DX",
        "plataforma": "Nintendo Switch",
        "generos": "Lucha",
        "score": "74",
        "descripcion": "Juego de lucha de Pokémon en tiempo real. Controla tu Pokémon favorito, realiza combos especiales y derrota a otros Pokémon en batallas uno contra uno. Modo Historia, Torneo y multijugador en línea.",
        "requisitos": "Nintendo Switch"
    }
]

def crear_archivo(juego):
    """Crea un archivo .txt para un juego de Pokémon."""
    nombre = juego["nombre"]
    plataforma = juego["plataforma"]

    # Crear slug para el nombre
    from unicodedata import normalize
    from re import sub
    slug = normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    slug = sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()

    # Nombre de archivo
    plataforma_slug = normalize("NFKD", plataforma).encode("ascii", "ignore").decode()
    plataforma_slug = sub(r"[^a-zA-Z0-9]+", "-", plataforma_slug).strip("-").lower()
    archivo = CARPETA / f"pokemon_{plataforma_slug}_{slug}.txt"

    # Contenido
    lineas = []
    lineas.append(f"JUEGO: {nombre}")
    lineas.append(f"PLATAFORMA: {plataforma}")
    lineas.append(f"GÉNEROS: {juego['generos']}")
    lineas.append(f"NOTA METACRITIC: {juego['score']}")
    lineas.append(f"\nRESEÑA / DESCRIPCIÓN:\n{juego['descripcion']}")
    lineas.append(f"\nREQUISITOS MÍNIMOS:\n{juego['requisitos']}")

    contenido = "\n".join(lineas)
    archivo.write_text(contenido, encoding="utf-8")
    return archivo.name

def main():
    print("=" * 60)
    print("🔴 Creador de Archivos Pokémon")
    print("=" * 60)

    archivos_creados = 0
    for juego in JUEGOS_POKEMON:
        try:
            nombre_archivo = crear_archivo(juego)
            print(f"✓ {juego['nombre']:<35} → {nombre_archivo}")
            archivos_creados += 1
        except Exception as e:
            print(f"✗ Error creando {juego['nombre']}: {e}")

    print("\n" + "=" * 60)
    print(f"✓ Total de archivos creados: {archivos_creados}")
    print(f"  Ubicación: {CARPETA.resolve()}")
    print("=" * 60)
    print("\nAhora ejecuta:")
    print("  python construir_base.py")
    print("  python Kira.py")

if __name__ == "__main__":
    main()