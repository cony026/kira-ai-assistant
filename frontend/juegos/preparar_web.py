"""
Convierte los juegos de escritorio (pygame) en versiones que corren
DENTRO de la página de Kira (navegador, con pygbag / WebAssembly).

Uso (desde la carpeta raíz kira/):
    python frontend/juegos/preparar_web.py

Qué hace:
  1. Copia cada juego de frontend/juegos/originales/ a una carpeta temporal.
  2. Le aplica los cambios mínimos para el navegador:
       - bucle principal asíncrono (el navegador necesita que el juego
         "suelte" el control en cada frame: await asyncio.sleep(0))
       - récords guardados en el localStorage del navegador
       - al salir del juego (ESC en el menú) avisa a la página de Kira
         para cerrar el panel
  3. Empaqueta todo en frontend/static/juegos/<juego>/<juego>.apk
     (un zip que el runtime de pygbag descomprime en el navegador).

Los .py originales NO se modifican: siguen funcionando en escritorio con
    python frontend/juegos/originales/tenisplay.py

Cada vez que edites un juego, vuelve a correr este script.
"""

import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]            # carpeta kira/
ORIGINALES = RAIZ / "frontend" / "juegos" / "originales"
DESTINO = RAIZ / "frontend" / "static" / "juegos"

# nombre web -> título, script original, archivos que necesita y cómo se guarda su récord
JUEGOS = {
    "tenis": {
        "titulo": "Tenis retro vs Kira",
        "script": "tenisplay.py",
        "archivos": ["kira.png"],
        "clave": "kira_tenis_records",
        "record": "RUTA_RECORDS",
        "guardar": "guardar_records",
    },
    "vasos": {
        "titulo": "¿Dónde está la mascota?",
        "script": "vasitofinal.py",
        "archivos": ["mascota.png", "vasito.png", "music.ogg"],
        "clave": "kira_vasos_record",
        "record": "ARCHIVO_RECORD",
        "guardar": "guardar_record",
    },
}

CABECERA_WEB = '''
import sys
import asyncio

# True cuando el juego corre dentro del navegador (pygbag / WebAssembly)
WEB = sys.platform == "emscripten"


def avisar_pagina(accion):
    # Le avisa a la página de Kira (la que contiene el juego) que algo pasó.
    if not WEB:
        return
    try:
        import platform
        platform.window.parent.postMessage("kira-juego:" + accion, "*")
    except Exception:
        pass


def restaurar_desde_navegador(ruta, clave):
    # Trae el récord guardado en el navegador al archivo virtual del juego.
    if not WEB:
        return
    try:
        import platform
        dato = platform.window.localStorage.getItem(clave)
        if dato:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(str(dato))
    except Exception:
        pass


def guardar_en_navegador(ruta, clave):
    # Copia el archivo de récord al localStorage para que no se pierda.
    if not WEB:
        return
    try:
        import platform
        with open(ruta, encoding="utf-8") as f:
            platform.window.localStorage.setItem(clave, f.read())
    except Exception:
        pass

'''


def reemplazar(codigo, viejo, nuevo, nombre):
    if codigo.count(viejo) != 1:
        sys.exit(f"[{nombre}] No encontré exactamente una vez:\n{viejo}\n"
                 "¿Cambiaste esa parte del juego? Ajusta preparar_web.py.")
    return codigo.replace(viejo, nuevo)


def adaptar(codigo, nombre, cfg):
    # 1) utilidades web justo después de los imports
    codigo = reemplazar(codigo, "from array import array\n",
                        "from array import array\n" + CABECERA_WEB, nombre)

    # 2) récords: restaurar desde el navegador y guardar también allí
    guardar = cfg["guardar"]
    codigo = reemplazar(
        codigo, f"\ndef {guardar}(",
        f"\nrestaurar_desde_navegador({cfg['record']}, \"{cfg['clave']}\")\n\n\n"
        f"def {guardar}(", nombre)
    envoltura = (
        f"\n\n_{guardar}_archivo = {guardar}\n\n\n"
        f"def {guardar}(*args, **kwargs):\n"
        f"    _{guardar}_archivo(*args, **kwargs)\n"
        f"    guardar_en_navegador({cfg['record']}, \"{cfg['clave']}\")\n"
    )
    # se inserta después del bloque completo de la función original
    inicio = codigo.index(f"\ndef {guardar}(")
    fin = codigo.index("\n# ====", inicio)
    codigo = codigo[:fin] + envoltura + codigo[fin:]

    # 3) bucle principal asíncrono
    codigo = reemplazar(codigo, "\ndef main():", "\nasync def main():", nombre)
    codigo = reemplazar(codigo, "        pygame.display.flip()\n",
                        "        pygame.display.flip()\n"
                        "        await asyncio.sleep(0)   # cede el control al navegador\n",
                        nombre)
    codigo = reemplazar(codigo, "\n    pygame.quit()\n",
                        "\n    avisar_pagina(\"cerrar\")\n    pygame.quit()\n", nombre)
    codigo = reemplazar(codigo, 'if __name__ == "__main__":\n    main()',
                        'if __name__ == "__main__":\n    asyncio.run(main())', nombre)
    return codigo


def empaquetar(nombre, cfg):
    carpeta = DESTINO / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    codigo = (ORIGINALES / cfg["script"]).read_text(encoding="utf-8")
    codigo = adaptar(codigo, nombre, cfg)

    apk = carpeta / f"{nombre}.apk"
    with zipfile.ZipFile(apk, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("assets/main.py", codigo)
        for archivo in cfg["archivos"]:
            ruta = ORIGINALES / archivo
            if not ruta.exists():
                sys.exit(f"[{nombre}] Falta {ruta}")
            z.write(ruta, f"assets/{archivo}")
        for fuente in sorted((ORIGINALES / "fuentes").glob("*.ttf")):
            z.write(fuente, f"assets/fuentes/{fuente.name}")
    # Página que carga el juego (se muestra dentro del chat en un iframe)
    plantilla = (RAIZ / "frontend" / "juegos" / "plantilla_web.html").read_text(encoding="utf-8")
    pagina = (plantilla.replace("__CDN__", "/static/juegos/runtime/")
                       .replace("__JUEGO__", nombre)
                       .replace("__TITULO__", cfg["titulo"]))
    (carpeta / "index.html").write_text(pagina, encoding="utf-8")
    print(f"✓ {nombre}: {apk.relative_to(RAIZ)} ({apk.stat().st_size // 1024} KB)")


def main():
    # La música en navegador funciona mejor en .ogg
    ogg = ORIGINALES / "music.ogg"
    mp3 = ORIGINALES / "music.mp3"
    if not ogg.exists() and mp3.exists():
        if shutil.which("ffmpeg"):
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                            "-c:a", "libvorbis", "-q:a", "3", str(ogg)], check=True)
        else:
            sys.exit("Falta music.ogg (convierte music.mp3 a .ogg o instala ffmpeg).")
    for nombre, cfg in JUEGOS.items():
        empaquetar(nombre, cfg)


if __name__ == "__main__":
    main()
