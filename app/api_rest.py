"""
Interface REST do servico de inferencia.

O QUE JA ESTA PRONTO:
  - carregamento do modelo UMA vez, na subida (nao a cada requisicao)
  - rota sincrona /predict-sync, usada no laboratorio da Aula 6

O QUE VOCE PRECISA FAZER (TAREFAS.md, itens 1 e 2):
  - POST /predict  -> colocar na fila e devolver o id
  - GET  /resultado/{id} -> devolver o resultado quando estiver pronto

Rodar:  uvicorn app.api_rest:app --reload --port 8000
Docs:   http://localhost:8000/docs
"""
import time

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app import fila
from app.logging_utils import configurar_log
from app.modelo import carregar_modelo

app = FastAPI(title="Servico de Inferencia - C1.A2", version="0.1.0")
log = configurar_log("api_rest")

modelo = None


class Entrada(BaseModel):
    texto: str


@app.on_event("startup")
def _subir():
    """Carrega o modelo UMA vez. Este e o ponto-chave da Aula 6."""
    global modelo
    inicio = time.time()
    modelo = carregar_modelo()
    log.info(f"modelo carregado em {time.time() - inicio:.3f}s")


@app.middleware("http")
async def log_requisicoes(request: Request, chamar_proximo):
    """Registra toda requisição recebida: método, rota, tamanho e tempo de resposta (item 6)."""
    inicio = time.time()
    corpo = await request.body()
    resposta = await chamar_proximo(request)
    tempo_ms = round((time.time() - inicio) * 1000, 2)
    log.info(
        f"{request.method} {request.url.path} | tamanho_entrada={len(corpo)}B "
        f"| status={resposta.status_code} | tempo_ms={tempo_ms}"
    )
    return resposta


@app.get("/saude")
def saude():
    return {"status": "ok", "modelo_carregado": modelo is not None}


@app.post("/predict-sync")
def predict_sync(entrada: Entrada):
    """Inferencia SINCRONA: o cliente espera a resposta. Lab da Aula 6."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    inicio = time.time()
    resultado = modelo.prever(entrada.texto)
    resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)
    return resultado


# ------------------------------------------------------------------
# TAREFA 1 - submissao assincrona
# ------------------------------------------------------------------
@app.post("/predict", status_code=202)
def predict(entrada: Entrada):
    """Enfileira a tarefa e devolve {"id": ...} SEM esperar a inferencia."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    tarefa_id = fila.enfileirar(entrada.texto)
    log.info(f"tarefa {tarefa_id} enfileirada | tamanho_entrada={len(entrada.texto)}")
    return {"id": tarefa_id}


# ------------------------------------------------------------------
# TAREFA 2 - consulta do resultado
# ------------------------------------------------------------------
@app.get("/resultado/{tarefa_id}")
def resultado(tarefa_id: str):
    """Devolve o resultado da tarefa; 404 se o id nao existir."""
    dados = fila.buscar_resultado(tarefa_id)
    if dados is None:
        raise HTTPException(status_code=404, detail="id nao encontrado")
    return dados
