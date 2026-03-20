#!/bin/bash
# Inicia o servidor de licenças em produção (VPS Linux)
# Uso: bash start_server.sh

set -e

echo "=== Shopee Affiliate Bot — License Server ==="

# Instala dependências
pip install -r requirements.txt

# Gera par de chaves RSA (só na 1ª vez)
python generate_keys.py

# Inicia servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
