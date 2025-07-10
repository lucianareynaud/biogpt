"""
LLM Service for PubMedBERT inference and embeddings.
"""

import os
from typing import List, Dict, Any
import torch
from transformers import AutoTokenizer, AutoModel, pipeline
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Genomic LLM Service", version="1.0.0")

# Request/Response models
class GenerateRequest(BaseModel):
    prompt: str
    max_length: int = 256
    temperature: float = 0.7

class EmbeddingRequest(BaseModel):
    texts: List[str]

class GenerateResponse(BaseModel):
    generated_text: str
    confidence: float

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool

# Global model variables
tokenizer = None
model = None
embedding_model = None
text_generator = None

@app.on_event("startup")
async def load_models():
    """Load models on startup."""
    global tokenizer, model, embedding_model, text_generator
    
    try:
        logger.info("Loading PubMedBERT tokenizer and model...")
        model_name = os.getenv("MODEL_NAME", "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext")
        cache_dir = "/app/models"
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        model = AutoModel.from_pretrained(model_name, cache_dir=cache_dir)
        
        # Create text generation pipeline
        text_generator = pipeline(
            "text-generation",
            model=model_name,
            tokenizer=tokenizer,
            device=-1,  # CPU
            torch_dtype=torch.float32,
            model_kwargs={"cache_dir": cache_dir}
        )
        
        logger.info("Loading embedding model...")
        embedding_model_name = os.getenv("EMBEDDING_MODEL", "intfloat/e5-small-v2")
        embedding_model = SentenceTransformer(
            embedding_model_name, 
            cache_folder=cache_dir
        )
        
        logger.info("All models loaded successfully!")
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        raise e

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    models_loaded = all([
        tokenizer is not None,
        model is not None,
        embedding_model is not None,
        text_generator is not None
    ])
    
    return HealthResponse(
        status="healthy" if models_loaded else "loading",
        model_loaded=models_loaded
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest):
    """Generate text using PubMedBERT."""
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Generate text
        results = text_generator(
            request.prompt,
            max_length=request.max_length,
            temperature=request.temperature,
            do_sample=True,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = results[0]["generated_text"]
        
        # Remove the original prompt from the generated text
        if generated_text.startswith(request.prompt):
            generated_text = generated_text[len(request.prompt):].strip()
        
        return GenerateResponse(
            generated_text=generated_text,
            confidence=0.8  # Placeholder confidence score
        )
        
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings for texts."""
    if embedding_model is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    
    try:
        # Create embeddings
        embeddings = embedding_model.encode(
            request.texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist()
        )
        
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_variant")
async def analyze_variant(variant_data: Dict[str, Any]):
    """Analyze a genetic variant using PubMedBERT."""
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create a biomedical context prompt
        rsid = variant_data.get("rsID", "unknown")
        genotype = variant_data.get("genotype", "unknown")
        classification = variant_data.get("classification", "unknown")
        
        prompt = f"""
        Genetic variant analysis:
        rsID: {rsid}
        Genotype: {genotype}
        Classification: {classification}
        
        Clinical interpretation:
        """
        
        # Generate analysis
        results = text_generator(
            prompt,
            max_length=400,
            temperature=0.3,  # Lower temperature for more focused analysis
            do_sample=True,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id
        )
        
        analysis = results[0]["generated_text"]
        
        # Clean up the response
        if analysis.startswith(prompt):
            analysis = analysis[len(prompt):].strip()
        
        return {
            "variant": variant_data,
            "analysis": analysis,
            "model": "PubMedBERT"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 