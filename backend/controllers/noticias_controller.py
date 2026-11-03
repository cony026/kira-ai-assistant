"""Controlador de noticias gaming (RSS) y estado del servidor."""

from flask import request, jsonify

from backend.services.noticias_service import obtener_noticias
from backend.vectorDb.store import obtener_coleccion


def noticias():
    try:
        forzar = request.args.get("forzar") == "1"
        return jsonify({"noticias": obtener_noticias(limit=10, forzar=forzar)})
    except Exception as e:
        print(f"Error en noticias: {e}")
        return jsonify({"error": "No se pudieron cargar las noticias.", "noticias": []}), 500


def health():
    return jsonify({"status": "ok", "db": "ok" if obtener_coleccion() else "no_cargada"})
