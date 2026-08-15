from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class BoletimOcorrencia(Base):
    __tablename__ = "boletins_ocorrencia"
    __table_args__ = (UniqueConstraint("numero_bo", name="uq_boletim_numero_bo"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    numero_bo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data_hora_ocorrencia: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    dia_semana: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    tipo_crime: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_hora_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status_processamento: Mapped[str] = mapped_column(String(50), nullable=False, default="INDEXADO_EM_TEMPO_REAL")
