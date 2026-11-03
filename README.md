# Kira IA — Asistente RAG de videojuegos

Sistema RAG (Retrieval-Augmented Generation) que responde sobre videojuegos usando reseñas y
fichas técnicas de PC (Steam), PlayStation, Xbox, Nintendo Switch y móviles.
Los usuarios se registran, inician sesión y guardan su perfil gamer en MySQL.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python + Flask |
| Base de datos | MySQL (SQLAlchemy + PyMySQL) |
| Seguridad | Contraseñas con hash (scrypt), sesiones con JWT |
| Base vectorial | ChromaDB |
| Embeddings | sentence-transformers `intfloat/multilingual-e5-small` (local, español + inglés) |
| LLM | Google Gemini |
| Frontend | HTML + CSS + JavaScript (servido por Flask) |
| NLP | nltk (stemming para BM25) y spaCy (NER: enmascarar nombres, red de entidades) |
| Despliegue | Docker: nginx (proxy) + app (Gunicorn) + MariaDB, en redes separadas |
| Pruebas | pytest (51 pruebas) + evaluación RAG con Golden Dataset |

## Estructura de carpetas

```
kira/
├── backend/
│   ├── app.py                   # Inicialización de Flask (punto de entrada)
│   ├── config.py                # Variables de entorno, rutas, llaves de API
│   ├── database.py              # Conexión a MySQL (SQLAlchemy)
│   ├── models/                  # Tablas de la BD
│   │   ├── usuario.py           # Usuario + perfil (consolas, géneros, fecha nac.)
│   │   └── chat.py              # Historial de consultas
│   ├── routes/__init__.py       # Definición de endpoints de la API
│   ├── controllers/             # Manejadores HTTP
│   │   ├── auth_controller.py       # Registrar / Iniciar sesión / Usuario actual
│   │   ├── cuenta_controller.py     # Derechos ARCO: descargar mis datos, eliminar cuenta
│   │   ├── perfil_controller.py     # Guardar perfil gamer
│   │   ├── chat_controller.py       # Consultar a Kira
│   │   └── noticias_controller.py   # Noticias RSS y health
│   ├── middleware/
│   │   ├── auth_middleware.py   # Verificación JWT (@login_requerido)
│   │   └── validacion.py        # Validación de nombre, correo, contraseña, fecha
│   ├── services/                # Lógica de negocio
│   │   ├── usuario_service.py   # Registro, login, perfil, historial
│   │   ├── email_service.py     # Envío del código de verificación (SMTP/Gmail)
│   │   ├── privacidad.py        # Enmascara datos personales antes de enviarlos a Gemini
│   │   ├── imagenes_service.py  # Índice de juegos + portadas Steam/IGDB/RAWG
│   │   └── noticias_service.py  # Feeds RSS gaming
│   ├── agent/                   # 🧠 MÓDULO RAG
│   │   ├── graph.py             # Flujo: retrieve → generate → images
│   │   ├── state.py             # Estado que pasa entre nodos
│   │   ├── prompts.py           # Personalidad de Kira (system prompt)
│   │   ├── perfil_contexto.py   # Personalización según el perfil
│   │   ├── reranking.py         # Re-ranking híbrido (vectores + BM25) y compactación
│   │   ├── nodes/
│   │   │   ├── router.py        # ¿Pregunta genérica? -> pide aclaración con botones
│   │   │   ├── retrieve.py      # Busca en ChromaDB (+ herramientas si hace falta)
│   │   │   ├── generate.py      # Genera la respuesta con Gemini
│   │   │   └── images.py        # Portadas de juegos mencionados
│   │   └── tools/               # Herramientas que el agente puede usar
│   │       ├── __init__.py      # Registro tipo MCP: esquema, validación, auditoría
│   │       └── precios.py       # Precios en vivo: Steam (país), CheapShark, IsThereAnyDeal
│   ├── vectorDb/
│   │   ├── limpieza.py          # Limpieza del texto antes de vectorizar (re)
│   │   ├── ingest.py            # Limpia, trocea y construye la base vectorial
│   │   ├── store.py             # Conexión a ChromaDB + modelo de embeddings
│   │   ├── analisis_nlp.py      # Análisis NLP del corpus (stopwords, frecuencias, stemming)
│   │   ├── red_entidades.py     # NER + red de enlaces entre entidades (laboratorio NLP-2)
│   │   └── calibrar.py          # Sugiere el umbral de distancia para el modelo actual
│   ├── evaluacion/              # Pruebas de calidad y costos
│   │   ├── golden_dataset.json  # 30 preguntas con la respuesta esperada
│   │   ├── evaluar_rag.py       # Context Precision, Hit Rate, Faithfulness, Answer Relevance
│   │   └── costos.py            # Costo mensual: tokens del LLM + embeddings + infraestructura
│   └── scrapers/                # Ingesta: descarga de fichas a data/documentos/
│       ├── steam.py             # Juegos de PC (ficha, requisitos, precio)
│       ├── steam_resenas.py     # Reseñas de usuarios de Steam
│       ├── igdb.py              # Catálogo multiplataforma (IGDB / Twitch)
│       ├── metacritic.py        # Notas y resúmenes de la crítica
│       ├── rawg.py              # Catálogo RAWG
│       ├── pokeapi.py           # Juegos de Pokémon (PokeAPI)
│       └── pokemon_manual.py    # Fichas manuales de Pokémon
├── database/
│   ├── schema.sql               # Script MySQL (crea BD y tablas)
│   └── usuario_app.sql          # Usuario kira_app con privilegio mínimo
├── docker/
│   ├── nginx/kira.conf          # Proxy inverso (única puerta expuesta)
│   └── mariadb-init/            # Crea kira_app al iniciar MariaDB en Docker
├── tests/                       # Pruebas automáticas (pytest)
├── Dockerfile                   # Imagen del backend (multi-etapa, usuario sin root)
├── docker-compose.yml           # nginx + app + db en capas separadas
├── data/
│   ├── documentos/              # Fichas .txt (fuente del RAG)
│   ├── kira_db/                 # Base vectorial ChromaDB (se genera)
│   └── evaluacion/              # Resultados de evaluar_rag.py, costos.py y red_entidades.py
├── frontend/templates/privacidad.html  # Política de privacidad (/privacidad)
├── frontend/
│   ├── templates/index.html     # Interfaz: login, perfil, chat, noticias y arcade
│   ├── static/                  # Logo y avatares
│   │   └── juegos/              # 🎮 Juegos ya listos para el navegador (se generan)
│   └── juegos/                  # 🎮 Código de los juegos del arcade
│       ├── originales/          # Juegos pygame (tenisplay.py, vasitofinal.py)
│       ├── preparar_web.py      # Los convierte para correr dentro del chat
│       └── plantilla_web.html   # Página de carga de cada juego
├── requirements.txt
├── .env.example
└── .gitignore
```

