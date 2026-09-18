"""
Modelo de IA da disciplina - PRONTO, NAO PRECISA ALTERAR.

Classificador de sentimento (positivo/negativo) em portugues.
Treina localmente na primeira execucao e salva em disco (modelo.joblib).
Nao baixa nada da internet: funciona 100% offline no laboratorio.

Voce NAO precisa entender machine learning para usar isto.
So precisa saber: carregar_modelo() devolve um objeto com .prever(texto).
"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

CAMINHO = os.path.join(os.path.dirname(__file__), "modelo.joblib")

# Mini base de treino embutida (suficiente para a disciplina).
TREINO = [
    ("o atendimento foi excelente e muito rapido", 1),
    ("adorei o produto, recomendo demais", 1),
    ("entrega pontual e embalagem perfeita", 1),
    ("otima qualidade pelo preco cobrado", 1),
    ("funcionou exatamente como prometido", 1),
    ("equipe super atenciosa, resolveram tudo", 1),
    ("melhor compra que fiz esse ano", 1),
    ("chegou antes do prazo, muito bom", 1),
    ("produto maravilhoso, superou expectativas", 1),
    ("simples de usar e muito eficiente", 1),
    ("pessimo atendimento, ninguem resolve nada", 0),
    ("produto quebrou no primeiro dia de uso", 0),
    ("entrega atrasou muito e ninguem avisou", 0),
    ("caro demais pelo que entrega", 0),
    ("nao funcionou como anunciado, decepcionante", 0),
    ("horrivel, quero meu dinheiro de volta", 0),
    ("suporte nunca responde, abandonado", 0),
    ("veio faltando peca e a embalagem rasgada", 0),
    ("qualidade muito ruim, nao recomendo", 0),
    ("perda de tempo e de dinheiro", 0),
]


class ModeloSentimento:
    """Envolve o pipeline treinado. Use apenas o metodo prever()."""

    def __init__(self, pipeline):
        self._pipeline = pipeline

    def prever(self, texto: str) -> dict:
        """Recebe um texto e devolve o rotulo e a confianca."""
        proba = self._pipeline.predict_proba([texto])[0]
        idx = int(proba.argmax())
        return {
            "texto": texto,
            "sentimento": "positivo" if idx == 1 else "negativo",
            "confianca": round(float(proba[idx]), 4),
        }


def _treinar():
    textos = [t for t, _ in TREINO]
    rotulos = [r for _, r in TREINO]
    pipe = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=1),
        LogisticRegression(max_iter=1000),
    )
    pipe.fit(textos, rotulos)
    joblib.dump(pipe, CAMINHO)
    return pipe


def carregar_modelo() -> ModeloSentimento:
    """Carrega o modelo do disco; treina na primeira vez. CHAME UMA VEZ SO."""
    if os.path.exists(CAMINHO):
        pipe = joblib.load(CAMINHO)
    else:
        pipe = _treinar()
    return ModeloSentimento(pipe)


if __name__ == "__main__":
    m = carregar_modelo()
    for frase in ["gostei muito do servico", "foi horrivel, nao volto mais"]:
        print(m.prever(frase))
