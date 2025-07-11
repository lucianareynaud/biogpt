# 🧬 Genomic-LLM: AI-Powered Genomic Analysis Platform

A comprehensive SaaS platform for analyzing 23andMe genomic data using ACMG classification guidelines and AI-powered interpretations with PubMedBERT.

## ✨ Features

- **🔬 ACMG-2015 Classification**: Automated variant classification following ACMG-AMP guidelines
- **🤖 AI-Powered Interpretations**: PubMedBERT-based clinical interpretations
- **📊 Population Data Integration**: ClinVar and gnomAD database integration
- **📄 Professional Reports**: PDF reports in Portuguese (PT-BR) and English
- **💬 Intelligent Chat**: RAG-powered conversations about genomic results
- **🔒 Privacy-First**: Local processing, educational use only
- **🌐 Modern UI**: Beautiful Next.js 15 interface with Tailwind CSS

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   LLM Service   │
│   Next.js 15    │◄──►│   FastAPI       │◄──►│   PubMedBERT    │
│   Tailwind CSS  │    │   Python 3.11   │    │   Transformers  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
        ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
        │   Vector DB     │    │   Database      │    │   File Storage  │
        │   ChromaDB      │    │   DuckDB        │    │   Local FS      │
        └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Colima** (lightweight Docker runtime for macOS/Linux) or Docker Desktop
- Docker Compose
- ~5GB free disk space
- At least 8GB RAM (recommended 16GB)

### Colima Installation (Recommended for macOS)

If you don't have Colima installed:

```bash
# Install via Homebrew (macOS)
brew install colima

# Install via package manager (Linux)
# See https://github.com/abiosoft/colima for Linux installation

# Start Colima with sufficient resources
colima start --cpu 4 --memory 8 --disk 20
```

For other operating systems or Docker Desktop users, ensure Docker is running before proceeding.

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/genomic-llm.git
   cd genomic-llm
   ```

2. **Start the platform**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
   
   The startup script will automatically:
   - Detect and start Colima if available (or use Docker Desktop)
   - Create environment configuration
   - Build and start all services
   - Initialize databases with ClinVar and gnomAD data
   - Set up AI embeddings for chat functionality

3. **Access the platform**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - ChromaDB: http://localhost:8002

### First Analysis

1. Open http://localhost:3000
2. Upload your 23andMe .txt file
3. Wait for processing (5-15 minutes)
4. View results, download reports, and chat with AI

### Troubleshooting

#### Colima Issues

If you encounter Docker-related errors:

```bash
# Check Colima status
colima status

# Restart Colima if needed
colima restart

# Stop and start with specific resources
colima stop
colima start --cpu 4 --memory 8 --disk 20

# Check Docker is working
docker --version
docker info
```

#### Port Conflicts

If ports are already in use, you can modify the docker-compose.yml file or stop conflicting services:

```bash
# Check what's using the ports
lsof -i :3000  # Frontend
lsof -i :8000  # Backend API
lsof -i :8001  # LLM Service
lsof -i :8002  # ChromaDB
```

#### Memory Issues

If containers are crashing due to memory:

```bash
# Increase Colima memory allocation
colima stop
colima start --cpu 4 --memory 12 --disk 20
```

#### Stopping the Platform

To cleanly stop all services:

```bash
# Stop all containers
docker compose down

# Optional: Stop Colima to free up system resources
colima stop
```

## 📁 Project Structure

```
genomic-llm/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── dependencies.py    # Database connections
│   │   ├── models/            # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Business logic
│   │   └── templates/         # Jinja2 templates
│   ├── scripts/               # Data ingestion scripts
│   └── requirements.txt       # Python dependencies
├── frontend/                  # Next.js frontend
│   ├── app/                   # App router
│   ├── components/            # React components
│   └── package.json           # Node dependencies
├── llm_service.py             # Standalone LLM service
├── docker-compose.yml         # Orchestration
├── start.sh                   # Startup script
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables

Create `.env` files in the root directory:

