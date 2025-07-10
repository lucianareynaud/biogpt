#!/usr/bin/env python3
"""
ClinVar data ingestion script.
Downloads and processes ClinVar variant summary data.
"""

import requests
import gzip
import pandas as pd
import duckdb
import os
import logging
from pathlib import Path
import tempfile
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLINVAR_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"

def download_clinvar_data(url: str = CLINVAR_URL, chunk_size: int = 8192) -> str:
    """Download ClinVar variant summary file."""
    logger.info(f"Downloading ClinVar data from {url}")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt.gz")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_file.name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if downloaded % (chunk_size * 100) == 0:  # Log every ~800KB
                            logger.info(f"Downloaded {percent:.1f}% ({downloaded:,} / {total_size:,} bytes)")
        
        logger.info(f"Download completed: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Error downloading ClinVar data: {e}")
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise e

def process_clinvar_data(file_path: str, db_path: str) -> int:
    """Process and insert ClinVar data into database."""
    logger.info("Processing ClinVar data...")
    
    try:
        # Read compressed file
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Read in chunks to manage memory
            chunk_size = 10000
            processed_rows = 0
            
            # Connect to database
            conn = duckdb.connect(db_path)
            
            # Read first chunk to get column names
            df_chunk = pd.read_csv(f, sep='\t', chunksize=chunk_size, low_memory=False, nrows=chunk_size)
            first_chunk = next(df_chunk)
            
            # Reset file pointer
            f.seek(0)
            
            # Process in chunks
            for chunk_num, df in enumerate(pd.read_csv(f, sep='\t', chunksize=chunk_size, low_memory=False)):
                if chunk_num % 10 == 0:
                    logger.info(f"Processing chunk {chunk_num}, rows: {processed_rows:,}")
                
                # Filter and process relevant columns
                processed_df = process_clinvar_chunk(df)
                
                if not processed_df.empty:
                    # Insert into database using UPSERT pattern
                    insert_clinvar_batch(conn, processed_df)
                    processed_rows += len(processed_df)
            
            conn.close()
            logger.info(f"ClinVar processing completed. Total rows processed: {processed_rows:,}")
            return processed_rows
            
    except Exception as e:
        logger.error(f"Error processing ClinVar data: {e}")
        raise e
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)

def process_clinvar_chunk(df: pd.DataFrame) -> pd.DataFrame:
    """Process a chunk of ClinVar data."""
    try:
        # Select relevant columns (adjust based on actual ClinVar format)
        relevant_columns = [
            'RS# (dbSNP)', 'VariationID', 'GeneSymbol', 'ClinicalSignificance',
            'ReviewStatus', 'Condition(s)', 'LastEvaluated', 'Chromosome', 
            'Start', 'ReferenceAllele', 'AlternateAllele', 'Assembly',
            'Cytogenetic', 'MolecularConsequence'
        ]
        
        # Keep only columns that exist in the dataframe
        available_columns = [col for col in relevant_columns if col in df.columns]
        df_filtered = df[available_columns].copy()
        
        # Filter for variants with rsIDs
        if 'RS# (dbSNP)' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['RS# (dbSNP)'].notna()]
            df_filtered = df_filtered[df_filtered['RS# (dbSNP)'] != -1]
            
            # Convert rsID to string format (rs123456)
            df_filtered['rsid'] = 'rs' + df_filtered['RS# (dbSNP)'].astype(str)
        else:
            # If no rsID column, return empty dataframe
            return pd.DataFrame()
        
        # Rename columns to match database schema
        column_mapping = {
            'VariationID': 'variation_id',
            'GeneSymbol': 'gene_symbol',
            'ClinicalSignificance': 'clinical_significance',
            'ReviewStatus': 'review_status',
            'Condition(s)': 'condition_name',
            'LastEvaluated': 'last_evaluated',
            'Chromosome': 'chromosome',
            'Start': 'start_position',
            'ReferenceAllele': 'reference_allele',
            'AlternateAllele': 'alternate_allele',
            'MolecularConsequence': 'molecular_consequence'
        }
        
        df_filtered = df_filtered.rename(columns=column_mapping)
        
        # Clean data
        if 'clinical_significance' in df_filtered.columns:
            df_filtered['clinical_significance'] = df_filtered['clinical_significance'].fillna('Unknown')
        
        if 'gene_symbol' in df_filtered.columns:
            df_filtered['gene_symbol'] = df_filtered['gene_symbol'].fillna('')
        
        # Keep only variants with meaningful clinical significance
        meaningful_significance = [
            'Pathogenic', 'Likely pathogenic', 'Benign', 'Likely benign',
            'Uncertain significance', 'Conflicting interpretations of pathogenicity'
        ]
        
        if 'clinical_significance' in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered['clinical_significance'].str.contains(
                    '|'.join(meaningful_significance), 
                    case=False, 
                    na=False
                )
            ]
        
        return df_filtered
        
    except Exception as e:
        logger.error(f"Error processing ClinVar chunk: {e}")
        return pd.DataFrame()

def insert_clinvar_batch(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame):
    """Insert batch of ClinVar data into database."""
    try:
        # Convert DataFrame to list of tuples for insertion
        columns = list(df.columns)
        values = df.values.tolist()
        
        # Create INSERT with ON CONFLICT DO UPDATE (UPSERT)
        placeholders = ','.join(['?' for _ in columns])
        columns_str = ','.join(columns)
        
        insert_sql = f"""
        INSERT OR REPLACE INTO clinvar_variants ({columns_str}, cached_at)
        VALUES ({placeholders}, CURRENT_TIMESTAMP)
        """
        
        # Execute batch insert
        conn.executemany(insert_sql, values)
        
    except Exception as e:
        logger.error(f"Error inserting ClinVar batch: {e}")
        raise e

def main():
    """Main function for ClinVar ingestion."""
    try:
        db_path = os.getenv("DUCKDB_PATH", "/app/data/genomic.duckdb")
        
        # Ensure database is initialized
        from scripts.init_database import init_database
        init_database(db_path)
        
        # Download and process ClinVar data
        temp_file = download_clinvar_data()
        processed_rows = process_clinvar_data(temp_file, db_path)
        
        logger.info(f"ClinVar ingestion completed successfully. Processed {processed_rows:,} variants.")
        
    except Exception as e:
        logger.error(f"ClinVar ingestion failed: {e}")
        raise e

if __name__ == "__main__":
    main() 