import pygame
import random
import os
import math
from array import array

# ============================================================
# INICIAR PYGAME
# ============================================================
# El mezclador de sonido se configura antes de iniciar pygame.
# 44100 Hz en estereo para que la musica de fondo suene bien
# (los beeps 8-bit se adaptan solos a esta configuracion).
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

ANCHO = 1000
ALTO = 700
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("¿Dónde está la mascota?")

CARPETA = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# COLORES - MISMA PALETA NEON DE LA PAGINA DE KIRA
# ============================================================
FONDO = (10, 7, 18)
PANEL = (22, 16, 36)
LINEA = (179, 122, 255)
NEON_MORADO = (179, 74, 255)
NEON_CIAN = (76, 215, 240)
MORADO_PROFUNDO = (138, 43, 232)
TEXTO = (243, 238, 252)
TEXTO_SUAVE = (171, 159, 201)
TEXTO_TENUE = (118, 106, 146)
ROSA_ERROR = (255, 107, 138)
BLANCO = (255, 255, 255)
DORADO = (255, 196, 92)        # vaso dorado y tiempo limite
NARANJA = (255, 150, 70)       # mano ladrona
VERDE_NEON = (110, 255, 170)   # mano tramposa
FUCSIA = (255, 110, 210)       # impostor
GRIS_NIEBLA = (190, 186, 222)  # niebla
AZUL_HIELO = (150, 225, 255)   # poder de hielo

COLOR_NORMAL = TEXTO
COLOR_EXITO = NEON_CIAN
COLOR_ERROR = ROSA_ERROR

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
fuente = cargar_fuente("ChakraPetch-Bold.ttf", 30, 42)
fuente_ui = cargar_fuente("ChakraPetch-SemiBold.ttf", 17, 26)
fuente_pequena = cargar_fuente("ChakraPetch-SemiBold.ttf", 20, 30)
fuente_mini = cargar_fuente("ChakraPetch-SemiBold.ttf", 13, 20)

# ============================================================
# SONIDOS 8-BIT (generados por codigo, no necesitan archivos)
# ============================================================
def _onda(frecuencia, duracion, volumen, frecuencia_final=None):
    muestreo, _, canales = pygame.mixer.get_init()
    muestras = int(muestreo * duracion)
    if frecuencia_final is None:
        frecuencia_final = frecuencia
    datos = []
    fase_onda = 0.0
    for i in range(muestras):
        t = i / muestras
        f = frecuencia + (frecuencia_final - frecuencia) * t
        fase_onda += f / muestreo
        onda = 1 if (fase_onda % 1) < 0.5 else -1
        valor = int(volumen * 32767 * onda * (1 - t) ** 0.6)
        datos.extend([valor] * canales)
    return datos


def crear_beep(frecuencia, duracion, volumen=0.2, frecuencia_final=None):
    if pygame.mixer.get_init() is None:
        return None
    datos = array("h", _onda(frecuencia, duracion, volumen, frecuencia_final))
    return pygame.mixer.Sound(buffer=datos.tobytes())


def crear_melodia(notas, duracion_nota=0.08, volumen=0.18):
    # Varias notas seguidas en un solo sonido (para los "jingles").
    if pygame.mixer.get_init() is None:
        return None
    datos = array("h")
    for nota in notas:
        datos.extend(_onda(nota, duracion_nota, volumen))
    return pygame.mixer.Sound(buffer=datos.tobytes())


try:
    SONIDO_BAJADA = crear_beep(170, 0.12, 0.25, 80)
    SONIDO_MEZCLA = crear_beep(320, 0.05, 0.08, 520)
    SONIDO_ELEGIR = crear_beep(760, 0.04, 0.15)
    SONIDO_ACIERTO = crear_melodia([523, 659, 784, 1046])
    SONIDO_PREMIO = crear_melodia([784, 988, 1175, 1568, 2093], 0.07)
    SONIDO_ERROR = crear_beep(220, 0.4, 0.25, 70)
    SONIDO_TICK = crear_beep(620, 0.05, 0.12)
    SONIDO_ESPECIAL = crear_melodia([392, 523, 784], 0.1, 0.16)
    SONIDO_GOLPE = crear_beep(180, 0.12, 0.3, 50)
    SONIDO_AGARRA = crear_beep(420, 0.08, 0.14, 260)
    SONIDO_PODER = crear_melodia([660, 880, 1320], 0.06, 0.15)
    SONIDO_NEGADO = crear_beep(200, 0.08, 0.12, 150)
    SONIDO_ALERTA = crear_beep(900, 0.06, 0.14)
except Exception:
    SONIDO_BAJADA = SONIDO_MEZCLA = SONIDO_ELEGIR = SONIDO_ACIERTO = None
    SONIDO_PREMIO = SONIDO_ERROR = SONIDO_TICK = SONIDO_ESPECIAL = None
    SONIDO_GOLPE = SONIDO_AGARRA = SONIDO_PODER = SONIDO_NEGADO = None
    SONIDO_ALERTA = None


def sonar(sonido):
    if sonido is not None:
        sonido.play()

# ============================================================
# MUSICA DE FONDO (archivo "music" en la misma carpeta)
# ============================================================
VOLUMEN_MUSICA = 0.35


class Musica:
    def __init__(self):
        self.cargada = False
        self.silenciada = False

    def iniciar(self):
        # Prueba las extensiones mas comunes; tambien sirve si el archivo
        # se llama solo "music" sin extension.
        if pygame.mixer.get_init() is None:
            return
        for nombre in ("music.mp3", "music.ogg", "music.wav", "music"):
            ruta = os.path.join(CARPETA, nombre)
            if os.path.exists(ruta):
                try:
                    pygame.mixer.music.load(ruta)
                    pygame.mixer.music.set_volume(VOLUMEN_MUSICA)
                    pygame.mixer.music.play(-1)   # -1 = se repite sin fin
                    self.cargada = True
                    return
                except Exception as e:
                    print(f"No se pudo reproducir {nombre}:", e)
        print("No se encontro el archivo 'music' en la carpeta del juego.")

    def aplicar_volumen(self, pausado):
        # La musica baja durante la pausa y se apaga si se silencio (M).
        if not self.cargada:
            return
        if self.silenciada:
            volumen = 0
        elif pausado:
            volumen = VOLUMEN_MUSICA * 0.4
        else:
            volumen = VOLUMEN_MUSICA
        pygame.mixer.music.set_volume(volumen)

    def alternar(self, pausado):
        # Tecla M: silenciar / volver a activar la musica.
        if not self.cargada:
            return
        self.silenciada = not self.silenciada
        self.aplicar_volumen(pausado)

# ============================================================
# CARGAR IMAGENES (mascota.png y vasito.png)
# ============================================================
def recortar_transparencia(img):
    # Quita los bordes transparentes para que la imagen mida
    # exactamente lo que mide el dibujo.
    rect = img.get_bounding_rect(min_alpha=40)
    if rect.width == 0 or rect.height == 0:
        return img
    return img.subsurface(rect).copy()


def cargar_imagen(*nombres):
    # Prueba cada nombre de archivo hasta encontrar uno que exista.
    for nombre in nombres:
        ruta = os.path.join(CARPETA, nombre)
        if os.path.exists(ruta):
            try:
                return recortar_transparencia(
                    pygame.image.load(ruta).convert_alpha())
            except Exception as e:
                print(f"No se pudo cargar {nombre}:", e)
    print(f"No se encontro {nombres[0]} en la carpeta del juego.")
    return None


def crear_vaso_respaldo():
    # Solo se usa si no se encuentra vasito.png: un vaso rojo simple
    # boca abajo (angosto arriba, ancho abajo).
    w, h = 300, 360
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(sup, (200, 20, 20),
                        [(70, 10), (230, 10), (285, h - 20), (15, h - 20)])
    pygame.draw.ellipse(sup, (230, 50, 50), (70, 0, 160, 24))
    pygame.draw.ellipse(sup, (245, 245, 245), (0, h - 34, w, 30))
    pygame.draw.polygon(sup, (200, 20, 20),
                        [(15, h - 30), (285, h - 30), (285, h - 22), (15, h - 22)])
    return sup


mascota_original = cargar_imagen("mascota.png")
vaso_original = cargar_imagen("vasito.png", "vaso.png")
if vaso_original is None:
    vaso_original = crear_vaso_respaldo()

# ============================================================
# TIEMPOS DE UNA RONDA
# ============================================================
# Fases de una ronda:
#   "mostrar"    -> la mascota esta sentada en el suelo y los vasos flotan encima
#   "bajando"    -> los vasos bajan y la tapan
#   "mezclando"  -> los vasos se revuelven
#   "elegir"     -> el jugador hace clic en un vaso
#   "revelando"  -> el vaso elegido se levanta
#   "resultado"  -> se muestra si gano (cuenta regresiva) o perdio (boton)
TIEMPO_MOSTRAR = 1.6        # segundos que se ve la mascota antes de taparla
DURACION_BAJADA = 0.45      # lo que tardan los vasos en bajar
PAUSA_ANTES_MEZCLA = 0.35   # pausa con la mascota ya tapada
DURACION_REVELAR = 0.35     # lo que tarda en levantarse el vaso elegido
TIEMPO_PREPARACION = 3      # espera entre una victoria y la siguiente ronda

# ============================================================
# RONDAS ESPECIALES
# ============================================================
# Una ronda puede tener uno o mas "efectos" a la vez (por ejemplo
# a oscuras + mano ladrona). En CADA ronda se sortea si es especial y
# que efecto trae, asi ninguna partida se repite. Todos los efectos
# pueden salir desde la ronda "desde" (1 = desde el comienzo) y el
# "peso" dice que tan seguido sale cada uno. Ademas:
#   - el mismo efecto no sale dos rondas seguidas,
#   - lo que aun no salio en la partida tiene mas chance
#     (PRIORIDAD_NUEVO), para que aparezcan todos.
#   grupo "mezcla"   -> complica la mezcla (oscuras, carrusel, niebla)
#   grupo "eleccion" -> complica el momento de elegir (manos, impostor)
# Las rondas combinadas juntan uno de cada grupo.
INFO_EFECTOS = {
    "dorado": {
        "corto": "VASO DORADO", "color": DORADO, "mult": 2,
        "desde": 1, "peso": 0.6, "grupo": None,
        "aviso": "¡Vaso dorado! Si está ahí, puntos x2",
    },
    "ladron": {
        "corto": "MANO LADRONA", "color": NARANJA, "mult": 2,
        "desde": 1, "peso": 1.2, "grupo": "eleccion",
        "aviso": "¡Cuidado con la mano ladrona!",
    },
    "oscuras": {
        "corto": "A OSCURAS", "color": NEON_MORADO, "mult": 1,
        "desde": 1, "peso": 1.0, "grupo": "mezcla",
        "aviso": "¡Ronda a oscuras! Memorízala bien",
    },
    "carrusel": {
        "corto": "CARRUSEL", "color": NEON_CIAN, "mult": 1,
        "desde": 1, "peso": 1.0, "grupo": "mezcla",
        "aviso": "¡Carrusel! Los vasos van a girar",
    },
    "niebla": {
        "corto": "NIEBLA", "color": GRIS_NIEBLA, "mult": 1,
        "desde": 1, "peso": 1.0, "grupo": "mezcla",
        "aviso": "¡Niebla! No pierdas de vista a la mascota",
    },
    "impostor": {
        "corto": "IMPOSTOR", "color": FUCSIA, "mult": 2,
        "desde": 1, "peso": 1.0, "grupo": "eleccion",
        "aviso": "¡Hay un impostor! Sigue a la verdadera",
    },
    "tramposa": {
        "corto": "MANO TRAMPOSA", "color": VERDE_NEON, "mult": 2,
        "desde": 1, "peso": 1.0, "grupo": "eleccion",
        "aviso": "¡Mano tramposa! Golpéala antes del cambio",
    },
    "jefe": {
        "corto": "RONDA JEFE", "color": ROSA_ERROR, "mult": 3,
        "desde": None, "peso": 0, "grupo": None,
        "aviso": "¡RONDA JEFE! Puntos x3",
    },
}
# Orden en que se nombran los efectos en pantalla.
ORDEN_EFECTOS = ["jefe", "ladron", "tramposa", "impostor", "dorado",
                 "oscuras", "carrusel", "niebla"]

CADA_JEFE = 5                 # ronda jefe cada 5 rondas
NIVEL_JEFE_CON_EFECTO = 15    # desde aqui el jefe trae ademas un efecto
EXTRA_MOSTRAR_ESPECIAL = 0.8  # tiempo extra para leer el aviso

NIVEL_TIEMPO = 14             # desde aqui hay tiempo limite para elegir
NIVEL_COMBINADAS = 10         # desde aqui pueden salir dos efectos juntos
PROB_COMBINADA = 0.4
NIVEL_DOS_MANOS = 19          # desde aqui pueden salir dos manos ladronas
PROB_DOS_MANOS = 0.5
MULT_DOS_MANOS = 3            # con dos manos los puntos son x3

# Cantidad de vasos: (desde la ronda, vasos). Nunca baja.
TRAMOS_VASOS = [(1, 3), (4, 4), (8, 5), (13, 6), (18, 7), (24, 8)]
VASOS_MAXIMO = TRAMOS_VASOS[-1][1]
RONDAS_CAMBIO_VASOS = {desde for desde, _ in TRAMOS_VASOS if desde > 1}

PRIORIDAD_NUEVO = 6           # x6 de chance si aun no salio en la partida


def vasos_para_ronda(nivel):
    return max(vasos for desde, vasos in TRAMOS_VASOS if nivel >= desde)


def prob_especial(nivel):
    # Probabilidad de que una ronda (que no es jefe) sea especial:
    # 35 % en la ronda 1 y sube de a poco hasta 75 % (ronda 15).
    return min(0.75, 0.35 + 0.03 * (nivel - 1))


OSCURIDAD_MAXIMA = 205        # que tan oscuro se pone (0 a 255)

