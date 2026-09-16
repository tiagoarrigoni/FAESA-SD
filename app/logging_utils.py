"""
Logging compartilhado pelos três serviços (REST, worker, gRPC).

Cada requisição processada deve gerar uma linha de log com: id da tarefa,
tamanho da entrada e tempo de resposta — item 6 do TAREFAS.md.
"""
import logging
import os

DIRETORIO_LOGS = os.path.join(os.path.dirname(__file__), "..", "logs")


def configurar_log(nome_servico: str) -> logging.Logger:
    """Cria um logger que grava em console e em logs/<nome_servico>.log."""
    os.makedirs(DIRETORIO_LOGS, exist_ok=True)

    logger = logging.getLogger(nome_servico)
    if logger.handlers:  # evita handlers duplicados em reload do uvicorn
        return logger

    logger.setLevel(logging.INFO)
    formato = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    para_console = logging.StreamHandler()
    para_console.setFormatter(formato)
    logger.addHandler(para_console)

    para_arquivo = logging.FileHandler(
        os.path.join(DIRETORIO_LOGS, f"{nome_servico}.log"), encoding="utf-8"
    )
    para_arquivo.setFormatter(formato)
    logger.addHandler(para_arquivo)

    return logger
