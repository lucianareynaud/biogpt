#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Parando Genomic-LLM stack..."

# Stop all Docker containers
echo "🐳 Parando containers Docker..."

# Check which docker compose command is available
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Erro: Nenhum comando docker compose encontrado"
    exit 1
fi

$DOCKER_COMPOSE down

echo "✅ Containers parados"

# Ask user if they want to stop Colima
if command -v colima >/dev/null 2>&1; then
    if colima status >/dev/null 2>&1; then
        echo ""
        read -p "🤔 Deseja parar o Colima também? (s/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            echo "🛑 Parando Colima..."
            colima stop
            echo "✅ Colima parado"
        else
            echo "ℹ️  Colima mantido rodando para outros projetos"
        fi
    fi
fi

echo ""
echo "✅ Genomic-LLM stack parado com sucesso!"
echo "🔄 Para reiniciar: ./start.sh" 