"""Modelo Chat: historial de preguntas y respuestas de cada usuario."""

from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Chat(Base):
    __tablename__ = "historial_chat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    respuesta: Mapped[str] = mapped_column(Text, nullable=False)
    # Trazabilidad y costos (lo que informa Gemini en cada respuesta)
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_salida: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latencia_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    usuario = relationship("Usuario", back_populates="chats")

    def a_dict(self):
        return {
            "id": self.id,
            "mensaje": self.mensaje,
            "respuesta": self.respuesta,
            "creado_en": self.creado_en.isoformat(),
        }
