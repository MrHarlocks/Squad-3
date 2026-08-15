# Squad-3
API de Despacho Policial e Análise Geoespacial em Python + FastAPI.

## Como executar

1. Crie um ambiente virtual Python.
2. Instale as dependências com `pip install -r requirements.txt`.
3. Inicie a API com `uvicorn app.main:app --reload`.

## Docker

1. Construa a imagem com `docker build -t squad-3-api .`.
2. Suba a aplicação e o PostgreSQL com `docker compose up --build`.
3. A API ficará disponível em `http://localhost:8000` e o banco em `localhost:5432`.

## Endpoints

- `POST /boletins` - registra um boletim de ocorrência.
- `GET /manchas-criminais` - consulta pontos de calor e análise sazonal.
- `POST /rotas/otimizar` - calcula rota otimizada de patrulhamento.
- `GET /health` - verificação simples de saúde.

## Contrato da API

- Veja o documento OpenAPI em [openapi.yaml](openapi.yaml).

## Observações

- O banco usado no projeto inicial é SQLite local em `app.db`.
- O contrato foi ajustado para o Trabalho 01: ingestão de BOs, manchas criminais e rotas.
- No Docker, a aplicação usa PostgreSQL via `DATABASE_URL`.

