FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas os requirements primeiro para usar o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o projeto
COPY . .

# Gerar os stubs do gRPC durante o build da imagem
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto

# O comando de inicialização será definido no docker-compose.yml

