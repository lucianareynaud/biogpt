#!/usr/bin/env python3
"""
Database initialization script for Genomic-LLM.
Creates all necessary tables and indexes for production.
"""

import duckdb
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database(db_path: str = "/app/data/genomic.duckdb"):
    """Initialize the DuckDB database with all required tables."""
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Initializing database at {db_path}")
    
    try:
        conn = duckdb.connect(db_path)
        
        # Create tables
        create_tables_sql = """
        -- User uploads table
        CREATE TABLE IF NOT EXISTS uploads (
            id VARCHAR PRIMARY KEY,
            filename VARCHAR NOT NULL,
            file_path VARCHAR NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size BIGINT,
            status VARCHAR DEFAULT 'uploaded',  -- uploaded, processing, completed, error
            user_id VARCHAR,
            metadata JSON
        );

        -- Genomic analyses table  
        CREATE TABLE IF NOT EXISTS analyses (
            id VARCHAR PRIMARY KEY,
            upload_id VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'pending',  -- pending, processing, completed, error
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            total_variants INTEGER,
            processed_variants INTEGER,
            pathogenic_variants INTEGER,
            likely_pathogenic_variants INTEGER,
            uncertain_variants INTEGER,
            likely_benign_variants INTEGER,
            benign_variants INTEGER,
            error_message TEXT,
            metadata JSON,
            FOREIGN KEY (upload_id) REFERENCES uploads(id)
        );

        -- Individual variant results
        CREATE TABLE IF NOT EXISTS variant_results (
            id VARCHAR PRIMARY KEY,
            analysis_id VARCHAR NOT NULL,
            rsid VARCHAR NOT NULL,
            chromosome VARCHAR,
            position BIGINT,
            reference_allele VARCHAR,
            alternate_allele VARCHAR,
            genotype VARCHAR,
            acmg_classification VARCHAR,
            acmg_score DOUBLE,
            confidence_score DOUBLE,
            clinical_significance VARCHAR,
            gene_symbol VARCHAR,
            consequence VARCHAR,
            clinvar_id VARCHAR,
            gnomad_frequency DOUBLE,
            interpretation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        -- Reports table
        CREATE TABLE IF NOT EXISTS reports (
            id VARCHAR PRIMARY KEY,
            analysis_id VARCHAR NOT NULL,
            report_type VARCHAR DEFAULT 'standard',  -- standard, detailed
            language VARCHAR DEFAULT 'pt-BR',  -- pt-BR, en
            file_path VARCHAR,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR DEFAULT 'pending',  -- pending, generating, completed, error
            error_message TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        -- Chat sessions table
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id VARCHAR PRIMARY KEY,
            analysis_id VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            context JSON,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        -- Chat messages table
        CREATE TABLE IF NOT EXISTS chat_messages (
            id VARCHAR PRIMARY KEY,
            session_id VARCHAR NOT NULL,
            message TEXT NOT NULL,
            response TEXT,
            is_user_message BOOLEAN DEFAULT true,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        );

        -- ClinVar cache table
        CREATE TABLE IF NOT EXISTS clinvar_variants (
            rsid VARCHAR PRIMARY KEY,
            variation_id VARCHAR,
            gene_symbol VARCHAR,
            clinical_significance VARCHAR,
            review_status VARCHAR,
            condition_name TEXT,
            last_evaluated DATE,
            chromosome VARCHAR,
            start_position BIGINT,
            reference_allele VARCHAR,
            alternate_allele VARCHAR,
            molecular_consequence VARCHAR,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- gnomAD frequency cache table
        CREATE TABLE IF NOT EXISTS gnomad_frequencies (
            rsid VARCHAR PRIMARY KEY,
            chromosome VARCHAR,
            position BIGINT,
            reference_allele VARCHAR,
            alternate_allele VARCHAR,
            allele_frequency DOUBLE,
            allele_count INTEGER,
            allele_number INTEGER,
            homozygote_count INTEGER,
            population_frequencies JSON,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Vector embeddings cache
        CREATE TABLE IF NOT EXISTS embeddings_cache (
            id VARCHAR PRIMARY KEY,
            content_hash VARCHAR UNIQUE,
            content TEXT,
            embedding DOUBLE[],
            model_name VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Execute table creation
        conn.executescript(create_tables_sql)
        
        # Create indexes for performance
        indexes_sql = """
        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
        CREATE INDEX IF NOT EXISTS idx_uploads_upload_time ON uploads(upload_time);
        CREATE INDEX IF NOT EXISTS idx_analyses_upload_id ON analyses(upload_id);
        CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);
        CREATE INDEX IF NOT EXISTS idx_variant_results_analysis_id ON variant_results(analysis_id);
        CREATE INDEX IF NOT EXISTS idx_variant_results_rsid ON variant_results(rsid);
        CREATE INDEX IF NOT EXISTS idx_variant_results_classification ON variant_results(acmg_classification);
        CREATE INDEX IF NOT EXISTS idx_reports_analysis_id ON reports(analysis_id);
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_analysis_id ON chat_sessions(analysis_id);
        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_clinvar_variants_rsid ON clinvar_variants(rsid);
        CREATE INDEX IF NOT EXISTS idx_gnomad_frequencies_rsid ON gnomad_frequencies(rsid);
        CREATE INDEX IF NOT EXISTS idx_embeddings_cache_hash ON embeddings_cache(content_hash);
        """
        
        conn.executescript(indexes_sql)
        
        conn.close()
        logger.info("Database initialized successfully!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e

if __name__ == "__main__":
    db_path = os.getenv("DUCKDB_PATH", "/app/data/genomic.duckdb")
    init_database(db_path) 