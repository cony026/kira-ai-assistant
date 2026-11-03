import pygame
import random
import os
import math
import json
from array import array

# ============================================================
# INICIAR PYGAME (el mezclador de sonido se configura antes)
# ============================================================
pygame.mixer.pre_init(22050, -16, 1, 256)
pygame.init()

ANCHO = 1000
ALTO = 700
# SCALED: el juego se dibuja a 1000x700 y pygame lo escala solo a la
# ventana o a la pantalla completa (F11), sin deformar ni pixelar.
try:
    pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.SCALED)
except pygame.error:
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Tenis retro vs Kira")

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_RECORDS = os.path.join(CARPETA, "records_tenis.json")

# ============================================================
# COLORES - MISMA PALETA NEON DE LA PAGINA DE KIRA
# ============================================================
FONDO = (10, 7, 18)
PANEL = (22, 16, 36)
LINEA = (179, 122, 255)
NEON_MORADO = (179, 74, 255)
NEON_CIAN = (76, 215, 240)
MORADO_PROFUNDO = (138, 43, 232)
CIAN_PROFUNDO = (16, 168, 204)
TEXTO = (243, 238, 252)
TEXTO_SUAVE = (171, 159, 201)
TEXTO_TENUE = (118, 106, 146)
ROSA_ERROR = (255, 107, 138)
AMARILLO = (255, 210, 90)
VERDE = (110, 255, 170)
BLANCO = (255, 255, 255)

COLOR_JUGADOR = NEON_CIAN
COLOR_CPU = NEON_MORADO
COLOR_SMASH = ROSA_ERROR

# ============================================================
# FUENTES (las mismas de la pagina: Bungee + Chakra Petch)
# ============================================================
def cargar_fuente(nombre_archivo, tam_ttf, tam_defecto):
    for ruta in (
        os.path.join(CARPETA, "fuentes", nombre_archivo),
        os.path.join(CARPETA, nombre_archivo),
    ):
        if os.path.exists(ruta):
            try:
                return pygame.font.Font(ruta, tam_ttf)
            except Exception:
                pass
    return pygame.font.Font(None, tam_defecto)


fuente_titulo = cargar_fuente("Bungee-Regular.ttf", 30, 50)
fuente_grande = cargar_fuente("Bungee-Regular.ttf", 44, 72)
fuente_marcador = cargar_fuente("Bungee-Regular.ttf", 110, 156)
fuente_aviso = cargar_fuente("Bungee-Regular.ttf", 22, 34)
fuente = cargar_fuente("ChakraPetch-Bold.ttf", 30, 42)
fuente_boton = cargar_fuente("ChakraPetch-Bold.ttf", 15, 22)
fuente_pequena = cargar_fuente("ChakraPetch-SemiBold.ttf", 20, 30)
fuente_mini = cargar_fuente("ChakraPetch-SemiBold.ttf", 13, 20)

# ============================================================
# REGLAS Y VELOCIDADES
# ============================================================
OPCIONES_PUNTOS = [5, 7, 11]
DIFERENCIA_PARA_GANAR = 2     # como en el tenis: hay que ganar por 2

VEL_JUGADOR = 560            # pixeles por segundo con teclado
VEL_JUGADOR_MOUSE = 1100     # con el mouse la paleta sigue al cursor

# Dificultad de Kira (la CPU).
#   vel        -> lo mas rapido que puede mover su paleta
#   reaccion   -> cada cuantos segundos corrige hacia donde ir
#   error      -> multiplica que tanto se equivoca al calcular
#   habilidad  -> multiplica que tan seguido usa habilidades
DIFICULTADES = {
    "facil": {"nombre": "FÁCIL", "vel": 300, "reaccion": 0.24,
              "error": 1.45, "habilidad": 0.5},
    "normal": {"nombre": "NORMAL", "vel": 380, "reaccion": 0.16,
               "error": 1.0, "habilidad": 1.0},
    "dificil": {"nombre": "DIFÍCIL", "vel": 470, "reaccion": 0.10,
                "error": 0.7, "habilidad": 1.4},
}
ORDEN_DIFICULTAD = ["facil", "normal", "dificil"]
RONDAS_TORNEO = len(ORDEN_DIFICULTAD)

MODOS = ["1j", "2j", "torneo"]
NOMBRE_MODO = {"1j": "1 JUGADOR", "2j": "2 JUGADORES", "torneo": "TORNEO"}

# Camara lenta en el punto de partido.
ESCALA_CAMARA_LENTA = 0.28   # 0.28 = el tiempo va al 28 %
DISTANCIA_CAMARA_LENTA = 260 # desde que distancia a la paleta se revisa
DURACION_MAX_LENTA = 2.0     # seguridad: nunca dura mas que esto

VEL_PELOTA_INICIAL = 430
AUMENTO_POR_GOLPE = 1.06     # +6% de velocidad en cada golpe
VEL_PELOTA_MAXIMA = 880      # tope normal de la pelota
ANGULO_MAXIMO = math.radians(55)

# Efecto: si la paleta se esta moviendo al golpear, la pelota se dobla
# hacia donde iba la paleta (y el efecto se va apagando solo).
EFECTO_FACTOR = 1.3
EFECTO_MAXIMO = 850
EFECTO_CAIDA = 2.2

TIEMPO_SAQUE = 2.0           # cuenta regresiva antes de cada saque
TIEMPO_PUNTO = 1.0           # pausa despues de cada punto

# ============================================================
# HABILIDADES
# ============================================================
# La energia se gana golpeando la pelota, perdiendo un punto
# (para remontar) o atravesando un orbe de energia con la pelota.
ENERGIA_MAXIMA = 100
ENERGIA_POR_GOLPE = 12
ENERGIA_POR_PUNTO_PERDIDO = 12
ENERGIA_POR_ORBE = 35

VEL_SMASH = 1250             # el smash si puede pasar el tope normal
MULTIPLICADOR_SMASH = 1.65
ACELERACION_CURVA = 1500     # que tan fuerte se dobla la curva
PALA_ALTO_GIGANTE = 156
DURACION_GIGANTE = 7.0
DURACION_ESCUDO = 10.0

# Recarga: segundos que hay que esperar desde que se activa una
# habilidad hasta poder usarla otra vez.
RECARGA = {"smash": 4.0, "curva": 4.0,
           "gigante": DURACION_GIGANTE + 8.0,
           "escudo": DURACION_ESCUDO + 10.0}

HABILIDADES = [
    {"id": "smash", "nombre": "SMASH", "tecla": "1", "tecla2": "7",
     "costo": 60, "desc": "Tu próximo golpe sale disparado, muchísimo "
                          "más rápido."},
    {"id": "curva", "nombre": "CURVA", "tecla": "2", "tecla2": "8",
     "costo": 45, "desc": "Tu próximo golpe se dobla en el aire. "
                          "A Kira le cuesta leerlo."},
    {"id": "gigante", "nombre": "GIGANTE", "tecla": "3", "tecla2": "9",
     "costo": 40, "desc": "Tu paleta crece durante 7 segundos."},
    {"id": "escudo", "nombre": "ESCUDO", "tecla": "4", "tecla2": "0",
     "costo": 75, "desc": "Un muro de luz te salva una pelota "
                          "(dura 10 segundos)."},
]
COSTO = {h["id"]: h["costo"] for h in HABILIDADES}

# Jugador 1: teclas 1 2 3 4 (las de arriba de las letras).
TECLAS_HABILIDAD = {
    pygame.K_1: "smash",
    pygame.K_2: "curva",
    pygame.K_3: "gigante",
    pygame.K_4: "escudo",
}
# Jugador 2 (modo 2 jugadores): 7 8 9 0 o el teclado numerico 1 2 3 0.
TECLAS_HABILIDAD_J2 = {
    pygame.K_7: "smash", pygame.K_KP1: "smash",
    pygame.K_8: "curva", pygame.K_KP2: "curva",
    pygame.K_9: "gigante", pygame.K_KP3: "gigante",
    pygame.K_0: "escudo", pygame.K_KP0: "escudo",
}

# ============================================================
# ORBES (aparecen en el medio; la pelota los recoge)
# ============================================================
TIPOS_ORBE = {
    "energia": {"nombre": "ENERGÍA", "color": NEON_CIAN, "peso": 45,
                "desc": "+35 de energía para quien golpeó la pelota."},
    "grande": {"nombre": "PELOTA XL", "color": ROSA_ERROR, "peso": 20,
               "desc": "La pelota crece por 6 segundos."},
    "multi": {"nombre": "MULTIBOLA", "color": AMARILLO, "peso": 20,
              "desc": "Sale una segunda pelota por 6 segundos."},
    "invertir": {"nombre": "INVERTIR", "color": VERDE, "peso": 15,
                 "desc": "El rival mueve su paleta al revés 5 segundos."},
}
ORDEN_ORBES = ["energia", "grande", "multi", "invertir"]
RADIO_ORBE = 16
DURACION_PELOTA_GRANDE = 6.0
DURACION_MULTI = 6.0
DURACION_INVERTIDO = 5.0
MAX_PELOTAS = 3

# ============================================================
# LO QUE DICE KIRA
# ============================================================
FRASES_KIRA = {
    "inicio": ["¡A ver qué tal juegas!", "No me la dejes fácil, ¿ok?",
               "Prepárate, voy en serio."],
    "ronda": ["Subo el nivel. ¿Aguantas?", "Ahora sí me pongo seria."],
    "punto_kira": ["¡Ja! Muy lento.", "Esa no la viste venir.",
                   "Uno más para mí."],
    "punto_tuyo": ["Ok... esa fue buena.", "Hmm, me distraje.",
                   "Suerte de principiante."],
    "habilidad": ["¡Prueba esto!", "¡Toma!", "A ver si atajas esta."],
    "confundida": ["¡Oye! ¿Qué le pasa a mi paleta?", "Eso es trampa..."],
    "presion": ["Todavía no ganas, ¿eh?", "No te emociones."],
    "gana": ["¡Gané! ¿Revancha?", "GG. Practica un poquito más ;)"],
    "pierde": ["Bien jugado... la próxima es mía.",
               "Ok, me ganaste. Por ahora."],
    "campeon": ["¡Me ganaste las tres! Eres increíble."],
}
FRASES_MENU = ["¿Jugamos una?", "Elige la dificultad... si te atreves.",
               "Te espero en la cancha."]

# ============================================================
# AJUSTES Y RECORDS (se guardan en records_tenis.json)
# ============================================================
AJUSTES = {"silencio": False}


def cargar_records():
    records = {"racha_maxima": 0,
               "victorias": {k: 0 for k in ORDEN_DIFICULTAD},
               "torneos": 0, "tutorial_visto": False, "silencio": False}
    try:
        with open(RUTA_RECORDS, encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict):
            records["racha_maxima"] = int(datos.get("racha_maxima", 0))
            records["torneos"] = int(datos.get("torneos", 0))
            records["tutorial_visto"] = bool(datos.get("tutorial_visto"))
            records["silencio"] = bool(datos.get("silencio"))
            victorias = datos.get("victorias", {})
            if isinstance(victorias, dict):
                for k in ORDEN_DIFICULTAD:
                    records["victorias"][k] = int(victorias.get(k, 0))
    except (OSError, ValueError, TypeError):
        pass    # si no existe o esta roto, se parte de cero
    return records


