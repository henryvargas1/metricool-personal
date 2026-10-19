#!/bin/bash
# Script de ejecución local para Metricool Personal
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "Iniciando Metricool Personal en http://localhost:8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