# Mano ladrona y mano tramposa
VELOCIDAD_VUELTAS = 1.4       # rapidez con que gira sobre los vasos
PAUSA_POR_VASO = 0.35         # cuanto se queda sobre cada vaso al pasearse
SALTOS_PRIMER_PASEO = (3, 5)  # vasos que recorre antes de elegir
SALTOS_PASEO = (2, 3)         # vasos que recorre en los paseos siguientes
SALTOS_TRAMPOSA = (3, 4)      # vasos que recorre la tramposa antes del cambio
TIEMPO_TEMBLOR = 0.5          # tiembla sobre el vaso elegido antes de bajar
DURACION_BAJADA_MANO = 0.25   # lo que tarda en bajar hasta el vaso
DURACION_LEVANTAR_MANO = 0.35 # lo que tarda en levantar un vaso vacio
PAUSA_SOLTAR_MANO = 0.3       # pausa antes de buscar otro vaso
DURACION_ATURDIDA = 5.0       # segundos aturdida tras un golpe
DURACION_ATURDIDA_TRAMPOSA = 0.7  # la tramposa se aturde y huye
DURACION_TRAMPA = 0.6         # lo que tarda el cambio de la tramposa
PROB_TRAMPA_MASCOTA = 0.6     # la tramposa prefiere mover a la mascota

# Carrusel
DURACION_ENTRAR_CARRUSEL = 0.45
DURACION_GIRO_CARRUSEL = 2.4
DURACION_SALIR_CARRUSEL = 0.45

# Tiempo limite
TIEMPO_LIMITE_INICIAL = 4.0   # segundos para elegir en la ronda 8
TIEMPO_LIMITE_MINIMO = 3.0    # nunca menos que esto


def tiempo_limite(nivel):
    return max(TIEMPO_LIMITE_MINIMO,
               TIEMPO_LIMITE_INICIAL - 0.1 * (nivel - NIVEL_TIEMPO))

# ============================================================
# PODERES (se compran con puntos)
# ============================================================
# Los poderes ayudan, pero poco y caro: cada uno se puede usar
# MAX_USOS_PARTIDA veces por partida (al perder se recuperan).
INFO_PODER = {
    "lupa": {"tecla": "1", "nombre": "LUPA", "color": NEON_CIAN,
             "base": 40, "por_ronda": 15},
    "hielo": {"tecla": "2", "nombre": "HIELO", "color": AZUL_HIELO,
              "base": 25, "por_ronda": 12},
}
PODERES = ["lupa", "hielo"]
MAX_USOS_PARTIDA = 1          # usos de cada poder por partida
AUMENTO_PRECIO = 1.5          # cada compra multiplica el precio
FACTOR_HIELO = 1.5            # la mezcla va 1,5 veces mas lenta
DURACION_SUBIDA_LUPA = 0.35   # lo que tardan en subir los vasos vacios

DURACION_SACUDIDA = 0.45

# ============================================================
# RECORD (se guarda en un archivo junto al juego)
# ============================================================
ARCHIVO_RECORD = os.path.join(CARPETA, "record_vasos.txt")


def cargar_record():
    try:
        with open(ARCHIVO_RECORD, encoding="utf-8") as f:
            pts, ronda = f.read().split()
            return int(pts), int(ronda)
    except Exception:
        return 0, 0


def guardar_record(pts, ronda):
    try:
        with open(ARCHIVO_RECORD, "w", encoding="utf-8") as f:
            f.write(f"{pts} {ronda}")
    except Exception as e:
        print("No se pudo guardar el record:", e)

# ============================================================
# DIFICULTAD
# ============================================================
MEZCLAS_MAXIMAS = 30          # tope de mezclas en una ronda normal
DURACION_MINIMA = 0.13        # intercambio mas rapido posible
VELOCIDAD_TOPE = 2000         # px/seg maximos al revolver


def obtener_dificultad(nivel, es_jefe=False):
    # Los vasos solo dependen de la ronda: nunca bajan (el jefe ya no
    # agrega un vaso que despues desaparecia).
    vasos_nivel = vasos_para_ronda(nivel)

    # Hasta la ronda 5 la velocidad sube rapido; despues sigue
    # subiendo de a poco hasta su tope (cerca de la ronda 15).
    if nivel <= 5:
        duracion = 0.30 - (nivel - 1) * 0.025
        pausa = 0.04 - (nivel - 1) * 0.005
        velocidad = 1400
    else:
        extra = nivel - 5
        duracion = max(DURACION_MINIMA, 0.20 - extra * 0.007)
        pausa = max(0.01, 0.02 - extra * 0.001)
        velocidad = min(VELOCIDAD_TOPE, 1400 + extra * 50)

    # Nivel 1 = 4 mezclas, nivel 2 = 6, nivel 3 = 8...
    mezclas = min(MEZCLAS_MAXIMAS, 4 + ((nivel - 1) * 2))
    if es_jefe:
        # El jefe mezcla 50 % mas y un poco mas rapido.
        mezclas = int(mezclas * 1.5)
        duracion = max(DURACION_MINIMA, duracion * 0.85)
        pausa *= 0.8

    return vasos_nivel, duracion, pausa, mezclas, velocidad


DURACION_MOVIMIENTO = 0.30    # duracion inicial de un intercambio

# ============================================================
# CONFIGURACION DE LOS VASOS
# ============================================================
ANCHO_VASO_BASE = 150
# El alto sale de la proporcion de tu imagen del vaso.
ALTO_VASO_BASE = int(
    ANCHO_VASO_BASE * vaso_original.get_height() / vaso_original.get_width()
)
ESPACIO_VASOS_BASE = 320
PROPORCION_VASO = 0.5

# Linea del suelo: aqui se sienta la mascota y aqui apoyan los vasos.
PISO_Y = 565

# Cuanto flotan los vasos sobre la mascota al comienzo de la ronda.
ALTURA_FLOTAR_BASE = 140

# Tamaño de la mascota respecto al vaso (debe quedar tapada entera).
MASCOTA_ANCHO_REL = 0.62
MASCOTA_ALTO_REL = 0.70

ANCHO_DISPONIBLE = ANCHO - 100
TOPE_SUBIDA = 230
TOPE_BAJADA = 632

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


def copia_con_alpha(img, alpha):
    copia = img.copy()
    copia.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return copia


_cache = {}


def cache(clave, fabrica):
    if clave not in _cache:
        # Los textos que cambian (puntos, ronda, cuentas) creaban una
        # entrada nueva cada vez y el cache crecia sin limite.
        # Si hay demasiados textos guardados, se borran y se regeneran.
        if clave[0] == "txt":
            textos = [k for k in _cache
                      if isinstance(k, tuple) and k[0] == "txt"]
            if len(textos) > 300:
                for k in textos:
                    del _cache[k]
        _cache[clave] = fabrica()
    return _cache[clave]


def suavizar(p):
    return p * p * (3 - 2 * p)

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


def escribir(texto, fuente_utilizada, color, x, y,
             brillo=None, alpha_brillo=170, espacio=0, ancla="center"):
    clave = ("txt", texto, id(fuente_utilizada), color, brillo,
             alpha_brillo, espacio)

    def fabricar():
        sup = render_espaciado(texto, fuente_utilizada, color, espacio)
        halo = None
        if brillo is not None:
            halo = resplandor_de(sup, brillo, 18, alpha_brillo, 5)
        return sup, halo

    sup, halo = cache(clave, fabricar)
    rect = sup.get_rect(**{ancla: (x, y)})
    if halo is not None:
        pantalla.blit(halo, halo.get_rect(center=rect.center))
    pantalla.blit(sup, rect)
    return rect


def superficie_degradado(texto, fuente_utilizada, espacio=1):
    def fabricar():
        base = render_espaciado(texto, fuente_utilizada, BLANCO, espacio)
        grad = degradado(base.get_size(), NEON_MORADO, NEON_CIAN)
        texto_color = teñir_forma(base, grad)
        halo = resplandor_de(base, NEON_MORADO, 22, 150, 5)
        return texto_color, halo

    return cache(("grad", texto, id(fuente_utilizada)), fabricar)


def escribir_degradado(texto, fuente_utilizada, x, y, espacio=1):
    sup, halo = superficie_degradado(texto, fuente_utilizada, espacio)
    pantalla.blit(halo, halo.get_rect(midleft=(x - 22, y)))
    pantalla.blit(sup, sup.get_rect(midleft=(x, y)))
    return sup.get_width()


def envolver(texto, fuente_utilizada, ancho):
    # Corta un texto en lineas que quepan en "ancho" pixeles.
    lineas = []
    actual = ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente_utilizada.size(prueba)[0] <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas

# ============================================================
# FONDO: VACIO OSCURO + ORBES DE LUZ QUE FLOTAN
# ============================================================
ORBE_MORADO = orbe(300, NEON_MORADO, 150)
ORBE_CIAN = orbe(300, NEON_CIAN, 130)
# Antes se guardaba una copia escalada cada 4 px (~19 copias de 600 px
# por orbe, unos 60-70 MB). Con pasos de 12 px son 7 copias y se ve
# igual de suave.
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


def crear_tarjeta():
    w, h = TARJETA.size
    m = 70
    sup = pygame.Surface((w + m * 2, h + m * 2), pygame.SRCALPHA)

    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(forma, (255, 255, 255, 255), forma.get_rect(),
                     border_radius=22)
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
def _crear_chip(tam, borde, alpha_borde, relleno):
    sup = pygame.Surface(tam, pygame.SRCALPHA)
    color_relleno = relleno if relleno is not None else (255, 255, 255, 13)
    pygame.draw.rect(sup, color_relleno, sup.get_rect(), border_radius=12)
    pygame.draw.rect(sup, borde + (alpha_borde,), sup.get_rect(), 1,
                     border_radius=12)
    return sup


def dibujar_chip(rect, borde=LINEA, alpha_borde=60, relleno=None):
    # Antes se creaba una imagen nueva en cada cuadro; ahora se guarda.
    sup = cache(("chip", rect.size, borde, alpha_borde, relleno),
                lambda: _crear_chip(rect.size, borde, alpha_borde, relleno))
    pantalla.blit(sup, rect)

# ============================================================
# PUNTO DE ESTADO QUE LATE (como .status-dot)
# ============================================================
def dibujar_punto_estado(x, y, t, color):
    pulso = (math.sin(t * 2 * math.pi / 1.8) + 1) / 2
    radio = 3.5 * (0.8 + 0.2 * pulso)
    # El brillo se guarda en 16 niveles (antes se copiaba cada cuadro).
    alpha = int(130 + 125 * pulso) // 8 * 8

    base = cache(("halo_punto", color), lambda: orbe(14, color, 170))
    halo = cache(("halo_punto", color, alpha),
                 lambda: copia_con_alpha(base, alpha))
    pantalla.blit(halo, halo.get_rect(center=(x, y)))
    pygame.draw.circle(pantalla, color, (x, y), max(2, int(radio)))

# ============================================================
# ICONO DE MONEDA (gema neon)
# ============================================================
def crear_moneda():
    r = 17
    forma = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(forma, (255, 255, 255, 255), (r, r), r)
    grad = degradado((r * 2, r * 2), NEON_MORADO, NEON_CIAN)
    cuerpo = teñir_forma(forma, grad)
    pygame.draw.circle(cuerpo, (255, 255, 255, 70), (r - 5, r - 6), 6)
    signo = fuente_ui.render("$", True, FONDO)
    cuerpo.blit(signo, signo.get_rect(center=(r, r + 1)))
    halo = resplandor_de(forma, NEON_MORADO, 16, 200, 4)
    halo.blit(cuerpo, (16, 16))
    return halo


def dibujar_moneda(x, y):
    sup = cache("moneda", crear_moneda)
    pantalla.blit(sup, sup.get_rect(center=(x, y)))

# ============================================================
# MEDIDAS: TAMAÑO DE VASOS, MASCOTAS Y MANO SEGUN CUANTOS VASOS HAY
# ============================================================
MARGEN_HALO = 24


def crear_mano(ancho):
    # Mano dibujada con figuras simples, con los dedos hacia abajo.
    w, h = 90, 110
    forma = pygame.Surface((w, h), pygame.SRCALPHA)
    piel = (255, 222, 236)
    pygame.draw.rect(forma, MORADO_PROFUNDO, (14, 0, 62, 22),
                     border_radius=6)                       # puño de la manga
    pygame.draw.rect(forma, NEON_MORADO, (14, 18, 62, 5))
    pygame.draw.rect(forma, piel, (12, 22, 66, 50), border_radius=20)
    for i, largo in enumerate((40, 48, 46, 38)):            # dedos
        pygame.draw.rect(forma, piel, (13 + i * 16, 50, 14, largo),
                         border_radius=7)
    pygame.draw.rect(forma, piel, (70, 34, 18, 30), border_radius=9)
    forma = recortar_transparencia(forma)
    fw, fh = forma.get_size()
    return pygame.transform.smoothscale(forma,
                                        (ancho, max(1, int(ancho * fh / fw))))