### De dónde salió cada archivo

| Antes | Ahora |
|---|---|
| `Kira.py` (todo junto) | `app.py`, `config.py`, `routes/`, `controllers/chat_controller.py`, `agent/*` |
| `extras_kira.py` | `services/imagenes_service.py` + `services/noticias_service.py` |
| `construir_base.py` | `vectorDb/ingest.py` |
| `descargar steam.py`, `Descargar metacritic consolas.py`, `descargar_rawg.py`, `descargar_poke.py`, `extras/pokemon.py` | `scrapers/` |
| `templates/`, `static/` | `frontend/` |
| `documentos/`, `kira_db/` | `data/` |
| Perfil en `localStorage` | Tabla `usuarios` en MySQL |
| *(no existía)* | Login/registro, JWT, historial de chat |
| *(no existía)* | Verificación del correo con código de 6 dígitos (`services/email_service.py`) |

## API

| Método | Ruta | Login | Descripción |
|---|---|---|---|
| POST | `/api/auth/register` | | Crear cuenta `{nombre, email, password, acepta_privacidad: true}` → envía un código al correo |
| POST | `/api/auth/verificar` | | Confirmar el correo `{email, codigo}` → `{token}` |
| POST | `/api/auth/reenviar` | | Enviar un código nuevo `{email}` (máx. 1 por minuto) |
| POST | `/api/auth/login` | | Iniciar sesión `{email, password}` → `{token}` (solo si el correo está verificado) |
| GET | `/api/auth/me` | ✔ | Usuario actual |
| PUT | `/api/perfil` | ✔ | Guardar perfil `{nombre, fecha_nacimiento, consolas, generos}` |
| POST | `/api/chat` | ✔ | Consultar a Kira `{mensaje}` |
| GET | `/api/chat/historial` | ✔ | Últimas 20 consultas |
| DELETE | `/api/chat/historial` | ✔ | Borrar mi historial (derecho de cancelación) |
| GET | `/api/cuenta/datos` | ✔ | Descargar todos mis datos en JSON (derecho de acceso) |
| DELETE | `/api/cuenta` | ✔ | Eliminar mi cuenta `{password}` (derecho de cancelación) |
| GET | `/privacidad` | | Política de privacidad |
| GET | `/api/noticias` | | Noticias gaming |
| GET | `/api/health` | | Estado del servidor |

