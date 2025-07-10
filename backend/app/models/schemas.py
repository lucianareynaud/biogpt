"""
Pydantic schemas for data validation and API models.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

# Enums
class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class VariantClassification(str, Enum):
    PATHOGENIC = "Patogênica"
    LIKELY_PATHOGENIC = "Provavelmente Patogênica"
    VUS = "VUS"  # Variant of Uncertain Significance
    LIKELY_BENIGN = "Provavelmente Benigna"
    BENIGN = "Benigna"

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ReportLanguage(str, Enum):
    PT_BR = "pt-BR"
    EN = "en"

# Base models
class GenomicVariant(BaseModel):
    """Base model for genomic variants."""
    rsID: str = Field(..., description="rsID identifier")
    chromosome: str = Field(..., description="Chromosome number")
    position: int = Field(..., description="Genomic position")
    genotype: str = Field(..., description="Genotype (e.g., AA, AG, GG)")

class ClinVarVariant(BaseModel):
    """ClinVar variant information."""
    rsID: str
    chromosome: str
    position: int
    reference_allele: str
    alternate_allele: str
    clinical_significance: str
    review_status: str
    phenotype: Optional[str] = None
    gene_symbol: Optional[str] = None
    hgvs_c: Optional[str] = None
    hgvs_p: Optional[str] = None
    molecular_consequence: Optional[str] = None

class GnomADFrequency(BaseModel):
    """gnomAD allele frequency information."""
    rsID: str
    chromosome: str
    position: int
    reference_allele: str
    alternate_allele: str
    allele_frequency: float
    allele_count: int
    allele_number: int
    population: str = "global"

# Upload models
class UploadResponse(BaseModel):
    """Response model for file upload."""
    upload_id: str
    filename: str
    file_size: int
    status: ProcessingStatus
    message: str
    processing_url: Optional[str] = None

class UploadStatus(BaseModel):
    """Upload processing status."""
    upload_id: str
    filename: str
    status: ProcessingStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: str
    variants_processed: int = 0
    total_variants: int = 0
    errors: List[str] = []

# Variant analysis models
class VariantAnalysis(BaseModel):
    """Variant analysis result."""
    analysis_id: str
    rsID: str
    chromosome: str
    position: int
    genotype: str
    classification: VariantClassification
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    clinical_interpretation: str
    acmg_criteria: List[str] = []
    clinvar_info: Optional[ClinVarVariant] = None
    gnomad_info: Optional[GnomADFrequency] = None

class VariantAnalysisRequest(BaseModel):
    """Request for variant analysis."""
    variants: List[GenomicVariant]
    include_interpretation: bool = True
    language: ReportLanguage = ReportLanguage.PT_BR

class VariantAnalysisResponse(BaseModel):
    """Response for variant analysis."""
    upload_id: str
    total_variants: int
    analyzed_variants: int
    analyses: List[VariantAnalysis]
    processing_time: float
    summary: Dict[str, int]

# Report models
class ReportRequest(BaseModel):
    """Request to generate a report."""
    upload_id: str
    language: ReportLanguage = ReportLanguage.PT_BR
    include_chat_link: bool = True

class ReportResponse(BaseModel):
    """Response with generated report information."""
    report_id: str
    upload_id: str
    report_type: str
    language: ReportLanguage
    pdf_url: str
    download_url: str
    generated_at: datetime
    summary: Dict[str, Any]

class ReportSummary(BaseModel):
    """Report summary information."""
    total_variants: int
    pathogenic_variants: int
    likely_pathogenic_variants: int
    vus_variants: int
    benign_variants: int
    likely_benign_variants: int
    key_findings: List[str]

# Chat models
class ChatMessage(BaseModel):
    """Chat message."""
    message_id: str
    session_id: str
    message_type: MessageType
    content: str
    sources: List[str] = []
    timestamp: datetime

class ChatRequest(BaseModel):
    """Chat request."""
    session_id: Optional[str] = None
    upload_id: str
    message: str
    include_sources: bool = True

class ChatResponse(BaseModel):
    """Chat response."""
    session_id: str
    message_id: str
    content: str
    sources: List[str] = []
    suggested_questions: List[str] = []

class ChatSession(BaseModel):
    """Chat session information."""
    session_id: str
    upload_id: str
    created_at: datetime
    message_count: int = 0

# RAG models
class RAGContext(BaseModel):
    """RAG context information."""
    query: str
    relevant_documents: List[Dict[str, Any]]
    context_summary: str
    sources: List[str]

class LLMRequest(BaseModel):
    """Request to LLM service."""
    prompt: str
    context: Optional[str] = None
    max_length: int = 512
    temperature: float = 0.7

class LLMResponse(BaseModel):
    """Response from LLM service."""
    generated_text: str
    confidence: float
    sources: List[str] = []

# Error models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Validation
@validator('rsID')
def validate_rsid(cls, v):
    """Validate rsID format."""
    if not v.startswith('rs') or not v[2:].isdigit():
        raise ValueError('rsID must start with "rs" followed by digits')
    return v

# Apply validator to relevant models
GenomicVariant.__validator_config__ = {'validate_assignment': True}
ClinVarVariant.__validator_config__ = {'validate_assignment': True} 