class Medidas:
    """Tamaños y dibujos que dependen de cuantos vasos hay en la ronda.

    Antes eran ~15 variables globales que se reescribian en cada ronda;
    ahora se calculan una vez por cantidad de vasos y se reutilizan."""

    def __init__(self, cantidad):
        self.cantidad = cantidad
        espacio = ANCHO_DISPONIBLE / (cantidad - 1 + PROPORCION_VASO)
        espacio = min(espacio, ESPACIO_VASOS_BASE)
        self.escala = min(1.0, espacio * PROPORCION_VASO / ANCHO_VASO_BASE)

        self.ancho_vaso = int(ANCHO_VASO_BASE * self.escala)
        self.alto_vaso = int(ALTO_VASO_BASE * self.escala)
        self.espacio = int(espacio)
        self.y_vasos = PISO_Y - self.alto_vaso      # vaso apoyado en el suelo
        self.y_flotando = self.y_vasos - int(ALTURA_FLOTAR_BASE * self.escala)

        tam = (self.ancho_vaso, self.alto_vaso)
        self.vaso_img = pygame.transform.smoothscale(vaso_original, tam)
        self.halo_normal = resplandor_de(self.vaso_img, NEON_MORADO,
                                         MARGEN_HALO, 110, 6)
        self.halo_activo = resplandor_de(self.vaso_img, NEON_CIAN,
                                         MARGEN_HALO, 255, 6)
        # El vaso dorado: el mismo vaso con un tono calido encima.
        self.dorado_img = self.vaso_img.copy()
        self.dorado_img.fill((90, 60, 0, 0),
                             special_flags=pygame.BLEND_RGBA_ADD)
        self.halo_dorado = resplandor_de(self.vaso_img, DORADO,
                                         MARGEN_HALO, 255, 6)
        # Vaso que la mano o la lupa ya levanto vacio: semitransparente.
        self.descartado_img = copia_con_alpha(self.vaso_img, 80)

        ancho_mano = max(40, int(self.ancho_vaso * 0.7))
        self.mano_img = crear_mano(ancho_mano)
        self.mano_halos = {
            nombre: resplandor_de(self.mano_img, color, MARGEN_HALO,
                                  alpha, 5)
            for nombre, color, alpha in (("ladron", NARANJA, 210),
                                         ("tramposa", VERDE_NEON, 210),
                                         ("aturdida", NEON_CIAN, 170))
        }

        self.mascota = self.halo_mascota = None
        self.impostor_img = self.halo_impostor = None
        if mascota_original is not None:
            # La mascota cabe completa debajo del vaso.
            caja_w = self.ancho_vaso * MASCOTA_ANCHO_REL
            caja_h = self.alto_vaso * MASCOTA_ALTO_REL
            mw, mh = mascota_original.get_size()
            f = min(caja_w / mw, caja_h / mh)
            tam_m = (max(1, int(mw * f)), max(1, int(mh * f)))
            self.mascota = pygame.transform.smoothscale(mascota_original,
                                                        tam_m)
            self.halo_mascota = resplandor_de(self.mascota, NEON_MORADO,
                                              30, 150, 5)
            self.halo_mascota.blit(resplandor_de(self.mascota, NEON_CIAN,
                                                 30, 90, 8), (0, 0))
            # La mascota falsa: mirando al otro lado y con otro color.
            self.impostor_img = pygame.transform.flip(self.mascota, True,
                                                      False)
            self.impostor_img.fill((255, 120, 210, 255),
                                   special_flags=pygame.BLEND_RGBA_MULT)
            self.halo_impostor = resplandor_de(self.impostor_img, FUCSIA,
                                               30, 170, 5)

    def x_posicion(self, posicion):
        inicio_x = ANCHO // 2 - ((self.cantidad - 1) * self.espacio) // 2
        return inicio_x + posicion * self.espacio


def obtener_medidas(cantidad):
    return cache(("medidas", cantidad), lambda: Medidas(cantidad))

