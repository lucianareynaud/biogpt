#!/usr/bin/env python3
"""
Build embeddings for RAG system.
Creates vector embeddings for ClinVar data and clinical knowledge.
"""

import duckdb
import chromadb
import os
import logging
import httpx
import asyncio
from typing import List, Dict, Any
import json
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingsBuilder:
    def __init__(self, db_path: str, chroma_path: str, llm_service_url: str):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.llm_service_url = llm_service_url
        self.chroma_client = None
        self.collection = None
        
    async def initialize(self):
        """Initialize connections."""
        logger.info("Initializing embeddings builder...")
        
        # Initialize Chroma
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection("genomic_knowledge")
            logger.info("Using existing genomic_knowledge collection")
        except:
            self.collection = self.chroma_client.create_collection(
                name="genomic_knowledge",
                metadata={"description": "Genomic analysis knowledge base"}
            )
            logger.info("Created new genomic_knowledge collection")
    
    async def build_clinvar_embeddings(self):
        """Build embeddings for ClinVar data."""
        logger.info("Building ClinVar embeddings...")
        
        conn = duckdb.connect(self.db_path)
        
        # Get ClinVar variants with meaningful clinical significance
        query = """
        SELECT rsid, variation_id, gene_symbol, clinical_significance, 
               review_status, condition_name, molecular_consequence
        FROM clinvar_variants 
        WHERE clinical_significance IS NOT NULL 
        AND clinical_significance != 'Unknown'
        AND gene_symbol IS NOT NULL
        ORDER BY rsid
        """
        
        results = conn.execute(query).fetchall()
        columns = [desc[0] for desc in conn.description]
        
        logger.info(f"Processing {len(results):,} ClinVar variants...")
        
        batch_size = 100
        processed = 0
        
        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]
            await self.process_clinvar_batch(batch, columns)
            processed += len(batch)
            
            if processed % 1000 == 0:
                logger.info(f"Processed {processed:,} ClinVar variants")
        
        conn.close()
        logger.info(f"ClinVar embeddings completed. Total: {processed:,}")
    
    async def process_clinvar_batch(self, batch: List, columns: List[str]):
        """Process a batch of ClinVar variants."""
        try:
            documents = []
            metadatas = []
            ids = []
            
            for row in batch:
                variant_dict = dict(zip(columns, row))
                
                # Create document text for embedding
                doc_text = self.create_clinvar_document(variant_dict)
                documents.append(doc_text)
                
                # Create metadata
                metadata = {
                    'type': 'clinvar_variant',
                    'rsid': variant_dict['rsid'],
                    'gene_symbol': variant_dict.get('gene_symbol', ''),
                    'clinical_significance': variant_dict.get('clinical_significance', ''),
                    'condition': variant_dict.get('condition_name', '')[:100] if variant_dict.get('condition_name') else '',
                    'source': 'clinvar'
                }
                metadatas.append(metadata)
                ids.append(f"clinvar_{variant_dict['rsid']}")
            
            # Get embeddings from LLM service
            embeddings = await self.get_embeddings(documents)
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
        except Exception as e:
            logger.error(f"Error processing ClinVar batch: {e}")
    
    def create_clinvar_document(self, variant: Dict[str, Any]) -> str:
        """Create document text for ClinVar variant."""
        doc_parts = []
        
        if variant.get('rsid'):
            doc_parts.append(f"Variant {variant['rsid']}")
        
        if variant.get('gene_symbol'):
            doc_parts.append(f"in gene {variant['gene_symbol']}")
        
        if variant.get('clinical_significance'):
            doc_parts.append(f"has clinical significance: {variant['clinical_significance']}")
        
        if variant.get('condition_name'):
            condition = variant['condition_name'][:200]  # Truncate long conditions
            doc_parts.append(f"associated with condition: {condition}")
        
        if variant.get('molecular_consequence'):
            doc_parts.append(f"molecular consequence: {variant['molecular_consequence']}")
        
        if variant.get('review_status'):
            doc_parts.append(f"review status: {variant['review_status']}")
        
        return " ".join(doc_parts)
    
    async def build_acmg_knowledge_embeddings(self):
        """Build embeddings for ACMG classification knowledge."""
        logger.info("Building ACMG knowledge embeddings...")
        
        acmg_knowledge = [
            {
                "title": "ACMG Pathogenic Classification",
                "content": "Pathogenic variants are disease-causing changes in DNA. These variants have strong evidence for causing disease and are associated with increased risk of disease development. Clinical action and genetic counseling are recommended.",
                "category": "classification"
            },
            {
                "title": "ACMG Likely Pathogenic Classification", 
                "content": "Likely pathogenic variants have good evidence for causing disease but not as strong as pathogenic variants. These variants are associated with increased disease risk. Clinical action and genetic counseling may be recommended.",
                "category": "classification"
            },
            {
                "title": "ACMG Uncertain Significance (VUS)",
                "content": "Variants of uncertain significance (VUS) do not have sufficient evidence to classify as pathogenic or benign. Additional studies and family history may help reclassify these variants. No specific clinical action is recommended based on the variant alone.",
                "category": "classification"
            },
            {
                "title": "ACMG Likely Benign Classification",
                "content": "Likely benign variants are probably not disease-causing. These variants have good evidence against causing disease but not as strong as benign variants. Generally no clinical action is needed.",
                "category": "classification"
            },
            {
                "title": "ACMG Benign Classification",
                "content": "Benign variants are not disease-causing changes in DNA. These variants have strong evidence against causing disease and are considered normal variation. No clinical action is needed.",
                "category": "classification"
            },
            {
                "title": "Population Frequency in ACMG",
                "content": "High population frequency suggests a variant is likely benign. Variants common in healthy populations (>1% frequency) are generally not disease-causing for severe genetic diseases. gnomAD database provides population frequency data.",
                "category": "evidence"
            },
            {
                "title": "Gene Function and Disease Mechanism",
                "content": "Understanding gene function helps interpret variant significance. Loss-of-function variants in essential genes are more likely pathogenic. Missense variants in functional domains require careful evaluation of protein structure and function.",
                "category": "evidence"
            }
        ]
        
        documents = []
        metadatas = []
        ids = []
        
        for i, knowledge in enumerate(acmg_knowledge):
            doc_text = f"{knowledge['title']}: {knowledge['content']}"
            documents.append(doc_text)
            
            metadata = {
                'type': 'acmg_knowledge',
                'title': knowledge['title'],
                'category': knowledge['category'],
                'source': 'acmg_guidelines'
            }
            metadatas.append(metadata)
            ids.append(f"acmg_knowledge_{i}")
        
        # Get embeddings
        embeddings = await self.get_embeddings(documents)
        
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        
        logger.info(f"Added {len(documents)} ACMG knowledge entries")
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from LLM service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.llm_service_url}/embeddings",
                    json={"texts": texts}
                )
                response.raise_for_status()
                result = response.json()
                return result["embeddings"]
                
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            # Return zero embeddings as fallback
            return [[0.0] * 384 for _ in texts]  # e5-small-v2 has 384 dimensions
    
    async def cache_embeddings_in_db(self, texts: List[str], embeddings: List[List[float]]):
        """Cache embeddings in database for future use."""
        conn = duckdb.connect(self.db_path)
        
        try:
            for text, embedding in zip(texts, embeddings):
                content_hash = hashlib.md5(text.encode()).hexdigest()
                
                conn.execute("""
                INSERT OR REPLACE INTO embeddings_cache 
                (id, content_hash, content, embedding, model_name, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    f"embed_{content_hash}",
                    content_hash,
                    text,
                    embedding,
                    "e5-small-v2"
                ))
        
        except Exception as e:
            logger.error(f"Error caching embeddings: {e}")
        finally:
            conn.close()

async def main():
    """Main function for building embeddings."""
    try:
        db_path = os.getenv("DUCKDB_PATH", "/app/data/genomic.duckdb")
        chroma_path = os.getenv("CHROMA_PERSIST_DIRECTORY", "/app/data/chroma")
        llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm:8001")
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(chroma_path, exist_ok=True)
        
        # Initialize builder
        builder = EmbeddingsBuilder(db_path, chroma_path, llm_service_url)
        await builder.initialize()
        
        # Build embeddings
        await builder.build_acmg_knowledge_embeddings()
        await builder.build_clinvar_embeddings()
        
        logger.info("Embeddings building completed successfully!")
        
    except Exception as e:
        logger.error(f"Embeddings building failed: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main()) 