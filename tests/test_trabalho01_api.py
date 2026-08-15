from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def boletim_payload(numero: str = "BO-2026-089123") -> dict:
    return {
        "numeroBO": numero,
        "dataHoraOcorrencia": "2026-08-14T22:30:00Z",
        "diaSemana": "SEXTA",
        "tipoCrime": "ROUBO",
        "descricao": "Assalto a pedestre em via pública.",
        "localizacao": {
            "latitude": -16.686891,
            "longitude": -49.264794,
            "endereco": "Av. Goiás, Centro",
        },
    }


def test_registrar_boletim(client: TestClient) -> None:
    response = client.post("/boletins", json=boletim_payload())

    assert response.status_code == 201
    body = response.json()
    UUID(body["id"])
    assert body["numeroBO"] == "BO-2026-089123"
    assert body["statusProcessamento"] == "INDEXADO_EM_TEMPO_REAL"


def test_registrar_boletim_duplicate_returns_400(client: TestClient) -> None:
    client.post("/boletins", json=boletim_payload())
    response = client.post("/boletins", json=boletim_payload())

    assert response.status_code == 400
    assert response.json()["erro"] == "VALIDATION_ERROR"


def test_consultar_manchas_criminais(client: TestClient) -> None:
    client.post("/boletins", json=boletim_payload())
    client.post(
        "/boletins",
        json={
            **boletim_payload("BO-2026-089124"),
            "localizacao": {
                "latitude": -16.686891,
                "longitude": -49.264794,
                "endereco": "Av. Goiás, Centro",
            },
        },
    )

    response = client.get("/manchas-criminais", params={"dataInicio": "2026-08-01", "dataFim": "2026-08-31", "tipoCrime": "ROUBO", "diaSemana": "SEXTA", "periodo": "NOITE"})

    assert response.status_code == 200
    body = response.json()
    assert body["totalPontosAnalisados"] == 2
    assert body["diaSemanaAnalisado"] == "SEXTA"
    assert body["periodoAnalisado"] == "NOITE"
    assert len(body["pontosCalor"]) == 1
    assert body["pontosCalor"][0]["totalOcorrencias"] == 2


def test_otimizar_rota(client: TestClient) -> None:
    client.post("/boletins", json=boletim_payload())

    response = client.post(
        "/rotas/otimizar",
        json={
            "idViatura": "VP-102",
            "localizacaoAtualViatura": {"latitude": -16.687, "longitude": -49.265, "endereco": "Base Central"},
            "raioAtuacaoKm": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    UUID(body["idRota"])
    assert body["idViatura"] == "VP-102"
    assert body["distanciaTotalKm"] >= 0
    assert isinstance(body["pontosDePatrulhamento"], list)


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
