# Guía de instalación — Kira IA

Guía para dejar Kira funcionando en un computador **Windows** desde cero.
Tiempo aproximado: 20–30 minutos (la mayor parte es esperar descargas).

---

## 1. Qué descargar

Todo es **gratis**.

| # | Programa | Para qué sirve | Link |
|---|---|---|---|
| 1 | **Python 3.11** | Ejecutar el backend | https://www.python.org/downloads/release/python-3119/ → *Windows installer (64-bit)* |
| 2 | **XAMPP** | Base de datos MySQL (usuarios, perfiles, historial) | https://www.apachefriends.org/es/download.html → *XAMPP para Windows* |
| 3 | **Visual Studio Code** *(opcional)* | Abrir y editar el proyecto | https://code.visualstudio.com/ |

Además, cada uno necesita una **API key** (también gratis):

| Key | Para qué | Dónde se obtiene |
|---|---|---|
| **GEMINI_API_KEY** *(obligatoria)* | Que Kira genere respuestas | https://aistudio.google.com/apikey → *Create API key* (con cuenta Google) |
| **RAWG_API_KEY** *(opcional)* | Portadas de juegos de consola | https://rawg.io/apidocs → *Get API Key* |

> Si no quieren sacar keys propias, pídanselas a quien ya las tiene, **por mensaje privado**. Nunca las suban a GitHub ni al grupo del curso.

---

## 2. Instalar Python

1. Abran el instalador de Python.
2. ⚠️ **Marquen la casilla `Add python.exe to PATH`** (abajo, en la primera pantalla). Si se la saltan, nada de lo que sigue va a funcionar.
3. Presionen **Install Now**.
4. Para comprobar, abran **PowerShell** (menú Inicio → escribir *PowerShell*) y ejecuten:
   ```powershell
   python --version
   ```
   Debe decir `Python 3.11.x`.

---

## 3. Instalar y encender MySQL (XAMPP)

1. Abran el instalador de XAMPP. Si sale un aviso del antivirus o del *Control de cuentas de usuario*, pongan **Sí / Aceptar**.
2. Dejen todo por defecto (carpeta `C:\xampp`) y presionen *Next* hasta terminar.
3. Abran el **XAMPP Control Panel**.
4. En la fila **MySQL** presionen **Start**. Debe quedar en **verde** con `Port(s): 3306`.
   Si Windows pregunta por el firewall → **Permitir acceso**.

> Cada vez que quieran usar Kira, **MySQL tiene que estar encendido en XAMPP**.

---

## 4. Preparar el proyecto

1. Descompriman `kira.zip` en **`C:\kira`** (que dentro de `C:\kira` queden directamente `backend`, `frontend` y `data`).
   ⚠️ **No lo dejen en el Escritorio, en Documentos ni en OneDrive.** Esas rutas son muy largas y la instalación de `torch` falla con `OSError: [Errno 2] No such file or directory ... HINT: ... Long Path support`. Además OneDrive bloquea archivos mientras sincroniza.
2. Abran PowerShell y entren a la carpeta:
   ```powershell
   cd C:\kira
   ```
3. Comprueben que están en la carpeta correcta:
   ```powershell
   dir
   ```
   Tienen que aparecer `backend`, `frontend`, `data`, `database` y `README.md`. Si solo ven otra carpeta `kira`, el zip quedó una carpeta más adentro: muevan su contenido a `C:\kira`.
4. Creen y activen un **entorno virtual** (una carpeta `.venv` con las librerías solo de este proyecto):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   Si sale un error de *ejecución de scripts deshabilitada*, ejecuten esto y repitan la última línea:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```
   Funcionó si la línea empieza con `(.venv) PS C:\kira>`.
   > **Cada vez** que abran una ventana nueva de PowerShell para usar Kira tienen que repetir `cd C:\kira` y `.\.venv\Scripts\Activate.ps1`. Si no, sale `No module named 'flask'`.
5. Instalen las librerías (tarda varios minutos, `torch` pesa bastante):
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
6. Descarguen el modelo de español de spaCy (detecta nombres de personas para ocultarlos antes de enviar los mensajes a Gemini):
   ```powershell
   python -m spacy download es_core_news_sm
   ```
   Si este paso falla, Kira funciona igual: oculta RUT, correos, teléfonos y tarjetas con expresiones regulares, pero no detecta nombres sueltos.

---

## 5. Crear el archivo `.env` (configuración)

El programa lee su configuración de un archivo llamado **exactamente `.env`** (no `.env.example`, no `.env.txt`).

1. Créenlo desde la plantilla:
   ```powershell
   copy .env.example .env
   ```
2. Ábranlo:
   ```powershell
   notepad .env
   ```
3. Completen estas líneas:
   ```env
   GEMINI_API_KEY=su_key_de_gemini
   RAWG_API_KEY=su_key_de_rawg_o_vacío
   DATABASE_URL=mysql+pymysql://root:@localhost:3306/kira
   JWT_SECRET=texto_largo_aleatorio
   ```
   - `DATABASE_URL` se deja **tal cual** si usan XAMPP (el usuario `root` no tiene clave).
   - Para `JWT_SECRET`, generen uno con este comando y peguen el resultado:
     ```powershell
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
4. Guarden con **Ctrl + S** y cierren.