# ============================================================
# VASO
# ============================================================
class Vaso:
    def __init__(self, posicion, med):
        self.med = med
        x = med.x_posicion(posicion)
        # Empiezan flotando sobre el suelo.
        self.x = float(x)
        self.y = float(med.y_flotando)
        self.posicion = posicion
        self.destino = posicion
        self.inicio_x = float(x)
        # Intercambio en la mezcla.
        self.moviendo = False
        self.inicio_movimiento = 0.0
        self.altura_movimiento = 0.0
        self.duracion = DURACION_MOVIMIENTO
        # Animacion vertical (bajar o levantar).
        self.y_desde = self.y
        self.y_hasta = self.y
        # Levantado vacio por una mano o por la lupa.
        self.descartado = False
        self.subida_inicio = None    # la lupa lo esta levantando
        self.subida_desde = 0.0
        # Carrusel.
        self.angulo_base = 0.0
        self.desde_x = self.desde_y = 0.0

    def rect(self):
        m = self.med
        return pygame.Rect(int(self.x - m.ancho_vaso // 2), int(self.y),
                           m.ancho_vaso, m.alto_vaso)


def mover_vertical(lista, y_hasta):
    # Prepara una animacion vertical (bajar o levantar vasos).
    for vaso in lista:
        vaso.y_desde = vaso.y
        vaso.y_hasta = float(y_hasta)

# ============================================================
# MANOS: LADRONA Y TRAMPOSA
# ============================================================
# Estados de una mano:
#   "vueltas"    -> da vueltas sobre los vasos (al mostrar y mezclar)
#   "paseando"   -> recorre varios vasos, deteniendose en cada uno
#   "apuntando"  -> se queda sobre el ultimo y tiembla
#   "bajando"    -> (ladrona) baja a agarrar ese vaso
#   "levantando" -> (ladrona) levanta un vaso vacio (queda descartado)
#   "soltando"   -> (ladrona) pausa antes de buscar otro vaso
#   "cambiando"  -> (tramposa) intercambia dos vasos
#   "aturdida"   -> el jugador la golpeo
#   "atrapada"   -> (ladrona) agarro el vaso de la mascota: pierdes
#   "huyendo"    -> se va volando
def dibujar_estrella(x, y, r, color):
    k = r * 0.3
    pygame.draw.polygon(pantalla, color, [
        (x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k),
        (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k),
    ])


class Mano:
    def __init__(self, juego, tipo, angulo):
        self.juego = juego
        self.tipo = tipo              # "ladron" o "tramposa"
        self.x = float(ANCHO // 2)
        self.y = -20.0
        self.estado = "vueltas"
        self.inicio = juego.ahora()
        self.angulo = angulo
        self.detras = False           # va detras de los vasos
        self.espera = TIEMPO_TEMBLOR
        self.ruta = []
        self.paso = 0
        self.objetivo = None
        self.sujeta = None            # vaso que tiene agarrado
        self.y_inicio = 0.0

    # ---------------- estados ----------------
    def cambiar_estado(self, estado):
        self.estado = estado
        self.inicio = self.juego.ahora()

    def huir(self):
        if self.estado == "huyendo":
            return
        self.sujeta = None
        self.detras = False
        self.cambiar_estado("huyendo")

    def golpeable(self):
        return self.estado in ("paseando", "apuntando", "bajando")

    def rect(self):
        return self.juego.med.mano_img.get_rect(
            midbottom=(int(self.x), int(self.y)))

    def agarre(self):
        # Cuanto se meten los dedos sobre el borde del vaso.
        return 14 * self.juego.med.escala

    # ---------------- acciones ----------------
    def iniciar_paseo(self, saltos):
        # Arma un recorrido por varios vasos (sin repetir el mismo dos
        # veces seguidas). El ultimo de la ruta es su objetivo; si hay otra
        # mano, intenta no elegir el mismo vaso que ella.
        juego = self.juego
        libres = juego.vasos_libres()
        if not libres:
            self.huir()
            return
        ocupados = []
        for otra in juego.manos:
            if otra is self:
                continue
            if otra.estado in ("paseando", "apuntando", "bajando"):
                ocupados.append(otra.objetivo)
            if otra.sujeta is not None:
                ocupados.append(otra.sujeta)
        cantidad = random.randint(*saltos)
        ruta = []
        anterior = None
        for i in range(cantidad):
            grupo = libres
            if i == cantidad - 1:
                grupo = [v for v in libres
                         if not any(v is o for o in ocupados)] or libres
            opciones = [v for v in grupo if v is not anterior] or grupo
            anterior = random.choice(opciones)
            ruta.append(anterior)
        self.ruta = ruta
        self.paso = 0
        self.objetivo = ruta[-1]
        self.sujeta = None
        self.detras = False
        self.cambiar_estado("paseando")

    def agarrar(self, vaso):
        juego = self.juego
        # Si otra mano ya se llevo ese vaso, busca otro.
        if vaso.descartado or any(o is not self and o.sujeta is vaso
                                  for o in juego.manos):
            self.iniciar_paseo(SALTOS_PASEO)
            return
        self.sujeta = vaso
        sonar(SONIDO_AGARRA)
        if vaso is juego.vaso_mascota:
            self.cambiar_estado("atrapada")
            juego.perder("¡LA MANO SE LLEVÓ A LA MASCOTA!")
            juego.preparar_revelado([vaso])
            juego.cambiar_fase("revelando")
        else:
            self.cambiar_estado("levantando")

    def empezar_trampa(self):
        # La tramposa intercambia su vaso con otro. Muchas veces elige
        # justo el de la mascota, para que haya que seguir el cambio.
        juego = self.juego
        vaso_a = self.objetivo
        if vaso_a.descartado:
            # La lupa levanto el vaso que iba a mover: usa otro.
            libres = juego.vasos_libres()
            if not libres:
                self.huir()
                return
            vaso_a = random.choice(libres)
        otros = [v for v in juego.vasos_libres() if v is not vaso_a]
        if not otros:
            self.huir()
            return
        if vaso_a is not juego.vaso_mascota \
                and any(v is juego.vaso_mascota for v in otros) \
                and random.random() < PROB_TRAMPA_MASCOTA:
            vaso_b = juego.vaso_mascota
        else:
            vaso_b = random.choice(otros)
        distancia_px = abs(vaso_a.x - vaso_b.x)
        duracion = max(DURACION_TRAMPA, distancia_px / 900)
        juego.iniciar_intercambio(vaso_a, vaso_b, duracion, a_arriba=True)
        self.sujeta = vaso_a
        self.cambiar_estado("cambiando")
        sonar(SONIDO_AGARRA)
        sonar(SONIDO_MEZCLA)
        juego.mensaje = "¡Hizo trampa! Sigue el cambio"
        juego.color_mensaje = VERDE_NEON

    # ---------------- cada cuadro ----------------
    def actualizar(self, dt):
        juego = self.juego
        med = juego.med
        pasado = juego.ahora() - self.inicio
        estado = self.estado
        suave = min(1, dt * 10)

        if estado == "huyendo":
            self.y -= 900 * dt

        elif estado == "vueltas":
            # Gira en una elipse sobre la fila de vasos: cuando va por
            # "atras" se dibuja detras de los vasos y un poco mas arriba.
            self.angulo += VELOCIDAD_VUELTAS * dt
            primero = med.x_posicion(0)
            ultimo = med.x_posicion(med.cantidad - 1)
            radio_x = min((ultimo - primero) / 2 + med.ancho_vaso * 0.3,
                          TARJETA.width / 2 - 70)
            radio_y = 22 * med.escala
            tope_vasos = min((v.y for v in juego.vasos if not v.moviendo),
                             default=med.y_vasos)
            seno = math.sin(self.angulo)
            objetivo_x = ANCHO / 2 + math.cos(self.angulo) * radio_x
            objetivo_y = tope_vasos + 8 * med.escala + seno * radio_y
            self.detras = seno < 0
            suave_vueltas = min(1, dt * 8)
            self.x += (objetivo_x - self.x) * suave_vueltas
            self.y += (objetivo_y - self.y) * suave_vueltas

        elif estado == "paseando":
            # Va de vaso en vaso y se detiene un momento sobre cada uno.
            vaso = self.ruta[self.paso]
            self.x += (vaso.x - self.x) * min(1, dt * 12)
            flotar = math.sin(pasado * 10) * 3
            self.y += (med.y_vasos - 26 * med.escala + flotar - self.y) \
                * suave
            if pasado >= PAUSA_POR_VASO:
                self.paso += 1
                self.inicio = juego.ahora()
                if self.paso >= len(self.ruta):
                    self.espera = TIEMPO_TEMBLOR
                    self.cambiar_estado("apuntando")

        elif estado == "apuntando":
            self.x += (self.objetivo.x - self.x) * suave
            self.y += (med.y_vasos - 26 * med.escala - self.y) * suave
            if pasado >= self.espera:
                if self.tipo == "ladron":
                    self.y_inicio = self.y
                    self.cambiar_estado("bajando")
                else:
                    self.empezar_trampa()

        elif estado == "bajando":
            p = min(1, pasado / DURACION_BAJADA_MANO)
            self.x = self.objetivo.x
            destino = med.y_vasos + self.agarre()
            self.y = self.y_inicio + (destino - self.y_inicio) * p * p
            if p >= 1:
                self.agarrar(self.objetivo)

        elif estado == "levantando":
            p = suavizar(min(1, pasado / DURACION_LEVANTAR_MANO))
            vaso = self.sujeta
            vaso.y = med.y_vasos + (med.y_flotando - med.y_vasos) * p
            self.y = vaso.y + self.agarre()
            if p >= 1:
                vaso.descartado = True
                self.sujeta = None
                self.cambiar_estado("soltando")

        elif estado == "soltando":
            self.y += (med.y_flotando - 20 * med.escala - self.y) * suave
            if pasado >= PAUSA_SOLTAR_MANO:
                self.iniciar_paseo(SALTOS_PASEO)

        elif estado == "cambiando":
            vaso = self.sujeta
            self.x = vaso.x
            self.y = vaso.y + self.agarre()
            if not any(v.moviendo for v in juego.vasos):
                self.huir()

        elif estado == "aturdida":
            self.y += (med.y_vasos - 95 * med.escala - self.y) * suave
            if self.tipo == "tramposa":
                if pasado >= DURACION_ATURDIDA_TRAMPOSA:
                    self.huir()
            elif pasado >= DURACION_ATURDIDA:
                self.iniciar_paseo(SALTOS_PASEO)

        elif estado == "atrapada":
            vaso = self.sujeta
            self.x = vaso.x
            self.y = vaso.y + self.agarre()

    def dibujar(self, t):
        med = self.juego.med
        x, y = self.x, self.y
        estado = self.estado
        pasado = self.juego.ahora() - self.inicio
        if estado == "apuntando":
            # Tiembla justo antes de actuar: es el aviso para golpearla.
            x += math.sin(t * 83) * 3
            y += math.sin(t * 61) * 2
        elif estado == "aturdida":
            x += math.sin(t * 9) * 4

        rect = med.mano_img.get_rect(midbottom=(int(x), int(y)))
        halo = med.mano_halos["aturdida" if estado == "aturdida"
                              else self.tipo]
        pantalla.blit(halo, (rect.x - MARGEN_HALO, rect.y - MARGEN_HALO))
        pantalla.blit(med.mano_img, rect)

        if estado == "aturdida":
            # Estrellitas girando sobre la mano.
            for i in range(3):
                ang = t * 5 + i * 2.094
                dibujar_estrella(rect.centerx
                                 + math.cos(ang) * rect.width * 0.45,
                                 rect.top - 6 + math.sin(ang) * 7, 6, DORADO)
            if self.tipo == "ladron":
                # Barra con el tiempo de aturdimiento que queda.
                resto = max(0, 1 - pasado / DURACION_ATURDIDA)
                barra = pygame.Rect(0, 0, rect.width, 5)
                barra.midtop = (rect.centerx, rect.bottom + 8)
                pygame.draw.rect(pantalla, (50, 40, 70), barra,
                                 border_radius=3)
                lleno = barra.copy()
                lleno.width = max(1, int(barra.width * resto))
                pygame.draw.rect(pantalla, NEON_CIAN, lleno, border_radius=3)

# ============================================================
# CARRUSEL: TODA LA FILA GIRA EN CIRCULO
# ============================================================
# Etapas: "entrar" (de la fila a la elipse), "girar" y "salir" (de
# vuelta a la fila, ahora en el orden en que quedaron).
class Carrusel:
    def __init__(self, inicio, giro):
        self.etapa = "entrar"
        self.inicio = inicio
        self.giro = giro
        self.duracion_giro = DURACION_GIRO_CARRUSEL

# ============================================================
# LUZ BAJO LOS VASOS
# ============================================================
def crear_luz_piso():
    sup = pygame.Surface((220, 60), pygame.SRCALPHA)
    pygame.draw.ellipse(sup, NEON_MORADO + (150,), (30, 18, 160, 24))
    pygame.draw.ellipse(sup, NEON_CIAN + (90,), (60, 24, 100, 12))
    return desenfocar(sup, 5)


LUZ_PISO = crear_luz_piso()
NIVELES_LUZ = 20


def crear_luz(factor, escala):
    luz = pygame.transform.smoothscale(
        LUZ_PISO,
        (max(1, int(220 * factor * escala)), max(1, int(60 * factor * escala)))
    )
    luz.fill((255, 255, 255, int(255 * factor)),
             special_flags=pygame.BLEND_RGBA_MULT)
    return luz

# ============================================================
# RONDA A OSCURAS Y NIEBLA (capas sobre el escenario)
# ============================================================
ZONA_OSCURA = pygame.Rect(TARJETA.x, 222, TARJETA.width,
                          TARJETA.bottom - 222)


def crear_oscuridad(alpha):
    w, h = ZONA_OSCURA.size
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    # Borde de arriba difuminado para que no se vea una linea dura.
    for y in range(h):
        a = alpha * min(1, y / 50)
        pygame.draw.line(sup, FONDO + (int(a),), (0, y), (w, y))
    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mascara, BLANCO, mascara.get_rect(),
                     border_bottom_left_radius=22,
                     border_bottom_right_radius=22)
    return teñir_forma(mascara, sup)


def crear_niebla(ancho):
    # Franja vertical de niebla con bordes suaves y algo de textura.
    h = ZONA_OSCURA.height
    sup = pygame.Surface((ancho, h), pygame.SRCALPHA)
    base = mezclar(PANEL, GRIS_NIEBLA, 0.55)
    for x in range(ancho):
        a = int(240 * math.sin(math.pi * x / (ancho - 1)) ** 0.6)
        pygame.draw.line(sup, base + (a,), (x, 0), (x, h))
    grumos = pygame.Surface((ancho, h), pygame.SRCALPHA)
    azar = random.Random(7)
    for _ in range(26):
        pygame.draw.circle(
            grumos, GRIS_NIEBLA + (azar.randint(25, 60),),
            (azar.randint(ancho // 5, ancho * 4 // 5), azar.randint(0, h)),
            azar.randint(20, 55))
    sup.blit(desenfocar(grumos, 6), (0, 0))
    # Se desvanece arriba para que no se vea un corte.
    mascara = pygame.Surface((ancho, h), pygame.SRCALPHA)
    for y in range(h):
        a = int(255 * min(1, y / 60))
        pygame.draw.line(mascara, (255, 255, 255, a), (0, y), (ancho, y))
    return teñir_forma(mascara, sup)

# ============================================================
# BOTONES
# ============================================================
RECT_BOTON = pygame.Rect(ANCHO // 2 - 120, 592, 240, 52)
RECT_JUGAR = pygame.Rect(0, 0, 300, 58)
RECT_JUGAR.center = (ANCHO // 2, 412)
RECT_GUIA = pygame.Rect(0, 0, 300, 50)
RECT_GUIA.center = (ANCHO // 2, 480)
RECT_VOLVER = pygame.Rect(0, 0, 220, 44)
RECT_VOLVER.center = (ANCHO // 2, TARJETA.bottom - 30)
RECT_CONTINUAR = pygame.Rect(0, 0, 280, 52)
RECT_CONTINUAR.center = (ANCHO // 2, 370)
RECT_MENU = pygame.Rect(0, 0, 280, 52)
RECT_MENU.center = (ANCHO // 2, 438)


def crear_boton(texto, tam, brillo_alpha):
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


def dibujar_boton(texto, rect):
    hover = rect.collidepoint(pygame.mouse.get_pos())
    sup = cache(("boton", texto, rect.size, hover),
                lambda: crear_boton(texto, rect.size, 255 if hover else 120))
    desplazamiento = -2 if hover else 0
    pantalla.blit(sup, sup.get_rect(center=(rect.centerx,
                                            rect.centery + desplazamiento)))

# ============================================================
# BARRA DE PROGRESO (mezcla y tiempo limite)
# ============================================================
ANCHO_BARRA = 320


def crear_barra(c1, c2):
    forma = pygame.Surface((ANCHO_BARRA, 8), pygame.SRCALPHA)
    pygame.draw.rect(forma, BLANCO, forma.get_rect(), border_radius=4)
    sup = resplandor_de(forma, c1, 14, 200, 4)
    sup.blit(teñir_forma(forma, degradado((ANCHO_BARRA, 8), c1, c2)),
             (14, 14))
    return sup


def _crear_fondo_barra():
    sup = pygame.Surface((ANCHO_BARRA, 8), pygame.SRCALPHA)
    pygame.draw.rect(sup, (255, 255, 255, 16), sup.get_rect(),
                     border_radius=4)
    return sup


def dibujar_barra(avance, texto, c1=NEON_MORADO, c2=NEON_CIAN):
    rect = pygame.Rect(ANCHO // 2 - ANCHO_BARRA // 2, 658, ANCHO_BARRA, 8)
    pantalla.blit(cache("fondo_barra", _crear_fondo_barra), rect)

    largo = int(ANCHO_BARRA * max(0, min(1, avance)))
    if largo > 4:
        barra = cache(("barra", c1, c2), lambda: crear_barra(c1, c2))
        pantalla.blit(barra, (rect.x - 14, rect.y - 14),
                      area=pygame.Rect(0, 0, largo + 28, 36))

    escribir(texto, fuente_mini, TEXTO_SUAVE, ANCHO // 2, 640, espacio=2)

# ============================================================
# CHIPS DE PODERES (abajo a la izquierda)
# ============================================================
RECT_PODER = {
    "lupa": pygame.Rect(TARJETA.x + 24, 592, 214, 36),
    "hielo": pygame.Rect(TARJETA.x + 24, 634, 214, 36),
}

# ============================================================
# LINEA DEL SUELO BAJO LOS VASOS
# ============================================================
def crear_escenario():
    w = TARJETA.width - 120
    sup = pygame.Surface((w, 40), pygame.SRCALPHA)
    linea = degradado((w, 2), NEON_MORADO, NEON_CIAN)
    mascara = pygame.Surface((w, 2), pygame.SRCALPHA)
    for i in range(w):
        t = i / (w - 1)
        a = int(255 * math.sin(t * math.pi) ** 1.5)
        pygame.draw.line(mascara, (255, 255, 255, a), (i, 0), (i, 1))
    linea = teñir_forma(mascara, linea)
    brillo = pygame.Surface((w, 40), pygame.SRCALPHA)
    brillo.blit(linea, (0, 19))
    brillo = desenfocar(brillo, 4)
    sup.blit(brillo, (0, 0))
    sup.blit(brillo, (0, 0))
    linea.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
    sup.blit(linea, (0, 19))
    return sup


ESCENARIO = crear_escenario()

# ============================================================
# GUIA: QUE HACE CADA RONDA ESPECIAL (pantalla del menu)
# ============================================================
def entradas_guia():
    def desde(e):
        ronda = INFO_EFECTOS[e]["desde"]
        return "CUALQUIER RONDA" if ronda <= 1 else f"DESDE RONDA {ronda}"
    return [
        ("VASO DORADO", DORADO, desde("dorado"),
         "Un vaso brilla dorado. Si la mascota queda debajo de él y la "
         "encuentras, ganas el doble de puntos."),
        ("MANO LADRONA", NARANJA, desde("ladron"),
         "Al final de la mezcla se pasea por los vasos para llevarse uno. "
         "Haz clic en ella para aturdirla 5 s: solo así puedes elegir. "
         "Si se lleva a la mascota, pierdes. x2"),
        ("A OSCURAS", NEON_MORADO, desde("oscuras"),
         "La luz se apaga mientras se mezclan los vasos. Fíjate bien dónde "
         "está la mascota antes de que oscurezca."),
        ("CARRUSEL", NEON_CIAN, desde("carrusel"),
         "Antes de la mezcla, todos los vasos giran en círculo y vuelven a "
         "la fila en otro orden. Sigue a la mascota con la vista."),
        ("NIEBLA", GRIS_NIEBLA, desde("niebla"),
         "Una franja de niebla va y viene de lado a lado durante la "
         "mezcla y tapa algunos vasos."),
        ("IMPOSTOR", FUCSIA, desde("impostor"),
         "Hay dos mascotas: la tuya y una falsa de otro color que mira al "
         "revés. Si eliges el vaso del impostor, pierdes. x2"),
        ("MANO TRAMPOSA", VERDE_NEON, desde("tramposa"),
         "Al final cambia dos vasos de lugar frente a ti, muchas veces el "
         "de la mascota. Golpéala antes y huye sin hacer trampa. x2"),
        ("TIEMPO LÍMITE", DORADO, f"DESDE RONDA {NIVEL_TIEMPO}",
         "Tienes de 4 a 3 segundos para elegir; si la barra se vacía, "
         "pierdes. No aplica en las rondas con mano ladrona."),
        ("DOS MANOS", NARANJA, f"DESDE RONDA {NIVEL_DOS_MANOS}",
         "A veces son dos manos ladronas. Tienes que aturdir a las dos al "
         "mismo tiempo para poder elegir. x3"),
        ("COMBINADAS", NEON_CIAN, f"DESDE RONDA {NIVEL_COMBINADAS}",
         "Se juntan dos rondas especiales: una que complica la mezcla y "
         "otra que complica la elección. Los multiplicadores se "
         "multiplican."),
        ("RONDA JEFE", ROSA_ERROR, f"CADA {CADA_JEFE} RONDAS",
         "Mezcla 50 % más y más rápido. Puntos x3. Desde la ronda "
         f"{NIVEL_JEFE_CON_EFECTO} trae además una ronda especial."),
        ("PODERES", AZUL_HIELO, "TECLAS 1 Y 2",
         "1 LUPA levanta la mitad de los vasos vacíos. 2 HIELO hace la "
         "mezcla más lenta. Cada uno se puede usar UNA sola vez por "
         "partida: guárdalo para cuando más lo necesites."),
    ]


def crear_tarjeta_guia(titulo, color, desde, texto, tam):
    w, h = tam
    sup = pygame.Surface(tam, pygame.SRCALPHA)
    pygame.draw.rect(sup, (255, 255, 255, 10), sup.get_rect(),
                     border_radius=12)
    pygame.draw.rect(sup, color + (70,), sup.get_rect(), 1,
                     border_radius=12)
    pygame.draw.circle(sup, color, (16, 15), 4)
    tit = fuente_ui.render(titulo, True, TEXTO)
    sup.blit(tit, tit.get_rect(midleft=(28, 15)))
    eti = render_espaciado(desde, fuente_mini, color, 1)
    sup.blit(eti, eti.get_rect(midright=(w - 14, 15)))
    y = 28
    for linea in envolver(texto, fuente_mini, w - 28):
        sup_linea = fuente_mini.render(linea, True, TEXTO_SUAVE)
        sup.blit(sup_linea, (14, y))
        y += fuente_mini.get_linesize()
    return sup


def dibujar_guia(t):
    dibujar_fondo(t)
    dibujar_tarjeta()
    titulo = "RONDAS ESPECIALES"
    sup, _ = superficie_degradado(titulo, fuente_titulo)
    escribir_degradado(titulo, fuente_titulo,
                       ANCHO // 2 - sup.get_width() // 2,
                       TARJETA.y + ALTO_ENCABEZADO // 2)

    tam = (440, 78)
    for i, (nombre, color, desde, texto) in enumerate(entradas_guia()):
        columna, fila = i % 2, i // 2
        x = TARJETA.x + 24 + columna * (tam[0] + 24)
        y = TARJETA.y + ALTO_ENCABEZADO + 10 + fila * (tam[1] + 4)
        tarjeta = cache(("guia", nombre, tam),
                        lambda: crear_tarjeta_guia(nombre, color, desde,
                                                   texto, tam))
        pantalla.blit(tarjeta, (x, y))

    dibujar_boton("VOLVER", RECT_VOLVER)


def _velo(alpha):
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    capa.fill(FONDO + (alpha,))
    return capa


def oscurecer_pantalla(alpha):
    capa = cache(("velo", alpha), lambda: _velo(alpha))
    pantalla.blit(capa, (0, 0))


def dibujar_pausa():
    oscurecer_pantalla(185)
    escribir("PAUSA", fuente_grande, TEXTO, ANCHO // 2, 270,
             brillo=NEON_MORADO, alpha_brillo=220)
    dibujar_boton("CONTINUAR", RECT_CONTINUAR)
    dibujar_boton("MENÚ PRINCIPAL", RECT_MENU)
    escribir("P O ESC PARA CONTINUAR", fuente_mini, TEXTO_SUAVE,
             ANCHO // 2, 500, espacio=2)


TECLAS_PODER = {
    pygame.K_1: "lupa", pygame.K_KP1: "lupa",
    pygame.K_2: "hielo", pygame.K_KP2: "hielo",
}


# ============================================================
# EL JUEGO
# ============================================================
# Todo lo que cambia mientras se juega vive dentro de esta clase
# (antes eran unas 50 variables "global").
class Juego:
    def __init__(self):
        self.musica = Musica()
        self.musica.iniciar()

        # Pantalla actual: "menu", "guia" o "jugando".
        self.estado_app = "menu"
        self.pausado = False

        # Reloj del juego: todas las animaciones usan este reloj en vez
        # de la hora real. Solo avanza mientras se juega, asi la pausa y
        # el menu congelan todo sin que las animaciones "salten".
        self.tiempo = 0.0

        self.nivel = 1
        self.puntos = 0

        self.med = obtener_medidas(3)
        self.vasos = []
        self.vaso_mascota = None
        self.vaso_impostor = None
        self.vaso_dorado = None

        self.fase = "mostrar"
        self.tiempo_fase = 0.0
        self.mezclas_realizadas = 0
        self.mensaje = ""
        self.color_mensaje = COLOR_NORMAL

        # Dificultad de la ronda actual.
        self.dur_movimiento = DURACION_MOVIMIENTO
        self.pausa_mezcla = 0.04
        self.mezclas_necesarias = 4
        self.vel_maxima = 1400

        self.perdio = False
        self.ronda_alcanzada = 1
        self.puntos_alcanzados = 0
        self.ultima_ganancia = 0
        self.ultimo_multiplicador = 1
        self.sono_bajada = False
        self.ultimo_numero_cuenta = 0

        # Rondas especiales.
        self.efectos = set()
        self.dos_manos = False
        self.novedad = ""         # texto "NUEVO · ..." de la ronda
        self.vistos = set()       # efectos que ya salieron en la partida
        self.efectos_anteriores = set()   # los de la ronda anterior
        self.oscuridad = 0.0      # 0 = luz normal, 1 = lo mas oscuro
        self.niebla = 0.0         # 0 = sin niebla, 1 = niebla completa
        self.manos = []
        self.carrusel = None

        # Tiempo limite.
        self.tiempo_limite_activo = False
        self.limite_inicio = None
        self.ultimo_tick_limite = 0

        # Poderes.
        self.compras = {"lupa": 0, "hielo": 0}   # compras en esta partida
        self.usados_ronda = set()                # usados en esta ronda
        self.factor_hielo = 1.0

        # Efectos visuales.
        self.particulas = []
        self.sacudida = 0.0

        # Record.
        self.record_puntos, self.record_ronda = cargar_record()
        self.nuevo_record = False

    # --------------------------------------------------------
    # Utilidades
    # --------------------------------------------------------
    def ahora(self):
        return self.tiempo

    def cambiar_fase(self, nueva):
        self.fase = nueva
        self.tiempo_fase = self.tiempo

    def revisar_record(self, pts, ronda):
        if pts > self.record_puntos:
            self.record_puntos, self.record_ronda = pts, ronda
            guardar_record(pts, ronda)
            self.nuevo_record = True

    def tiempo_limite(self):
        return tiempo_limite(self.nivel)

    # --------------------------------------------------------
    # Poderes: precio y usos
    # --------------------------------------------------------
    def costo_poder(self, nombre):
        info = INFO_PODER[nombre]
        precio = (info["base"] + info["por_ronda"] * self.nivel) \
            * AUMENTO_PRECIO ** self.compras[nombre]
        return int(round(precio / 5) * 5)     # redondeado a multiplos de 5

    def usos_restantes(self, nombre):
        return MAX_USOS_PARTIDA - self.compras[nombre]

    def reiniciar_poderes(self):
        # Al empezar una partida nueva (o perder) los poderes vuelven a
        # su precio base y a sus usos completos.
        for nombre in self.compras:
            self.compras[nombre] = 0

    # --------------------------------------------------------
    # Vasos
    # --------------------------------------------------------
    def crear_vasos(self):
        self.vasos = [Vaso(i, self.med) for i in range(self.med.cantidad)]
        self.vaso_mascota = random.choice(self.vasos)

    def preparar_revelado(self, levantar):
        # Al revelar, los vasos elegidos suben y el resto baja al suelo.
        # Los vasos ya descartados (levantados por la mano o la lupa) se
        # quedan arriba para no tapar al impostor.
        for vaso in self.vasos:
            vaso.y_desde = vaso.y
            arriba = vaso.descartado or any(vaso is v for v in levantar)
            vaso.y_hasta = float(self.med.y_flotando if arriba
                                 else self.med.y_vasos)
            vaso.subida_inicio = None

    def animar_vertical(self, duracion):
        progreso = min(1, (self.ahora() - self.tiempo_fase) / duracion)
        p = suavizar(progreso)
        for vaso in self.vasos:
            vaso.y = vaso.y_desde + (vaso.y_hasta - vaso.y_desde) * p
        return progreso

    def vasos_libres(self):
        # Vasos que ninguna mano levanto todavia.
        return [v for v in self.vasos if not v.descartado]

    def vasos_desbloqueados(self):
        # Con manos en la ronda, los vasos se pueden elegir solo si todas
        # las manos ladronas estan aturdidas y la tramposa ya se fue.
        for m in self.manos:
            if m.tipo == "ladron" and m.estado not in ("aturdida",
                                                       "huyendo"):
                return False
            if m.tipo == "tramposa" and m.estado != "huyendo":
                return False
        return True

    def vaso_elegible(self, vaso):
        if self.fase != "elegir" or self.pausado or vaso.descartado \
                or vaso.moviendo:
            return False
        return self.vasos_desbloqueados()

    # --------------------------------------------------------
    # Elegir los efectos de la ronda
    # --------------------------------------------------------
    def sortear(self, opciones):
        # Sorteo con pesos; lo que aun no salio en la partida pesa mas
        # y lo que salio en la ronda anterior no puede repetirse.
        opciones = [e for e in opciones
                    if e not in self.efectos_anteriores] or opciones
        pesos = [INFO_EFECTOS[e]["peso"]
                 * (PRIORIDAD_NUEVO if e not in self.vistos else 1)
                 for e in opciones]
        return random.choices(opciones, weights=pesos)[0]

    def elegir_efectos(self):
        self.efectos_anteriores = self.efectos - {"jefe"}
        self.efectos = set()
        self.dos_manos = False
        n = self.nivel

        disponibles = [
            e for e, info in INFO_EFECTOS.items()
            if info["peso"] > 0 and n >= info["desde"]
            and not (e == "impostor" and mascota_original is None)
        ]

        if n % CADA_JEFE == 0:
            # Ronda jefe (desde la 15 trae ademas un efecto al azar).
            self.efectos.add("jefe")
            if n >= NIVEL_JEFE_CON_EFECTO and disponibles:
                self.efectos.add(self.sortear(disponibles))
        elif disponibles and random.random() < prob_especial(n):
            principal = self.sortear(disponibles)
            self.efectos.add(principal)
            # Rondas combinadas: un efecto de mezcla + uno de eleccion.
            grupo = INFO_EFECTOS[principal]["grupo"]
            if n >= NIVEL_COMBINADAS and grupo is not None \
                    and random.random() < PROB_COMBINADA:
                otro_grupo = "eleccion" if grupo == "mezcla" else "mezcla"
                candidatos = [e for e in disponibles
                              if INFO_EFECTOS[e]["grupo"] == otro_grupo]
                if candidatos:
                    self.efectos.add(self.sortear(candidatos))

        if "ladron" in self.efectos and n >= NIVEL_DOS_MANOS \
                and random.random() < PROB_DOS_MANOS:
            self.dos_manos = True

        # Lo que aparece por primera vez en esta partida se marca
        # como "NUEVO" debajo del mensaje.
        nuevas = []
        if n in RONDAS_CAMBIO_VASOS:
            nuevas.append(f"{vasos_para_ronda(n)} VASOS")
        if n == NIVEL_TIEMPO:
            nuevas.append("TIEMPO LÍMITE")
        for e in self.efectos_ordenados():
            if e not in self.vistos:
                nuevas.append(INFO_EFECTOS[e]["corto"])
        if self.dos_manos and "dos_manos" not in self.vistos:
            nuevas.append("DOS MANOS")
            self.vistos.add("dos_manos")
        if len(self.efectos - {"jefe"}) >= 2 \
                and "combinadas" not in self.vistos:
            nuevas.append("COMBINADAS")
            self.vistos.add("combinadas")
        self.vistos |= self.efectos
        self.novedad = ("NUEVO · " + " + ".join(nuevas)) if nuevas else ""

    def efectos_ordenados(self):
        return [e for e in ORDEN_EFECTOS if e in self.efectos]

    def nombre_efecto(self, e):
        if e == "ladron" and self.dos_manos:
            return "DOS MANOS"
        return INFO_EFECTOS[e]["corto"]

    def multiplicador_ronda(self, vaso_elegido=None):
        # Si no se pasa un vaso, el vaso dorado cuenta como x2 (para
        # mostrarlo en el encabezado).
        mult = 1
        for e in self.efectos:
            if e == "dorado":
                if vaso_elegido is None or vaso_elegido is self.vaso_dorado:
                    mult *= 2
            elif e == "ladron" and self.dos_manos:
                mult *= MULT_DOS_MANOS
            else:
                mult *= INFO_EFECTOS[e]["mult"]
        return mult

    def etiqueta_ronda(self):
        if not self.efectos:
            return None, None
        lista = self.efectos_ordenados()
        texto = " + ".join(self.nombre_efecto(e) for e in lista)
        mult = self.multiplicador_ronda()
        if mult > 1:
            texto += f" x{mult}"
        return texto, INFO_EFECTOS[lista[0]]["color"]

    # --------------------------------------------------------
    # Nueva ronda
    # --------------------------------------------------------
    def nueva_ronda(self):
        self.perdio = False
        self.nuevo_record = False
        self.sono_bajada = False
        self.manos = []
        self.carrusel = None
        self.limite_inicio = None
        self.ultimo_tick_limite = 0
        self.usados_ronda.clear()
        self.factor_hielo = 1.0

        self.elegir_efectos()

        (cantidad, self.dur_movimiento, self.pausa_mezcla,
         self.mezclas_necesarias, self.vel_maxima) = \
            obtener_dificultad(self.nivel, "jefe" in self.efectos)
        if "carrusel" in self.efectos:
            # El carrusel ya revuelve bastante: menos intercambios despues.
            self.mezclas_necesarias = max(3,
                                          int(self.mezclas_necesarias * 0.6))

        # En las rondas con mano ladrona la presion la pone la mano.
        self.tiempo_limite_activo = (self.nivel >= NIVEL_TIEMPO
                                     and "ladron" not in self.efectos)

        self.med = obtener_medidas(cantidad)
        self.crear_vasos()
        self.vaso_dorado = (random.choice(self.vasos)
                            if "dorado" in self.efectos else None)
        self.vaso_impostor = None
        if "impostor" in self.efectos:
            self.vaso_impostor = random.choice(
                [v for v in self.vasos if v is not self.vaso_mascota])

        # Las manos aparecen desde el comienzo, dando vueltas.
        angulo = random.uniform(0, 2 * math.pi)
        if "ladron" in self.efectos:
            self.manos.append(Mano(self, "ladron", angulo))
            if self.dos_manos:
                self.manos.append(Mano(self, "ladron", angulo + math.pi))
        if "tramposa" in self.efectos:
            self.manos.append(Mano(self, "tramposa", angulo))

        self.mezclas_realizadas = 0
        lista = self.efectos_ordenados()
        if len(lista) >= 2:
            self.mensaje = "¡COMBO! " + " + ".join(self.nombre_efecto(e)
                                                   for e in lista)
            self.color_mensaje = INFO_EFECTOS[lista[0]]["color"]
        elif lista:
            e = lista[0]
            self.mensaje = INFO_EFECTOS[e]["aviso"]
            if e == "ladron" and self.dos_manos:
                self.mensaje = "¡Cuidado! ¡Son dos manos ladronas!"
            self.color_mensaje = INFO_EFECTOS[e]["color"]
        elif self.nivel in RONDAS_CAMBIO_VASOS:
            self.mensaje = f"¡Ahora son {cantidad} vasos!"
            self.color_mensaje = NEON_CIAN
        elif self.nivel == NIVEL_TIEMPO:
            self.mensaje = "¡Ahora hay tiempo límite para elegir!"
            self.color_mensaje = DORADO
        else:
            self.mensaje = "¡Mira dónde está!"
            self.color_mensaje = COLOR_NORMAL
        if self.efectos or self.novedad:
            sonar(SONIDO_ESPECIAL)
        self.cambiar_fase("mostrar")

    def tiempo_mostrar(self):
        extra = EXTRA_MOSTRAR_ESPECIAL if (self.efectos or self.novedad) \
            else 0
        return TIEMPO_MOSTRAR + extra

    def iniciar_bajada(self):
        mover_vertical(self.vasos, self.med.y_vasos)
        self.cambiar_fase("bajando")

    # --------------------------------------------------------
    # Mezcla
    # --------------------------------------------------------
    def comenzar_mezcla(self):
        for vaso in self.vasos:
            vaso.y = float(self.med.y_vasos)

        self.mezclas_realizadas = 0
        self.mensaje = "¡Sigue la mascota!"
        self.color_mensaje = COLOR_NORMAL
        self.cambiar_fase("mezclando")

        if "carrusel" in self.efectos:
            self.iniciar_carrusel()
        else:
            self.preparar_movimiento()

    def iniciar_intercambio(self, vaso_a, vaso_b, duracion, a_arriba=None):
        med = self.med
        posicion_a = vaso_a.posicion
        posicion_b = vaso_b.posicion

        vaso_a.destino = posicion_b
        vaso_b.destino = posicion_a

        vaso_a.inicio_x = vaso_a.x
        vaso_b.inicio_x = vaso_b.x

        # Un vaso pasa por arriba y el otro por abajo para no chocar.
        distancia = abs(posicion_a - posicion_b)
        altura = (80 + distancia * 25) * med.escala

        # max(0, ...) evita valores negativos si el vaso es muy alto
        # (con un negativo, el vaso que "sube" terminaria bajando).
        espacio_arriba = max(0, med.y_vasos - TOPE_SUBIDA)
        espacio_abajo = max(0, TOPE_BAJADA - (med.y_vasos + med.alto_vaso))
        subida = min(altura, espacio_arriba)
        bajada = min(altura, espacio_abajo)

        if a_arriba is None:
            a_arriba = random.random() < 0.5
        if a_arriba:
            vaso_a.altura_movimiento = subida
            vaso_b.altura_movimiento = -bajada
        else:
            vaso_a.altura_movimiento = -bajada
            vaso_b.altura_movimiento = subida

        for vaso in (vaso_a, vaso_b):
            vaso.duracion = duracion
            vaso.inicio_movimiento = self.ahora()
            vaso.moviendo = True

        vaso_a.posicion = posicion_b
        vaso_b.posicion = posicion_a

    def preparar_movimiento(self):
        if self.fase != "mezclando" or self.med.cantidad < 2 \
                or self.carrusel is not None:
            return

        vaso_a, vaso_b = random.sample(self.vasos, 2)
        # Duracion del intercambio: nunca menos que la del nivel, pero mas
        # larga si la distancia es grande (velocidad tope constante).
        # El hielo la alarga.
        distancia_px = abs(self.med.x_posicion(vaso_a.posicion)
                           - self.med.x_posicion(vaso_b.posicion))
        duracion = max(self.dur_movimiento, distancia_px / self.vel_maxima)
        self.iniciar_intercambio(vaso_a, vaso_b,
                                 duracion * self.factor_hielo)
        sonar(SONIDO_MEZCLA)

    def avanzar_vasos(self):
        # Mueve los vasos que estan intercambiandose. Devuelve True en el
        # cuadro en que termina el ultimo movimiento.
        habia_movimiento = False
        for vaso in self.vasos:
            if not vaso.moviendo:
                continue

            habia_movimiento = True
            progreso = (self.ahora() - vaso.inicio_movimiento) / vaso.duracion
            progreso = max(0, min(1, progreso))
            suave = suavizar(progreso)

            destino_x = self.med.x_posicion(vaso.destino)
            vaso.x = vaso.inicio_x + (destino_x - vaso.inicio_x) * suave

            arco = math.sin(progreso * math.pi)
            vaso.y = self.med.y_vasos - (arco * vaso.altura_movimiento)

            if progreso >= 1:
                vaso.x = destino_x
                vaso.y = self.med.y_vasos
                vaso.moviendo = False

        return habia_movimiento and not any(v.moviendo for v in self.vasos)

    def actualizar_movimiento(self):
        if self.carrusel is not None:
            self.actualizar_carrusel()
            return

        if self.avanzar_vasos():
            self.mezclas_realizadas += 1
            self.tiempo_fase = self.ahora()
            if self.mezclas_realizadas >= self.mezclas_necesarias:
                self.terminar_mezcla()

    def terminar_mezcla(self):
        self.mensaje = "¡Listo! ¿Dónde está?"
        self.color_mensaje = COLOR_NORMAL
        self.cambiar_fase("elegir")
        for m in self.manos:
            if m.tipo == "ladron":
                m.iniciar_paseo(SALTOS_PRIMER_PASEO)
            else:
                m.iniciar_paseo(SALTOS_TRAMPOSA)
        if "ladron" in self.efectos:
            self.mensaje = ("¡Aturde a las dos manos!" if self.dos_manos
                            else "¡Golpea la mano antes de que elija!")
            self.color_mensaje = NARANJA
        elif "tramposa" in self.efectos:
            self.mensaje = "¡Golpea la mano antes de que haga trampa!"
            self.color_mensaje = VERDE_NEON

    def controlar_siguiente_movimiento(self):
        if self.fase != "mezclando" or self.carrusel is not None:
            return
        if any(v.moviendo for v in self.vasos):
            return
        if self.ahora() - self.tiempo_fase >= \
                self.pausa_mezcla * self.factor_hielo:
            self.preparar_movimiento()

    # --------------------------------------------------------
    # Carrusel
    # --------------------------------------------------------
    def punto_carrusel(self, angulo):
        med = self.med
        radio_x = (med.x_posicion(med.cantidad - 1) - med.x_posicion(0)) / 2
        radio_y = 50 * med.escala
        # sin > 0 = mas abajo = mas cerca de la camara (queda delante).
        return (ANCHO / 2 + math.cos(angulo) * radio_x,
                med.y_vasos + math.sin(angulo) * radio_y)

    def iniciar_carrusel(self):
        n = self.med.cantidad
        orden = sorted(self.vasos, key=lambda v: v.posicion)
        vueltas = 2 if self.nivel >= NIVEL_COMBINADAS else 1
        giro = vueltas * 2 * math.pi \
            + random.randint(1, n - 1) * 2 * math.pi / n
        for i, vaso in enumerate(orden):
            vaso.angulo_base = math.pi - i * 2 * math.pi / n
            vaso.desde_x, vaso.desde_y = vaso.x, vaso.y
        self.carrusel = Carrusel(self.ahora(),
                                 giro * random.choice((-1, 1)))
        sonar(SONIDO_ESPECIAL)

    def actualizar_carrusel(self):
        c = self.carrusel
        med = self.med
        pasado = self.ahora() - c.inicio

        if c.etapa == "entrar":
            p = suavizar(min(1, pasado / DURACION_ENTRAR_CARRUSEL))
            for vaso in self.vasos:
                x, y = self.punto_carrusel(vaso.angulo_base)
                vaso.x = vaso.desde_x + (x - vaso.desde_x) * p
                vaso.y = vaso.desde_y + (y - vaso.desde_y) * p
            if p >= 1:
                c.etapa = "girar"
                c.inicio = self.ahora()

        elif c.etapa == "girar":
            # El hielo tambien hace mas lento el giro.
            duracion = c.duracion_giro * self.factor_hielo
            p = suavizar(min(1, pasado / duracion))
            for vaso in self.vasos:
                vaso.x, vaso.y = self.punto_carrusel(vaso.angulo_base
                                                     + c.giro * p)
            if p >= 1:
                # El nuevo orden es de izquierda a derecha.
                for posicion, vaso in enumerate(sorted(self.vasos,
                                                       key=lambda v: v.x)):
                    vaso.posicion = vaso.destino = posicion
                    vaso.desde_x, vaso.desde_y = vaso.x, vaso.y
                c.etapa = "salir"
                c.inicio = self.ahora()

        elif c.etapa == "salir":
            p = suavizar(min(1, pasado / DURACION_SALIR_CARRUSEL))
            for vaso in self.vasos:
                x = med.x_posicion(vaso.posicion)
                vaso.x = vaso.desde_x + (x - vaso.desde_x) * p
                vaso.y = vaso.desde_y + (med.y_vasos - vaso.desde_y) * p
            if p >= 1:
                for vaso in self.vasos:
                    vaso.x = vaso.inicio_x = float(
                        med.x_posicion(vaso.posicion))
                    vaso.y = float(med.y_vasos)
                self.carrusel = None
                self.tiempo_fase = self.ahora()

    def progreso_carrusel(self):
        c = self.carrusel
        if c is None:
            return 1
        pasado = self.ahora() - c.inicio
        if c.etapa == "entrar":
            return 0
        if c.etapa == "girar":
            return min(1, pasado / (c.duracion_giro * self.factor_hielo))
        return 1

    # --------------------------------------------------------
    # Elegir vaso, ganar y perder
    # --------------------------------------------------------
    def elegir_vaso(self, pos_mouse):
        if self.fase != "elegir":
            return

        # Un clic sobre una mano la golpea y no elige ningun vaso
        # (asi no se elige uno sin querer).
        if self.golpear_mano(pos_mouse):
            return

        for vaso in self.vasos:
            if not vaso.rect().collidepoint(pos_mouse):
                continue
            if not self.vaso_elegible(vaso):
                return

            for m in self.manos:
                m.huir()

            # Se levanta el vaso elegido. Si no era, tambien se levanta
            # el que tenia a la mascota para que se vea donde estaba.
            levantar = [vaso]
            if vaso is not self.vaso_mascota:
                levantar.append(self.vaso_mascota)
            self.preparar_revelado(levantar)

            sonar(SONIDO_ELEGIR)

            if vaso is self.vaso_mascota:
                self.ultimo_multiplicador = self.multiplicador_ronda(vaso)
                self.ultima_ganancia = \
                    self.nivel * 10 * self.ultimo_multiplicador
                self.puntos += self.ultima_ganancia
                self.nivel += 1
                self.mensaje = "¡CORRECTO! ¡Encontraste a la mascota!"
                self.color_mensaje = COLOR_EXITO
            elif vaso is self.vaso_impostor:
                self.perder("¡ERA EL IMPOSTOR!")
            else:
                self.perder("¡NO ERA! El juego se reinició.")

            self.cambiar_fase("revelando")
            return

    def perder(self, texto):
        self.perdio = True
        self.ronda_alcanzada = self.nivel
        self.puntos_alcanzados = self.puntos
        self.revisar_record(self.puntos_alcanzados, self.ronda_alcanzada)
        self.nivel = 1
        self.puntos = 0
        self.reiniciar_poderes()
        self.vistos = set()
        self.mensaje = texto
        self.color_mensaje = COLOR_ERROR
        self.sacudida = DURACION_SACUDIDA
        sonar(SONIDO_ERROR)
        for m in self.manos:
            if m.estado != "atrapada":
                m.huir()

    def perder_revelando(self, texto):
        # Pierde sin haber elegido: se muestra donde estaba la mascota.
        self.perder(texto)
        self.preparar_revelado([self.vaso_mascota])
        self.cambiar_fase("revelando")

    def mostrar_resultado(self):
        if not self.perdio:
            # Se mantiene el "¡CORRECTO!" a la vista durante la cuenta
            # regresiva.
            if self.ultimo_multiplicador > 1:
                self.mensaje = f"¡CORRECTO! x{self.ultimo_multiplicador}"
                self.color_mensaje = (DORADO if self.ultimo_multiplicador == 2
                                      else ROSA_ERROR)
                sonar(SONIDO_PREMIO)
            else:
                self.mensaje = "¡CORRECTO!"
                self.color_mensaje = COLOR_EXITO
                sonar(SONIDO_ACIERTO)
            self.festejo(self.vaso_mascota.x,
                         PISO_Y - self.med.alto_vaso * 0.35,
                         self.ultimo_multiplicador)
        self.cambiar_fase("resultado")

    def preparando_siguiente_ronda(self):
        return self.fase == "resultado" and not self.perdio

    def boton_visible(self):
        return self.fase == "resultado" and self.perdio

    # --------------------------------------------------------
    # Tiempo limite para elegir
    # --------------------------------------------------------
    def actualizar_tiempo_limite(self):
        if not self.tiempo_limite_activo or self.fase != "elegir":
            return
        # El reloj arranca cuando de verdad se puede elegir (por ejemplo,
        # despues de que la mano tramposa se fue).
        if self.limite_inicio is None:
            if self.vasos_desbloqueados() and \
                    not any(v.moviendo for v in self.vasos):
                self.limite_inicio = self.ahora()
            return
        resto = self.tiempo_limite() - (self.ahora() - self.limite_inicio)
        segundos = math.ceil(resto)
        if segundos != self.ultimo_tick_limite and 0 < segundos <= 3:
            self.ultimo_tick_limite = segundos
            sonar(SONIDO_ALERTA)
        if resto <= 0:
            self.perder_revelando("¡SE ACABÓ EL TIEMPO!")

    def resto_tiempo_limite(self):
        if self.limite_inicio is None:
            return self.tiempo_limite()
        return max(0.0, self.tiempo_limite()
                   - (self.ahora() - self.limite_inicio))

    # --------------------------------------------------------
    # Poderes
    # --------------------------------------------------------
    def poder_usado(self, nombre):
        return nombre in self.usados_ronda

    def candidatos_lupa(self):
        # Vasos vacios que la lupa puede levantar: no el de la mascota,
        # ni los que se estan moviendo o que tiene agarrados una mano.
        return [v for v in self.vasos_libres()
                if v is not self.vaso_mascota and not v.moviendo
                and not any(m.sujeta is v for m in self.manos)]

    def momento_poder(self, nombre):
        if self.estado_app != "jugando" or self.perdio:
            return False
        if nombre == "lupa":
            return self.fase == "elegir" and len(self.candidatos_lupa()) > 0
        return self.fase in ("mostrar", "bajando", "mezclando")

    def poder_disponible(self, nombre):
        return (not self.poder_usado(nombre)
                and self.usos_restantes(nombre) > 0
                and self.momento_poder(nombre)
                and self.puntos >= self.costo_poder(nombre))

    def poder_en_uso(self, nombre):
        if nombre == "lupa":
            return any(v.subida_inicio is not None for v in self.vasos)
        return self.factor_hielo > 1 and self.fase in ("mostrar", "bajando",
                                                       "mezclando")

    def usar_lupa(self):
        # Como el "50/50": levanta la mitad de los vasos que quedan,
        # todos vacios. Con 6 vasos quedan 3; con 4 quedan 2.
        candidatos = self.candidatos_lupa()
        cantidad = min(len(candidatos), len(self.vasos_libres()) // 2)
        for vaso in random.sample(candidatos, cantidad):
            vaso.descartado = True
            vaso.subida_inicio = self.ahora()
            vaso.subida_desde = vaso.y

    def animar_subidas_lupa(self):
        for vaso in self.vasos:
            if vaso.subida_inicio is None:
                continue
            p = min(1, (self.ahora() - vaso.subida_inicio)
                    / DURACION_SUBIDA_LUPA)
            vaso.y = vaso.subida_desde + \
                (self.med.y_flotando - vaso.subida_desde) * suavizar(p)
            if p >= 1:
                vaso.subida_inicio = None

    def usar_poder(self, nombre):
        if not self.poder_disponible(nombre):
            sonar(SONIDO_NEGADO)
            return
        self.puntos -= self.costo_poder(nombre)
        self.compras[nombre] += 1
        self.usados_ronda.add(nombre)
        if nombre == "lupa":
            self.usar_lupa()
        else:
            c = self.carrusel
            if c is not None and c.etapa == "girar":
                # Se corre el inicio para que el giro siga desde donde iba
                # (si no, los vasos saltarian hacia atras en el circulo).
                pasado = self.ahora() - c.inicio
                c.inicio = self.ahora() - pasado * FACTOR_HIELO
            self.factor_hielo = FACTOR_HIELO
        sonar(SONIDO_PODER)
        rect = RECT_PODER[nombre]
        self.chispas(rect.center, [INFO_PODER[nombre]["color"], BLANCO], 14)

    # --------------------------------------------------------
    # Manos
    # --------------------------------------------------------
    def golpear_mano(self, pos):
        # Devuelve True si el clic cayo sobre alguna mano. Si dos manos se
        # tapan entre si, se golpea primero la que todavia esta despierta
        # (asi una mano ya aturdida no "roba" el clic a la otra).
        for m in reversed(self.manos):
            if m.golpeable() and m.rect().inflate(16, 16).collidepoint(pos):
                m.cambiar_estado("aturdida")
                self.sacudida = max(self.sacudida, 0.15)
                sonar(SONIDO_GOLPE)
                self.chispas(pos, [DORADO, BLANCO, NARANJA])
                return True
        # El clic sobre una mano que no se puede golpear no elige vaso.
        for m in self.manos:
            if m.estado not in ("huyendo", "atrapada") and \
                    m.rect().inflate(16, 16).collidepoint(pos):
                return True
        return False

    def actualizar_manos(self, dt):
        for m in list(self.manos):
            m.actualizar(dt)
        self.manos[:] = [m for m in self.manos
                         if not (m.estado == "huyendo" and m.y < -80)]

    # --------------------------------------------------------
    # Particulas (chispas, confeti y nieve)
    # --------------------------------------------------------
    def festejo(self, x, y, multiplicador):
        colores = [NEON_CIAN, NEON_MORADO, BLANCO]
        if multiplicador == 2:
            colores = [DORADO, BLANCO, NEON_CIAN]
        elif multiplicador >= 3:
            colores = [ROSA_ERROR, DORADO, NEON_MORADO, BLANCO]
        cantidad = 40 + 25 * min(3, multiplicador - 1)
        for _ in range(cantidad):
            ang = random.uniform(0, 2 * math.pi)
            vel = random.uniform(140, 420)
            self.particulas.append({
                "x": x, "y": y,
                "vx": math.cos(ang) * vel,
                "vy": math.sin(ang) * vel - 180,
                "vida": random.uniform(0.6, 1.2), "max": 1.2,
                "color": random.choice(colores),
                "tam": random.randint(3, 6),
                "gravedad": 520,
            })

    def chispas(self, pos, colores, cantidad=18):
        for _ in range(cantidad):
            ang = random.uniform(0, 2 * math.pi)
            vel = random.uniform(120, 300)
            self.particulas.append({
                "x": pos[0], "y": pos[1],
                "vx": math.cos(ang) * vel, "vy": math.sin(ang) * vel,
                "vida": random.uniform(0.35, 0.6), "max": 0.6,
                "color": random.choice(colores),
                "tam": random.randint(3, 5), "gravedad": 300,
            })

    def brillito_dorado(self, vaso):
        # Chispitas que salen del vaso dorado de vez en cuando.
        r = vaso.rect()
        self.particulas.append({
            "x": random.uniform(r.left, r.right),
            "y": random.uniform(r.top, r.bottom),
            "vx": random.uniform(-15, 15), "vy": random.uniform(-50, -20),
            "vida": 0.7, "max": 0.7, "color": DORADO, "tam": 3,
            "gravedad": 0,
        })

    def copo_de_nieve(self):
        # Nieve que cae mientras el hielo esta activo.
        self.particulas.append({
            "x": random.uniform(TARJETA.left + 30, TARJETA.right - 30),
            "y": TARJETA.y + ALTO_ENCABEZADO + 10,
            "vx": random.uniform(-20, 20), "vy": random.uniform(60, 120),
            "vida": 3.5, "max": 3.5, "color": AZUL_HIELO,
            "tam": random.randint(2, 4), "gravedad": 0,
        })

    def actualizar_particulas(self, dt):
        for p in self.particulas:
            p["vy"] += p["gravedad"] * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.985
            p["vida"] -= dt
        self.particulas[:] = [p for p in self.particulas if p["vida"] > 0]

    def dibujar_particulas(self):
        for p in self.particulas:
            t = max(0, p["vida"] / p["max"])
            color = mezclar(FONDO, p["color"], min(1, t * 1.5))
            tam = max(1, int(p["tam"] * (0.5 + 0.5 * t)))
            pygame.draw.rect(pantalla, color,
                             (int(p["x"]), int(p["y"]), tam, tam))

    # --------------------------------------------------------
    # A oscuras y niebla
    # --------------------------------------------------------
    def actualizar_capas(self, dt):
        mezclando = self.fase == "mezclando"
        for nombre in ("oscuras", "niebla"):
            actual = self.oscuridad if nombre == "oscuras" else self.niebla
            objetivo = 1.0 if (nombre in self.efectos and mezclando) else 0.0
            velocidad = 2.0 if objetivo > actual else 3.5
            if actual < objetivo:
                actual = min(objetivo, actual + velocidad * dt)
            else:
                actual = max(objetivo, actual - velocidad * dt)
            if nombre == "oscuras":
                self.oscuridad = actual
            else:
                self.niebla = actual

    def dibujar_oscuridad(self):
        if self.oscuridad <= 0:
            return
        # Se guarda en 16 niveles para no crear una imagen por cuadro.
        nivel_q = max(1, round(self.oscuridad * 16))
        sup = cache(("oscuridad", nivel_q),
                    lambda: crear_oscuridad(OSCURIDAD_MAXIMA * nivel_q / 16))
        pantalla.blit(sup, ZONA_OSCURA)

    def dibujar_niebla(self, t):
        if self.niebla <= 0:
            return
        ancho = int(max(240, self.med.espacio * 1.4))
        sup = cache(("niebla", ancho), lambda: crear_niebla(ancho))
        # Va y viene de un lado al otro de la tarjeta.
        recorrido = TARJETA.width - ancho
        x = TARJETA.left + recorrido * (0.5 + 0.5 * math.sin(t * 1.75
                                                              - math.pi / 2))
        sup.set_alpha(int(255 * self.niebla))
        pantalla.set_clip(TARJETA)
        pantalla.blit(sup, (int(x), ZONA_OSCURA.y))
        pantalla.set_clip(None)
        sup.set_alpha(255)

    # --------------------------------------------------------
    # Sacudida de pantalla (al fallar)
    # --------------------------------------------------------
    def aplicar_sacudida(self):
        if self.sacudida <= 0:
            return
        fuerza = int(12 * self.sacudida / DURACION_SACUDIDA)
        copia = pantalla.copy()
        pantalla.fill(FONDO)
        pantalla.blit(copia, (random.randint(-fuerza, fuerza),
                              random.randint(-fuerza, fuerza)))

    # --------------------------------------------------------
    # Menu, pausa y partida
    # --------------------------------------------------------
    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.musica.aplicar_volumen(self.pausado)

    def volver_al_menu(self):
        if not self.perdio:
            self.revisar_record(self.puntos, self.nivel)
        self.estado_app = "menu"
        self.pausado = False
        self.nivel = 1
        self.puntos = 0
        self.vistos = set()
        self.particulas.clear()
        self.musica.aplicar_volumen(self.pausado)

    def empezar_partida(self):
        self.estado_app = "jugando"
        self.nivel = 1
        self.puntos = 0
        self.reiniciar_poderes()
        self.vistos = set()
        self.sacudida = 0.0
        self.particulas.clear()
        self.nueva_ronda()

    def al_cerrar(self):
        # Si cierra el juego a mitad de una racha, igual se guarda el
        # record.
        if self.estado_app == "jugando" and not self.perdio:
            self.revisar_record(self.puntos, self.nivel)

    # --------------------------------------------------------
    # Logica de un cuadro de juego
    # --------------------------------------------------------
    def actualizar_juego(self, dt):
        self.tiempo += dt
        t = self.tiempo
        momento = self.ahora()
        med = self.med

        if self.fase == "mostrar":
            # Los vasos flotan encima de la mascota con un leve vaiven.
            for vaso in self.vasos:
                vaso.y = med.y_flotando + math.sin(t * 2.5
                                                   + vaso.posicion) * 5
            if momento - self.tiempo_fase >= self.tiempo_mostrar():
                self.iniciar_bajada()

        elif self.fase == "bajando":
            self.animar_vertical(DURACION_BAJADA)
            if not self.sono_bajada and \
                    momento - self.tiempo_fase >= DURACION_BAJADA:
                self.sono_bajada = True
                sonar(SONIDO_BAJADA)
            if momento - self.tiempo_fase >= \
                    DURACION_BAJADA + PAUSA_ANTES_MEZCLA:
                self.comenzar_mezcla()

        elif self.fase == "mezclando":
            self.actualizar_movimiento()
            self.controlar_siguiente_movimiento()

        elif self.fase == "elegir":
            self.avanzar_vasos()             # el cambio de la mano tramposa
            self.animar_subidas_lupa()
            self.actualizar_tiempo_limite()

        elif self.fase == "revelando":
            if self.animar_vertical(DURACION_REVELAR) >= 1:
                self.mostrar_resultado()

        elif self.preparando_siguiente_ronda():
            numero = math.ceil(TIEMPO_PREPARACION
                               - (momento - self.tiempo_fase))
            if numero != self.ultimo_numero_cuenta and numero > 0:
                self.ultimo_numero_cuenta = numero
                sonar(SONIDO_TICK)
            if momento - self.tiempo_fase >= TIEMPO_PREPARACION:
                self.ultimo_numero_cuenta = 0
                self.nueva_ronda()

        # Efectos que corren en todas las fases.
        self.actualizar_manos(dt)
        self.actualizar_particulas(dt)
        self.actualizar_capas(dt)
        self.sacudida = max(0.0, self.sacudida - dt)
        if self.vaso_dorado is not None and random.random() < dt * 10:
            self.brillito_dorado(self.vaso_dorado)
        if self.factor_hielo > 1 and \
                self.fase in ("mostrar", "bajando", "mezclando") \
                and random.random() < dt * 30:
            self.copo_de_nieve()

    # --------------------------------------------------------
    # Dibujar: vasos y mascotas
    # --------------------------------------------------------
    def dibujar_luz(self, vaso):
        # Sombra/luz en el suelo: mas chica y tenue cuanto mas lejos
        # del suelo esta el vaso. Se guarda en 20 tamaños (antes se
        # reescalaba la imagen en cada cuadro y para cada vaso).
        med = self.med
        elevacion = abs(med.y_vasos - vaso.y)
        factor = max(0.35, 1 - elevacion / 200)
        nivel = round(factor * NIVELES_LUZ)
        luz = cache(("luz", nivel, med.cantidad),
                    lambda: crear_luz(nivel / NIVELES_LUZ, med.escala))
        pantalla.blit(luz, luz.get_rect(center=(int(vaso.x), PISO_Y + 4)))

    def dibujar_vaso(self, vaso):
        med = self.med
        rect = vaso.rect()

        if vaso.descartado:
            pantalla.blit(med.descartado_img, rect)
            return

        activo = (self.vaso_elegible(vaso)
                  and rect.collidepoint(pygame.mouse.get_pos()))
        es_dorado = vaso is self.vaso_dorado
        if es_dorado:
            pantalla.blit(med.halo_dorado,
                          (rect.x - MARGEN_HALO, rect.y - MARGEN_HALO))
        if activo or not es_dorado:
            halo = med.halo_activo if activo else med.halo_normal
            pantalla.blit(halo, (rect.x - MARGEN_HALO, rect.y - MARGEN_HALO))
        pantalla.blit(med.dorado_img if es_dorado else med.vaso_img, rect)

    def dibujar_figura(self, img, halo, vaso, saltar):
        rect = img.get_rect()
        salto = 0
        if saltar:
            # Saltitos de alegria mientras corre la cuenta regresiva.
            tiempo = self.ahora() - self.tiempo_fase
            salto = abs(math.sin(tiempo * 7)) * 28 * self.med.escala
        rect.midbottom = (int(vaso.x), PISO_Y - int(salto))
        pantalla.blit(halo, halo.get_rect(center=rect.center))
        pantalla.blit(img, rect)

    def dibujar_mascotas(self):
        med = self.med
        if med.mascota is None or self.vaso_mascota is None:
            return
        visibles = self.fase in ("mostrar", "bajando", "revelando",
                                 "resultado")
        # El impostor tambien se ve si una mano o la lupa levanto su vaso.
        if self.vaso_impostor is not None and (visibles or
                                               self.vaso_impostor.descartado):
            self.dibujar_figura(med.impostor_img, med.halo_impostor,
                                self.vaso_impostor, False)
        if visibles:
            self.dibujar_figura(med.mascota, med.halo_mascota,
                                self.vaso_mascota,
                                self.fase == "resultado" and not self.perdio)

    # --------------------------------------------------------
    # Dibujar: encabezado y poderes
    # --------------------------------------------------------
    def dibujar_encabezado(self, t):
        centro_y = TARJETA.y + ALTO_ENCABEZADO // 2
        x = TARJETA.x + 32

        escribir_degradado("ENCUENTRA A LA MASCOTA", fuente_titulo, x,
                           centro_y - 12)

        if self.perdio:
            estado, color_estado = "JUEGO REINICIADO", ROSA_ERROR
        elif self.fase == "mezclando":
            estado, color_estado = "MEZCLANDO", NEON_MORADO
        elif self.preparando_siguiente_ronda():
            estado, color_estado = "PREPARANDO RONDA", NEON_MORADO
        elif self.fase == "elegir":
            if not self.vasos_desbloqueados():
                estado, color_estado = "GOLPEA LA MANO", NARANJA
            else:
                estado, color_estado = "ELIGE UN VASO", NEON_CIAN
        elif self.fase in ("mostrar", "bajando"):
            estado, color_estado = "OBSERVA A LA MASCOTA", NEON_CIAN
        else:
            estado, color_estado = "KIRA · MINIJUEGO", NEON_CIAN

        etiqueta_tipo, color_tipo = self.etiqueta_ronda()
        if etiqueta_tipo and not self.perdio \
                and not self.preparando_siguiente_ronda():
            estado = f"{estado} · {etiqueta_tipo}"
            color_estado = color_tipo

        dibujar_punto_estado(x + 5, centro_y + 22, t, color_estado)
        etiqueta = cache(
            ("etq", estado),
            lambda: render_espaciado(estado, fuente_mini, TEXTO_TENUE, 2)
        )
        pantalla.blit(etiqueta, etiqueta.get_rect(midleft=(x + 16,
                                                           centro_y + 22)))

        derecha = TARJETA.right - 28
        chip_puntos = pygame.Rect(0, 0, 130, 46)
        chip_puntos.midright = (derecha, centro_y)
        dibujar_chip(chip_puntos)
        dibujar_moneda(chip_puntos.x + 26, chip_puntos.centery)
        escribir(str(self.puntos), fuente, TEXTO, chip_puntos.x + 82,
                 chip_puntos.centery + 1)

        chip_ronda = pygame.Rect(0, 0, 124, 46)
        chip_ronda.midright = (chip_puntos.x - 12, centro_y)
        dibujar_chip(chip_ronda)
        escribir("RONDA", fuente_mini, TEXTO_SUAVE, chip_ronda.x + 40,
                 chip_ronda.centery + 1, espacio=2)
        # El numero se pone rosado solo durante la ronda jefe.
        es_jefe = "jefe" in self.efectos \
            and not self.preparando_siguiente_ronda()
        color_ronda = ROSA_ERROR if es_jefe else NEON_CIAN
        escribir(str(self.nivel), fuente, color_ronda, chip_ronda.x + 96,
                 chip_ronda.centery + 1, brillo=color_ronda,
                 alpha_brillo=140)

    def dibujar_poderes(self):
        for nombre in PODERES:
            info = INFO_PODER[nombre]
            rect = RECT_PODER[nombre]
            disponible = self.poder_disponible(nombre)
            en_uso = self.poder_en_uso(nombre)
            usado = self.poder_usado(nombre)
            costo = self.costo_poder(nombre)

            # Fondo solido para que se lean aunque pase la niebla.
            fondo_chip = PANEL + (235,)
            if en_uso:
                dibujar_chip(rect, info["color"], 230,
                             mezclar(PANEL, info["color"], 0.25) + (240,))
            elif disponible:
                dibujar_chip(rect, info["color"], 170, fondo_chip)
            else:
                dibujar_chip(rect, LINEA, 40, fondo_chip)

            tecla = pygame.Rect(rect.x + 8, rect.y + 7, 22, 22)
            pygame.draw.rect(pantalla, info["color"] if disponible else
                             TEXTO_TENUE, tecla, 1, border_radius=6)
            escribir(info["tecla"], fuente_mini,
                     info["color"] if disponible else TEXTO_TENUE,
                     tecla.centerx, tecla.centery + 1)
            escribir(info["nombre"], fuente_mini,
                     TEXTO if disponible or en_uso else TEXTO_TENUE,
                     rect.x + 38, rect.centery + 1, espacio=2,
                     ancla="midleft")
            # Puntitos con los usos que quedan en la partida.
            restantes = self.usos_restantes(nombre)
            for i in range(MAX_USOS_PARTIDA):
                centro = (rect.x + 100 + i * 9, rect.centery)
                if i < restantes:
                    pygame.draw.circle(pantalla, info["color"], centro, 3)
                else:
                    pygame.draw.circle(pantalla, TEXTO_TENUE, centro, 3, 1)
            if restantes <= 0:
                derecha, color = "AGOTADO", TEXTO_TENUE
            elif usado:
                derecha, color = "USADO", TEXTO_TENUE
            else:
                derecha = f"{costo} PTS"
                color = DORADO if self.puntos >= costo else TEXTO_TENUE
            escribir(derecha, fuente_mini, color, rect.right - 10,
                     rect.centery + 1, ancla="midright")

    # --------------------------------------------------------
    # Dibujar: menu principal
    # --------------------------------------------------------
    def dibujar_menu(self, t):
        dibujar_fondo(t)
        dibujar_tarjeta()

        # Titulo centrado en el encabezado.
        titulo = "ENCUENTRA A LA MASCOTA"
        sup, _ = superficie_degradado(titulo, fuente_titulo)
        escribir_degradado(titulo, fuente_titulo,
                           ANCHO // 2 - sup.get_width() // 2,
                           TARJETA.y + ALTO_ENCABEZADO // 2)

        centro_x = ANCHO // 2
        if mascota_original is not None:
            def fabricar():
                mw, mh = mascota_original.get_size()
                f = min(180 / mw, 180 / mh)
                img = pygame.transform.smoothscale(
                    mascota_original,
                    (max(1, int(mw * f)), max(1, int(mh * f))))
                halo = resplandor_de(img, NEON_MORADO, 40, 170, 5)
                halo.blit(resplandor_de(img, NEON_CIAN, 40, 100, 8), (0, 0))
                return img, halo
            img, halo = cache("mascota_menu", fabricar)
            flotar = math.sin(t * 2.2) * 8
            rect = img.get_rect(center=(centro_x, 245 + flotar))
            pantalla.blit(halo, halo.get_rect(center=rect.center))
            pantalla.blit(img, rect)
        else:
            img = cache("vaso_menu", lambda: pygame.transform.smoothscale(
                vaso_original, (140, int(140 * vaso_original.get_height()
                                         / vaso_original.get_width()))))
            pantalla.blit(img, img.get_rect(center=(centro_x, 245)))

        dibujar_boton("JUGAR", RECT_JUGAR)
        dibujar_boton("RONDAS ESPECIALES", RECT_GUIA)

        if self.record_puntos > 0:
            escribir(f"RÉCORD {self.record_puntos} PTS · RONDA "
                     f"{self.record_ronda}",
                     fuente_mini, DORADO, centro_x, 548, espacio=2)
        else:
            escribir("TODAVÍA SIN RÉCORD", fuente_mini, TEXTO_TENUE,
                     centro_x, 548, espacio=2)

        escribir("CLIC: ELEGIR / GOLPEAR · 1-2: PODERES · P: PAUSA · "
                 "M: MÚSICA · ESC: SALIR",
                 fuente_mini, TEXTO_TENUE, centro_x, 640, espacio=1)

    # --------------------------------------------------------
    # Dibujar: partida
    # --------------------------------------------------------
    def texto_inferior(self):
        if self.fase == "elegir":
            ladronas = [m for m in self.manos if m.tipo == "ladron"
                        and m.estado != "huyendo"]
            tramposa = [m for m in self.manos if m.tipo == "tramposa"
                        and m.estado != "huyendo"]
            if tramposa:
                if tramposa[0].estado == "cambiando":
                    return "¡Sigue el cambio!"
                return "¡Haz clic en la mano antes de que haga trampa!"
            if ladronas:
                if self.vasos_desbloqueados():
                    resto = min(DURACION_ATURDIDA
                                - (self.ahora() - m.inicio)
                                for m in ladronas)
                    return ("¡Aturdida! Elige un vaso "
                            f"({max(1, math.ceil(resto))} s)")
                if len(ladronas) > 1:
                    return "¡Aturde a las dos manos para poder elegir!"
                return "¡Haz clic en la mano para aturdirla!"
            return "Sigue el vaso donde está la mascota"
        if self.fase in ("mostrar", "bajando"):
            return "Memoriza dónde está la mascota"
        return "Sigue el vaso donde está la mascota"

    def dibujar_juego(self, t):
        dibujar_fondo(t)
        dibujar_tarjeta()
        self.dibujar_encabezado(t)

        momento = self.ahora()
        if self.preparando_siguiente_ronda():
            restante = max(0, TIEMPO_PREPARACION
                           - (momento - self.tiempo_fase))
            escribir(self.mensaje, fuente_grande, self.color_mensaje,
                     ANCHO // 2, 170, brillo=self.color_mensaje,
                     alpha_brillo=220)
            escribir(f"+{self.ultima_ganancia} PUNTOS · SIGUIENTE RONDA EN "
                     f"{math.ceil(restante)}", fuente_mini,
                     TEXTO_SUAVE, ANCHO // 2, 212, espacio=2)
        else:
            escribir(self.mensaje, fuente, self.color_mensaje, ANCHO // 2,
                     175,
                     brillo=(NEON_MORADO
                             if self.color_mensaje == COLOR_NORMAL
                             else self.color_mensaje),
                     alpha_brillo=150)
            if self.novedad and not self.perdio \
                    and self.fase in ("mostrar", "bajando"):
                escribir(self.novedad, fuente_mini, DORADO, ANCHO // 2,
                         212, espacio=3)
            if self.perdio:
                escribir(
                    f"LLEGASTE A LA RONDA {self.ronda_alcanzada} CON "
                    f"{self.puntos_alcanzados} PUNTOS",
                    fuente_mini, TEXTO_SUAVE, ANCHO // 2, 212, espacio=2
                )
                if self.nuevo_record:
                    escribir("¡NUEVO RÉCORD!", fuente_pequena, DORADO,
                             ANCHO // 2, 240, brillo=DORADO,
                             alpha_brillo=200, espacio=2)

        # Suelo y luces bajo los vasos.
        pantalla.blit(ESCENARIO,
                      ESCENARIO.get_rect(center=(ANCHO // 2, PISO_Y)))
        for vaso in self.vasos:
            self.dibujar_luz(vaso)

        # Las mascotas van sentadas en el suelo y se dibujan ANTES de los
        # vasos, asi el vaso queda encima y las tapa.
        self.dibujar_mascotas()

        # Las manos que van por "atras" en sus vueltas quedan detras de
        # los vasos; el resto va encima de ellos.
        for m in self.manos:
            if m.detras:
                m.dibujar(t)

        # Se dibujan de arriba hacia abajo: el vaso que pasa "por abajo"
        # (mas cerca de la camara) queda delante del que pasa por arriba
        # y de los que estan quietos, asi no se cruzan al reves.
        for vaso in sorted(self.vasos, key=lambda v: v.y):
            self.dibujar_vaso(vaso)

        for m in self.manos:
            if not m.detras:
                m.dibujar(t)

        self.dibujar_particulas()
        self.dibujar_niebla(t)
        self.dibujar_oscuridad()

        # Record guardado (abajo a la derecha).
        record_visible = max(self.record_puntos, self.puntos)
        if record_visible > 0:
            escribir(f"RÉCORD {record_visible} PTS", fuente_mini,
                     TEXTO_TENUE, TARJETA.right - 32, TARJETA.bottom - 26,
                     espacio=2, ancla="midright")

        # Informacion de abajo.
        if self.fase == "mezclando":
            if self.carrusel is not None:
                dibujar_barra(self.progreso_carrusel(), "CARRUSEL")
            else:
                actual = min(self.mezclas_realizadas + 1,
                             self.mezclas_necesarias)
                dibujar_barra(
                    self.mezclas_realizadas
                    / max(1, self.mezclas_necesarias),
                    f"MEZCLA {actual} / {self.mezclas_necesarias}")
        elif self.boton_visible():
            dibujar_boton("JUGAR DE NUEVO", RECT_BOTON)
        elif self.fase == "elegir" and self.tiempo_limite_activo \
                and self.limite_inicio is not None:
            resto = self.resto_tiempo_limite()
            dibujar_barra(resto / self.tiempo_limite(),
                          f"ELIGE RÁPIDO · {max(1, math.ceil(resto))} S",
                          ROSA_ERROR, DORADO)
        else:
            escribir(self.texto_inferior(), fuente_pequena, TEXTO_TENUE,
                     ANCHO // 2, 655)

        self.dibujar_poderes()
        self.aplicar_sacudida()

    def dibujar(self, tiempo_real):
        if self.estado_app == "menu":
            self.dibujar_menu(tiempo_real)
        elif self.estado_app == "guia":
            dibujar_guia(tiempo_real)
        else:
            self.dibujar_juego(self.tiempo)
            if self.pausado:
                dibujar_pausa()

    # --------------------------------------------------------
    # Eventos
    # --------------------------------------------------------
    def manejar_evento(self, evento):
        # Devuelve False si hay que cerrar el juego.
        if evento.type == pygame.QUIT:
            return False

        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_m:
            self.musica.alternar(self.pausado)
            return True

        clic = (evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1)
        tecla = evento.key if evento.type == pygame.KEYDOWN else None

        if self.estado_app == "menu":
            if tecla == pygame.K_ESCAPE:
                return False
            if tecla in (pygame.K_SPACE, pygame.K_RETURN) or \
                    (clic and RECT_JUGAR.collidepoint(evento.pos)):
                self.empezar_partida()
            elif tecla == pygame.K_g or \
                    (clic and RECT_GUIA.collidepoint(evento.pos)):
                self.estado_app = "guia"
            return True

        if self.estado_app == "guia":
            if tecla in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_g) or \
                    (clic and RECT_VOLVER.collidepoint(evento.pos)):
                self.estado_app = "menu"
            return True

        if self.pausado:
            if tecla in (pygame.K_p, pygame.K_ESCAPE):
                self.alternar_pausa()
            elif clic and RECT_CONTINUAR.collidepoint(evento.pos):
                self.alternar_pausa()
            elif clic and RECT_MENU.collidepoint(evento.pos):
                self.volver_al_menu()
            return True

        if tecla in (pygame.K_p, pygame.K_ESCAPE):
            self.alternar_pausa()
        elif tecla in TECLAS_PODER:
            self.usar_poder(TECLAS_PODER[tecla])
        elif tecla in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) \
                and self.boton_visible():
            # ESPACIO o ENTER sirven para "jugar de nuevo" despues de perder.
            self.nueva_ronda()
        elif clic:
            if self.boton_visible() and RECT_BOTON.collidepoint(evento.pos):
                self.nueva_ronda()
                return True
            for nombre, rect in RECT_PODER.items():
                if rect.collidepoint(evento.pos):
                    self.usar_poder(nombre)
                    return True
            self.elegir_vaso(evento.pos)
        return True

# ============================================================
# BUCLE PRINCIPAL
# ============================================================
def main():
    reloj = pygame.time.Clock()
    juego = Juego()
    ejecutando = True
    tiempo_real = 0.0
    while ejecutando:
        dt = min(reloj.tick(60) / 1000, 0.05)
        tiempo_real += dt

        for evento in pygame.event.get():
            if not juego.manejar_evento(evento):
                ejecutando = False

        if not ejecutando:
            juego.al_cerrar()
            break

        if juego.estado_app == "jugando" and not juego.pausado:
            juego.actualizar_juego(dt)
        juego.dibujar(tiempo_real)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
