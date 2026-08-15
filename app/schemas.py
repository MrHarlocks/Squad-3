from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator


class DiaSemana(str, Enum):
    SEGUNDA = "SEGUNDA"
    TERCA = "TERCA"
    QUARTA = "QUARTA"
    QUINTA = "QUINTA"
    SEXTA = "SEXTA"
    SABADO = "SABADO"
    DOMINGO = "DOMINGO"


class PeriodoDia(str, Enum):
    MANHA = "MANHA"
    TARDE = "TARDE"
    NOITE = "NOITE"
    MADRUGADA = "MADRUGADA"


class Localizacao(BaseModel):
    latitude: float
    longitude: float
    endereco: str | None = None


class BoletimOcorrenciaInput(BaseModel):
    numeroBO: str
    dataHoraOcorrencia: datetime
    diaSemana: DiaSemana | None = None
    tipoCrime: str
    descricao: str | None = None
    localizacao: Localizacao

    @field_validator("dataHoraOcorrencia")
    @classmethod
    def validar_data_hora(cls, value: datetime) -> datetime:
        return value


class BoletimOcorrenciaOutput(BaseModel):
    id: UUID
    numeroBO: str
    statusProcessamento: str
    dataHoraCriacao: datetime


class PontoMancha(BaseModel):
    localizacao: Localizacao
    intensidade: float
    totalOcorrencias: int


class ManchaCriminalResponse(BaseModel):
    totalPontosAnalisados: int
    diaSemanaAnalisado: str
    periodoAnalisado: str
    pontosCalor: list[PontoMancha]


class RequisicaoRota(BaseModel):
    idViatura: str
    localizacaoAtualViatura: Localizacao
    raioAtuacaoKm: float = 5.0


class Waypoint(BaseModel):
    ordem: int
    localizacao: Localizacao
    instrucao: str


class RespostaRota(BaseModel):
    idRota: UUID
    idViatura: str
    distanciaTotalKm: float
    tempoEstimadoMinutos: int
    pontosDePatrulhamento: list[Waypoint]