### 5.1 (Recomendado) Usuario de MySQL con privilegio mínimo

Con `root` la aplicación puede hacer cualquier cosa en MySQL. Lo correcto es que use un usuario que solo pueda leer y escribir filas de la base `kira`:

1. Arranquen Kira una vez con `root` para que se creen las tablas (paso 8), y deténganla.
2. Abran `database/usuario_app.sql` con el Bloc de notas y cambien `CAMBIA_ESTA_CLAVE` por una clave propia (solo letras y números).
3. En XAMPP presionen **Shell** y ejecuten (ajusten la ruta a donde está su carpeta):
   ```
   mysql -u root < C:\Users\SU_USUARIO\Desktop\kira\database\usuario_app.sql
   ```
4. En el `.env` cambien la conexión:
   ```env
   DATABASE_URL=mysql+pymysql://kira_app:SU_CLAVE@localhost:3306/kira
   ```

---

## 6. Correo para verificar cuentas (Gmail)

Al registrarse, Kira envía un **código de 6 dígitos** al correo de la persona. La cuenta solo se activa cuando ese código se ingresa, así se confirma que el correo existe y que es suyo.

Para enviar esos correos se necesita **una cuenta de Gmail que haga de remitente**. Recomendamos crear una solo para el proyecto (por ejemplo `kira.ia.proyecto@gmail.com`), no usar la personal.

1. En esa cuenta, activen la **verificación en 2 pasos**: https://myaccount.google.com/security → «Verificación en 2 pasos»
   (sin esto, Google no deja crear contraseñas de aplicación).
2. Creen una **contraseña de aplicación**: https://myaccount.google.com/apppasswords
   - Nombre de la app: `Kira IA` → **Crear**.
   - Google muestra una clave de 16 letras (ej. `abcd efgh ijkl mnop`). Cópienla; solo se muestra una vez.
3. Agréguenla al `.env`:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USUARIO=kira.ia.proyecto@gmail.com
   SMTP_CLAVE=abcd efgh ijkl mnop
   ```
   ⚠️ `SMTP_CLAVE` es la **contraseña de aplicación**, no la contraseña normal de Gmail.

> **Modo de prueba sin correo:** si dejan `SMTP_USUARIO` vacío, el código no se envía: aparece en la consola donde corre `python -m backend.app`, en una línea `[MODO DESARROLLO] … código para … → 123456`. Sirve para probar, pero así no se comprueba que el correo exista.

**Cómo funciona para el usuario:**
- Se registra → ve la pantalla «Verifica tu correo» → escribe el código que le llegó.
- El código vence en **15 minutos** y permite **5 intentos**; con «Reenviar código» se pide otro (máximo uno por minuto).
- Si el servidor de correo responde que la casilla no existe, el registro se rechaza con «Ese correo no existe». Con Gmail esto no siempre ocurre al instante (a veces el rebote llega después), pero en ese caso el código nunca llega y la cuenta **no se puede usar**.
- Las cuentas creadas antes de este cambio deben verificar su correo la próxima vez que inicien sesión (el código se envía solo al intentar entrar).

---

## 7. Base de conocimiento de Kira (`kira_db`)

Kira responde usando una base vectorial que **no viene en el zip** (pesa ~130 MB). Hay dos opciones:

- **A (rápida):** pedir la carpeta `kira_db` a quien la tenga y copiarla dentro de `data\`, para que quede `data\kira_db\`.
- **B (la generan ustedes):** ejecutar lo siguiente (la primera vez descarga un modelo de ~90 MB y tarda unos minutos):
  ```powershell
  python -m backend.vectorDb.ingest
  ```

---

## 8. Iniciar Kira

Con MySQL encendido en XAMPP:

```powershell
python -m backend.app
```

Deben ver algo así:
```
✓ Conectado a la base de datos: mysql+pymysql://root:***@localhost:3306/kira
✓ Índice de juegos construido: 2528 juegos
 * Running on http://127.0.0.1:5000
