"""
Dependency injection for database and vector store connections.
"""

import os
import duckdb
import chromadb
from chromadb.config import Settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global connections
_database_connection: Optional[duckdb.DuckDBPyConnection] = None
_vector_store_client: Optional[chromadb.ClientAPI] = None

def get_database() -> duckdb.DuckDBPyConnection:
    """
    Get or create DuckDB connection.
    
    Returns
    -------
    duckdb.DuckDBPyConnection
        DuckDB connection instance.
    """
    global _database_connection
    
    if _database_connection is None:
        db_path = os.getenv("DUCKDB_PATH", "/app/data/genomic.duckdb")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        logger.info(f"Connecting to DuckDB at: {db_path}")
        _database_connection = duckdb.connect(db_path)
        
        # Initialize tables if they don't exist
        _initialize_database_schema(_database_connection)
    
    return _database_connection

def get_vector_store() -> chromadb.ClientAPI:
    """
    Get or create Chroma vector store client.
    
    Returns
    -------
    chromadb.ClientAPI
        Chroma client instance.
    """
    global _vector_store_client
    
    if _vector_store_client is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "/app/data/chroma")
        
        # Ensure persist directory exists
        os.makedirs(persist_dir, exist_ok=True)
        
        logger.info(f"Connecting to Chroma at: {persist_dir}")
        _vector_store_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    
    return _vector_store_client

def _initialize_database_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Initialize database schema with required tables.
    
    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        Database connection.
    """
    logger.info("Initializing database schema...")
    
    # ClinVar table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clinvar_variants (
            rsID VARCHAR PRIMARY KEY,
            chromosome VARCHAR,
            position BIGINT,
            reference_allele VARCHAR,
            alternate_allele VARCHAR,
            clinical_significance VARCHAR,
            review_status VARCHAR,
            phenotype VARCHAR,
            gene_symbol VARCHAR,
            hgvs_c VARCHAR,
            hgvs_p VARCHAR,
            molecular_consequence VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # gnomAD table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gnomad_frequencies (
            rsID VARCHAR PRIMARY KEY,
            chromosome VARCHAR,
            position BIGINT,
            reference_allele VARCHAR,
            alternate_allele VARCHAR,
            allele_frequency DOUBLE,
            allele_count INTEGER,
            allele_number INTEGER,
            population VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User uploads table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_uploads (
            upload_id VARCHAR PRIMARY KEY,
            filename VARCHAR,
            file_size INTEGER,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_status VARCHAR DEFAULT 'pending',
            user_id VARCHAR,
            file_path VARCHAR
        )
    """)
    
    # Variant analysis results table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS variant_analyses (
            analysis_id VARCHAR PRIMARY KEY,
            upload_id VARCHAR,
            rsID VARCHAR,
            chromosome VARCHAR,
            position BIGINT,
            genotype VARCHAR,
            classification VARCHAR,
            confidence_score DOUBLE,
            clinical_interpretation TEXT,
            acmg_criteria VARCHAR[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (upload_id) REFERENCES user_uploads(upload_id)
        )
    """)
    
    # Reports table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id VARCHAR PRIMARY KEY,
            upload_id VARCHAR,
            report_type VARCHAR DEFAULT 'genomic_analysis',
            language VARCHAR DEFAULT 'pt-BR',
            pdf_path VARCHAR,
            markdown_content TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (upload_id) REFERENCES user_uploads(upload_id)
        )
    """)
    
    # Chat sessions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id VARCHAR PRIMARY KEY,
            upload_id VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (upload_id) REFERENCES user_uploads(upload_id)
        )
    """)
    
    # Chat messages table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id VARCHAR PRIMARY KEY,
            session_id VARCHAR,
            message_type VARCHAR, -- 'user' or 'assistant'
            content TEXT,
            sources VARCHAR[], -- Array of source references
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
    """)
    
    # Create indexes for better performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_clinvar_rsid ON clinvar_variants(rsID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gnomad_rsid ON gnomad_frequencies(rsID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_variant_analyses_upload ON variant_analyses(upload_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_upload ON reports(upload_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
    
    logger.info("Database schema initialized successfully")

def close_connections():
    """Close all database connections."""
    global _database_connection, _vector_store_client
    
    if _database_connection:
        _database_connection.close()
        _database_connection = None
        logger.info("DuckDB connection closed")
    
    # Chroma client doesn't need explicit closing
    _vector_store_client = None
    logger.info("Chroma client connection cleared") 