## Instalación

📄 **Guía paso a paso con links de descarga: [INSTALACION.md](INSTALACION.md)**

Resumen. Todos los comandos se ejecutan **desde la carpeta `kira/`**.

0. **Carpeta corta:** dejar el proyecto en `C:\kira`, nunca en OneDrive ni en el Escritorio
   (la ruta larga hace fallar la instalación de `torch`).

1. **Entorno virtual y dependencias**
   ```bash
   cd C:\kira
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m spacy download es_core_news_sm
   ```

2. **Base de datos MySQL:** tener MySQL encendido (XAMPP → Start). La base `kira` y sus
   tablas se crean solas al arrancar (`database/schema.sql` queda como referencia).

3. **Variables de entorno:** copiar `.env.example` como `.env` y completar
   `GEMINI_API_KEY`, `RAWG_API_KEY`, `DATABASE_URL` y `JWT_SECRET`.

4. **Base vectorial:** copiar su carpeta `kira_db/` actual dentro de `data/`, o reconstruirla:
   ```bash
   python -m backend.vectorDb.ingest
   ```

5. **Iniciar**
   ```bash
   python -m backend.app
   ```
   Abrir http://localhost:5000

### Descargar más juegos (opcional)
```bash
python -m backend.scrapers.steam
python -m backend.scrapers.metacritic
python -m backend.scrapers.rawg
python -m backend.scrapers.pokeapi
python -m backend.vectorDb.ingest      # siempre después de descargar
```

## Requerimientos

**Funcionales:** Registrar usuario · Iniciar sesión · Completar/editar perfil gamer · Consultar a Kira
(reseñas, requisitos, recomendaciones) · Ver historial · Ver noticias gaming.

**No funcionales (ISO/IEC 25010):**
- *Seguridad:* verificación del correo con código de 6 dígitos (vence en 15 min, máx. 5 intentos),
  contraseñas con hash scrypt, JWT con expiración, perfil tomado del servidor
  (no del navegador), validación en backend, defensa contra prompt injection.
- *Fiabilidad:* si ChromaDB o las APIs externas fallan, el servidor sigue respondiendo con mensajes claros.
- *Mantenibilidad / Flexibilidad:* capas separadas (rutas, controladores, servicios, agente);
  modelo de LLM y parámetros del RAG configurables en `config.py` y `.env`.


## 🧠 Arquitectura RAG (en el orden del pipeline)

| Fase | Qué hace en Kira | Archivos |
|---|---|---|
| 1. Ingesta y procesamiento | Descarga fichas, reseñas y notas desde las fuentes y las limpia | `scrapers/*.py`, `vectorDb/limpieza.py` |
| 2. Chunking | Fragmentos por sección (descripción, reseñas, requisitos...) con solapamiento y la cabecera del juego; metadatos por fragmento | `vectorDb/ingest.py` |
| 3. Vectorización | Embeddings multilingües (`multilingual-e5-small`) | `vectorDb/store.py`, `vectorDb/ingest.py` |
| 4. Almacenamiento | ChromaDB local (distancia coseno) | `data/kira_db/` |
| 5. Recuperación | Detecta el juego (aunque esté mal escrito), trae 20 candidatos (sus fragmentos + búsqueda semántica), los reordena con re-ranking híbrido y deja los 5 mejores; si pregunta precios, usa la herramienta en vivo | `agent/nodes/router.py`, `agent/nodes/retrieve.py`, `agent/reranking.py`, `agent/tools/` |
| 6. Generación | Prompt con contexto + perfil + historial, **con los datos personales enmascarados**, enviado a Gemini; se registran los tokens usados | `agent/nodes/generate.py`, `agent/prompts.py`, `services/privacidad.py` |

