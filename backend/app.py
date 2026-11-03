"""
Inicialización de Flask (equivale a app.ts + server.ts del ejemplo).

Uso (desde la carpeta raíz kira/):
    python -m backend.app
"""

import mimetypes

from flask import Flask, render_template

from backend.config import CARPETA_FRONTEND, PORT, DEBUG_MODE
from backend.database import crear_tablas
from backend.routes import api
from backend.services.imagenes_service import construir_indice_juegos


# Los juegos del arcade (frontend/static/juegos) corren con WebAssembly:
# en Windows el registro a veces da un tipo MIME incorrecto a .js/.wasm
# y el navegador se niega a cargarlos. Se fijan aquí.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/wasm", ".wasm")


def crear_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(CARPETA_FRONTEND / "templates"),
        static_folder=str(CARPETA_FRONTEND / "static"),
        static_url_path="/static",
    )
    app.register_blueprint(api)

    @app.get("/")
    def home():
        return render_template("index.html")

    crear_tablas()
    try:
        indice = construir_indice_juegos()
        print(f"✓ Índice de juegos construido: {len(indice)} juegos")
    except Exception as e:
        print(f"✗ Error construyendo índice de juegos: {e}")

    # Cargar ChromaDB y el modelo de embeddings al arrancar (no en la primera pregunta):
    # así los errores se ven de inmediato y la primera respuesta no tarda de más.
    from backend.vectorDb.store import obtener_coleccion
    obtener_coleccion()

    return app


if __name__ == "__main__":
    # DEBUG_MODE=1 activa el debugger de Werkzeug: solo en tu propia máquina,
    # nunca si expones el servidor (ngrok, 0.0.0.0, nube).
    # use_reloader=False: el recargador automático de Flask reiniciaba el servidor
    # a mitad de una respuesta al cargar el modelo de embeddings ("Failed to fetch").
    crear_app().run(debug=DEBUG_MODE, use_reloader=False, port=PORT)

#$py = "C:/Users/Cony02/AppData/Local/Programs/Python/Python311/python.exe"
#& $py -m backend.app