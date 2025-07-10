"""
Parser for 23andMe .txt files using pandas.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def parse_23andme_txt(file_path: str) -> List[Dict[str, Any]]:
    """
    Parseia arquivo .txt do 23andMe para lista de variantes.
    
    Parameters
    ----------
    file_path : str
        Caminho para o arquivo .txt.
        
    Returns
    -------
    list
        Lista de dicionários com rsID, cromossomo, posição e genótipo.
        
    Raises
    ------
    FileNotFoundError
        Se o arquivo não for encontrado.
    ValueError
        Se o formato do arquivo for inválido.
    """
    try:
        logger.info(f"Parsing 23andMe file: {file_path}")
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read the file, skipping comment lines
        df = pd.read_csv(
            file_path, 
            comment='#', 
            sep='\t',
            names=['rsID', 'chromosome', 'position', 'genotype'],
            dtype={
                'rsID': 'string',
                'chromosome': 'string', 
                'position': 'Int64',
                'genotype': 'string'
            }
        )
        
        logger.info(f"Raw data loaded: {len(df)} rows")
        
        # Clean the data
        df_clean = clean_variant_data(df)
        
        logger.info(f"Clean data: {len(df_clean)} variants")
        
        # Convert to list of dictionaries
        variants = df_clean.to_dict(orient='records')
        
        return variants
        
    except Exception as e:
        logger.error(f"Error parsing 23andMe file: {e}")
        raise e

def clean_variant_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and filter variant data from 23andMe.
    
    Parameters
    ----------
    df : pd.DataFrame
        Raw dataframe from 23andMe file.
        
    Returns
    -------
    pd.DataFrame
        Cleaned dataframe with valid variants.
    """
    # Remove rows with missing data
    df_clean = df.dropna()
    
    # Filter for valid rsIDs
    df_clean = df_clean[df_clean['rsID'].str.startswith('rs', na=False)]
    
    # Filter out invalid chromosomes
    valid_chromosomes = [str(i) for i in range(1, 23)] + ['X', 'Y', 'MT']
    df_clean = df_clean[df_clean['chromosome'].isin(valid_chromosomes)]
    
    # Filter out invalid genotypes (keep only standard nucleotides)
    valid_genotype_pattern = r'^[ATCG-]{1,2}$|^[ATCG][ATCG]$|^--$'
    df_clean = df_clean[df_clean['genotype'].str.match(valid_genotype_pattern, na=False)]
    
    # Remove duplicates
    df_clean = df_clean.drop_duplicates(subset=['rsID'])
    
    # Sort by chromosome and position
    chromosome_order = [str(i) for i in range(1, 23)] + ['X', 'Y', 'MT']
    df_clean['chr_order'] = df_clean['chromosome'].apply(
        lambda x: chromosome_order.index(x) if x in chromosome_order else 999
    )
    df_clean = df_clean.sort_values(['chr_order', 'position']).drop('chr_order', axis=1)
    
    return df_clean

def validate_23andme_format(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if file is in 23andMe format.
    
    Parameters
    ----------
    file_path : str
        Path to the file to validate.
        
    Returns
    -------
    tuple
        (is_valid, error_message)
    """
    try:
        # Check file extension
        if not file_path.lower().endswith('.txt'):
            return False, "File must have .txt extension"
        
        # Check file size (should be reasonable)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            return False, "File too large (>50MB)"
        
        if file_size < 1024:  # 1KB minimum
            return False, "File too small (<1KB)"
        
        # Read first few lines to check format
        with open(file_path, 'r') as f:
            lines = []
            for i, line in enumerate(f):
                lines.append(line.strip())
                if i >= 100:  # Check first 100 lines
                    break
        
        # Should have comment lines starting with #
        has_comments = any(line.startswith('#') for line in lines)
        if not has_comments:
            return False, "Missing header comments (lines starting with #)"
        
        # Find first data line
        data_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        if not data_lines:
            return False, "No data lines found"
        
        # Check if first data line has 4 tab-separated columns
        first_data_line = data_lines[0]
        columns = first_data_line.split('\t')
        if len(columns) != 4:
            return False, f"Expected 4 columns, found {len(columns)}"
        
        # Check if first column looks like rsID
        rsid = columns[0].strip()
        if not rsid.startswith('rs'):
            return False, f"First column should be rsID, found: {rsid}"
        
        # Check if position is numeric
        try:
            int(columns[2])
        except ValueError:
            return False, f"Third column should be numeric position, found: {columns[2]}"
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def get_file_statistics(file_path: str) -> Dict[str, Any]:
    """
    Get statistics about the 23andMe file.
    
    Parameters
    ----------
    file_path : str
        Path to the file.
        
    Returns
    -------
    dict
        File statistics including variant counts by chromosome.
    """
    try:
        variants = parse_23andme_txt(file_path)
        
        df = pd.DataFrame(variants)
        
        stats = {
            'total_variants': len(df),
            'chromosomes': sorted(df['chromosome'].unique().tolist()),
            'variants_by_chromosome': df['chromosome'].value_counts().to_dict(),
            'genotype_distribution': df['genotype'].value_counts().to_dict(),
            'file_size_bytes': os.path.getsize(file_path),
            'sample_variants': variants[:5] if variants else []
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting file statistics: {e}")
        return {
            'error': str(e),
            'total_variants': 0,
            'file_size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }

def extract_header_info(file_path: str) -> Dict[str, str]:
    """
    Extract header information from 23andMe file.
    
    Parameters
    ----------
    file_path : str
        Path to the file.
        
    Returns
    -------
    dict
        Header information extracted from comments.
    """
    header_info = {}
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('#'):
                    break
                    
                # Remove the # and parse key-value pairs
                line = line[1:].strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    header_info[key.strip()] = value.strip()
                elif line:
                    # Store lines without colons as general info
                    if 'general_info' not in header_info:
                        header_info['general_info'] = []
                    header_info['general_info'].append(line)
        
        return header_info
        
    except Exception as e:
        logger.error(f"Error extracting header info: {e}")
        return {'error': str(e)}

def convert_to_standard_format(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert parsed variants to standardized format for further processing.
    
    Parameters
    ----------
    variants : list
        List of variant dictionaries from parse_23andme_txt.
        
    Returns
    -------
    list
        Standardized variant format.
    """
    standardized = []
    
    for variant in variants:
        try:
            standardized_variant = {
                'rsID': variant['rsID'],
                'chromosome': str(variant['chromosome']),
                'position': int(variant['position']),
                'genotype': variant['genotype'],
                'source': '23andMe',
                'file_format': 'txt'
            }
            
            # Parse alleles from genotype
            genotype = variant['genotype']
            if genotype != '--' and len(genotype) == 2:
                standardized_variant['allele1'] = genotype[0]
                standardized_variant['allele2'] = genotype[1]
                standardized_variant['is_heterozygous'] = genotype[0] != genotype[1]
            else:
                standardized_variant['allele1'] = None
                standardized_variant['allele2'] = None
                standardized_variant['is_heterozygous'] = None
                
            standardized.append(standardized_variant)
            
        except Exception as e:
            logger.warning(f"Error standardizing variant {variant}: {e}")
            continue
    
    return standardized 