**Qué va a la base vectorial y qué se consulta en vivo.** Lo que cambia poco (descripciones,
géneros, notas, reseñas) se guarda en ChromaDB con la ingesta. Los precios cambian a diario,
así que no se guardan: la herramienta `agent/tools/precios.py` los consulta en el momento en
que se pregunta "¿cuánto cuesta X?" (fase 4 del PPT: obsolescencia de los datos).

### Fuentes de datos

| Fuente | Aporta | Clave en `.env` | Comando |
|---|---|---|---|
| Steam | Juegos de PC: ficha, requisitos | no | `python -m backend.scrapers.steam` |
| Reseñas de Steam | Opiniones de usuarios y valoración (% positivas) | no | `python -m backend.scrapers.steam_resenas` |
| IGDB | Catálogo de todas las plataformas: resumen, historia, géneros, nota de crítica y usuarios, juegos parecidos, portada | `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET` | `python -m backend.scrapers.igdb` |
| Metacritic | Nota y resumen de la crítica | no | `python -m backend.scrapers.metacritic` |
| RAWG | Catálogo y nota | `RAWG_API_KEY` | `python -m backend.scrapers.rawg` |
| PokeAPI | Juegos de Pokémon | no | `python -m backend.scrapers.pokeapi` |
| Precios en vivo | Steam en tu país, tiendas de PC (CheapShark), mínimos históricos | `ITAD_API_KEY` (opcional), `PAIS_PRECIOS` | automático en el chat |

Después de cualquier scraper: `python -m backend.vectorDb.ingest`.

## 🧹 Limpieza y preprocesamiento antes de vectorizar

Antes de generar los embeddings, `ingest.py` pasa cada documento por `limpieza.py`:

| Paso | Qué hace | Ejemplo |
|---|---|---|
| Normalización Unicode | Unifica tildes, quita espacios invisibles | `\u00a0`, `\u200b` |
| HTML / BBCode | Decodifica entidades y borra etiquetas | `&quot;` → `"`, `<br/>`, `[b]` |
| Ruido del scraping | Quita colas de Metacritic | `Summary …`, `… Read More Adventure Developer: …` |
| Símbolos y URLs | Borra lo que no aporta significado | `®`, `™`, emojis, `https://…` (la URL pasa a metadato) |
| Palabras pegadas | Separa palabras unidas al perder un salto de línea | `construirloConstruye` → `construirlo. Construye` |
| Duplicados | Borra secciones y párrafos repetidos | resumen igual a la descripción |
| Secciones vacías | Descarta requisitos sin contenido | `REQUISITOS MÍNIMOS (MAC): Mínimo:` |
| Espacios | Colapsa espacios y líneas en blanco | |

Luego se trocea **por secciones** (descripción, reseña, requisitos), respetando oraciones,
con solapamiento, y cada fragmento lleva la cabecera `Juego: X | Plataforma: Y` para que no
pierda de qué juego habla. Cada fragmento guarda metadatos (`juego`, `plataforma`, `origen`,
`generos`, `fecha`, `nota_metacritic`, `url`).

**Por qué no se usan minúsculas, stopwords ni stemming en el texto que se vectoriza:** el
modelo de embeddings entiende frases completas ("no me gustó" ≠ "me gustó") y el mismo texto
es el que lee el LLM para responder. Esas técnicas se usan en `analisis_nlp.py` para estudiar
el corpus.

Resultado sobre los 3979 documentos: **21,6% menos caracteres de ruido** y fragmentos que caben
en el límite de tokens del modelo (con el modelo y tamaño anteriores el 52% se cortaba).

```bash
python -m backend.vectorDb.ingest --revisar   # ver la limpieza sin vectorizar
python -m backend.vectorDb.ingest             # limpiar + vectorizar (recrea data/kira_db)
python -m backend.vectorDb.analisis_nlp       # estadísticas NLP del corpus
```

## 🌎 Búsqueda multilingüe y tolerante a errores

**Modelo multilingüe.** La base está 95% en inglés y los usuarios preguntan en español. Se usa
`intfloat/multilingual-e5-small`, que pone ambos idiomas en el mismo espacio vectorial (una
pregunta en español queda cerca de la reseña en inglés) y lee hasta 512 tokens por fragmento.
Los modelos E5 necesitan el prefijo `query: ` en las preguntas y `passage: ` en los documentos
(lo agrega `store.py`). La colección usa distancia coseno y guarda el nombre del modelo: si se
cambia el modelo sin reconstruir la base, el servidor lo avisa al arrancar.