```

Abran **http://localhost:5000** en el navegador, creen una cuenta, ingresen el código que les llega al correo y listo.
Para apagar el servidor: **Ctrl + C** en la consola.

> La base `kira` y sus tablas se crean solas la primera vez. Pueden verlas en XAMPP → botón **Admin** de MySQL (phpMyAdmin).

---

## 9. Problemas comunes

| Mensaje en la consola | Qué pasa | Solución |
|---|---|---|
| `No module named 'backend'` | Están en la carpeta equivocada | Vuelvan al paso 4.3: deben estar donde está la carpeta `backend`, no dentro de ella |
| `No existe el archivo .env` o `Falta JWT_SECRET` | Falta el `.env` o está incompleto | Paso 5. Revisen con `dir -Force .env*` que se llame `.env` y no `.env.txt` |
| `No module named 'flask'`, `'sqlalchemy'` (u otra librería) | El entorno virtual no está activado, o están en otra carpeta | `cd C:\kira` y `.\.venv\Scripts\Activate.ps1` (la línea debe empezar con `(.venv) PS C:\kira>`). Si sigue, `python -m pip install -r requirements.txt` |
| `OSError: [Errno 2] No such file or directory ... Long Path support` al instalar | La carpeta del proyecto tiene una ruta demasiado larga (OneDrive, Escritorio) | Muevan el proyecto a `C:\kira` **sin** la carpeta `.venv` y créenla de nuevo (paso 4) |
| `Permission denied: ...\.venv\Scripts\python.exe` | Intentaron crear el `.venv` con otro `.venv` activado | `deactivate` y vuelvan a intentar |
| `'mysql' no se reconoce como nombre de un cmdlet` | Escribieron `mysql` en PowerShell | Úsenlo en XAMPP → **Shell**, o con la ruta completa `C:\xampp\mysql\bin\mysql.exe -u root kira` |
| `MySQL no está encendido o no está instalado` | MySQL apagado | XAMPP Control Panel → **Start** en MySQL |
| `Usuario o contraseña incorrectos` | `DATABASE_URL` mal escrito | Con XAMPP debe ser `mysql+pymysql://root:@localhost:3306/kira` |
| MySQL se pone rojo en XAMPP / `Port 3306 in use` | Otro MySQL ocupa el puerto | Cierren otros programas de bases de datos o reinicien el PC y prueben de nuevo |
| `'python' no se reconoce como un comando` | Python sin PATH | Reinstalen Python marcando **Add python.exe to PATH** |
| `Error cargando ChromaDB` | Falta `data\kira_db` | Paso 7 |
| Kira responde "no pudo responder" | Falta o es inválida la `GEMINI_API_KEY` | Revisen la key en el `.env` |
| `SMTP: usuario o contraseña de aplicación incorrectos` | `SMTP_CLAVE` es la contraseña normal o está mal copiada | Paso 6.2: creen una contraseña de aplicación y péguenla en `SMTP_CLAVE` |
| No llega el código | Está en spam, o el correo está mal escrito | Revisar spam; usar «Usar otro correo» y registrarse de nuevo |
| `[MODO DESARROLLO] … código para …` en la consola | `SMTP_USUARIO` está vacío | Es normal para probar; para enviar correos reales, paso 6 |

---

## Resumen rápido (para cuando ya está todo instalado)

1. Abrir XAMPP → **Start** en MySQL
2. PowerShell:
   ```powershell
   cd C:\kira
   .\.venv\Scripts\Activate.ps1
   python -m backend.app
   ```
3. Navegador → http://localhost:5000

Otros comandos útiles (con el entorno activado):

| Para qué | Comando |
|---|---|
| Pruebas automáticas (no necesitan MySQL encendido) | `python -m pytest -v` |
| Evaluar la calidad del RAG (usa Gemini) | `python -m backend.evaluacion.evaluar_rag --con-llm` |
| Calcular los costos | `python -m backend.evaluacion.costos --desde-evaluacion` |
| Red de entidades (NLP) | `python -m backend.vectorDb.red_entidades` |
| Levantar todo con Docker | `docker compose up --build -d` (ver README) |
