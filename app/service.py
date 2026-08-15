from collections import defaultdict
from datetime import date, datetime, time, timezone
from math import atan2, cos, radians, sin, sqrt
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _dia_semana_from_datetime(value: datetime) -> str:
    dias = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]
    return dias[_normalize_datetime(value).weekday()]


def _periodo_from_datetime(value: datetime) -> str:
    hora = _normalize_datetime(value).hour
    if 5 <= hora < 12:
        return "MANHA"
    if 12 <= hora < 18:
        return "TARDE"
    if 18 <= hora < 24:
        return "NOITE"
    return "MADRUGADA"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius * c


def criar_boletim(db: Session, payload: schemas.BoletimOcorrenciaInput) -> schemas.BoletimOcorrenciaOutput:
    existente = db.query(models.BoletimOcorrencia).filter(models.BoletimOcorrencia.numero_bo == payload.numeroBO).first()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"erro": "VALIDATION_ERROR", "detalhes": ["O número do BO já foi cadastrado."]},
        )

    boletim = models.BoletimOcorrencia(
        numero_bo=payload.numeroBO,
        data_hora_ocorrencia=_normalize_datetime(payload.dataHoraOcorrencia),
        dia_semana=payload.diaSemana.value if payload.diaSemana else _dia_semana_from_datetime(payload.dataHoraOcorrencia),
        tipo_crime=payload.tipoCrime,
        descricao=payload.descricao,
        latitude=payload.localizacao.latitude,
        longitude=payload.localizacao.longitude,
        endereco=payload.localizacao.endereco,
        data_hora_criacao=datetime.now(tz=timezone.utc),
        status_processamento="INDEXADO_EM_TEMPO_REAL",
    )
    db.add(boletim)
    db.commit()
    db.refresh(boletim)

    return schemas.BoletimOcorrenciaOutput(
        id=UUID(str(boletim.id)),
        numeroBO=boletim.numero_bo,
        statusProcessamento=boletim.status_processamento,
        dataHoraCriacao=boletim.data_hora_criacao,
    )


def calcular_manchas_criminais(
    db: Session,
    data_inicio: date,
    data_fim: date,
    tipo_crime: str | None,
    dia_semana: schemas.DiaSemana | None,
    periodo: schemas.PeriodoDia | None,
) -> schemas.ManchaCriminalResponse:
    query = db.query(models.BoletimOcorrencia)
    inicio = datetime.combine(data_inicio, time.min, tzinfo=timezone.utc)
    fim = datetime.combine(data_fim, time.max, tzinfo=timezone.utc)
    query = query.filter(models.BoletimOcorrencia.data_hora_ocorrencia >= inicio)
    query = query.filter(models.BoletimOcorrencia.data_hora_ocorrencia <= fim)
    if tipo_crime:
        query = query.filter(models.BoletimOcorrencia.tipo_crime == tipo_crime)

    boletins = query.all()
    filtrados = []
    for boletim in boletins:
        dia_calculado = boletim.dia_semana or _dia_semana_from_datetime(boletim.data_hora_ocorrencia)
        periodo_calculado = _periodo_from_datetime(boletim.data_hora_ocorrencia)
        if dia_semana and dia_calculado != dia_semana.value:
            continue
        if periodo and periodo_calculado != periodo.value:
            continue
        filtrados.append((boletim, dia_calculado, periodo_calculado))

    agrupados: dict[tuple[float, float, str | None], list[models.BoletimOcorrencia]] = defaultdict(list)
    for boletim, _, _ in filtrados:
        agrupados[(round(boletim.latitude, 4), round(boletim.longitude, 4), boletim.endereco)].append(boletim)

    total_pontos = len(filtrados)
    maior_grupo = max((len(lista) for lista in agrupados.values()), default=1)
    pontos = []
    for (latitude, longitude, endereco), lista in sorted(agrupados.items(), key=lambda item: len(item[1]), reverse=True):
        pontos.append(
            schemas.PontoMancha(
                localizacao=schemas.Localizacao(latitude=latitude, longitude=longitude, endereco=endereco),
                intensidade=round(len(lista) / maior_grupo, 2),
                totalOcorrencias=len(lista),
            )
        )

    return schemas.ManchaCriminalResponse(
        totalPontosAnalisados=total_pontos,
        diaSemanaAnalisado=dia_semana.value if dia_semana else "TODOS",
        periodoAnalisado=periodo.value if periodo else "TODOS",
        pontosCalor=pontos,
    )


def otimizar_rota(db: Session, payload: schemas.RequisicaoRota) -> schemas.RespostaRota:
    boletins = db.query(models.BoletimOcorrencia).all()
    if not boletins:
        return schemas.RespostaRota(
            idRota=uuid4(),
            idViatura=payload.idViatura,
            distanciaTotalKm=0.0,
            tempoEstimadoMinutos=0,
            pontosDePatrulhamento=[],
        )

    hotspots = defaultdict(list)
    for boletim in boletins:
        distancia = _haversine_km(
            payload.localizacaoAtualViatura.latitude,
            payload.localizacaoAtualViatura.longitude,
            boletim.latitude,
            boletim.longitude,
        )
        if distancia <= payload.raioAtuacaoKm:
            hotspots[(round(boletim.latitude, 4), round(boletim.longitude, 4), boletim.endereco)].append((boletim, distancia))

    ordenados = sorted(hotspots.items(), key=lambda item: (len(item[1]), -min(dist for _, dist in item[1])), reverse=True)
    pontos = []
    distancia_total = 0.0
    local_atual = payload.localizacaoAtualViatura
    for indice, ((latitude, longitude, endereco), ocorrencias) in enumerate(ordenados[:5], start=1):
        proxima_distancia = _haversine_km(local_atual.latitude, local_atual.longitude, latitude, longitude)
        distancia_total += proxima_distancia
        local_atual = schemas.Localizacao(latitude=latitude, longitude=longitude, endereco=endereco)
        pontos.append(
            schemas.Waypoint(
                ordem=indice,
                localizacao=local_atual,
                instrucao=f"Patrulhar {endereco or f'{latitude}, {longitude}'} por 15 minutos (Mancha crítica identificada)",
            )
        )

    tempo_estimado = int(round(distancia_total / 30.0 * 60.0))
    return schemas.RespostaRota(
        idRota=uuid4(),
        idViatura=payload.idViatura,
        distanciaTotalKm=round(distancia_total, 2),
        tempoEstimadoMinutos=tempo_estimado,
        pontosDePatrulhamento=pontos,
    )
