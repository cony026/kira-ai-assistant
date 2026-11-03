"""
Servicio de correo: envía el código de verificación por SMTP (por ejemplo Gmail).

Si SMTP_USUARIO no está configurado en el .env, el código se imprime en la
consola del servidor (modo desarrollo) para poder probar sin correo real.
"""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from backend.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USUARIO, SMTP_CLAVE, SMTP_REMITENTE,
    CORREO_MODO_CONSOLA, CODIGO_MINUTOS_VALIDEZ,
)


class ErrorCorreo(Exception):
    """No se pudo enviar el correo."""


class CorreoInexistente(ErrorCorreo):
    """El servidor de correo respondió que esa casilla no existe."""


def _mensaje(destino: str, nombre: str, codigo: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Tu código de verificación de Kira IA: {codigo}"
    msg["From"] = formataddr(("Kira IA", SMTP_REMITENTE))
    msg["To"] = destino
    msg.set_content(
        f"Hola {nombre},\n\n"
        f"Tu código para verificar tu correo en Kira IA es: {codigo}\n\n"
        f"Vence en {CODIGO_MINUTOS_VALIDEZ} minutos. Si no creaste una cuenta en Kira IA, ignora este mensaje.\n"
    )
    msg.add_alternative(f"""\
<div style="font-family:Arial,sans-serif;max-width:460px;margin:auto;padding:24px;border:1px solid #ddd;border-radius:12px">
  <h2 style="margin:0 0 12px;color:#6b2fd6">Kira IA</h2>
  <p>Hola {nombre},</p>
  <p>Tu código para verificar tu correo es:</p>
  <p style="font-size:32px;letter-spacing:8px;font-weight:bold;text-align:center;margin:20px 0">{codigo}</p>
  <p style="color:#555;font-size:13px">Vence en {CODIGO_MINUTOS_VALIDEZ} minutos.
  Si no creaste una cuenta en Kira IA, ignora este mensaje.</p>
</div>""", subtype="html")
    return msg


def enviar_codigo(destino: str, nombre: str, codigo: str) -> None:
    if CORREO_MODO_CONSOLA:
        print(f"\n  [MODO DESARROLLO] SMTP no configurado: código para {destino} → {codigo}\n")
        return
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(SMTP_USUARIO, SMTP_CLAVE)
            # Si el servidor rechaza al destinatario, lanza SMTPRecipientsRefused
            smtp.send_message(_mensaje(destino, nombre, codigo))
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ SMTP: usuario o contraseña de aplicación incorrectos ({e.smtp_code})")
        raise ErrorCorreo("El servidor no pudo enviar el correo (configuración SMTP).") from e
    except smtplib.SMTPRecipientsRefused as e:
        raise CorreoInexistente("Ese correo no existe. Revisa que esté bien escrito.") from e
    except (smtplib.SMTPException, OSError) as e:
        print(f"✗ SMTP: {e}")
        raise ErrorCorreo("No se pudo enviar el correo de verificación. Intenta reenviarlo.") from e
