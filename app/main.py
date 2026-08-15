from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import schemas
from .database import Base, engine, get_db
from .service import calcular_manchas_criminais, criar_boletim, otimizar_rota

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Despacho Policial e Análise Geoespacial",
    description="API RESTful para ingestão em tempo real de Boletins de Ocorrência (BOs), geração de manchas criminais geoespaciais com análise sazonal e cálculo de rotas otimizadas de patrulhamento.",
    version="1.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    detalhes = [error["msg"] for error in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"erro": "VALIDATION_ERROR", "detalhes": detalhes},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"erro": str(exc.detail)})


@app.post(
    "/boletins",
    response_model=schemas.BoletimOcorrenciaOutput,
    status_code=status.HTTP_201_CREATED,
    tags=["Boletins"],
    summary="Registrar Boletim de Ocorrência (Ingestão em Tempo Real)",
    description="Recebe os dados de um novo BO para processamento contínuo, correlação temporal/espacial e atualização imediata do modelo geoespacial.",
)
def registrar_boletim(payload: schemas.BoletimOcorrenciaInput, db: Session = Depends(get_db)) -> schemas.BoletimOcorrenciaOutput:
    return criar_boletim(db, payload)


@app.get(
    "/manchas-criminais",
    response_model=schemas.ManchaCriminalResponse,
    tags=["Manchas Criminais"],
    summary="Consultar Mancha Criminal e Análise Sazonal",
    description="Retorna os agrupamentos geoespaciais e pontos de calor baseados em filtros de tempo, data, turno, dia da semana e tipo de crime.",
)
def consultar_manchas_criminais(
    dataInicio: date = Query(..., description="Data inicial do recorte"),
    dataFim: date = Query(..., description="Data final do recorte"),
    tipoCrime: str | None = None,
    diaSemana: schemas.DiaSemana | None = None,
    periodo: schemas.PeriodoDia | None = None,
    db: Session = Depends(get_db),
) -> schemas.ManchaCriminalResponse:
    return calcular_manchas_criminais(db, dataInicio, dataFim, tipoCrime, diaSemana, periodo)


@app.post(
    "/rotas/otimizar",
    response_model=schemas.RespostaRota,
    tags=["Rotas"],
    summary="Gerar Rota Otimizada de Patrulhamento / Despacho",
    description="Calcula a melhor rota para uma viatura cobrir áreas críticas com base na mancha criminal ativa e localização atual.",
)
def gerar_rota(payload: schemas.RequisicaoRota, db: Session = Depends(get_db)) -> schemas.RespostaRota:
    return otimizar_rota(db, payload)


@app.get("/health", tags=["Sistema"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
