# C1.A2 — Serviço de Inferência Distribuído

**Sistemas Distribuídos e Computação em Nuvem · FAESA · 2026/2**
Trabalho C1.A2 — baseado no [kit de partida](https://github.com/howardroatti/sd-2026-2-kit-c1a2) do Prof. Howard Roatti.

**Alunos** - Eliã Barros Ferreira 

Serviço que recebe um texto, executa uma inferência de classificação de sentimento
(positivo/negativo) e devolve o resultado por **duas interfaces de comunicação**
(REST e gRPC), processando de forma **assíncrona** via fila + worker.

---

## Arquitetura

```
                    ┌──────────────────┐
        REST        │                  │
  cliente ─────────►│   app/api_rest   │◄── carrega o modelo 1x na subida
   (FastAPI)         │  (FastAPI)       │
                    └────────┬─────────┘
                             │ enfileira (rpush) / consulta (get)
                             ▼
                    ┌──────────────────┐
                    │   Redis (fila)   │  "tarefas"          → pendentes
                    │   app/fila.py    │  "resultado:<id>"   → resultados
                    └────────┬─────────┘  "tarefas:descarte" → dead-letter
                             │ blpop (bloqueante)
                             ▼
                    ┌──────────────────┐
                    │   app/worker.py  │◄── carrega o modelo 1x na subida
                    │  (1..N processos)│    retry (3x) + dead-letter
                    └──────────────────┘

        gRPC        ┌──────────────────┐
  cliente ─────────►│ app/servidor_grpc│◄── carrega o modelo 1x na subida
  (.proto)          │  Prever/PreverLote│   (síncrono, sem fila)
                    └──────────────────┘
```

**Decisões de arquitetura:**

- **API REST e worker são processos separados** que só se comunicam pela fila
  Redis — nenhum dos dois conhece o outro diretamente. Isso permite escalar o
  número de workers independente da API (ver extensão "múltiplos workers").
- **O gRPC não passa pela fila.** Ele expõe o mesmo modelo de forma síncrona,
  atendendo ao requisito de "duas interfaces produzindo o mesmo resultado" sem
  duplicar a lógica de inferência (ambos usam `app/modelo.py`).
- **O modelo é carregado uma única vez por processo**, na inicialização de
  cada serviço (`api_rest`, `worker`, `servidor_grpc`) — nunca a cada
  requisição. Ponto-chave para desempenho, verificável nos logs de startup.
- **Fila e resultados usam chaves separadas no Redis** (`tarefas` para
  pendências, `resultado:<id>` para resultados prontos, `tarefas:descarte`
  para falhas) — permite consultar o resultado sem interferir na fila de
  processamento.

---

## Endpoints REST

| Método | Rota | Descrição |
|---|---|---|
| GET | `/saude` | Healthcheck; confirma se o modelo está carregado |
| POST | `/predict-sync` | Inferência síncrona (cliente espera a resposta) |
| POST | `/predict` | Enfileira a tarefa e devolve `{"id": ...}` (202), sem esperar |
| GET | `/resultado/{id}` | Consulta o resultado pelo id; 404 se não existir |

Docs interativas (Swagger): `http://localhost:8000/docs`

## Serviço gRPC (`proto/inferencia.proto`)

| RPC | Descrição |
|---|---|
| `Prever(PedidoPrever) → RespostaPrever` | Inferência de um texto |
| `PreverLote(PedidoLote) → RespostaLote` | Inferência de vários textos em uma chamada |

REST e gRPC chamam o mesmo `app/modelo.py` — para o mesmo texto, ambas as
interfaces devolvem exatamente o mesmo `sentimento` e `confianca`.

## Resiliência

- **Retentativa**: o worker tenta processar cada tarefa até **3 vezes**
  (`app/worker.py::processar_tarefa`) antes de desistir.
- **Dead-letter**: após esgotar as tentativas, a tarefa é movida para a fila
  `tarefas:descarte` (com o erro registrado) e o cliente recebe
  `{"status": "falhou", "erro": ...}` ao consultar o resultado — nunca fica
  esperando um resultado que nunca vai chegar.
- **Falha de conexão com a fila**: se o próprio Redis ficar indisponível
  momentaneamente, o worker registra o erro e tenta de novo, em vez de
  encerrar o processo.
- **Entrada inválida**: texto vazio é rejeitado com `400` tanto em
  `/predict` quanto em `/predict-sync`.

## Logs

Cada serviço grava logs estruturados em console **e** em arquivo
(`logs/api_rest.log`, `logs/worker.log`, `logs/grpc.log`), com timestamp, id
da tarefa (quando aplicável), tamanho da entrada e tempo de resposta.
Implementado em `app/logging_utils.py`.

---

## Como executar do zero

Pré-requisitos: **Python 3.11+** e **Docker Desktop** (para o Redis).

```bash
# 1. Clone e entre na pasta
git clone https://github.com/tiagoarrigoni/FAESA-SD.git
cd FAESA-SD

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Suba o Redis
docker compose up -d

# 5. Gere os stubs do gRPC (necessário antes de rodar o servidor gRPC)
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto

# 6. Em terminais separados, suba os três serviços:
uvicorn app.api_rest:app --port 8000       # API REST — http://localhost:8000/docs
python -m app.worker                        # worker (pode subir mais de um)
python -m app.servidor_grpc                 # servidor gRPC — porta 50051
```

Teste rápido:

```bash
# síncrono
python exemplos/cliente_rest.py "o atendimento foi otimo"

# assincrono (submete, consulta o id, aguarda o worker processar)
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"texto\": \"produto excelente\"}"
curl http://localhost:8000/resultado/<id-devolvido-acima>
```

### Observação sobre ambiente Windows / Python 3.14

As versões do `requirements.txt` foram atualizadas em relação ao kit
original porque as versões antes fixadas (`scikit-learn==1.5.2`,
`pydantic==2.9.2`, `grpcio==1.66.1`) não possuem wheel pré-compilada para
Python 3.14 no Windows, e a compilação a partir do código-fonte falha sem
as ferramentas de build do Visual Studio/Rust. Todas as versões atuais são
apenas mais recentes da mesma biblioteca, sem mudança de comportamento
relevante para este projeto.

Também alterei o valor padrão de `REDIS_URL` de `redis://localhost:6379/0`
para `redis://127.0.0.1:6379/0`: no Windows, resolver `localhost` pode
tentar IPv6 antes de cair para IPv4, adicionando ~2s de latência na
**primeira** conexão de cada processo com o Redis — o que é especialmente
perceptível na rota `/predict`, que deveria responder quase instantaneamente
por ser assíncrona. Usar o IP direto elimina esse atraso.

---

## Extensões implementadas

Nenhuma das extensões opcionais (múltiplos workers, cache, latência média,
batch via REST) foi implementada além do núcleo obrigatório — o
`PreverLote` do gRPC já cobre o caso de lote pela via gRPC.

Para demonstrar múltiplos workers dividindo carga, basta abrir mais
terminais rodando `python -m app.worker`: cada um consome da mesma fila
Redis via `BLPOP`, que garante que cada tarefa é entregue a exatamente um
worker.

---

## Estrutura do projeto

```
FAESA-SD/
├── app/
│   ├── modelo.py           # modelo de sentimento (pronto, do kit)
│   ├── fila.py              # fila Redis + dead-letter
│   ├── logging_utils.py     # logger compartilhado pelos 3 serviços
│   ├── api_rest.py          # API REST (FastAPI)
│   ├── worker.py            # worker assíncrono (retry + dead-letter)
│   └── servidor_grpc.py     # servidor gRPC (Prever + PreverLote)
├── proto/inferencia.proto   # contrato gRPC
├── exemplos/cliente_rest.py # cliente de exemplo (síncrono e assíncrono)
├── scripts/gerar_stubs.*    # atalhos para gerar os stubs gRPC
├── docker-compose.yml       # sobe o Redis
└── TAREFAS.md               # checklist original do kit
```
