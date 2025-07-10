#!/usr/bin/env bash
set -euo pipefail

echo "🧬 Inicializando Genomic-LLM stack…"

# Check for Docker runtime (Colima or Docker Desktop)
echo "🔍 Verificando Docker runtime..."

# Function to check if docker is available
check_docker() {
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if Colima is available
if command -v colima >/dev/null 2>&1; then
    echo "✅ Colima detectado"
    
    # Check if Colima is running
    if ! colima status >/dev/null 2>&1; then
        echo "🚀 Iniciando Colima com recursos adequados..."
        echo "   CPU: 4 cores, Memory: 8GB, Disk: 20GB"
        colima start --cpu 4 --memory 8 --disk 20
        
        # Wait a moment for Colima to fully start
        sleep 5
        
        echo "✅ Colima iniciado com sucesso!"
    else
        echo "✅ Colima já está rodando"
    fi
    
    # Verify Docker is accessible through Colima
    if ! check_docker; then
        echo "❌ Erro: Docker não está acessível através do Colima"
        echo "   Tente reiniciar o Colima: colima restart"
        exit 1
    fi
    
elif check_docker; then
    echo "✅ Docker Desktop detectado e funcionando"
    
else
    echo "❌ Erro: Nenhum runtime Docker encontrado!"
    echo ""
    echo "Por favor, instale uma das opções:"
    echo "  • Colima (recomendado para macOS): brew install colima"
    echo "  • Docker Desktop: https://docker.com/products/docker-desktop"
    echo ""
    echo "Para Colima, após instalar execute:"
    echo "  colima start --cpu 4 --memory 8 --disk 20"
    exit 1
fi

echo "🐳 Docker runtime verificado e pronto!"

# Create .env if it doesn't exist
if [[ ! -f .env ]]; then
    echo "📝 Criando arquivo .env..."
    cat > .env << 'EOF'
# Database Configuration
DUCKDB_PATH=/app/data/genomic.duckdb
CHROMA_PERSIST_DIRECTORY=/app/data/chroma

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LLM_SERVICE_URL=http://llm:8001

# LLM Configuration
MODEL_NAME=microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext
EMBEDDING_MODEL=intfloat/e5-small-v2
MAX_SEQUENCE_LENGTH=256

# File Storage
REPORTS_DIR=/app/reports
UPLOADS_DIR=/app/uploads

# External Data Sources
CLINVAR_URL=https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz
GNOMAD_URL=https://storage.googleapis.com/gcp-public-data--gnomad/release/2.1.1/vcf/genomes/gnomad.genomes.r2.1.1.sites.vcf.bgz

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO

# Development
DEBUG=true
RELOAD=true
EOF
fi

echo "🐳 Baixando e construindo containers..."

# Check which docker compose command is available
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Erro: Nenhum comando docker compose encontrado"
    echo "   Instale docker-compose ou use uma versão mais recente do Docker"
    exit 1
fi

echo "🐳 Usando comando: $DOCKER_COMPOSE"

$DOCKER_COMPOSE pull
$DOCKER_COMPOSE build

echo "🚀 Subindo serviços..."
$DOCKER_COMPOSE up -d chroma llm api frontend

echo "⏳ Aguardando API subir…"
until curl -s http://localhost:8000/healthz > /dev/null 2>&1; do
  echo "  Aguardando API estar disponível..."
  sleep 2
done

echo "🔄 Aguardando LLM service estar pronto..."
until curl -s http://localhost:8001/health > /dev/null 2>&1; do
  echo "  Aguardando LLM service estar disponível..."
  sleep 2
done

echo "📊 Ingestão ClinVar / gnomAD / Embeddings…"
$DOCKER_COMPOSE exec api python -m scripts.ingest_clinvar_rsid
$DOCKER_COMPOSE exec api python -m scripts.ingest_gnomad_rsid
$DOCKER_COMPOSE exec api python -m scripts.build_embeddings

echo ""
echo "✅ Sistema online!"
echo "📡 API → http://localhost:8000/docs"
echo "🌐 Frontend → http://localhost:3000"
echo "🤖 LLM Service → http://localhost:8001"
echo "💾 ChromaDB → http://localhost:8002"
echo ""
echo "🧪 Para testar: acesse http://localhost:3000 e faça upload de um arquivo 23andMe .txt" 