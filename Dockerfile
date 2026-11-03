# =====================================================================
# Kira IA - Imagen del backend (Flask + agente RAG)
#
# Multi-etapa:
#   1. "dependencias": instala los paquetes de Python y el modelo de spaCy
#   2. "final": copia solo lo necesario y corre con un usuario sin privilegios
#
# Se usa python:3.11-slim (Debian) y no Alpine: PyTorch y ChromaDB publican
# paquetes precompilados para Debian; en Alpine habría que compilarlos (lento y frágil).
# =====================================================================

FROM python:3.11-slim AS dependencias
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /instalar
COPY requirements.txt requirements-docker.txt ./
# PyTorch solo CPU (la versión con CUDA pesa ~2 GB más y el servidor no tiene GPU)
RUN pip install --prefix=/paquetes torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --prefix=/paquetes -r requirements.txt -r requirements-docker.txt

FROM python:3.11-slim AS final
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/kira/.cache/huggingface \
    PORT=5000
COPY --from=dependencias /paquetes /usr/local

# Usuario sin privilegios: si alguien comprometiera la app, no sería root en el contenedor
RUN useradd --create-home --uid 1000 kira
WORKDIR /app
COPY --chown=kira:kira backend ./backend
COPY --chown=kira:kira frontend ./frontend
COPY --chown=kira:kira database ./database
COPY --chown=kira:kira data/documentos ./data/documentos
RUN mkdir -p data/kira_db data/evaluacion && chown -R kira:kira /app
USER kira

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=4)"

# Gunicorn (servidor de producción) en vez del servidor de desarrollo de Flask.
# 1 proceso con 4 hilos: cada proceso carga el modelo de embeddings (~500 MB de RAM).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--timeout", "120", "--access-logfile", "-", "backend.app:crear_app()"]