**Nombres mal escritos.** Antes de buscar, se detectan los juegos nombrados comparando el mensaje
con los 2528 títulos del índice:

| Escribe | Kira entiende |
|---|---|
| `asassins creed shadow` | Assassin's Creed Shadows |
| `elden rign` | ELDEN RING |
| `god of war ragnarock vale la pena?` | God of War: Ragnarok |
| `hollow knigth con celestte` | Hollow Knight y Celeste |
| `dark souls 3` | Dark Souls III |
| `zelda breath of the wild` | The Legend of Zelda: Breath of the Wild |

1. Normalización: minúsculas, sin tildes, apóstrofos ni plurales, romanos como números.
2. Coincidencia exacta con el índice; si no hay, similitud de texto con `rapidfuzz`
   (distancia de edición, mínimo 88/100; 92 para títulos de una palabra).
3. Con el juego identificado, la búsqueda trae primero sus fragmentos (filtro por el metadato
   `juego_clave`) y completa con la búsqueda semántica normal (búsqueda híbrida).
4. Al LLM se le indica el nombre correcto del juego.

Probado con 25 preguntas comunes sin nombres de juegos: 0 falsos positivos.

```bash
python -m backend.vectorDb.calibrar   # después de la ingesta: sugiere UMBRAL_DISTANCIA_MAXIMA
```

## 🎮 Arcade: juegos dentro del chat

En la página del chat hay un botón **🎮 Juegos** (también el atajo “Jugar con Kira” del
saludo, o escribir “quiero jugar”). Se abre un panel dentro de la misma tarjeta del chat
donde eliges el juego y se juega ahí mismo; con **💬 Volver al chat** sigues la conversación.

| Juego | Archivo original |
|---|---|
| Tenis retro vs Kira | `frontend/juegos/originales/tenisplay.py` |
| ¿Dónde está la mascota? | `frontend/juegos/originales/vasitofinal.py` |

