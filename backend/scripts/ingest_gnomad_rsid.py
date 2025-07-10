#!/usr/bin/env python3
"""
gnomAD frequency data ingestion script.
Downloads and processes gnomAD population frequency data.
"""

import requests
import gzip
import pandas as pd
import duckdb
import os
import logging
from pathlib import Path
import tempfile
import re
from typing import Optional, Dict, Any
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Using gnomAD v3.1.2 sites VCF (smaller than genomes)
GNOMAD_URL = "https://storage.googleapis.com/gcp-public-data--gnomad/release/3.1.2/vcf/genomes/gnomad.genomes.v3.1.2.sites.chr22.vcf.bgz"

def download_gnomad_data(url: str = GNOMAD_URL, chunk_size: int = 8192) -> str:
    """Download gnomAD frequency file (using chr22 for demo/testing)."""
    logger.info(f"Downloading gnomAD data from {url}")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".vcf.bgz")
    
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
        logger.error(f"Error downloading gnomAD data: {e}")
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise e

def process_gnomad_vcf(file_path: str, db_path: str) -> int:
    """Process gnomAD VCF file and extract frequency data."""
    logger.info("Processing gnomAD VCF data...")
    
    try:
        processed_rows = 0
        conn = duckdb.connect(db_path)
        
        # Process VCF file line by line (it's compressed)
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            batch_size = 1000
            batch_data = []
            
            for line_num, line in enumerate(f):
                if line_num % 10000 == 0:
                    logger.info(f"Processing line {line_num:,}")
                
                # Skip header lines
                if line.startswith('#'):
                    continue
                
                # Parse VCF line
                variant_data = parse_vcf_line(line)
                if variant_data:
                    batch_data.append(variant_data)
                    
                    # Insert batch when full
                    if len(batch_data) >= batch_size:
                        insert_gnomad_batch(conn, batch_data)
                        processed_rows += len(batch_data)
                        batch_data = []
            
            # Insert remaining data
            if batch_data:
                insert_gnomad_batch(conn, batch_data)
                processed_rows += len(batch_data)
        
        conn.close()
        logger.info(f"gnomAD processing completed. Total variants processed: {processed_rows:,}")
        return processed_rows
        
    except Exception as e:
        logger.error(f"Error processing gnomAD data: {e}")
        raise e
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)

def parse_vcf_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single VCF line and extract relevant frequency data."""
    try:
        fields = line.strip().split('\t')
        if len(fields) < 8:
            return None
        
        chrom = fields[0]
        pos = int(fields[1])
        variant_id = fields[2]  # May contain rsID
        ref = fields[3]
        alt = fields[4]
        info = fields[7]
        
        # Extract rsID if present
        rsid = None
        if variant_id.startswith('rs'):
            rsid = variant_id
        else:
            # Look for rsID in INFO field
            rs_match = re.search(r'RS=(\d+)', info)
            if rs_match:
                rsid = f"rs{rs_match.group(1)}"
        
        # Skip variants without rsID
        if not rsid:
            return None
        
        # Parse INFO field for frequency data
        info_dict = parse_info_field(info)
        
        # Extract allele frequency
        af = info_dict.get('AF', 0.0)
        ac = info_dict.get('AC', 0)
        an = info_dict.get('AN', 0)
        nhomalt = info_dict.get('nhomalt', 0)
        
        # Extract population frequencies
        pop_frequencies = extract_population_frequencies(info_dict)
        
        variant_data = {
            'rsid': rsid,
            'chromosome': chrom,
            'position': pos,
            'reference_allele': ref,
            'alternate_allele': alt,
            'allele_frequency': float(af) if af else 0.0,
            'allele_count': int(ac) if ac else 0,
            'allele_number': int(an) if an else 0,
            'homozygote_count': int(nhomalt) if nhomalt else 0,
            'population_frequencies': json.dumps(pop_frequencies)
        }
        
        return variant_data
        
    except Exception as e:
        logger.debug(f"Error parsing VCF line: {e}")
        return None

def parse_info_field(info: str) -> Dict[str, Any]:
    """Parse VCF INFO field into dictionary."""
    info_dict = {}
    
    for item in info.split(';'):
        if '=' in item:
            key, value = item.split('=', 1)
            # Try to convert to appropriate type
            try:
                if ',' in value:
                    # Multiple values
                    info_dict[key] = [float(v) if '.' in v else int(v) for v in value.split(',')]
                elif '.' in value:
                    info_dict[key] = float(value)
                else:
                    info_dict[key] = int(value)
            except ValueError:
                info_dict[key] = value
        else:
            # Flag field
            info_dict[item] = True
    
    return info_dict

def extract_population_frequencies(info_dict: Dict[str, Any]) -> Dict[str, float]:
    """Extract population-specific frequencies from INFO field."""
    pop_frequencies = {}
    
    # Common gnomAD population frequency fields
    population_fields = {
        'AF_afr': 'African',
        'AF_ami': 'Amish', 
        'AF_amr': 'Latino',
        'AF_asj': 'Ashkenazi Jewish',
        'AF_eas': 'East Asian',
        'AF_fin': 'Finnish',
        'AF_nfe': 'Non-Finnish European',
        'AF_oth': 'Other',
        'AF_sas': 'South Asian'
    }
    
    for field, population in population_fields.items():
        if field in info_dict:
            freq = info_dict[field]
            if isinstance(freq, list) and freq:
                freq = freq[0]  # Take first value for multi-allelic
            if freq is not None:
                pop_frequencies[population] = float(freq)
    
    return pop_frequencies

def insert_gnomad_batch(conn: duckdb.DuckDBPyConnection, batch_data: list):
    """Insert batch of gnomAD data into database."""
    try:
        # Prepare data for insertion
        values = []
        for variant in batch_data:
            values.append((
                variant['rsid'],
                variant['chromosome'],
                variant['position'],
                variant['reference_allele'],
                variant['alternate_allele'],
                variant['allele_frequency'],
                variant['allele_count'],
                variant['allele_number'],
                variant['homozygote_count'],
                variant['population_frequencies']
            ))
        
        insert_sql = """
        INSERT OR REPLACE INTO gnomad_frequencies 
        (rsid, chromosome, position, reference_allele, alternate_allele, 
         allele_frequency, allele_count, allele_number, homozygote_count, 
         population_frequencies, cached_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        conn.executemany(insert_sql, values)
        
    except Exception as e:
        logger.error(f"Error inserting gnomAD batch: {e}")
        raise e

def main():
    """Main function for gnomAD ingestion."""
    try:
        db_path = os.getenv("DUCKDB_PATH", "/app/data/genomic.duckdb")
        
        # Ensure database is initialized
        from scripts.init_database import init_database
        init_database(db_path)
        
        # Download and process gnomAD data
        temp_file = download_gnomad_data()
        processed_rows = process_gnomad_vcf(temp_file, db_path)
        
        logger.info(f"gnomAD ingestion completed successfully. Processed {processed_rows:,} variants.")
        
    except Exception as e:
        logger.error(f"gnomAD ingestion failed: {e}")
        raise e

if __name__ == "__main__":
    main() 