"""
Worker: consome a fila e executa a inferencia.

Implementa:
  - TAREFA 3: grava o resultado ao terminar (fila.guardar_resultado)
  - TAREFA 5: retentativa (3 tentativas) e dead-letter em caso de falha persistente
  - TAREFA 6: log de cada tarefa processada (id, tamanho da entrada, tempo de resposta)

Rodar:  python -m app.worker
Suba mais de um worker em terminais diferentes e veja a carga se dividir.
"""
import time

from app import fila
from app.logging_utils import configurar_log
from app.modelo import carregar_modelo

MAX_TENTATIVAS = 3
ESPERA_ENTRE_TENTATIVAS_S = 0.5

log = configurar_log("worker")


def processar_tarefa(modelo, tarefa: dict) -> dict:
    """Executa a inferencia com retentativa. Levanta a última exceção se esgotar as tentativas."""
    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resultado = modelo.prever(tarefa["texto"])
            resultado["status"] = "pronto"
            return resultado
        except Exception as erro:  # noqa: BLE001
            ultimo_erro = erro
            log.warning(
                f"tarefa {tarefa['id']} falhou na tentativa {tentativa}/{MAX_TENTATIVAS}: {erro}"
            )
            if tentativa < MAX_TENTATIVAS:
                time.sleep(ESPERA_ENTRE_TENTATIVAS_S)
    raise ultimo_erro


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        try:
            tarefa = fila.proxima_tarefa(timeout=5)
        except Exception as erro:  # noqa: BLE001
            log.error(f"falha ao consultar a fila: {erro}")
            time.sleep(1)
            continue
        if tarefa is None:
            continue

        inicio = time.time()
        try:
            resultado = processar_tarefa(modelo, tarefa)
            resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)
            fila.guardar_resultado(tarefa["id"], resultado)
            log.info(
                f"tarefa {tarefa['id']} concluida | tamanho_entrada={len(tarefa['texto'])} "
                f"| tempo_ms={resultado['tempo_ms']}"
            )
        except Exception as erro:  # noqa: BLE001
            tempo_ms = round((time.time() - inicio) * 1000, 2)
            fila.enviar_para_descarte(tarefa, str(erro))
            fila.guardar_resultado(
                tarefa["id"], {"status": "falhou", "erro": str(erro)}
            )
            log.error(
                f"tarefa {tarefa['id']} enviada para dead-letter apos "
                f"{MAX_TENTATIVAS} tentativas | tempo_ms={tempo_ms} | erro={erro}"
            )


if __name__ == "__main__":
    main()
