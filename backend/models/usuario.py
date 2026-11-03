"""Modelo Usuario: cuenta + verificación de correo + perfil de preferencias gamer."""

from datetime import datetime, date
from sqlalchemy import Integer, String, Date, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Verificación del correo: la cuenta no puede usarse hasta ingresar el código
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    codigo_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    codigo_expira: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    codigo_intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    codigo_enviado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Perfil (antes vivía en localStorage del navegador)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    consolas: Mapped[list] = mapped_column(JSON, default=list)
    generos: Mapped[list] = mapped_column(JSON, default=list)
    perfil_completo: Mapped[bool] = mapped_column(default=False)

    # Consentimiento informado (Ley 21.719): cuándo aceptó la política de privacidad
    acepta_privacidad_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chats = relationship("Chat", back_populates="usuario", cascade="all, delete-orphan")

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        n = self.fecha_nacimiento
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))

    def a_dict(self):
        """Versión pública (nunca incluye password_hash ni el código)."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "email": self.email,
            "email_verificado": bool(self.email_verificado),
            "fecha_nacimiento": self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else "",
            "edad": self.edad,
            "consolas": self.consolas or [],
            "generos": self.generos or [],
            "perfil_completo": bool(self.perfil_completo),
            "acepta_privacidad_en": self.acepta_privacidad_en.isoformat() if self.acepta_privacidad_en else None,
        }
