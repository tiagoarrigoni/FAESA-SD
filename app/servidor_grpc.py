"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

O QUE JA ESTA PRONTO: o metodo Prever.
O QUE VOCE PRECISA FAZER (TAREFAS.md, item 4): o metodo PreverLote.

Rodar:  python -m app.servidor_grpc
"""
import time
from concurrent import futures

import grpc

from app.logging_utils import configurar_log
from app.modelo import carregar_modelo

log = configurar_log("grpc")

try:
    import inferencia_pb2
    import inferencia_pb2_grpc
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Stubs nao encontrados. Rode antes:\n"
        "  python -m grpc_tools.protoc -I proto --python_out=. "
        "--grpc_python_out=. proto/inferencia.proto"
    )


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        print("[grpc] carregando modelo...")
        self.modelo = carregar_modelo()
        print("[grpc] modelo pronto")

    def Prever(self, request, context):
        inicio = time.time()
        r = self.modelo.prever(request.texto)
        tempo_ms = round((time.time() - inicio) * 1000, 2)
        log.info(f"Prever | tamanho_entrada={len(request.texto)} | tempo_ms={tempo_ms}")
        return inferencia_pb2.RespostaPrever(
            texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
        )

    # TAREFA 4: PreverLote - recebe varios textos e devolve varias respostas.
    def PreverLote(self, request, context):
        inicio = time.time()
        respostas = []
        for texto in request.textos:
            r = self.modelo.prever(texto)
            respostas.append(
                inferencia_pb2.RespostaPrever(
                    texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
                )
            )
        tempo_ms = round((time.time() - inicio) * 1000, 2)
        log.info(
            f"PreverLote | qtd_textos={len(request.textos)} | tempo_ms={tempo_ms}"
        )
        return inferencia_pb2.RespostaLote(resultados=respostas)


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor)
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    print(f"[grpc] escutando na porta {porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
