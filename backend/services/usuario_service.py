"""
Servicio de usuarios: registro, verificación de correo, login, perfil e historial.
Las contraseñas y los códigos se guardan con hash (werkzeug), nunca en texto plano.
"""

import secrets
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, delete
from werkzeug.security import generate_password_hash, check_password_hash

from backend.config import (CODIGO_MINUTOS_VALIDEZ, CODIGO_MAX_INTENTOS, CODIGO_SEGUNDOS_REENVIO,
                            RETENCION_HISTORIAL_DIAS)
from backend.database import SessionLocal
from backend.models.usuario import Usuario
from backend.models.chat import Chat


class ErrorUsuario(Exception):
    """Error de negocio que se muestra tal cual al usuario."""


HORAS_CUENTA_SIN_VERIFICAR = 24   # después se borra y libera el correo y el nombre

MSG_NOMBRE_OCUPADO = "Ese nombre ya está en uso. Elige otro (por ejemplo, agrega tu apellido o un número)."


def _nombre_ocupado(db, nombre: str, excepto_id: int | None = None) -> bool:
    """El nombre es único sin importar mayúsculas: «Cony», «cony» y «CONY» son el mismo."""
    consulta = select(Usuario.id).where(func.lower(Usuario.nombre) == nombre.strip().lower())
    if excepto_id is not None:
        consulta = consulta.where(Usuario.id != excepto_id)
    return db.scalar(consulta.limit(1)) is not None


def _limpiar_no_verificados(db) -> None:
    """Borra cuentas que nunca verificaron su correo después de 24 h (liberan nombre y correo)."""
    limite = datetime.utcnow() - timedelta(hours=HORAS_CUENTA_SIN_VERIFICAR)
    db.execute(delete(Usuario).where(Usuario.email_verificado.is_(False), Usuario.creado_en < limite))


# ---------------------------------------------------------------- registro y login
def registrar(nombre: str, email: str, password: str, acepta_privacidad: bool = True) -> Usuario:
    """
    Crea la cuenta SIN verificar. El correo y el nombre de usuario son únicos.
    Si ya existe una cuenta con ese correo que nunca se verificó (por ejemplo,
    alguien no recibió el código), se reemplazan su nombre y contraseña en vez
    de bloquear el correo.
    """
    with SessionLocal() as db:
        _limpiar_no_verificados(db)
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if usuario and usuario.email_verificado:
            raise ErrorUsuario("Ya existe una cuenta con ese correo.")
        if _nombre_ocupado(db, nombre, excepto_id=usuario.id if usuario else None):
            raise ErrorUsuario(MSG_NOMBRE_OCUPADO)
        if not acepta_privacidad:
            raise ErrorUsuario("Para crear la cuenta debes aceptar la política de privacidad.")
        if usuario:
            usuario.nombre = nombre
            usuario.password_hash = generate_password_hash(password)
            usuario.acepta_privacidad_en = datetime.utcnow()
        else:
            usuario = Usuario(
                nombre=nombre, email=email, password_hash=generate_password_hash(password),
                email_verificado=False, consolas=[], generos=[],
                acepta_privacidad_en=datetime.utcnow(),
            )
            db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario


def autenticar(email: str, password: str) -> Usuario | None:
    with SessionLocal() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if usuario and check_password_hash(usuario.password_hash, password):
            return usuario
        return None


def obtener_por_id(usuario_id: int) -> Usuario | None:
    with SessionLocal() as db:
        return db.get(Usuario, usuario_id)


def obtener_por_email(email: str) -> Usuario | None:
    with SessionLocal() as db:
        return db.scalar(select(Usuario).where(Usuario.email == email))


# ---------------------------------------------------------------- verificación de correo
def nuevo_codigo(usuario_id: int) -> tuple[Usuario, str]:
    """Genera un código de 6 dígitos, guarda su hash y lo devuelve para enviarlo."""
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            raise ErrorUsuario("Usuario no encontrado.")
        ahora = datetime.utcnow()
        if usuario.codigo_enviado_en:
            espera = CODIGO_SEGUNDOS_REENVIO - (ahora - usuario.codigo_enviado_en).total_seconds()
            if espera > 0:
                raise ErrorUsuario(f"Espera {int(espera) + 1} segundos antes de pedir otro código.")
        codigo = f"{secrets.randbelow(10**6):06d}"
        usuario.codigo_hash = generate_password_hash(codigo)
        usuario.codigo_expira = ahora + timedelta(minutes=CODIGO_MINUTOS_VALIDEZ)
        usuario.codigo_intentos = 0
        usuario.codigo_enviado_en = ahora
        db.commit()
        db.refresh(usuario)
        return usuario, codigo


def eliminar_no_verificado(usuario_id: int) -> None:
    """Borra una cuenta que nunca se verificó (por ejemplo, correo inexistente)."""
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if usuario and not usuario.email_verificado:
            db.delete(usuario)
            db.commit()


def anular_envio(usuario_id: int) -> None:
    """Si el correo no se pudo enviar, permite reintentar de inmediato."""
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if usuario:
            usuario.codigo_enviado_en = None
            db.commit()