def guardar_records(records):
    try:
        with open(RUTA_RECORDS, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except OSError:
        pass    # sin permiso de escritura: el juego sigue igual

# ============================================================
# SONIDOS 8-BIT (generados por codigo, no necesitan archivos)
# ============================================================
def crear_beep(frecuencia, duracion, volumen=0.22, frecuencia_final=None):
    info = pygame.mixer.get_init()
    if info is None:
        return None
    muestreo, _, canales = info
    muestras = int(muestreo * duracion)
    if frecuencia_final is None:
        frecuencia_final = frecuencia
    datos = array("h")
    fase_onda = 0.0
    for i in range(muestras):
        t = i / muestras
        f = frecuencia + (frecuencia_final - frecuencia) * t
        fase_onda += f / muestreo
        onda = 1 if (fase_onda % 1) < 0.5 else -1
        valor = int(volumen * 32767 * onda * (1 - t))
        for _ in range(canales):
            datos.append(valor)
    return pygame.mixer.Sound(buffer=datos.tobytes())


try:
    SONIDO_PALETA = crear_beep(440, 0.06)
    SONIDO_PARED = crear_beep(240, 0.05)
    SONIDO_PUNTO = crear_beep(880, 0.25)
    SONIDO_CUENTA = crear_beep(620, 0.07, 0.15)
    SONIDO_HABILIDAD = crear_beep(500, 0.16, 0.18, 1100)
    SONIDO_SMASH = crear_beep(220, 0.18, 0.3, 90)
    SONIDO_ESCUDO = crear_beep(1200, 0.14, 0.2, 600)
    SONIDO_ORBE = crear_beep(900, 0.12, 0.18, 1500)
    SONIDO_SIN_ENERGIA = crear_beep(140, 0.08, 0.15)
    SONIDO_LENTO = crear_beep(700, 0.6, 0.16, 120)
    SONIDO_MENU = crear_beep(660, 0.04, 0.12)
except Exception:
    SONIDO_PALETA = SONIDO_PARED = SONIDO_PUNTO = SONIDO_CUENTA = None
    SONIDO_HABILIDAD = SONIDO_SMASH = SONIDO_ESCUDO = None
    SONIDO_ORBE = SONIDO_SIN_ENERGIA = None
    SONIDO_LENTO = SONIDO_MENU = None


def sonar(sonido):
    if sonido is not None and not AJUSTES["silencio"]:
        sonido.play()

# ============================================================
# UTILIDADES GRAFICAS (degradados, desenfoque, resplandor)
# ============================================================
def mezclar(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def desenfocar(superficie, factor=6, pasadas=2):
    w, h = superficie.get_size()
    resultado = superficie
    for _ in range(pasadas):
        chica = pygame.transform.smoothscale(
            resultado, (max(1, w // factor), max(1, h // factor))
        )
        resultado = pygame.transform.smoothscale(chica, (w, h))
    return resultado


def degradado(tam, c1, c2, horizontal=True, a1=255, a2=255):
    w, h = tam
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    largo = w if horizontal else h
    for i in range(largo):
        t = i / max(1, largo - 1)
        color = mezclar(c1, c2, t) + (int(a1 + (a2 - a1) * t),)
        if horizontal:
            pygame.draw.line(sup, color, (i, 0), (i, h - 1))
        else:
            pygame.draw.line(sup, color, (0, i), (w - 1, i))
    return sup


def teñir_forma(forma, relleno):
    resultado = relleno.copy()
    resultado.blit(forma, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return resultado


def resplandor_de(forma, color, margen, alpha=255, factor=6):
    w, h = forma.get_size()
    base = pygame.Surface((w + margen * 2, h + margen * 2), pygame.SRCALPHA)
    base.fill(color + (0,))
    silueta = forma.copy()
    silueta.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    silueta.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    base.blit(silueta, (margen, margen))
    base = desenfocar(base, factor)
    if alpha < 255:
        base.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return base


def orbe(radio, color, alpha_max):
    sup = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
    pasos = 90
    for i in range(pasos):
        t = i / pasos
        r = int(radio * (1 - t))
        a = int(alpha_max * (t ** 1.8))
        pygame.draw.circle(sup, color + (a,), (radio, radio), max(1, r))
    return sup


_cache = {}


def cache(clave, fabrica):
    if clave not in _cache:
        # Los textos que cambian (marcador, energia) se limpian cuando
        # hay demasiados guardados, asi el cache no crece sin fin.
        if isinstance(clave, tuple) and clave[0] == "txt":
            textos = [k for k in _cache
                      if isinstance(k, tuple) and k[0] == "txt"]
            if len(textos) > 300:
                for k in textos:
                    del _cache[k]
        _cache[clave] = fabrica()
    return _cache[clave]


def envolver(texto, fuente_utilizada, ancho):
    # Corta un texto en lineas que quepan en "ancho" pixeles.
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if not actual or fuente_utilizada.size(prueba)[0] <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def fuente_que_cabe(texto, fuentes, ancho):
    for f in fuentes:
        if f.size(texto)[0] <= ancho:
            return f
    return fuentes[-1]

# ============================================================
# DIBUJAR TEXTO
# ============================================================
def render_espaciado(texto, fuente_utilizada, color, espacio=0):
    if espacio == 0:
        return fuente_utilizada.render(texto, True, color)
    letras = [fuente_utilizada.render(c, True, color) for c in texto]
    ancho = sum(l.get_width() for l in letras) + espacio * (len(letras) - 1)
    alto = max(l.get_height() for l in letras)
    sup = pygame.Surface((max(1, ancho), alto), pygame.SRCALPHA)
    x = 0
    for l in letras:
        sup.blit(l, (x, 0))
        x += l.get_width() + espacio
    return sup


def texto_cacheado(texto, fuente_utilizada, color, brillo=None,
                   alpha_brillo=170, espacio=0, alpha=255):
    clave = ("txt", texto, id(fuente_utilizada), color, brillo,
             alpha_brillo, espacio, alpha)

    def fabricar():
        sup = render_espaciado(texto, fuente_utilizada, color, espacio)
        halo = None
        if brillo is not None:
            halo = resplandor_de(sup, brillo, 18, alpha_brillo, 5)
        if alpha < 255:
            sup = sup.copy()
            sup.fill((255, 255, 255, alpha),
                     special_flags=pygame.BLEND_RGBA_MULT)
        return sup, halo

    return cache(clave, fabricar)


def escribir(texto, fuente_utilizada, color, x, y,
             brillo=None, alpha_brillo=170, espacio=0, alpha=255,
             ancla="center"):
    sup, halo = texto_cacheado(texto, fuente_utilizada, color, brillo,
                               alpha_brillo, espacio, alpha)
    rect = sup.get_rect(**{ancla: (x, y)})
    if halo is not None:
        pantalla.blit(halo, halo.get_rect(center=rect.center))
    pantalla.blit(sup, rect)


def escribir_degradado(texto, fuente_utilizada, x, y, espacio=1):
    def fabricar():
        base = render_espaciado(texto, fuente_utilizada, BLANCO, espacio)
        grad = degradado(base.get_size(), NEON_MORADO, NEON_CIAN)
        texto_color = teñir_forma(base, grad)
        halo = resplandor_de(base, NEON_MORADO, 22, 150, 5)
        return texto_color, halo

    sup, halo = cache(("grad", texto, id(fuente_utilizada)), fabricar)
    pantalla.blit(halo, halo.get_rect(midleft=(x - 22, y)))
    pantalla.blit(sup, sup.get_rect(midleft=(x, y)))

# ============================================================
# FONDO: VACIO OSCURO + ORBES DE LUZ QUE FLOTAN
# ============================================================
ORBE_MORADO = orbe(300, NEON_MORADO, 150)
ORBE_CIAN = orbe(300, NEON_CIAN, 130)
# Antes se guardaba una copia cada 4 px (~19 copias de 600 px por orbe,
# unos 60-70 MB). Con pasos de 12 px son 7 copias y se ve igual.
PASO_ORBE_FONDO = 12


def dibujar_fondo(t):
    pantalla.fill(FONDO)

    fase1 = (math.sin(t * math.pi / 16) + 1) / 2
    fase2 = (math.sin(t * math.pi / 16 + math.pi) + 1) / 2

    for sup, f, (bx, by) in (
        (ORBE_MORADO, fase1, (-100, -150)),
        (ORBE_CIAN, fase2, (ANCHO - 480, ALTO - 430)),
    ):
        escala = 1 + 0.12 * f
        tam = int(600 * escala) // PASO_ORBE_FONDO * PASO_ORBE_FONDO
        img = cache(("orbe", id(sup), tam),
                    lambda: pygame.transform.smoothscale(sup, (tam, tam)))
        pantalla.blit(
            img,
            (bx + int(ANCHO * 0.04 * f) - (tam - 600) // 2,
             by + int(ALTO * 0.05 * f) - (tam - 600) // 2)
        )

# ============================================================
# TARJETA DE VIDRIO (como .app-card)
# ============================================================
TARJETA = pygame.Rect(24, 18, ANCHO - 48, ALTO - 36)
ALTO_ENCABEZADO = 96


def forma_tarjeta():
    forma = pygame.Surface(TARJETA.size, pygame.SRCALPHA)
    pygame.draw.rect(forma, (255, 255, 255, 255), forma.get_rect(),
                     border_radius=22)
    return forma


def crear_tarjeta():
    w, h = TARJETA.size
    m = 70
    sup = pygame.Surface((w + m * 2, h + m * 2), pygame.SRCALPHA)

    forma = forma_tarjeta()
    sombra = resplandor_de(forma, (0, 0, 0), m, 120, 8)
    sup.blit(sombra, (0, 14))
    halo = resplandor_de(forma, MORADO_PROFUNDO, m, 55, 8)
    sup.blit(halo, (0, 0))

    cuerpo = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(cuerpo, PANEL + (190,), cuerpo.get_rect(),
                     border_radius=22)

    grad = degradado((w, ALTO_ENCABEZADO), NEON_MORADO, NEON_MORADO,
                     horizontal=False, a1=34, a2=0)
    cuerpo.blit(grad, (0, 0))
    pygame.draw.line(cuerpo, LINEA + (46,), (0, ALTO_ENCABEZADO),
                     (w, ALTO_ENCABEZADO))

    pygame.draw.rect(cuerpo, LINEA + (60,), cuerpo.get_rect(), 1,
                     border_radius=22)

    cuerpo = teñir_forma(forma, cuerpo)
    sup.blit(cuerpo, (m, m))
    return sup, m


SUP_TARJETA, MARGEN_TARJETA = crear_tarjeta()


def dibujar_tarjeta():
    pantalla.blit(
        SUP_TARJETA,
        (TARJETA.x - MARGEN_TARJETA, TARJETA.y - MARGEN_TARJETA)
    )

# ============================================================
# CHIP (como .icon-btn de la pagina)
# ============================================================
def dibujar_chip(rect, borde=LINEA, alpha_borde=60):
    sup = cache(("chip", rect.size, borde, alpha_borde), lambda: _chip(
        rect.size, borde, alpha_borde))
    pantalla.blit(sup, rect)


def _chip(tam, borde, alpha_borde):
    sup = pygame.Surface(tam, pygame.SRCALPHA)
    pygame.draw.rect(sup, (255, 255, 255, 13), sup.get_rect(),
                     border_radius=12)
    pygame.draw.rect(sup, borde + (alpha_borde,), sup.get_rect(), 1,
                     border_radius=12)
    return sup

# ============================================================
# PUNTO DE ESTADO QUE LATE (como .status-dot)
# ============================================================
def dibujar_punto_estado(x, y, t, color):
    pulso = (math.sin(t * 2 * math.pi / 1.8) + 1) / 2
    radio = 3.5 * (0.8 + 0.2 * pulso)
    alpha = int(130 + 125 * pulso)

    halo = cache(("halo_punto", color), lambda: orbe(14, color, 170))
    halo = halo.copy()
    halo.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    pantalla.blit(halo, halo.get_rect(center=(x, y)))
    pygame.draw.circle(pantalla, color, (x, y), max(2, int(radio)))

# ============================================================
# KIRA: IMAGEN, RETRATO Y GLOBO DE TEXTO
# ============================================================
# Donde esta la cara dentro de la imagen (en proporcion al tamaño), para
# recortar el retrato circular.
KIRA_CARA = (0.52, 0.25)
KIRA_LADO_RETRATO = 0.36


def cargar_kira():
    for nombre in ("kira.png", "kira.jpg", "Kira.png"):
        for ruta in (os.path.join(CARPETA, nombre),
                     os.path.join(CARPETA, "imagenes", nombre)):
            if os.path.exists(ruta):
                try:
                    return pygame.image.load(ruta).convert_alpha()
                except pygame.error:
                    pass
    return None


KIRA_IMG = cargar_kira()


def retrato_kira(tam):
    def fabricar():
        m = 6
        mascara = pygame.Surface((tam, tam), pygame.SRCALPHA)
        pygame.draw.circle(mascara, BLANCO, (tam // 2, tam // 2), tam // 2)
        if KIRA_IMG is not None:
            w, h = KIRA_IMG.get_size()
            lado = int(w * KIRA_LADO_RETRATO)
            rect = pygame.Rect(0, 0, lado, lado)
            rect.center = (int(w * KIRA_CARA[0]), int(h * KIRA_CARA[1]))
            rect = rect.clamp(KIRA_IMG.get_rect())
            cara = pygame.transform.smoothscale(
                KIRA_IMG.subsurface(rect), (tam, tam))
        else:
            # Sin imagen: un circulo con una K.
            cara = degradado((tam, tam), NEON_MORADO, MORADO_PROFUNDO,
                             horizontal=False)
            letra = fuente_boton.render("K", True, BLANCO)
            cara.blit(letra, letra.get_rect(center=(tam // 2, tam // 2)))
        cara = teñir_forma(mascara, cara)
        sup = resplandor_de(mascara, NEON_MORADO, m, 190, 4)
        sup.blit(cara, (m, m))
        pygame.draw.circle(sup, NEON_MORADO, (tam // 2 + m, tam // 2 + m),
                           tam // 2, 2)
        return sup

    return cache(("retrato", tam), fabricar)


def crear_kira_menu():
    # Kira de cuerpo entero a la derecha del menu, con los bordes
    # fundidos para que se mezcle con la tarjeta.
    if KIRA_IMG is None:
        return None, (TARJETA.right - 200, TARJETA.y + 200)
    w0, h0 = KIRA_IMG.get_size()
    alto = 640
    ancho = int(w0 * alto / h0)
    if ancho > 480:
        ancho = 480
        alto = int(h0 * ancho / w0)
    img = pygame.transform.smoothscale(KIRA_IMG, (ancho, alto))

    izq, arriba, abajo = 150, 60, 90
    fundido_h = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    fundido_h.fill((255, 255, 255, 255))
    for x in range(min(izq, ancho)):
        pygame.draw.line(fundido_h, (255, 255, 255, int(255 * x / izq)),
                         (x, 0), (x, alto - 1))
    fundido_v = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    fundido_v.fill((255, 255, 255, 255))
    for y in range(arriba):
        pygame.draw.line(fundido_v, (255, 255, 255, int(255 * y / arriba)),
                         (0, y), (ancho - 1, y))
    for y in range(abajo):
        pygame.draw.line(fundido_v, (255, 255, 255, int(255 * y / abajo)),
                         (0, alto - 1 - y), (ancho - 1, alto - 1 - y))
    img.blit(fundido_h, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    img.blit(fundido_v, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    lienzo = pygame.Surface(TARJETA.size, pygame.SRCALPHA)
    ox = TARJETA.width - ancho - 6
    oy = TARJETA.height - alto
    halo = orbe(int(ancho * 0.62), NEON_MORADO, 110)
    lienzo.blit(halo, halo.get_rect(center=(ox + ancho // 2,
                                            oy + alto // 2)))
    lienzo.blit(img, (ox, oy))
    lienzo = teñir_forma(forma_tarjeta(), lienzo)
    cara = (TARJETA.x + ox + int(ancho * KIRA_CARA[0]),
            TARJETA.y + oy + int(alto * KIRA_CARA[1]))
    return lienzo, cara


KIRA_MENU, KIRA_MENU_CARA = crear_kira_menu()


def crear_burbuja(texto, cola, ancho_max=230):
    # Globo de dialogo. cola: "arriba" (apunta al chip de Kira) o
    # "derecha" (apunta a su cara en el menu).
    lineas = [fuente_boton.render(l, True, TEXTO)
              for l in envolver(texto, fuente_boton, ancho_max)]
    w = max(l.get_width() for l in lineas) + 28
    h = sum(l.get_height() for l in lineas) + 18
    m = 16
    sup = pygame.Surface((w + m * 2, h + m * 2), pygame.SRCALPHA)
    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=12)
    sup.blit(resplandor_de(forma, NEON_MORADO, m, 120, 5), (0, 0))

    relleno = FONDO + (235,)
    borde = NEON_MORADO + (210,)
    pygame.draw.rect(sup, relleno, (m, m, w, h), border_radius=12)
    pygame.draw.rect(sup, borde, (m, m, w, h), 1, border_radius=12)
    if cola == "arriba":
        a, punta, b = (m + w - 52, m + 1), (m + w - 40, m - 11), \
            (m + w - 30, m + 1)
    else:
        a, punta, b = (m + w - 1, m + h // 2 - 7), (m + w + 12, m + h // 2), \
            (m + w - 1, m + h // 2 + 7)
    pygame.draw.polygon(sup, relleno, (a, punta, b))
    pygame.draw.line(sup, borde, a, punta)
    pygame.draw.line(sup, borde, punta, b)

    y = m + 9
    for l in lineas:
        sup.blit(l, (m + 14, y))
        y += l.get_height()
    return sup, m

# ============================================================
# CANCHA (red punteada, bordes neon y lineas de TV antigua)
# ============================================================
CANCHA = pygame.Rect(TARJETA.x + 40, TARJETA.y + ALTO_ENCABEZADO + 22,
                     TARJETA.width - 80, 410)


def crear_cancha():
    w, h = CANCHA.size
    sup = pygame.Surface((w, h), pygame.SRCALPHA)

    pygame.draw.rect(sup, (255, 255, 255, 6), sup.get_rect(),
                     border_radius=16)

    # Red central punteada con degradado morado -> cian.
    red = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(16, h - 16, 28):
        color = mezclar(NEON_MORADO, NEON_CIAN, y / h)
        pygame.draw.rect(red, color + (200,), (w // 2 - 3, y, 6, 14),
                         border_radius=2)
    brillo = desenfocar(red, 5)
    sup.blit(brillo, (0, 0))
    red.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
    sup.blit(red, (0, 0))

    # Circulo central tenue.
    pygame.draw.circle(sup, LINEA + (35,), (w // 2, h // 2), 64, 2)

    # Lineas horizontales tipo pantalla CRT (el toque retro).
    for y in range(0, h, 4):
        pygame.draw.line(sup, (0, 0, 0, 34), (0, y), (w, y))

    # Borde de la cancha.
    pygame.draw.rect(sup, LINEA + (70,), sup.get_rect(), 2,
                     border_radius=16)

    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mascara, BLANCO, mascara.get_rect(), border_radius=16)
    return teñir_forma(mascara, sup)


SUP_CANCHA = crear_cancha()


def crear_vineta():
    # Bordes oscuros sobre la cancha mientras dura la camara lenta.
    w, h = CANCHA.size
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(60):
        a = int(150 * (1 - i / 60) ** 2)
        pygame.draw.rect(sup, (20, 6, 30, a), (i, i, w - 2 * i, h - 2 * i),
                         1, border_radius=16)
    return sup


VINETA = crear_vineta()

# ============================================================
# SPRITES: PALETAS, ESCUDO, PELOTA Y ORBES
# ============================================================
PALA_ANCHO = 14
PALA_ALTO = 96
MARGEN_PALA = 26
MARGEN_HALO_PALA = 24


def crear_pala(c1, c2, alto):
    forma = pygame.Surface((PALA_ANCHO, alto), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=7)
    cuerpo = teñir_forma(forma, degradado((PALA_ANCHO, alto), c1, c2,
                                          horizontal=False))
    pygame.draw.rect(cuerpo, (255, 255, 255, 90), (3, 6, 3, alto - 12),
                     border_radius=2)
    sup = resplandor_de(forma, c1, MARGEN_HALO_PALA, 210, 5)
    sup.blit(cuerpo, (MARGEN_HALO_PALA, MARGEN_HALO_PALA))
    return sup


def crear_escudo(color):
    w, h = 8, CANCHA.height - 24
    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=4)
    sup = resplandor_de(forma, color, 26, 230, 4)
    cuerpo = teñir_forma(forma, degradado((w, h), BLANCO, color,
                                          horizontal=False))
    cuerpo.fill((255, 255, 255, 200), special_flags=pygame.BLEND_RGBA_MULT)
    sup.blit(cuerpo, (26, 26))
    return sup


SUP_ESCUDO = {True: crear_escudo(COLOR_JUGADOR),
              False: crear_escudo(COLOR_CPU)}

TAM_PELOTA = 14
TAM_PELOTA_GRANDE = 26
LARGO_ESTELA = 12


def crear_pelota(color, tam):
    forma = pygame.Surface((tam, tam), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(),
                     border_radius=max(3, tam // 5))
    sup = resplandor_de(forma, color, 20, 255, 4)
    sup.blit(forma, (20, 20))
    return sup


def crear_estela(color, tam):
    pasos = []
    for i in range(LARGO_ESTELA):
        t = 1 - i / LARGO_ESTELA
        lado = max(3, int(tam * (0.4 + 0.6 * t)))
        sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.rect(sup, color + (int(160 * t * t),), sup.get_rect(),
                         border_radius=2)
        pasos.append(sup)
    return pasos


SUP_PELOTA = {}
ESTELA = {}
for _color in (COLOR_JUGADOR, COLOR_CPU, COLOR_SMASH):
    for _tam in (TAM_PELOTA, TAM_PELOTA_GRANDE):
        SUP_PELOTA[(_color, _tam)] = crear_pelota(_color, _tam)
        grosor = 1.4 if _color == COLOR_SMASH else 1.0
        ESTELA[(_color, _tam)] = crear_estela(_color, int(_tam * grosor))


def crear_sprite_orbe(tipo):
    tam = 80
    c = tam // 2
    color = TIPOS_ORBE[tipo]["color"]
    sup = pygame.Surface((tam, tam), pygame.SRCALPHA)
    sup.blit(orbe(40, color, 120), (0, 0))
    forma = pygame.Surface((tam, tam), pygame.SRCALPHA)
    r = RADIO_ORBE

    if tipo == "energia":
        figuras = [[(c, c - r), (c + r * 0.8, c), (c, c + r),
                    (c - r * 0.8, c)]]
        c1, c2 = NEON_MORADO, NEON_CIAN
    elif tipo == "multi":
        figuras = []
        for dx, dy in ((-7, -5), (7, 5)):
            figuras.append([(c + dx, c + dy - 11), (c + dx + 9, c + dy),
                            (c + dx, c + dy + 11), (c + dx - 9, c + dy)])
        c1, c2 = AMARILLO, ROSA_ERROR
    elif tipo == "invertir":
        figuras = [[(c, c - r - 2), (c + 10, c - 3), (c - 10, c - 3)],
                   [(c, c + r + 2), (c + 10, c + 3), (c - 10, c + 3)]]
        c1, c2 = VERDE, NEON_CIAN
    else:   # grande
        figuras = None
        c1, c2 = ROSA_ERROR, NEON_MORADO

    if figuras is None:
        pygame.draw.circle(forma, BLANCO, (c, c), r)
    else:
        for puntos in figuras:
            pygame.draw.polygon(forma, BLANCO, puntos)
    sup.blit(teñir_forma(forma, degradado((tam, tam), c1, c2,
                                          horizontal=False)), (0, 0))
    if figuras is None:
        pygame.draw.circle(sup, BLANCO, (c, c), r, 2)
        pygame.draw.circle(sup, BLANCO, (c, c), r - 7, 1)
    else:
        for puntos in figuras:
            pygame.draw.polygon(sup, BLANCO, puntos, 2)
    return sup


SUP_ORBE = {tipo: crear_sprite_orbe(tipo) for tipo in TIPOS_ORBE}

# ============================================================
# BOTONES Y OPCIONES
# ============================================================
def crear_boton(texto, tam, brillo_alpha):
    # Boton principal: degradado morado -> cian con resplandor.
    w, h = tam
    m = 30
    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=12)
    sup = resplandor_de(forma, NEON_MORADO, m, brillo_alpha, 5)
    cuerpo = teñir_forma(forma, degradado((w, h), NEON_MORADO, NEON_CIAN))
    letras = render_espaciado(texto, fuente_pequena, FONDO, 2)
    cuerpo.blit(letras, letras.get_rect(center=(w // 2, h // 2 + 1)))
    sup.blit(cuerpo, (m, m))
    return sup


def crear_opcion(texto, tam, estado):
    # Opcion de menu. estado: "sel", "hover", "normal" o "off".
    w, h = tam
    m = 20
    sup = pygame.Surface((w + m * 2, h + m * 2), pygame.SRCALPHA)
    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=12)
    if estado == "sel":
        sup.blit(resplandor_de(forma, NEON_MORADO, m, 170, 5), (0, 0))
        cuerpo = teñir_forma(forma, degradado((w, h), NEON_MORADO,
                                              NEON_CIAN))
        color_txt = FONDO
    else:
        cuerpo = pygame.Surface((w, h), pygame.SRCALPHA)
        relleno = {"hover": 22, "normal": 12, "off": 4}[estado]
        borde = {"hover": NEON_CIAN + (170,), "normal": LINEA + (80,),
                 "off": LINEA + (30,)}[estado]
        pygame.draw.rect(cuerpo, (255, 255, 255, relleno),
                         cuerpo.get_rect(), border_radius=12)
        pygame.draw.rect(cuerpo, borde, cuerpo.get_rect(), 1,
                         border_radius=12)
        color_txt = TEXTO_TENUE if estado == "off" else TEXTO
    # Si el texto no cabe con la fuente normal, usa una mas chica.
    letras = render_espaciado(texto, fuente_pequena, color_txt, 2)
    if letras.get_width() > w - 16:
        letras = render_espaciado(texto, fuente_boton, color_txt, 1)
    cuerpo.blit(letras, letras.get_rect(center=(w // 2, h // 2 + 1)))
    sup.blit(cuerpo, (m, m))
    return sup


def dibujar_boton_principal(rect, texto, resaltado=False):
    hover = resaltado or rect.collidepoint(pygame.mouse.get_pos())
    sup = cache(("boton", texto, rect.size, hover),
                lambda: crear_boton(texto, rect.size, 255 if hover else 120))
    pantalla.blit(sup, sup.get_rect(center=(rect.centerx,
                                            rect.centery - (2 if hover
                                                            else 0))))


def dibujar_opcion(rect, texto, seleccionada, apagada=False):
    if seleccionada:
        estado = "sel"
    elif apagada:
        estado = "off"
    elif rect.collidepoint(pygame.mouse.get_pos()):
        estado = "hover"
    else:
        estado = "normal"
    sup = cache(("opcion", texto, rect.size, estado),
                lambda: crear_opcion(texto, rect.size, estado))
    pantalla.blit(sup, (rect.x - 20, rect.y - 20))


def dibujar_panel_mensaje(alto, centro_y, ancho=560):
    # Panel oscuro detras de los mensajes grandes.
    tam = (ancho, alto)

    def fabricar():
        forma = pygame.Surface(tam, pygame.SRCALPHA)
        pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=18)
        sup = resplandor_de(forma, MORADO_PROFUNDO, 30, 70, 6)
        cuerpo = pygame.Surface(tam, pygame.SRCALPHA)
        pygame.draw.rect(cuerpo, FONDO + (225,), cuerpo.get_rect(),
                         border_radius=18)
        pygame.draw.rect(cuerpo, LINEA + (60,), cuerpo.get_rect(), 1,
                         border_radius=18)
        sup.blit(cuerpo, (30, 30))
        return sup

    sup = cache(("panel_msj", tam), fabricar)
    pantalla.blit(sup, sup.get_rect(center=(ANCHO // 2, centro_y)))

# ============================================================
# POSICIONES FIJAS (menu, tutorial, pantalla final, barra inferior)
# ============================================================
_cx, _cy = ANCHO // 2, CANCHA.centery

# Pantalla final.
RECT_BOTON = pygame.Rect(0, 0, 240, 52)
RECT_BOTON.center = (_cx - 110, _cy + 92)
RECT_MENU = pygame.Rect(0, 0, 160, 52)
RECT_MENU.center = (_cx + 140, _cy + 92)

# Menu de inicio: columna izquierda (Kira ocupa la derecha).
COL_X = 290
Y_FILA = {"modo": 236, "dificultad": 316, "puntos": 396, "jugar": 466}
FILAS_MENU = ["modo", "dificultad", "puntos", "jugar"]

RECT_MODO = {}
for _i, _m in enumerate(MODOS):
    RECT_MODO[_m] = pygame.Rect(0, 0, 150, 46)
    RECT_MODO[_m].center = (COL_X + (_i - 1) * 158, Y_FILA["modo"])
RECT_DIF = {}
for _i, _clave in enumerate(ORDEN_DIFICULTAD):
    RECT_DIF[_clave] = pygame.Rect(0, 0, 150, 42)
    RECT_DIF[_clave].center = (COL_X + (_i - 1) * 158, Y_FILA["dificultad"])
RECT_PTS = {}
for _i, _p in enumerate(OPCIONES_PUNTOS):
    RECT_PTS[_p] = pygame.Rect(0, 0, 100, 42)
    RECT_PTS[_p].center = (COL_X + (_i - 1) * 112, Y_FILA["puntos"])
RECT_JUGAR = pygame.Rect(0, 0, 240, 52)
RECT_JUGAR.center = (COL_X, Y_FILA["jugar"])
RECT_RECORDS = pygame.Rect(0, 0, 470, 112)
RECT_RECORDS.midtop = (COL_X, 514)

# Tutorial.
RECT_ENTENDIDO = pygame.Rect(0, 0, 240, 52)
RECT_ENTENDIDO.center = (_cx, 624)

# Barra de habilidades (abajo de la cancha, una mitad por lado).
ANCHO_MITAD = (CANCHA.width - 24) // 2
Y_ENERGIA = CANCHA.bottom + 18
Y_SLOTS = CANCHA.bottom + 64
SEPARACION_SLOT = 8
ANCHO_SLOT = (ANCHO_MITAD - 3 * SEPARACION_SLOT) // 4
ALTO_SLOT = 46
MARGEN_SLOT = 16


def crear_relleno_energia(c1, c2):
    forma = pygame.Surface((ANCHO_MITAD, 8), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=4)
    sup = resplandor_de(forma, c1, 14, 200, 4)
    sup.blit(teñir_forma(forma, degradado((ANCHO_MITAD, 8), c1, c2)),
             (14, 14))
    return sup


RELLENO_ENERGIA = {True: crear_relleno_energia(CIAN_PROFUNDO, NEON_CIAN),
                   False: crear_relleno_energia(MORADO_PROFUNDO,
                                                NEON_MORADO)}


def _fondo_energia():
    sup = pygame.Surface((ANCHO_MITAD, 8), pygame.SRCALPHA)
    pygame.draw.rect(sup, (255, 255, 255, 18), sup.get_rect(),
                     border_radius=4)
    return sup


def crear_slot(hab, estado, color, tecla):
    # estado: "lista", "sin_energia", "recarga" o "activa"
    w, h = ANCHO_SLOT, ALTO_SLOT
    m = MARGEN_SLOT
    sup = pygame.Surface((w + m * 2, h + m * 2), pygame.SRCALPHA)
    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=11)

    if estado == "activa":
        sup.blit(resplandor_de(forma, color, m, 230, 4), (0, 0))
        cuerpo = teñir_forma(forma, degradado((w, h), NEON_MORADO,
                                              NEON_CIAN))
        color_txt, color_tecla = FONDO, FONDO
        fondo_tecla = (255, 255, 255, 90)
    else:
        lista = estado == "lista"
        cuerpo = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(cuerpo, (255, 255, 255, 16 if lista else 6),
                         cuerpo.get_rect(), border_radius=11)
        pygame.draw.rect(cuerpo, (color if lista else LINEA)
                         + (170 if lista else 40,),
                         cuerpo.get_rect(), 1, border_radius=11)
        color_txt = TEXTO if lista else TEXTO_TENUE
        color_tecla = color if lista else TEXTO_TENUE
        fondo_tecla = (255, 255, 255, 22 if lista else 8)
        if lista:
            sup.blit(resplandor_de(forma, color, m, 70, 4), (0, 0))

    x_texto = 10
    if tecla:
        caja = pygame.Rect(7, (h - 22) // 2, 22, 22)
        pygame.draw.rect(cuerpo, fondo_tecla, caja, border_radius=6)
        letra = fuente_boton.render(tecla, True, color_tecla)
        cuerpo.blit(letra, letra.get_rect(center=caja.center))
        x_texto = 35

    nombre = render_espaciado(hab["nombre"], fuente_mini, color_txt, 0)
    cuerpo.blit(nombre, nombre.get_rect(midleft=(x_texto, h // 2 - 8)))
    if estado == "activa":
        detalle = "EN USO"
    elif estado == "recarga":
        detalle = "RECARGA"
    else:
        detalle = f"COSTO {hab['costo']}"
    texto = render_espaciado(detalle, fuente_mini,
                             color_txt if estado == "activa"
                             else TEXTO_TENUE, 0)
    cuerpo.blit(texto, texto.get_rect(midleft=(x_texto, h // 2 + 9)))

    sup.blit(cuerpo, (m, m))
    return sup


def cruza_pala(pala, x_frente, x_antes, x_ahora, y_antes, y_ahora, mitad):
    # Revisa si la pelota cruzo el frente de la paleta en este cuadro
    # (asi no la atraviesa aunque vaya muy rapido).
    if (x_antes - x_frente) * (x_ahora - x_frente) > 0:
        return False
    t = (x_frente - x_antes) / (x_ahora - x_antes) if x_ahora != x_antes else 0
    y_cruce = y_antes + (y_ahora - y_antes) * t
    return pala.top - mitad <= y_cruce <= pala.bottom + mitad


# ============================================================
# CLASES: PALETA, LADO (jugador o Kira) Y PELOTA
# ============================================================
class Pala:
    def __init__(self, x):
        self.rect = pygame.Rect(0, 0, PALA_ANCHO, PALA_ALTO)
        self.rect.center = (x, CANCHA.centery)
        self.y = float(self.rect.y)
        self.alto = float(PALA_ALTO)
        self.vel = 0.0                       # px/s (para el efecto)
        self._centro_previo = float(self.rect.centery)

    def mover(self, dy):
        alto = self.rect.height
        self.y += dy
        self.y = max(CANCHA.top + 8, min(self.y, CANCHA.bottom - 8 - alto))
        self.rect.y = int(self.y)

    def ajustar_alto(self, objetivo, dt):
        # Crece o se encoge suavemente sin moverse de su centro.
        self.alto += (objetivo - self.alto) * min(1, dt * 10)
        nuevo = int(round(self.alto))
        if nuevo != self.rect.height:
            centro = self.y + self.rect.height / 2
            self.rect.height = nuevo
            self.y = centro - nuevo / 2
            self.mover(0)

    def medir_velocidad(self, dt):
        centro = self.y + self.rect.height / 2
        if dt > 0:
            v = (centro - self._centro_previo) / dt
            self.vel += (v - self.vel) * min(1.0, dt * 25)
        self._centro_previo = centro


class Lado:
    def __init__(self, es_jugador):
        self.es_jugador = es_jugador         # True = izquierda (J1)
        self.color = COLOR_JUGADOR if es_jugador else COLOR_CPU
        x = (CANCHA.left + MARGEN_PALA) if es_jugador else \
            (CANCHA.right - MARGEN_PALA)
        self.pala = Pala(x)
        self.puntos = 0
        self.energia = 0.0
        self.energia_vista = 0.0             # para animar la barra
        self.smash = False                   # armado para el proximo golpe
        self.curva = False                   # armado para el proximo golpe
        self.gigante_t = 0.0                 # segundos que le quedan
        self.escudo_t = 0.0
        self.invertido_t = 0.0
        self.recarga = {h["id"]: 0.0 for h in HABILIDADES}

    @property
    def x_escudo(self):
        return CANCHA.left + 10 if self.es_jugador else CANCHA.right - 10

    def sumar_energia(self, cantidad):
        self.energia = min(ENERGIA_MAXIMA, self.energia + cantidad)

    def habilidad_activa(self, id_hab):
        if id_hab == "smash":
            return self.smash
        if id_hab == "curva":
            return self.curva
        if id_hab == "gigante":
            return self.gigante_t > 0
        return self.escudo_t > 0

    def estado_slot(self, hab):
        if self.habilidad_activa(hab["id"]):
            return "activa"
        if self.recarga[hab["id"]] > 0:
            return "recarga"
        if self.energia >= hab["costo"]:
            return "lista"
        return "sin_energia"


class Pelota:
    def __init__(self):
        self.x = float(CANCHA.centerx)
        self.y = float(CANCHA.centery)
        self.vx = self.vy = 0.0
        self.vel = self.vel_normal = VEL_PELOTA_INICIAL
        self.curva = 0.0          # aceleracion de la habilidad CURVA
        self.efecto = 0.0         # aceleracion por golpear moviendose
        self.smash = False
        self.dueno = None         # el Lado que la golpeo por ultima vez
        self.color = COLOR_JUGADOR
        self.estela = []
        self.vida = None          # None = principal; numero = extra

    def dividir(self):
        # MULTIBOLA: una copia que sale en espejo hacia arriba/abajo.
        n = Pelota()
        n.x, n.y, n.vx = self.x, self.y, self.vx
        n.vel, n.vel_normal = self.vel, self.vel_normal
        if abs(self.vy) > 60:
            n.vy = -self.vy
        else:
            n.vy = random.choice((-1, 1)) * self.vel * 0.4
        n.curva, n.efecto = -self.curva, -self.efecto
        n.dueno = self.dueno
        n.color = self.dueno.color if self.dueno else self.color
        n.vida = DURACION_MULTI
        return n


# ============================================================
# EL JUEGO
# ============================================================
# Fases:
#   "menu"     -> pantalla de inicio
#   "tutorial" -> explica habilidades y orbes
#   "saque"    -> cuenta regresiva con la pelota en el centro
#   "jugando"  -> la pelota esta en movimiento
#   "punto"    -> alguien anoto, pausa corta con el mensaje
#   "final"    -> partida terminada
class Juego:
    def __init__(self):
        self.records = cargar_records()
        AJUSTES["silencio"] = self.records["silencio"]
        self.ejecutando = True
        self.t = 0.0

        self.fase = "menu"
        self.tiempo_fase = 0.0
        self.pausado = False

        self.modo = "1j"
        self.dificultad_menu = "normal"
        self.dificultad = "normal"
        self.puntos_objetivo = 7
        self.fila_menu = 0
        self.ronda = 0
        self.tutorial_luego_jugar = False

        self.jugador = Lado(True)
        self.cpu = Lado(False)
        self.pelotas = [Pelota()]
        self.golpes = 0
        self.racha_maxima = 0
        self.ultimo_punto_jugador = True

        self.error_cpu = 0.0
        self.objetivo_cpu = float(CANCHA.centery)
        self.espera_cpu = 0.0

        self.usar_mouse = False
        self.particulas = []
        self.avisos = []
        self.orbe = None
        self.proximo_orbe = 6.0
        self.pelota_grande_t = 0.0
        self.sacudida = 0.0

        self.mensaje = ""
        self.submensaje = ""
        self.color_mensaje = TEXTO
        self.torneo_continua = False
        self.nuevo_record = False

        self.camara_lenta = False
        self.tiempo_lento = 0.0
        self.defensor_lento = None

        self.kira_frase = ""
        self.kira_t = 0.0
        self.toast = ""
        self.toast_t = 0.0

    # --------------------------------------------------------
    # Consultas
    # --------------------------------------------------------
    @property
    def pelota(self):
        return self.pelotas[0]

    @property
    def contra_cpu(self):
        return self.modo != "2j"

    def dif(self):
        return DIFICULTADES[self.dificultad]

    def rival(self, lado):
        return self.cpu if lado is self.jugador else self.jugador

    def nombre_lado(self, lado):
        if self.contra_cpu:
            return "TÚ" if lado.es_jugador else "KIRA"
        return "J1" if lado.es_jugador else "J2"

    def tam_pelota(self):
        return TAM_PELOTA_GRANDE if self.pelota_grande_t > 0 else TAM_PELOTA

    def punto_de_partido(self, lado):
        # Si gana el proximo punto, gana la partida.
        n = lado.puntos + 1
        return (n >= self.puntos_objetivo
                and n - self.rival(lado).puntos >= DIFERENCIA_PARA_GANAR)

    def gano(self, lado):
        return (lado.puntos >= self.puntos_objetivo
                and lado.puntos - self.rival(lado).puntos
                >= DIFERENCIA_PARA_GANAR)

    def iguales(self):
        a, b = self.jugador.puntos, self.cpu.puntos
        return a == b and a >= self.puntos_objetivo - 1

    def cambiar_fase(self, nueva):
        self.fase = nueva
        self.tiempo_fase = 0.0

    def mostrar_toast(self, texto):
        self.toast = texto
        self.toast_t = 1.6

    def kira_decir(self, tipo, probabilidad=1.0):
        if not self.contra_cpu or random.random() > probabilidad:
            return
        self.kira_frase = random.choice(FRASES_KIRA[tipo])
        self.kira_t = 2.8

    # --------------------------------------------------------
    # Flujo: menu -> tutorial -> partida -> final
    # --------------------------------------------------------
    def ir_al_menu(self):
        self.pausado = False
        self.camara_lenta = False
        self.sacudida = 0.0
        self.jugador = Lado(True)
        self.cpu = Lado(False)
        self.pelotas = [Pelota()]
        self.orbe = None
        self.pelota_grande_t = 0.0
        self.kira_t = 0.0
        self.particulas.clear()
        self.avisos.clear()
        self.cambiar_fase("menu")

    def empezar_desde_menu(self):
        # El tutorial se muestra siempre antes de empezar desde el menu.
        self.abrir_tutorial(luego_jugar=True)

    def iniciar(self):
        if self.modo == "torneo":
            self.ronda = 0
            self.dificultad = ORDEN_DIFICULTAD[0]
        else:
            self.dificultad = self.dificultad_menu
        self.nueva_partida()

    def abrir_tutorial(self, luego_jugar):
        self.tutorial_luego_jugar = luego_jugar
        self.cambiar_fase("tutorial")

    def cerrar_tutorial(self, jugar=True):
        if not self.records["tutorial_visto"]:
            self.records["tutorial_visto"] = True
            guardar_records(self.records)
        if self.tutorial_luego_jugar and jugar:
            self.iniciar()
        else:
            self.cambiar_fase("menu")

    def nueva_partida(self):
        self.camara_lenta = False
        self.espera_cpu = 0.0
        self.sacudida = 0.0
        self.pausado = False
        self.jugador = Lado(True)
        self.cpu = Lado(False)
        self.racha_maxima = 0
        self.proximo_orbe = random.uniform(5, 8)
        self.torneo_continua = False
        self.nuevo_record = False
        self.particulas.clear()
        self.avisos.clear()
        self.preparar_saque(random.random() < 0.5)
        if self.modo == "torneo" and self.ronda > 0:
            self.kira_decir("ronda")
        else:
            self.kira_decir("inicio")

    def preparar_saque(self, hacia_jugador):
        p = Pelota()
        angulo = random.uniform(-0.45, 0.45)
        direccion = -1 if hacia_jugador else 1
        p.vx = direccion * VEL_PELOTA_INICIAL * math.cos(angulo)
        p.vy = VEL_PELOTA_INICIAL * math.sin(angulo)
        p.dueno = self.cpu if hacia_jugador else self.jugador
        p.color = p.dueno.color
        self.pelotas = [p]
        self.golpes = 0
        self.orbe = None
        self.pelota_grande_t = 0.0
        for lado in (self.jugador, self.cpu):
            lado.invertido_t = 0.0
        self.cambiar_fase("saque")
        sonar(SONIDO_CUENTA)          # beep del primer numero
        if self.punto_de_partido(self.jugador):
            self.kira_decir("presion", 0.6)

    def anotar(self, ganador):
        perdedor = self.rival(ganador)
        self.camara_lenta = False
        ganador.puntos += 1
        perdedor.sumar_energia(ENERGIA_POR_PUNTO_PERDIDO)
        self.ultimo_punto_jugador = ganador.es_jugador
        sonar(SONIDO_PUNTO)

        if not self.contra_cpu:
            self.mensaje = f"¡PUNTO PARA {self.nombre_lado(ganador)}!"
            self.color_mensaje = ganador.color
        elif ganador.es_jugador:
            self.mensaje = "¡PUNTO PARA TI!"
            self.color_mensaje = COLOR_JUGADOR
            self.kira_decir("punto_tuyo", 0.5)
        else:
            self.mensaje = "PUNTO PARA KIRA"
            self.color_mensaje = ROSA_ERROR
            self.kira_decir("punto_kira", 0.7)

        if self.gano(ganador):
            self.terminar_partida(ganador)
            return

        # Deuce: los dos estan a un punto de la meta.
        self.submensaje = ""
        a, b = self.jugador.puntos, self.cpu.puntos
        if min(a, b) >= self.puntos_objetivo - 1:
            if a == b:
                self.submensaje = "IGUALES · HAY QUE SACAR 2 DE VENTAJA"
            else:
                lider = self.jugador if a > b else self.cpu
                self.submensaje = f"VENTAJA {self.nombre_lado(lider)}"
        self.cambiar_fase("punto")

    def terminar_partida(self, ganador):
        gano_jugador = ganador.es_jugador
        self.submensaje = ""
        self.torneo_continua = False

        if self.modo == "2j":
            self.mensaje = f"¡GANA {self.nombre_lado(ganador)}!"
            self.color_mensaje = ganador.color
        elif self.modo == "torneo":
            if gano_jugador and self.ronda < RONDAS_TORNEO - 1:
                self.mensaje = f"¡RONDA {self.ronda + 1} GANADA!"
                siguiente = ORDEN_DIFICULTAD[self.ronda + 1]
                self.submensaje = (f"SIGUIENTE: KIRA EN "
                                   f"{DIFICULTADES[siguiente]['nombre']}")
                self.color_mensaje = COLOR_JUGADOR
                self.torneo_continua = True
                self.kira_decir("pierde")
            elif gano_jugador:
                self.mensaje = "¡CAMPEÓN DEL TORNEO!"
                self.submensaje = "LE GANASTE A KIRA EN LAS 3 DIFICULTADES"
                self.color_mensaje = COLOR_JUGADOR
                self.records["torneos"] += 1
                self.kira_decir("campeon")
            else:
                self.mensaje = "TORNEO TERMINADO"
                self.submensaje = (f"LLEGASTE A LA RONDA {self.ronda + 1} "
                                   f"DE {RONDAS_TORNEO}")
                self.color_mensaje = ROSA_ERROR
                self.kira_decir("gana")
        else:
            if gano_jugador:
                self.mensaje = "¡LE GANASTE A KIRA!"
                self.color_mensaje = COLOR_JUGADOR
                self.kira_decir("pierde")
            else:
                self.mensaje = "KIRA GANA"
                self.color_mensaje = ROSA_ERROR
                self.kira_decir("gana")

        # Records.
        if self.contra_cpu and gano_jugador:
            self.records["victorias"][self.dificultad] += 1
        if self.racha_maxima > self.records["racha_maxima"]:
            self.records["racha_maxima"] = self.racha_maxima
            self.nuevo_record = True
        guardar_records(self.records)
        self.cambiar_fase("final")

    def accion_final(self):
        # Boton principal de la pantalla final.
        if self.torneo_continua:
            self.ronda += 1
            self.dificultad = ORDEN_DIFICULTAD[self.ronda]
            self.nueva_partida()
        else:
            self.iniciar()

    # --------------------------------------------------------
    # Menu
    # --------------------------------------------------------
    def fila_habilitada(self, fila):
        if fila == "dificultad":
            return self.modo == "1j"
        return True

    def menu_mover(self, paso):
        i = self.fila_menu
        while True:
            i = max(0, min(len(FILAS_MENU) - 1, i + paso))
            if self.fila_habilitada(FILAS_MENU[i]) or i in (0, len(
                    FILAS_MENU) - 1):
                break
        if i != self.fila_menu:
            self.fila_menu = i
            sonar(SONIDO_MENU)

    def menu_cambiar(self, paso):
        fila = FILAS_MENU[self.fila_menu]
        if fila == "modo":
            lista, actual = MODOS, self.modo
        elif fila == "dificultad" and self.fila_habilitada(fila):
            lista, actual = ORDEN_DIFICULTAD, self.dificultad_menu
        elif fila == "puntos":
            lista, actual = OPCIONES_PUNTOS, self.puntos_objetivo
        else:
            return
        i = max(0, min(len(lista) - 1, lista.index(actual) + paso))
        if lista[i] == actual:
            return
        if fila == "modo":
            self.modo = lista[i]
            self.usar_mouse = self.usar_mouse and self.modo != "2j"
        elif fila == "dificultad":
            self.dificultad_menu = lista[i]
        else:
            self.puntos_objetivo = lista[i]
        sonar(SONIDO_MENU)

    def click_menu(self, pos):
        for valor, rect in RECT_MODO.items():
            if rect.collidepoint(pos):
                self.modo = valor
                self.fila_menu = 0
                sonar(SONIDO_MENU)
        if self.modo == "1j":
            for clave, rect in RECT_DIF.items():
                if rect.collidepoint(pos):
                    self.dificultad_menu = clave
                    self.fila_menu = 1
                    sonar(SONIDO_MENU)
        for valor, rect in RECT_PTS.items():
            if rect.collidepoint(pos):
                self.puntos_objetivo = valor
                self.fila_menu = 2
                sonar(SONIDO_MENU)
        if RECT_JUGAR.collidepoint(pos):
            self.empezar_desde_menu()

    # --------------------------------------------------------
    # Eventos
    # --------------------------------------------------------
    def manejar_evento(self, evento):
        if evento.type == pygame.QUIT:
            self.ejecutando = False
            return

        # Si la ventana pierde el foco en plena partida, se pausa sola.
        if evento.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            if self.fase in ("saque", "jugando", "punto"):
                self.pausado = True
            return

        if evento.type == pygame.MOUSEMOTION:
            if self.modo != "2j":
                self.usar_mouse = True
            return

        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.fase == "menu":
                self.click_menu(evento.pos)
            elif self.fase == "tutorial":
                if RECT_ENTENDIDO.collidepoint(evento.pos):
                    self.cerrar_tutorial()
            elif self.fase == "final":
                if RECT_BOTON.collidepoint(evento.pos):
                    self.accion_final()
                elif RECT_MENU.collidepoint(evento.pos):
                    self.ir_al_menu()
            return

        if evento.type != pygame.KEYDOWN:
            return
        tecla = evento.key

        # Teclas que funcionan en cualquier pantalla.
        if tecla == pygame.K_F11:
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error:
                self.mostrar_toast("PANTALLA COMPLETA NO DISPONIBLE")
            return
        if tecla == pygame.K_m:
            AJUSTES["silencio"] = not AJUSTES["silencio"]
            self.records["silencio"] = AJUSTES["silencio"]
            guardar_records(self.records)
            self.mostrar_toast("SONIDO DESACTIVADO" if AJUSTES["silencio"]
                               else "SONIDO ACTIVADO")
            return

        if self.fase == "menu":
            if tecla in (pygame.K_UP, pygame.K_w):
                self.menu_mover(-1)
            elif tecla in (pygame.K_DOWN, pygame.K_s):
                self.menu_mover(1)
            elif tecla in (pygame.K_LEFT, pygame.K_a):
                self.menu_cambiar(-1)
            elif tecla in (pygame.K_RIGHT, pygame.K_d):
                self.menu_cambiar(1)
            elif tecla in (pygame.K_RETURN, pygame.K_SPACE,
                           pygame.K_KP_ENTER):
                self.empezar_desde_menu()
            elif tecla == pygame.K_h:
                self.abrir_tutorial(luego_jugar=False)
            elif tecla == pygame.K_ESCAPE:
                self.ejecutando = False
            return

        if self.fase == "tutorial":
            if tecla in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.cerrar_tutorial()
            elif tecla == pygame.K_ESCAPE:
                self.cerrar_tutorial(jugar=False)
            return

        if tecla in (pygame.K_w, pygame.K_s) or (
                tecla in (pygame.K_UP, pygame.K_DOWN) and self.contra_cpu):
            self.usar_mouse = False
        if tecla in TECLAS_HABILIDAD:
            self.activar(self.jugador, TECLAS_HABILIDAD[tecla])
        if not self.contra_cpu and tecla in TECLAS_HABILIDAD_J2:
            self.activar(self.cpu, TECLAS_HABILIDAD_J2[tecla])
        if tecla == pygame.K_p and self.fase != "final":
            self.pausado = not self.pausado
        if tecla in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) \
                and self.fase == "final":
            self.accion_final()
        if tecla == pygame.K_ESCAPE:
            self.ir_al_menu()

    # --------------------------------------------------------
    # Efectos: particulas, avisos flotantes
    # --------------------------------------------------------
    def chispas(self, x, y, color, direccion, cantidad=14, fuerza=1.0):
        for _ in range(cantidad):
            ang = random.uniform(-1.0, 1.0)
            vel = random.uniform(120, 340) * fuerza
            self.particulas.append({
                "x": x, "y": y,
                "vx": direccion * vel * math.cos(ang),
                "vy": vel * math.sin(ang),
                "vida": random.uniform(0.25, 0.5), "max": 0.5,
                "color": color,
            })

    def actualizar_particulas(self, dt):
        for p in self.particulas:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.92
            p["vy"] *= 0.92
            p["vida"] -= dt
        self.particulas[:] = [p for p in self.particulas if p["vida"] > 0]

    def avisar(self, texto, x, y, color):
        # Siempre dentro de la cancha, aunque la paleta este muy arriba.
        y = max(CANCHA.top + 24, min(y, CANCHA.bottom - 24))
        self.avisos.append({"texto": texto, "x": x, "y": y, "color": color,
                            "vida": 1.0})

    def actualizar_avisos(self, dt):
        for a in self.avisos:
            a["vida"] -= dt
            a["y"] -= 40 * dt
        self.avisos[:] = [a for a in self.avisos if a["vida"] > 0]

    # --------------------------------------------------------
    # Habilidades
    # --------------------------------------------------------
    def puede_activar(self, lado, id_hab):
        return (self.fase in ("saque", "jugando") and not self.pausado
                and not lado.habilidad_activa(id_hab)
                and lado.recarga[id_hab] <= 0
                and lado.energia >= COSTO[id_hab])

    def activar(self, lado, id_hab):
        if not self.puede_activar(lado, id_hab):
            # Solo suena si de verdad se podia intentar.
            humano = lado.es_jugador or not self.contra_cpu
            if humano and not self.pausado and \
                    self.fase in ("saque", "jugando"):
                sonar(SONIDO_SIN_ENERGIA)
            return False

        lado.energia -= COSTO[id_hab]
        lado.recarga[id_hab] = RECARGA[id_hab]
        if id_hab == "smash":
            lado.smash = True
        elif id_hab == "curva":
            lado.curva = True
        elif id_hab == "gigante":
            lado.gigante_t = DURACION_GIGANTE
        elif id_hab == "escudo":
            lado.escudo_t = DURACION_ESCUDO

        nombre = next(h["nombre"] for h in HABILIDADES if h["id"] == id_hab)
        r = lado.pala.rect
        x = r.centerx + (90 if lado.es_jugador else -90)
        self.avisar(nombre, x, r.top - 14, lado.color)
        sonar(SONIDO_HABILIDAD)
        if lado is self.cpu:
            self.kira_decir("habilidad", 0.35)
        return True

    def actualizar_habilidades(self, dt):
        for lado in (self.jugador, self.cpu):
            # Los tiempos solo corren con la pelota en juego.
            if self.fase == "jugando":
                lado.gigante_t = max(0.0, lado.gigante_t - dt)
                lado.escudo_t = max(0.0, lado.escudo_t - dt)
                lado.invertido_t = max(0.0, lado.invertido_t - dt)
                for id_hab in lado.recarga:
                    lado.recarga[id_hab] = max(0.0, lado.recarga[id_hab] - dt)
            objetivo = PALA_ALTO_GIGANTE if lado.gigante_t > 0 else PALA_ALTO
            lado.pala.ajustar_alto(objetivo, dt)
            lado.energia_vista += (lado.energia - lado.energia_vista) \
                * min(1, dt * 8)

    # --------------------------------------------------------
    # Orbes
    # --------------------------------------------------------
    def actualizar_orbe(self, dt):
        if self.fase != "jugando":
            return

        if self.orbe is None:
            self.proximo_orbe -= dt
            if self.proximo_orbe <= 0:
                tipo = random.choices(
                    ORDEN_ORBES,
                    weights=[TIPOS_ORBE[k]["peso"] for k in ORDEN_ORBES])[0]
                self.orbe = {
                    "tipo": tipo,
                    "x": random.uniform(CANCHA.left + CANCHA.width * 0.35,
                                        CANCHA.right - CANCHA.width * 0.35),
                    "y": random.uniform(CANCHA.top + 50, CANCHA.bottom - 50),
                    "vida": 9.0,
                }
            return

        self.orbe["vida"] -= dt
        if self.orbe["vida"] <= 0:
            self.orbe = None
            self.proximo_orbe = random.uniform(5, 9)
            return

        alcance = (RADIO_ORBE + self.tam_pelota()) ** 2
        for p in self.pelotas:
            dx = p.x - self.orbe["x"]
            dy = p.y - self.orbe["y"]
            if dx * dx + dy * dy <= alcance:
                self.recoger_orbe(p)
                break

    def recoger_orbe(self, p):
        o = self.orbe
        tipo = o["tipo"]
        dueno = p.dueno
        color = TIPOS_ORBE[tipo]["color"]
        x, y = o["x"], o["y"] - 24

        if tipo == "multi" and len(self.pelotas) >= MAX_PELOTAS:
            tipo = "energia"     # ya hay muchas pelotas: da energia

        if tipo == "energia":
            dueno.sumar_energia(ENERGIA_POR_ORBE)
            self.avisar(f"+{ENERGIA_POR_ORBE} ENERGÍA", x, y, dueno.color)
        elif tipo == "grande":
            self.pelota_grande_t = DURACION_PELOTA_GRANDE
            self.avisar("¡PELOTA XL!", x, y, color)
        elif tipo == "multi":
            self.pelotas.append(p.dividir())
            self.avisar("¡MULTIBOLA!", x, y, color)
        elif tipo == "invertir":
            victima = self.rival(dueno)
            victima.invertido_t = DURACION_INVERTIDO
            if self.contra_cpu and victima.es_jugador:
                texto = "¡CONTROLES AL REVÉS!"
            elif self.contra_cpu:
                texto = "¡KIRA CONFUNDIDA!"
                self.kira_decir("confundida", 0.8)
            else:
                texto = f"¡{self.nombre_lado(victima)} AL REVÉS!"
            r = victima.pala.rect
            self.avisar(texto, r.centerx + (110 if victima.es_jugador
                                            else -110), r.top - 14, color)

        self.chispas(o["x"], o["y"], color, 1, 10)
        self.chispas(o["x"], o["y"], color, -1, 10)
        sonar(SONIDO_ORBE)
        self.orbe = None
        self.proximo_orbe = random.uniform(6, 10)

    # --------------------------------------------------------
    # Fisica de la pelota
    # --------------------------------------------------------
    def rebotar_en_pala(self, p, lado, direccion):
        # Kira decide si usa una habilidad justo en el momento del golpe.
        if lado is self.cpu and self.contra_cpu:
            self.cpu_decide_al_golpear()

        pala = lado.pala.rect
        # Donde pega en la paleta decide el angulo.
        desvio = (p.y - pala.centery) / (pala.height / 2)
        desvio = max(-1, min(1, desvio))
        angulo = desvio * ANGULO_MAXIMO

        p.vel_normal = min(p.vel_normal * AUMENTO_POR_GOLPE,
                           VEL_PELOTA_MAXIMA)
        vel = p.vel_normal

        p.smash = lado.smash
        if lado.smash:
            # SMASH: este tiro sale mucho mas rapido.
            lado.smash = False
            vel = min(vel * MULTIPLICADOR_SMASH, VEL_SMASH)
            angulo *= 0.6
            self.sacudida = 0.25
            self.chispas(p.x, p.y, COLOR_SMASH, direccion, 26, 1.6)
            sonar(SONIDO_SMASH)
        else:
            sonar(SONIDO_PALETA)

        p.vel = vel
        p.vx = direccion * vel * math.cos(angulo)
        p.vy = vel * math.sin(angulo)

        if lado.curva:
            # CURVA: la pelota se dobla hacia el lado contrario al que sale.
            lado.curva = False
            sentido = -1 if p.vy > 0 else 1
            if abs(p.vy) < 40:
                sentido = random.choice((-1, 1))
                p.vy = -sentido * vel * 0.35
            p.curva = sentido * ACELERACION_CURVA
        else:
            p.curva = 0.0

        # EFECTO: la paleta en movimiento "arrastra" la pelota.
        efecto = max(-EFECTO_MAXIMO,
                     min(EFECTO_MAXIMO, lado.pala.vel * EFECTO_FACTOR))
        p.efecto = efecto if abs(efecto) > 80 else 0.0
        humano = lado.es_jugador or not self.contra_cpu
        if humano and abs(p.efecto) > 600:
            self.avisar("EFECTO", pala.centerx + 70 * direccion,
                        pala.bottom + 14, lado.color)

        p.dueno = lado
        p.color = COLOR_SMASH if p.smash else lado.color

        lado.sumar_energia(ENERGIA_POR_GOLPE)
        self.golpes += 1
        self.racha_maxima = max(self.racha_maxima, self.golpes)
        self.nuevo_error_cpu(p)
        self.chispas(p.x, p.y, lado.color, direccion)

    def nuevo_error_cpu(self, p):
        # Kira se equivoca un poco distinto en cada golpe; mientras mas
        # rapida o con mas truco va la pelota, mas le cuesta.
        rapidez = min(1, p.vel / VEL_PELOTA_MAXIMA)
        self.error_cpu = random.uniform(-1, 1) * (
            PALA_ALTO * (0.25 + 0.5 * rapidez))
        if p.smash or p.curva or abs(p.efecto) > 300:
            self.error_cpu *= 1.5
        self.error_cpu *= self.dif()["error"]

    def rebotar_en_escudo(self, p, lado):
        mitad = self.tam_pelota() / 2
        lado.escudo_t = 0.0
        # Si para un SMASH, la pelota vuelve a velocidad normal.
        if p.smash:
            escala = p.vel_normal / max(1.0, p.vel)
            p.vx *= escala
            p.vy *= escala
            p.vel = p.vel_normal
            p.smash = False
        if lado.es_jugador:
            p.x = lado.x_escudo + mitad + 4
            p.vx = abs(p.vx)
        else:
            p.x = lado.x_escudo - mitad - 4
            p.vx = -abs(p.vx)
        p.curva = 0.0
        p.efecto = 0.0
        p.dueno = lado
        p.color = lado.color
        self.nuevo_error_cpu(p)
        self.chispas(p.x, p.y, lado.color, 1 if lado.es_jugador else -1,
                     24, 1.3)
        self.avisar("¡SALVADA!", p.x + (80 if lado.es_jugador else -80),
                    p.y - 20, lado.color)
        sonar(SONIDO_ESCUDO)

    def actualizar_pelota(self, p, dt):
        # Mueve una pelota. Devuelve el Lado que anoto, o None.
        mitad = self.tam_pelota() / 2
        x_antes, y_antes = p.x, p.y

        if p.curva or p.efecto:
            p.vy += (p.curva + p.efecto) * dt
            limite = p.vel * 0.9
            p.vy = max(-limite, min(limite, p.vy))
            p.efecto *= math.exp(-EFECTO_CAIDA * dt)
            if abs(p.efecto) < 5:
                p.efecto = 0.0

        p.x += p.vx * dt
        p.y += p.vy * dt

        # Paredes de arriba y abajo.
        if p.y - mitad < CANCHA.top:
            p.y = CANCHA.top + mitad
            p.vy = abs(p.vy)
            p.curva = abs(p.curva)
            p.efecto = abs(p.efecto)
            sonar(SONIDO_PARED)
        elif p.y + mitad > CANCHA.bottom:
            p.y = CANCHA.bottom - mitad
            p.vy = -abs(p.vy)
            p.curva = -abs(p.curva)
            p.efecto = -abs(p.efecto)
            sonar(SONIDO_PARED)

        # Paleta izquierda.
        r = self.jugador.pala.rect
        frente = r.right + mitad
        if p.vx < 0 and cruza_pala(r, frente, x_antes, p.x, y_antes, p.y,
                                   mitad):
            p.x = frente
            self.rebotar_en_pala(p, self.jugador, 1)

        # Paleta derecha.
        r = self.cpu.pala.rect
        frente = r.left - mitad
        if p.vx > 0 and cruza_pala(r, frente, x_antes, p.x, y_antes, p.y,
                                   mitad):
            p.x = frente
            self.rebotar_en_pala(p, self.cpu, -1)

        # Escudos: si la pelota llega al fondo y hay escudo, rebota.
        if (p.vx < 0 and self.jugador.escudo_t > 0
                and p.x - mitad <= self.jugador.x_escudo + 4):
            self.rebotar_en_escudo(p, self.jugador)
        elif (p.vx > 0 and self.cpu.escudo_t > 0
                and p.x + mitad >= self.cpu.x_escudo - 4):
            self.rebotar_en_escudo(p, self.cpu)

        p.estela.insert(0, (p.x, p.y))
        del p.estela[LARGO_ESTELA:]

        if p.x < CANCHA.left:
            return self.cpu
        if p.x > CANCHA.right:
            return self.jugador
        return None

    # --------------------------------------------------------
    # Camara lenta en el punto de partido
    # --------------------------------------------------------
    def velocidad_defensa(self, lado):
        if lado.es_jugador:
            return VEL_JUGADOR_MOUSE if self.usar_mouse else VEL_JUGADOR
        if not self.contra_cpu:
            return VEL_JUGADOR
        return self.dif()["vel"] * (0.55 if lado.invertido_t > 0 else 1)

    def simular_llegada(self, p, x_destino):
        # Simula paso a paso (asi acierta con la CURVA y el EFECTO).
        x, y = p.x, p.y
        vx, vy, curva, efecto = p.vx, p.vy, p.curva, p.efecto
        limite = p.vel * 0.9
        mitad = self.tam_pelota() / 2
        paso = 1 / 240
        caida = math.exp(-EFECTO_CAIDA * paso)
        for _ in range(480):
            if (x_destino - x) * vx <= 0:
                break
            if curva or efecto:
                vy = max(-limite, min(limite, vy + (curva + efecto) * paso))
                efecto *= caida
            x += vx * paso
            y += vy * paso
            if y - mitad < CANCHA.top:
                y, vy = CANCHA.top + mitad, abs(vy)
                curva, efecto = abs(curva), abs(efecto)
            elif y + mitad > CANCHA.bottom:
                y, vy = CANCHA.bottom - mitad, -abs(vy)
                curva, efecto = -abs(curva), -abs(efecto)
        return y

    def revisar_camara_lenta(self, dt_real):
        # Si el que ataca esta a 1 punto de ganar y la pelota ya no la
        # alcanza el que defiende, todo se ralentiza hasta que entre.
        if self.camara_lenta:
            self.tiempo_lento += dt_real
            if (self.tiempo_lento > DURACION_MAX_LENTA
                    or self.pelota.dueno is self.defensor_lento):
                self.camara_lenta = False
            return

        if self.fase != "jugando" or len(self.pelotas) > 1:
            return
        p = self.pelota
        defensor = self.jugador if p.vx < 0 else self.cpu
        atacante = self.rival(defensor)
        if not self.punto_de_partido(atacante) or defensor.escudo_t > 0:
            return

        r = defensor.pala.rect
        mitad = self.tam_pelota() / 2
        if defensor.es_jugador:
            frente = r.right + mitad
            ya_paso = p.x < frente - 2
        else:
            frente = r.left - mitad
            ya_paso = p.x > frente + 2
        distancia = abs(p.x - frente)
        if not ya_paso and distancia > DISTANCIA_CAMARA_LENTA:
            return

        inalcanzable = ya_paso
        if not ya_paso:
            tiempo = distancia / max(1.0, abs(p.vx))
            llega = self.simular_llegada(p, frente)
            falta = abs(llega - r.centery) - (r.height / 2 + mitad)
            inalcanzable = falta > self.velocidad_defensa(defensor) * tiempo \
                + 12
            if self.contra_cpu and defensor is self.cpu and not inalcanzable:
                # Kira va hacia donde ELLA cree que llega la pelota.
                paso = self.velocidad_defensa(self.cpu) * tiempo
                centro_final = r.centery + max(
                    -paso, min(paso, self.objetivo_cpu - r.centery))
                inalcanzable = (abs(llega - centro_final)
                                > r.height / 2 + mitad + 6)

        if inalcanzable:
            self.camara_lenta = True
            self.tiempo_lento = 0.0
            self.defensor_lento = defensor
            sonar(SONIDO_LENTO)

    # --------------------------------------------------------
    # Controles y Kira (CPU)
    # --------------------------------------------------------
    def actualizar_jugador(self, dt):
        teclas = pygame.key.get_pressed()
        direccion = 0
        # En 2 jugadores las flechas son del J2, asi que el J1 usa W/S.
        if teclas[pygame.K_w] or (teclas[pygame.K_UP] and self.contra_cpu):
            direccion -= 1
        if teclas[pygame.K_s] or (teclas[pygame.K_DOWN] and self.contra_cpu):
            direccion += 1

        pala = self.jugador.pala
        invertido = self.jugador.invertido_t > 0
        if invertido:
            direccion = -direccion
        if direccion != 0:
            pala.mover(direccion * VEL_JUGADOR * dt)
        elif self.usar_mouse and self.contra_cpu:
            objetivo = pygame.mouse.get_pos()[1]
            if invertido:
                objetivo = 2 * CANCHA.centery - objetivo
            delta = objetivo - pala.rect.centery
            paso = VEL_JUGADOR_MOUSE * dt
            pala.mover(max(-paso, min(paso, delta)))

    def actualizar_jugador2(self, dt):
        teclas = pygame.key.get_pressed()
        direccion = 0
        if teclas[pygame.K_UP]:
            direccion -= 1
        if teclas[pygame.K_DOWN]:
            direccion += 1
        if self.cpu.invertido_t > 0:
            direccion = -direccion
        if direccion != 0:
            self.cpu.pala.mover(direccion * VEL_JUGADOR * dt)

    def predecir_y(self, p, x_destino):
        # A que altura llegara la pelota contando rebotes en las paredes
        # (la curva y el efecto no los ve venir: por eso la enganan).
        if p.vx == 0:
            return p.y
        tiempo = (x_destino - p.x) / p.vx
        y = p.y + p.vy * tiempo
        mitad = self.tam_pelota() / 2
        arriba = CANCHA.top + mitad
        alto = CANCHA.height - 2 * mitad
        rel = (y - arriba) % (2 * alto)
        if rel > alto:
            rel = 2 * alto - rel
        return arriba + rel

    def pelota_que_viene(self):
        # La pelota que va a llegar antes al lado de Kira.
        if self.fase != "jugando":
            return None
        mejor, mejor_t = None, None
        for p in self.pelotas:
            if p.vx > 0:
                t = (self.cpu.pala.rect.left - p.x) / p.vx
                if t > 0 and (mejor_t is None or t < mejor_t):
                    mejor, mejor_t = p, t
        return mejor

    def cpu_decide_al_golpear(self):
        r = random.random()
        # Con la barra casi llena no tiene sentido guardar: la usa seguro.
        if self.cpu.energia >= 90:
            r = 0.0
        usado = False
        f = self.dif()["habilidad"]
        if self.cpu.energia >= COSTO["smash"] + 10 and r < 0.4 * f:
            usado = self.activar(self.cpu, "smash")
        if not usado and self.cpu.energia >= COSTO["curva"] and r < 0.55 * f:
            self.activar(self.cpu, "curva")

    def cpu_decide_en_juego(self, dt):
        viene = [p for p in self.pelotas if p.vx > 0]
        if not viene:
            return
        f = self.dif()["habilidad"]
        rapida = max(p.vel for p in viene)
        if (rapida > 620 and self.cpu.energia >= COSTO["gigante"]
                and random.random() < dt * 1.2 * f):
            self.activar(self.cpu, "gigante")
        if (self.cpu.puntos < self.jugador.puntos
                and self.cpu.energia >= COSTO["escudo"]
                and any(p.x > CANCHA.centerx for p in viene)
                and random.random() < dt * 0.8 * f):
            self.activar(self.cpu, "escudo")

    def actualizar_cpu(self, dt):
        pala = self.cpu.pala
        confundida = self.cpu.invertido_t > 0
        # Kira no ve todo al instante: revisa donde ir cada cierto tiempo.
        self.espera_cpu -= dt
        if self.espera_cpu <= 0:
            self.espera_cpu = self.dif()["reaccion"] * \
                (1.6 if confundida else 1)
            p = self.pelota_que_viene()
            if p is not None and p.x > CANCHA.left + CANCHA.width * 0.3:
                error = self.error_cpu * (1.8 if confundida else 1)
                self.objetivo_cpu = self.predecir_y(p, pala.rect.left) + error
            else:
                self.objetivo_cpu = CANCHA.centery
        delta = self.objetivo_cpu - pala.rect.centery
        if abs(delta) >= 4:
            paso = self.velocidad_defensa(self.cpu) * dt
            pala.mover(max(-paso, min(paso, delta)))

        if self.fase == "jugando":
            self.cpu_decide_en_juego(dt)

    # --------------------------------------------------------
    # Actualizar todo
    # --------------------------------------------------------
    def actualizar(self, dt_real):
        self.t += dt_real
        self.toast_t = max(0.0, self.toast_t - dt_real)
        self.kira_t = max(0.0, self.kira_t - dt_real)
        if self.fase in ("menu", "tutorial") or self.pausado:
            return

        dt = dt_real * (ESCALA_CAMARA_LENTA if self.camara_lenta else 1.0)
        self.tiempo_fase += dt
        self.actualizar_jugador(dt)
        if self.contra_cpu:
            self.actualizar_cpu(dt)
        else:
            self.actualizar_jugador2(dt)
        self.jugador.pala.medir_velocidad(dt)
        self.cpu.pala.medir_velocidad(dt)
        self.actualizar_habilidades(dt)
        self.actualizar_particulas(dt)
        self.actualizar_avisos(dt)
        self.actualizar_orbe(dt)
        self.sacudida = max(0.0, self.sacudida - dt)

        if self.fase == "saque":
            if self.tiempo_fase >= TIEMPO_SAQUE:
                self.cambiar_fase("jugando")
            elif int(self.tiempo_fase) != int(self.tiempo_fase - dt):
                sonar(SONIDO_CUENTA)

        elif self.fase == "jugando":
            for p in list(self.pelotas):
                ganador = self.actualizar_pelota(p, dt)
                if ganador is not None:
                    self.anotar(ganador)
                    break
            else:
                # Las pelotas extra (multibola) duran poco.
                for p in self.pelotas[1:]:
                    p.vida -= dt
                    if p.vida <= 0:
                        self.chispas(p.x, p.y, p.color, 1, 8)
                        self.chispas(p.x, p.y, p.color, -1, 8)
                        self.pelotas.remove(p)
                self.pelota_grande_t = max(0.0, self.pelota_grande_t - dt)
                self.revisar_camara_lenta(dt_real)

        elif self.fase == "punto":
            for p in self.pelotas:
                if p.estela:
                    p.estela.pop()
            if self.tiempo_fase >= TIEMPO_PUNTO:
                # Saca el que perdio el punto, hacia el que lo gano.
                self.preparar_saque(hacia_jugador=self.ultimo_punto_jugador)

    # --------------------------------------------------------
    # Dibujar: encabezado
    # --------------------------------------------------------
    def estado_encabezado(self):
        if self.fase == "menu":
            return "ELIGE MODO, DIFICULTAD Y PUNTOS", NEON_CIAN
        if self.fase == "tutorial":
            return "CÓMO SE JUEGA", NEON_CIAN
        if self.pausado:
            return "EN PAUSA", TEXTO_SUAVE
        if self.fase == "final":
            gano = self.jugador.puntos > self.cpu.puntos
            return "PARTIDA TERMINADA", (COLOR_JUGADOR if gano
                                         or not self.contra_cpu
                                         else ROSA_ERROR)
        if self.iguales():
            return "IGUALES · HAY QUE SACAR 2 DE VENTAJA", AMARILLO
        if self.punto_de_partido(self.jugador) or \
                self.punto_de_partido(self.cpu):
            return "PUNTO DE PARTIDO", ROSA_ERROR
        if self.fase == "saque":
            return "PREPARANDO SAQUE", NEON_MORADO
        if self.fase == "punto":
            return "PUNTO", self.color_mensaje
        if self.modo == "2j":
            modo_txt = "2 JUGADORES"
        elif self.modo == "torneo":
            modo_txt = (f"TORNEO {self.ronda + 1}/{RONDAS_TORNEO} · "
                        f"{self.dif()['nombre']}")
        else:
            modo_txt = self.dif()["nombre"]
        return f"A {self.puntos_objetivo} PUNTOS · {modo_txt}", NEON_CIAN

    def dibujar_encabezado(self):
        centro_y = TARJETA.y + ALTO_ENCABEZADO // 2
        x = TARJETA.x + 32
        escribir_degradado("TENIS RETRO", fuente_titulo, x, centro_y - 12)

        estado, color_estado = self.estado_encabezado()
        dibujar_punto_estado(x + 5, centro_y + 22, self.t, color_estado)
        etiqueta = cache(
            ("etq", estado),
            lambda: render_espaciado(estado, fuente_mini, TEXTO_TENUE, 2))
        pantalla.blit(etiqueta, etiqueta.get_rect(midleft=(x + 16,
                                                           centro_y + 22)))

        if self.fase in ("menu", "tutorial"):
            return

        derecha = TARJETA.right - 28
        chip_cpu = pygame.Rect(0, 0, 150, 46)
        chip_cpu.midright = (derecha, centro_y)
        dibujar_chip(chip_cpu)
        if self.contra_cpu:
            ret = retrato_kira(34)
            pantalla.blit(ret, ret.get_rect(center=(chip_cpu.x + 25,
                                                    chip_cpu.centery)))
            escribir("KIRA", fuente_mini, TEXTO_SUAVE, chip_cpu.x + 72,
                     chip_cpu.centery + 1, espacio=2)
        else:
            escribir("J2", fuente_mini, TEXTO_SUAVE, chip_cpu.x + 56,
                     chip_cpu.centery + 1, espacio=2)
        escribir(str(self.cpu.puntos), fuente, COLOR_CPU, chip_cpu.x + 122,
                 chip_cpu.centery + 1, brillo=COLOR_CPU, alpha_brillo=140)

        chip_tu = pygame.Rect(0, 0, 118, 46)
        chip_tu.midright = (chip_cpu.x - 12, centro_y)
        dibujar_chip(chip_tu)
        escribir(self.nombre_lado(self.jugador), fuente_mini, TEXTO_SUAVE,
                 chip_tu.x + 36, chip_tu.centery + 1, espacio=2)
        escribir(str(self.jugador.puntos), fuente, COLOR_JUGADOR,
                 chip_tu.x + 88, chip_tu.centery + 1, brillo=COLOR_JUGADOR,
                 alpha_brillo=140)

    def dibujar_toast(self):
        if self.toast_t <= 0:
            return
        centro_y = TARJETA.y + ALTO_ENCABEZADO // 2
        sup, _ = texto_cacheado(self.toast, fuente_mini, TEXTO, espacio=2)
        rect = pygame.Rect(0, 0, sup.get_width() + 32, 34)
        rect.center = (ANCHO // 2 + 10, centro_y)
        dibujar_chip(rect, NEON_CIAN, 150)
        pantalla.blit(sup, sup.get_rect(center=rect.center))

    def dibujar_burbuja_kira(self):
        if self.kira_t <= 0 or not self.contra_cpu:
            return
        sup, m = cache(("burbuja", self.kira_frase, "arriba"),
                       lambda: crear_burbuja(self.kira_frase, "arriba"))
        alpha = int(255 * min(1.0, self.kira_t * 3))
        if alpha < 255:
            sup = sup.copy()
            sup.set_alpha(alpha)
        pantalla.blit(sup, sup.get_rect(topright=(CANCHA.right - 8 + m,
                                                  CANCHA.top + 14 - m)))

    # --------------------------------------------------------
    # Dibujar: menu
    # --------------------------------------------------------
    def dibujar_menu(self):
        if KIRA_MENU is not None:
            pantalla.blit(KIRA_MENU, TARJETA.topleft)
        cx, cy = KIRA_MENU_CARA
        frase = FRASES_MENU[int(self.t / 4) % len(FRASES_MENU)]
        sup, m = cache(("burbuja", frase, "derecha"),
                       lambda: crear_burbuja(frase, "derecha", 190))
        pantalla.blit(sup, sup.get_rect(midright=(cx - 92 + m, cy - 44)))
        escribir("KIRA", fuente_grande, TEXTO, TARJETA.right - 120,
                 TARJETA.bottom - 78, brillo=NEON_MORADO, alpha_brillo=220)
        escribir("TU RIVAL", fuente_mini, TEXTO_SUAVE, TARJETA.right - 120,
                 TARJETA.bottom - 44, espacio=3)

        escribir("ELIGE CÓMO JUGAR", fuente_aviso, TEXTO, COL_X, 158,
                 brillo=NEON_MORADO, alpha_brillo=170)

        etiquetas = {
            "modo": "MODO",
            "dificultad": ("DIFICULTAD DE KIRA" if self.modo == "1j" else
                           "DIFICULTAD (SOLO CONTRA KIRA)" if self.modo == "2j"
                           else "DIFICULTAD: SUBE SOLA EN EL TORNEO"),
            "puntos": "PUNTOS PARA GANAR · POR 2 DE DIFERENCIA",
        }
        fila_activa = FILAS_MENU[self.fila_menu]
        for fila, texto in etiquetas.items():
            activa = fila == fila_activa
            habil = self.fila_habilitada(fila) or fila != "dificultad"
            color = NEON_CIAN if activa else (TEXTO_SUAVE if habil
                                              else TEXTO_TENUE)
            escribir(texto, fuente_mini, color, COL_X, Y_FILA[fila] - 36,
                     espacio=2)

        # Indicador de la fila activa (se mueve con arriba/abajo).
        y = Y_FILA[fila_activa]
        pulso = 0.6 + 0.4 * (math.sin(self.t * 5) + 1) / 2
        barra = pygame.Rect(COL_X - 248, y - 15, 4, 30)
        pygame.draw.rect(pantalla, mezclar(FONDO, NEON_CIAN, pulso), barra,
                         border_radius=2)

        for m_, rect in RECT_MODO.items():
            dibujar_opcion(rect, NOMBRE_MODO[m_], m_ == self.modo)
        for clave, rect in RECT_DIF.items():
            dibujar_opcion(rect, DIFICULTADES[clave]["nombre"],
                           clave == self.dificultad_menu
                           and self.modo == "1j",
                           apagada=self.modo != "1j")
        for valor, rect in RECT_PTS.items():
            dibujar_opcion(rect, str(valor), valor == self.puntos_objetivo)
        dibujar_boton_principal(RECT_JUGAR, "JUGAR",
                                resaltado=fila_activa == "jugar")

        # Records guardados.
        r = self.records
        dibujar_chip(RECT_RECORDS)
        x = RECT_RECORDS.centerx
        y = RECT_RECORDS.y
        escribir("RÉCORDS", fuente_mini, NEON_MORADO, x, y + 18, espacio=3)
        escribir(f"RACHA MÁS LARGA · {r['racha_maxima']} GOLPES",
                 fuente_mini, TEXTO, x, y + 44, espacio=1)
        v = r["victorias"]
        escribir(f"VICTORIAS VS KIRA · FÁCIL {v['facil']} · NORMAL "
                 f"{v['normal']} · DIFÍCIL {v['dificil']}",
                 fuente_mini, TEXTO, x, y + 66, espacio=1)
        escribir(f"TORNEOS GANADOS · {r['torneos']}", fuente_mini, TEXTO,
                 x, y + 88, espacio=1)

    # --------------------------------------------------------
    # Dibujar: tutorial
    # --------------------------------------------------------
    def dibujar_tutorial(self):
        escribir("CÓMO SE JUEGA", fuente_aviso, TEXTO, ANCHO // 2, 146,
                 brillo=NEON_MORADO, alpha_brillo=170)
        escribir("HABILIDADES · SE PAGAN CON LA ENERGÍA DE TU BARRA",
                 fuente_mini, TEXTO_SUAVE, ANCHO // 2, 176, espacio=2)

        for i, hab in enumerate(HABILIDADES):
            rect = pygame.Rect(70 + (i % 2) * 440, 192 + (i // 2) * 84,
                               420, 74)
            dibujar_chip(rect, NEON_CIAN, 80)
            caja = pygame.Rect(0, 0, 36, 36)
            caja.center = (rect.x + 32, rect.centery)
            dibujar_chip(caja, NEON_CIAN, 170)
            escribir(hab["tecla"], fuente_pequena, NEON_CIAN, caja.centerx,
                     caja.centery + 1)
            escribir(hab["nombre"], fuente_pequena, TEXTO, rect.x + 64,
                     rect.y + 20, ancla="midleft", espacio=1)
            escribir(f"COSTO {hab['costo']}", fuente_mini, TEXTO_TENUE,
                     rect.right - 14, rect.y + 20, ancla="midright")
            for j, linea in enumerate(envolver(hab["desc"], fuente_mini,
                                               rect.width - 84)[:2]):
                escribir(linea, fuente_mini, TEXTO_SUAVE, rect.x + 64,
                         rect.y + 42 + j * 16, ancla="midleft")

        escribir("ORBES · LA PELOTA LOS RECOGE PARA QUIEN LA GOLPEÓ",
                 fuente_mini, TEXTO_SUAVE, ANCHO // 2, 374, espacio=2)
        for i, tipo in enumerate(ORDEN_ORBES):
            info = TIPOS_ORBE[tipo]
            rect = pygame.Rect(70 + i * 218, 390, 208, 96)
            dibujar_chip(rect, info["color"], 70)
            icono = cache(("orbe_tuto", tipo), lambda: pygame.transform
                          .smoothscale(SUP_ORBE[tipo], (64, 64)))
            pantalla.blit(icono, icono.get_rect(center=(rect.x + 34,
                                                        rect.y + 34)))
            escribir(info["nombre"], fuente_mini, info["color"],
                     rect.x + 66, rect.y + 22, ancla="midleft", espacio=1)
            for j, linea in enumerate(envolver(info["desc"], fuente_mini,
                                               rect.width - 76)[:3]):
                escribir(linea, fuente_mini, TEXTO_SUAVE, rect.x + 66,
                         rect.y + 42 + j * 16, ancla="midleft")

        consejos = [
            "· Ganas energía golpeando, perdiendo puntos o con orbes de "
            "energía.",
            "· Mueve la paleta justo al golpear para darle EFECTO a la "
            "pelota.",
            "· Hay que ganar por 2 puntos de diferencia, como en el tenis.",
            "· En 2 jugadores: J1 usa W/S + 1 2 3 4, J2 usa FLECHAS + "
            "7 8 9 0.",
        ]
        for i, c in enumerate(consejos):
            escribir(c, fuente_mini, TEXTO_SUAVE, ANCHO // 2, 510 + i * 21)

        dibujar_boton_principal(RECT_ENTENDIDO, "¡ENTENDIDO!")

    # --------------------------------------------------------
    # Dibujar: cancha y partida
    # --------------------------------------------------------
    def dibujar_marcador_fondo(self):
        y = CANCHA.top + 80
        escribir(str(self.jugador.puntos), fuente_marcador, COLOR_JUGADOR,
                 CANCHA.left + CANCHA.width // 4, y, alpha=34)
        escribir(str(self.cpu.puntos), fuente_marcador, COLOR_CPU,
                 CANCHA.right - CANCHA.width // 4, y, alpha=34)

    def dibujar_orbe(self):
        if self.orbe is None:
            return
        flota = math.sin(self.t * 3) * 4
        escala = 1 + 0.08 * math.sin(self.t * 5)
        tam = int(80 * escala) // 2 * 2
        tipo = self.orbe["tipo"]
        sup = cache(("orbe_e", tipo, tam), lambda: pygame.transform
                    .smoothscale(SUP_ORBE[tipo], (tam, tam)))
        if self.orbe["vida"] < 2 and int(self.t * 10) % 2 == 0:
            sup = sup.copy()
            sup.set_alpha(90)
        pantalla.blit(sup, sup.get_rect(center=(int(self.orbe["x"]),
                                                int(self.orbe["y"] + flota))))

    def dibujar_escudo(self, lado):
        if lado.escudo_t <= 0:
            return
        sup = SUP_ESCUDO[lado.es_jugador].copy()
        parpadeo = lado.escudo_t < 2 and int(self.t * 10) % 2 == 0
        pulso = 0.35 if parpadeo else 0.75 + 0.25 * math.sin(self.t * 6)
        sup.fill((255, 255, 255, int(255 * pulso)),
                 special_flags=pygame.BLEND_RGBA_MULT)
        pantalla.blit(sup, sup.get_rect(center=(lado.x_escudo,
                                                CANCHA.centery)))

    def dibujar_pala(self, lado):
        r = lado.pala.rect
        alto = r.height
        c1, c2 = ((NEON_CIAN, CIAN_PROFUNDO) if lado.es_jugador
                  else (NEON_MORADO, MORADO_PROFUNDO))
        sup = cache(("pala", lado.es_jugador, alto),
                    lambda: crear_pala(c1, c2, alto))
        pantalla.blit(sup, (r.x - MARGEN_HALO_PALA, r.y - MARGEN_HALO_PALA))
        if lado.invertido_t > 0 and int(self.t * 8) % 2 == 0:
            pygame.draw.rect(pantalla, VERDE, r.inflate(8, 8), 2,
                             border_radius=8)

    def dibujar_pelotas(self):
        tam = self.tam_pelota()
        for p in self.pelotas:
            if p.vida is not None and p.vida < 1.5 and \
                    int(self.t * 12) % 2 == 0:
                continue      # la pelota extra parpadea antes de irse
            estela = ESTELA[(p.color, tam)]
            for i, (x, y) in enumerate(p.estela[1:], start=1):
                sup = estela[i]
                pantalla.blit(sup, sup.get_rect(center=(int(x), int(y))))
            sup = SUP_PELOTA[(p.color, tam)]
            pantalla.blit(sup, sup.get_rect(center=(int(p.x), int(p.y))))

    def dibujar_particulas(self):
        for p in self.particulas:
            t = max(0, p["vida"] / p["max"])
            color = mezclar(FONDO, p["color"], t)
            tam = 2 + int(3 * t)
            pygame.draw.rect(pantalla, color, (int(p["x"]), int(p["y"]),
                                               tam, tam))

    def dibujar_avisos(self):
        for a in self.avisos:
            sup, halo = texto_cacheado(a["texto"], fuente_aviso, a["color"],
                                       brillo=a["color"], alpha_brillo=200)
            opacidad = int(255 * min(1, a["vida"] * 2.5))
            x = max(CANCHA.left + sup.get_width() // 2 + 10,
                    min(a["x"], CANCHA.right - sup.get_width() // 2 - 10))
            for s in (halo, sup):
                s = s.copy()
                s.set_alpha(opacidad)
                pantalla.blit(s, s.get_rect(center=(int(x), int(a["y"]))))

    def dibujar_energia(self, lado):
        x = CANCHA.left if lado.es_jugador else CANCHA.right - ANCHO_MITAD
        if lado.invertido_t > 0:
            escribir(f"{self.nombre_lado(lado)} · ¡AL REVÉS!", fuente_mini,
                     VERDE, x, Y_ENERGIA, espacio=2, ancla="midleft")
        else:
            escribir(f"{self.nombre_lado(lado)} · ENERGÍA", fuente_mini,
                     TEXTO_SUAVE, x, Y_ENERGIA, espacio=2, ancla="midleft")
        escribir(str(int(lado.energia)), fuente_mini, lado.color,
                 x + ANCHO_MITAD, Y_ENERGIA, ancla="midright")

        rect = pygame.Rect(x, Y_ENERGIA + 12, ANCHO_MITAD, 8)
        pantalla.blit(cache("fondo_energia", _fondo_energia), rect)
        for h in HABILIDADES:
            mx = x + int(ANCHO_MITAD * h["costo"] / ENERGIA_MAXIMA)
            pygame.draw.line(pantalla, TEXTO_TENUE, (mx, rect.y - 3),
                             (mx, rect.bottom + 2))
        largo = int(ANCHO_MITAD * lado.energia_vista / ENERGIA_MAXIMA)
        if largo > 3:
            pantalla.blit(RELLENO_ENERGIA[lado.es_jugador],
                          (rect.x - 14, rect.y - 14),
                          area=pygame.Rect(0, 0, largo + 28, 36))

    def dibujar_slots(self, lado):
        x0 = CANCHA.left if lado.es_jugador else CANCHA.right - ANCHO_MITAD
        if lado.es_jugador:
            clave_tecla = "tecla"
        else:
            clave_tecla = None if self.contra_cpu else "tecla2"
        for i, hab in enumerate(HABILIDADES):
            estado = lado.estado_slot(hab)
            tecla = hab[clave_tecla] if clave_tecla else ""
            sup = cache(("slot", hab["id"], estado, lado.es_jugador, tecla),
                        lambda: crear_slot(hab, estado, lado.color, tecla))
            rect = pygame.Rect(x0 + i * (ANCHO_SLOT + SEPARACION_SLOT),
                               Y_SLOTS - ALTO_SLOT // 2, ANCHO_SLOT,
                               ALTO_SLOT)
            pantalla.blit(sup, (rect.x - MARGEN_SLOT, rect.y - MARGEN_SLOT))

            restante = 0
            if hab["id"] == "gigante":
                restante = lado.gigante_t / DURACION_GIGANTE
            elif hab["id"] == "escudo":
                restante = lado.escudo_t / DURACION_ESCUDO
            if restante > 0:
                pygame.draw.rect(pantalla, FONDO,
                                 (rect.x + 10, rect.bottom - 6,
                                  int((rect.width - 20) * restante), 3),
                                 border_radius=2)

    def dibujar_mensajes(self):
        cy = CANCHA.centery
        if self.pausado:
            dibujar_panel_mensaje(170, cy + 6)
            escribir("PAUSA", fuente_grande, TEXTO, ANCHO // 2, cy - 30,
                     brillo=NEON_MORADO, alpha_brillo=200)
            escribir("P PARA SEGUIR · ESC PARA IR AL MENÚ", fuente_mini,
                     TEXTO_SUAVE, ANCHO // 2, cy + 18, espacio=2)
            escribir("M SONIDO · F11 PANTALLA COMPLETA", fuente_mini,
                     TEXTO_TENUE, ANCHO // 2, cy + 42, espacio=2)
        elif self.fase == "saque":
            restante = max(1, math.ceil(TIEMPO_SAQUE - self.tiempo_fase))
            escribir(str(restante), fuente_grande, TEXTO, ANCHO // 2,
                     cy - 70, brillo=NEON_MORADO, alpha_brillo=220)
            saca = self.cpu if self.pelota.vx < 0 else self.jugador
            if not self.contra_cpu:
                quien = f"SACA {self.nombre_lado(saca)}"
            else:
                quien = "SACA KIRA" if saca is self.cpu else "SACAS TÚ"
            escribir(quien, fuente_mini, TEXTO_SUAVE, ANCHO // 2, cy - 28,
                     espacio=2)
            if self.iguales():
                escribir("IGUALES", fuente_aviso, AMARILLO, ANCHO // 2,
                         cy + 40, brillo=AMARILLO, alpha_brillo=200)
            elif self.punto_de_partido(self.jugador) or \
                    self.punto_de_partido(self.cpu):
                escribir("¡PUNTO DE PARTIDO!", fuente_aviso, ROSA_ERROR,
                         ANCHO // 2, cy + 40, brillo=ROSA_ERROR,
                         alpha_brillo=200)
        elif self.fase == "punto":
            escribir(self.mensaje, fuente, self.color_mensaje, ANCHO // 2,
                     cy - 60, brillo=self.color_mensaje, alpha_brillo=180)
            if self.submensaje:
                escribir(self.submensaje, fuente_mini, AMARILLO, ANCHO // 2,
                         cy - 26, espacio=2)
        elif self.fase == "final":
            dibujar_panel_mensaje(270, cy + 26)
            f = fuente_que_cabe(self.mensaje, [fuente_grande, fuente], 520)
            escribir(self.mensaje, f, self.color_mensaje, ANCHO // 2,
                     cy - 62, brillo=self.color_mensaje, alpha_brillo=220)
            if self.submensaje:
                escribir(self.submensaje, fuente_mini, TEXTO, ANCHO // 2,
                         cy - 22, espacio=2)
            escribir(f"MARCADOR {self.jugador.puntos} - {self.cpu.puntos} · "
                     f"RACHA MÁS LARGA {self.racha_maxima} GOLPES",
                     fuente_mini, TEXTO_SUAVE, ANCHO // 2, cy + 4, espacio=2)
            if self.nuevo_record:
                escribir("¡NUEVO RÉCORD DE RACHA!", fuente_mini, AMARILLO,
                         ANCHO // 2, cy + 28, espacio=2)
            principal = ("SIGUIENTE RONDA" if self.torneo_continua
                         else "JUGAR DE NUEVO")
            dibujar_boton_principal(RECT_BOTON, principal)
            dibujar_opcion(RECT_MENU, "MENÚ", False)

    def dibujar_partida(self):
        pantalla.blit(SUP_CANCHA, CANCHA)
        self.dibujar_marcador_fondo()
        self.dibujar_orbe()
        self.dibujar_escudo(self.jugador)
        self.dibujar_escudo(self.cpu)
        self.dibujar_pala(self.jugador)
        self.dibujar_pala(self.cpu)
        if self.fase in ("saque", "jugando"):
            self.dibujar_pelotas()
        self.dibujar_particulas()
        self.dibujar_avisos()

        if self.camara_lenta:
            pantalla.blit(VINETA, CANCHA)
            escribir("PUNTO DE PARTIDO", fuente_mini, ROSA_ERROR,
                     ANCHO // 2, CANCHA.top + 22, espacio=3)

        if self.sacudida > 0 and not self.pausado:
            fuerza = int(8 * self.sacudida / 0.25)
            zona = CANCHA.inflate(40, 40)
            capa = pantalla.subsurface(zona).copy()
            pantalla.blit(capa, (zona.x + random.randint(-fuerza, fuerza),
                                 zona.y + random.randint(-fuerza, fuerza)))

        self.dibujar_burbuja_kira()
        self.dibujar_mensajes()
        for lado in (self.jugador, self.cpu):
            self.dibujar_energia(lado)
            self.dibujar_slots(lado)

    def dibujar(self):
        dibujar_fondo(self.t)
        dibujar_tarjeta()
        if self.fase == "menu":
            self.dibujar_menu()
        elif self.fase == "tutorial":
            self.dibujar_tutorial()
        else:
            self.dibujar_partida()
        self.dibujar_encabezado()
        self.dibujar_toast()

        if self.fase == "menu":
            ayuda = ("ARRIBA/ABAJO: FILA · IZQ/DER: CAMBIAR · ENTER: JUGAR · "
                     "H: CÓMO JUGAR · M: SONIDO · F11 · ESC: SALIR")
        elif self.fase == "tutorial":
            ayuda = "ENTER: CONTINUAR · ESC: VOLVER AL MENÚ"
        elif not self.contra_cpu:
            ayuda = ("J1: W / S + 1 2 3 4  ·  J2: FLECHAS + 7 8 9 0  ·  "
                     "P PAUSA · M SONIDO · F11 · ESC MENÚ")
        else:
            ayuda = ("W / S, FLECHAS O MOUSE · 1 2 3 4 HABILIDADES · "
                     "P PAUSA · M SONIDO · F11 · ESC MENÚ")
        escribir(ayuda, fuente_mini, TEXTO_TENUE, ANCHO // 2,
                 TARJETA.bottom - 18, espacio=1)


# ============================================================
# BUCLE PRINCIPAL
# ============================================================
def main():
    reloj = pygame.time.Clock()
    juego = Juego()
    while juego.ejecutando:
        # dt con tope para que un tiron de la ventana no haga saltar
        # la pelota.
        dt_real = min(reloj.tick(60) / 1000, 0.05)
        for evento in pygame.event.get():
            juego.manejar_evento(evento)
        juego.actualizar(dt_real)
        juego.dibujar()
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