**Cómo funciona:** los juegos son pygame (Python). Para que corran en el navegador se usan con
[pygbag](https://pygame-web.github.io/) (Python compilado a WebAssembly). Todo lo necesario
está en `frontend/static/juegos/runtime/`, así que no dependen de ningún sitio externo.
Los récords se guardan en el navegador (localStorage).

**Si modificas un juego**, edita el archivo en `frontend/juegos/originales/` y vuelve a empaquetar:

```bash
python frontend/juegos/preparar_web.py
```

Los originales siguen funcionando en escritorio: `python frontend/juegos/originales/tenisplay.py`.

## 🎯 Re-ranking híbrido y ahorro de tokens

La búsqueda solo por vectores a veces trae fragmentos que "suenan parecido" pero no responden.
Por eso la recuperación tiene dos etapas (`agent/reranking.py`):

1. ChromaDB trae **20 candidatos** (los del juego nombrado más los semánticos bajo el umbral).
2. Cada candidato recibe un puntaje: `0,6 × semántico + 0,4 × BM25`. BM25 es la búsqueda por
   palabras exactas; para calcularla se usan las técnicas del laboratorio de NLP (minúsculas,
   tokens, stopwords y stemming, así "requisito" y "requisitos" cuentan igual).
3. Pasan solo los **5 mejores**, sin fragmentos repetidos por el solapamiento y con un tope de
   5.000 caracteres.

Antes se mandaban 8 fragmentos sin reordenar. Ahora el prompt lleva menos texto, y cada
respuesta guarda los tokens reales que informa Gemini (`historial_chat.tokens_entrada` y
`tokens_salida`).

## 🔒 Privacidad (Ley 19.628 y Ley 21.719)

| Medida | Dónde |
|---|---|
| **Enmascaramiento de PII antes de Gemini:** RUT, correos, teléfonos, tarjetas e IP con regex; nombres de personas con NER de spaCy; el nombre del usuario pasa como `[USUARIO]` y se restaura al volver. Los personajes de juegos (Mario, Kratos) no se tocan | `services/privacidad.py`, `agent/nodes/generate.py` |
| **Minimización:** a Gemini no se envía el correo, la fecha de nacimiento ni la edad exacta (solo un tramo) | `agent/perfil_contexto.py` |
| **Consentimiento informado:** casilla obligatoria al registrarse y fecha guardada (`acepta_privacidad_en`) | `index.html`, `auth_controller.py` |
| **Derechos ARCO:** descargar mis datos, corregir el perfil, borrar historial y eliminar cuenta | `cuenta_controller.py`, modal de perfil |
| **Retención:** el historial se borra solo a los 180 días (`RETENCION_HISTORIAL_DIAS`) | `usuario_service.purgar_historial_antiguo` |
| **Privilegio mínimo en la base:** usuario `kira_app` con solo SELECT, INSERT, UPDATE, DELETE | `database/usuario_app.sql` |
| **Privilegio mínimo en herramientas:** esquema validado, solo lectura, lista blanca de dominios, sin datos del usuario, registro de cada llamada | `agent/tools/__init__.py`, `precios.py` |
| **No entrenamiento:** en el plan gratuito de la API de Gemini, Google puede usar los mensajes para mejorar sus productos; en el plan pagado no. En producción se debe usar el plan pagado | `.env` (clave de un proyecto con facturación) |

## 🧪 Pruebas y evaluación

```bash
python -m pytest -v                                   # 51 pruebas, sin internet ni MySQL
python -m backend.evaluacion.evaluar_rag              # recuperación (gratis)
python -m backend.evaluacion.evaluar_rag --con-llm    # también respuestas (usa Gemini)
```

| Prueba | Qué verifica |
|---|---|
| `test_chunking.py` | Fragmentos que no superan el tamaño, con solapamiento, sin cortar palabras |
| `test_reranking.py` | BM25, re-ranking, compactación y recuperación en dos etapas |
| `test_herramientas.py` | Tool calling: esquema JSON, argumentos inválidos rechazados, caídas de API (500 y timeout) con mocks, lista blanca de dominios |
| `test_privacidad.py` | Que el prompt que sale a Gemini no lleve RUT, correo, nombre ni fecha de nacimiento |
| `test_api_privacidad.py` | Consentimiento, exportar datos, borrar historial, eliminar cuenta, tokens guardados |
| `test_nlp.py` | Normalización de entidades e idioma (red de entidades) |

`evaluar_rag.py` usa `golden_dataset.json` (20 preguntas sobre juegos, 7 por tema y 3 fuera del
dominio) y calcula **Context Precision**, **Hit Rate**, **rechazo fuera de dominio**,
**Faithfulness** (Gemini como juez revisa cada afirmación contra el contexto) y **Answer Relevance**.
Guarda el detalle en `data/evaluacion/` (JSON y CSV para Excel).

## 💰 Costos

```bash
python -m backend.evaluacion.costos                        # estimación por tamaño del prompt
python -m backend.evaluacion.costos --desde-evaluacion     # tokens medidos en la evaluación
python -m backend.evaluacion.costos --desde-bd             # tokens reales de las consultas
```

Calcula, para 1.000 usuarios × 10 consultas al día (como el ejemplo del profe), el costo de
tokens de entrada y salida de Gemini, lo que costarían los embeddings si fueran por API (en
Kira son locales y gratis) y la infraestructura del servidor.

## 🕸️ Red de entidades (NLP)

```bash
python -m spacy download en_core_web_sm      # el corpus está casi todo en inglés
python -m backend.vectorDb.red_entidades
```

Como en el laboratorio del Quijote: detecta personajes y estudios con spaCy, une variantes
("Geralt" → "Geralt of Rivia") y crea una red con **enlaces** entre las entidades que aparecen en
el mismo documento. Genera `data/evaluacion/red_entidades.png` y `.gexf` (se abre con Gephi).

## 🐳 Despliegue con Docker

```
Internet ──► nginx (puerto 80/443) ──► app (Gunicorn + Flask + RAG) ──► db (MariaDB)
             red "publica"              redes "publica" y "datos"      red "datos" (interna)
```

1. Instalar [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. En el `.env` completar también `MARIADB_ROOT_PASSWORD` y `KIRA_DB_APP_PASSWORD`.
3. Copiar la base vectorial en `data/kira_db/`.
4. `docker compose up --build -d` y abrir http://localhost

Cada capa va en su propio contenedor. La app corre sin root y se conecta a la base con `kira_app`.
MariaDB no tiene puertos expuestos ni salida a internet, y solo nginx recibe tráfico de afuera
(con límite de 20 consultas por minuto por IP al chat).