def verificar_codigo(email: str, codigo: str) -> Usuario:
    with SessionLocal() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if not usuario:
            raise ErrorUsuario("Código incorrecto o vencido.")
        if usuario.email_verificado:
            return usuario
        if not usuario.codigo_hash or not usuario.codigo_expira or datetime.utcnow() > usuario.codigo_expira:
            raise ErrorUsuario("El código venció. Pide uno nuevo con «Reenviar código».")
        if usuario.codigo_intentos >= CODIGO_MAX_INTENTOS:
            raise ErrorUsuario("Demasiados intentos. Pide un código nuevo con «Reenviar código».")
        if not check_password_hash(usuario.codigo_hash, codigo):
            usuario.codigo_intentos += 1
            db.commit()
            quedan = CODIGO_MAX_INTENTOS - usuario.codigo_intentos
            raise ErrorUsuario(f"Código incorrecto. Te quedan {quedan} intento(s)." if quedan
                               else "Código incorrecto. Pide un código nuevo con «Reenviar código».")
        usuario.email_verificado = True
        usuario.codigo_hash = None
        usuario.codigo_expira = None
        usuario.codigo_intentos = 0
        db.commit()
        db.refresh(usuario)
        return usuario


# ---------------------------------------------------------------- perfil e historial
def actualizar_perfil(usuario_id: int, nombre: str, fecha_nacimiento: date | None,
                      consolas: list, generos: list) -> Usuario:
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            raise ErrorUsuario("Usuario no encontrado.")
        if _nombre_ocupado(db, nombre, excepto_id=usuario.id):
            raise ErrorUsuario(MSG_NOMBRE_OCUPADO)
        usuario.nombre = nombre
        usuario.fecha_nacimiento = fecha_nacimiento
        usuario.consolas = consolas
        usuario.generos = generos
        usuario.perfil_completo = True
        db.commit()
        db.refresh(usuario)
        return usuario


def guardar_chat(usuario_id: int, mensaje: str, respuesta: str,
                 tokens_entrada: int = 0, tokens_salida: int = 0, latencia_ms: int = 0) -> None:
    with SessionLocal() as db:
        db.add(Chat(usuario_id=usuario_id, mensaje=mensaje, respuesta=respuesta,
                    tokens_entrada=tokens_entrada, tokens_salida=tokens_salida, latencia_ms=latencia_ms))
        db.commit()


def ultimos_turnos(usuario_id: int, cantidad: int = 2, minutos: int = 30) -> list[dict]:
    """Memoria corta para el LLM: los últimos turnos de los últimos N minutos."""
    desde = datetime.utcnow() - timedelta(minutes=minutos)
    with SessionLocal() as db:
        filas = db.scalars(
            select(Chat).where(Chat.usuario_id == usuario_id, Chat.creado_en >= desde)
            .order_by(Chat.creado_en.desc(), Chat.id.desc()).limit(cantidad)
        ).all()
        return [{"mensaje": c.mensaje, "respuesta": c.respuesta} for c in reversed(filas)]


def historial(usuario_id: int, limite: int = 20) -> list[dict]:
    with SessionLocal() as db:
        filas = db.scalars(
            select(Chat).where(Chat.usuario_id == usuario_id)
            .order_by(Chat.creado_en.desc(), Chat.id.desc()).limit(limite)
        ).all()
        return [c.a_dict() for c in reversed(filas)]


# ---------------------------------------------------------------- derechos ARCO (Ley 19.628 / 21.719)
# Acceso:        exportar_datos()       -> GET    /api/cuenta/datos
# Rectificación: actualizar_perfil()    -> PUT    /api/perfil
# Cancelación:   eliminar_cuenta()      -> DELETE /api/cuenta   (borra usuario + historial)
#                borrar_historial()     -> DELETE /api/chat/historial
# Oposición:     el usuario puede borrar su historial y Kira deja de usarlo como memoria.
#
# La base vectorial (ChromaDB) NO guarda datos de usuarios: solo fichas públicas de
# juegos. Por eso al borrar una cuenta no hay embeddings personales que purgar.

def exportar_datos(usuario_id: int) -> dict:
    """Todos los datos personales que Kira guarda de la persona, en formato portable (JSON)."""
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            raise ErrorUsuario("Usuario no encontrado.")
        chats = db.scalars(select(Chat).where(Chat.usuario_id == usuario_id).order_by(Chat.creado_en)).all()
        datos = usuario.a_dict()
        datos["creado_en"] = usuario.creado_en.isoformat() if usuario.creado_en else None
        return {
            "usuario": datos,
            "historial_chat": [c.a_dict() for c in chats],
            "tratamiento": {
                "finalidad": "Personalizar recomendaciones de videojuegos y mantener el contexto de la conversación.",
                "proveedor_externo": "Google Gemini (API). Recibe los mensajes con los datos personales enmascarados.",
                "retencion_historial_dias": RETENCION_HISTORIAL_DIAS,
            },
            "exportado_en": datetime.utcnow().isoformat(),
        }


def borrar_historial(usuario_id: int) -> int:
    with SessionLocal() as db:
        borradas = db.execute(delete(Chat).where(Chat.usuario_id == usuario_id)).rowcount
        db.commit()
        return borradas or 0


def eliminar_cuenta(usuario_id: int, password: str) -> None:
    """Borra la cuenta y todo su historial. Pide la contraseña para confirmar."""
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            raise ErrorUsuario("Usuario no encontrado.")
        if not check_password_hash(usuario.password_hash, password or ""):
            raise ErrorUsuario("Contraseña incorrecta.")
        db.execute(delete(Chat).where(Chat.usuario_id == usuario_id))
        db.delete(usuario)
        db.commit()


def purgar_historial_antiguo(dias: int = RETENCION_HISTORIAL_DIAS) -> int:
    """Minimización: borra conversaciones más antiguas que el plazo de retención."""
    limite = datetime.utcnow() - timedelta(days=dias)
    with SessionLocal() as db:
        borradas = db.execute(delete(Chat).where(Chat.creado_en < limite)).rowcount
        db.commit()
        return borradas or 0