```bash
# Database Configuration
DUCKDB_PATH=/app/data/genomic.duckdb
CHROMA_PERSIST_DIRECTORY=/app/data/chroma

# LLM Configuration
LLM_SERVICE_URL=http://llm:8001
HUGGINGFACE_HUB_CACHE=/app/models

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Data Sources

During system initialization, the platform automatically downloads and caches reference data:
- **ClinVar**: Variant clinical significance database (~2GB) - Downloaded once during setup from NCBI FTP
- **gnomAD**: Population frequency data (variable size) - Downloaded once during setup from Broad Institute
- **PubMedBERT**: Pre-trained biomedical language models (~500MB) - Downloaded during LLM service startup from HuggingFace Hub

**Important**: These are public reference databases downloaded once during setup and cached locally. Your personal genomic data is never uploaded to external services.

## 📊 Data Processing Pipeline

1. **File Upload**: 23andMe .txt file validation and storage
2. **Variant Parsing**: Extract rsIDs, positions, and genotypes
3. **Database Lookup**: Cross-reference with ClinVar and gnomAD
4. **ACMG Classification**: Apply simplified ACMG-2015 criteria
5. **AI Interpretation**: Generate clinical interpretations with PubMedBERT
6. **Report Generation**: Create professional PDF reports
7. **Vector Indexing**: Build embeddings for RAG chat functionality

## 🤖 AI Components

### PubMedBERT Integration
- **Model**: microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext
- **Embeddings**: intfloat/e5-small-v2
- **Tasks**: Text generation, embeddings, variant interpretation

### RAG (Retrieval-Augmented Generation)
- **Vector Database**: ChromaDB for semantic search
- **Knowledge Base**: ClinVar annotations + ACMG guidelines
- **Context**: Analysis-specific variant data

## 📄 Report Generation

### Supported Languages
- **Portuguese (PT-BR)**: Default language with medical terminology
- **English (EN)**: International standard version

### Report Sections
- Executive Summary with key findings
- ACMG Classification distribution
- Clinically significant variants
- Gene summaries and interpretations
- Methodology and limitations
- Professional disclaimers

## 🔒 Privacy & Security

### Data Protection
- **Local Processing**: All data processed locally, never shared
- **Temporary Storage**: Files deleted after analysis
- **No Cloud Upload**: Complete air-gapped operation
- **Educational Use**: Not for medical diagnosis

### Compliance
- ACMG-AMP 2015 guidelines implementation
- Medical disclaimers and limitations
- Educational use notifications

## 🧪 Testing

### Sample Data
Test the platform with the provided sample file:
```bash
# Use the sample 23andMe file
cp test_data/sample_23andme.txt /path/to/upload/
```

### API Testing
```bash
# Test backend health
curl http://localhost:8000/health

# Test LLM service
curl http://localhost:8001/health

# Upload test file
curl -X POST "http://localhost:8000/api/v1/genome-upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_data/sample_23andme.txt"
```

## 🛠️ Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### LLM Service Development
```bash
python llm_service.py
```

## 📚 API Documentation

### Key Endpoints

#### Genome Upload
```bash
POST /api/v1/genome-upload          # Upload 23andMe file
POST /api/v1/genome-upload/{id}/process  # Start analysis
GET  /api/v1/genome-upload/{id}/status   # Check progress
GET  /api/v1/genome-upload/{id}          # Get results
```

#### Reports
```bash
POST /api/v1/reports/generate       # Generate PDF report
GET  /api/v1/reports/{id}/download  # Download report
```

#### Chat
```bash
POST /api/v1/chat/session          # Create chat session
POST /api/v1/chat/message          # Send message
```

Full API documentation available at: http://localhost:8000/docs

## 🚨 Important Disclaimers

⚠️ **This system is for educational and research purposes only**

- **Not for medical diagnosis**: Results should not be used for medical decisions
- **Consult professionals**: Always consult healthcare providers for genetic counseling
- **Limited scope**: Only analyzes variants present in 23andMe data
- **Evolving science**: Genetic interpretation guidelines change over time
- **No warranty**: Software provided as-is without medical guarantees

## 🔧 System Requirements

### Minimum Requirements
- **CPU**: 4 cores, 2.0 GHz
- **RAM**: 8GB (16GB recommended)
- **Storage**: 10GB free space
- **Network**: Internet for initial data download

### Recommended Setup
- **CPU**: 8+ cores, 3.0+ GHz
- **RAM**: 16-32GB for faster processing
- **Storage**: SSD with 20GB+ free space
- **GPU**: Optional, for faster AI inference

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt
npm install --dev

# Run tests
pytest backend/tests/
npm test


# Format code
black backend/
prettier --write frontend/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **ACMG-AMP**: For variant classification guidelines
- **ClinVar**: NIH genetic variant database
- **gnomAD**: Genome Aggregation Database
- **Microsoft**: PubMedBERT model
- **23andMe**: Direct-to-consumer genetic testing
- **Open Source Community**: For the amazing tools and libraries

## 📞 Support

- **Documentation**: [Wiki](https://github.com/your-org/genomic-llm/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-org/genomic-llm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/genomic-llm/discussions)

---

**Made with ❤️ for the genomics community**

*Remember: This tool is for educational purposes. Always consult qualified healthcare providers for medical advice.* 