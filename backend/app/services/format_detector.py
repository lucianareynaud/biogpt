"""
File format detector and validator for genomic data.
"""

from typing import Dict, Any, Tuple, Optional
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def detect_file_format(file_path: str) -> Tuple[str, float, Optional[str]]:
    """
    Detect the format of a genomic file.
    
    Parameters
    ----------
    file_path : str
        Path to the file to analyze.
        
    Returns
    -------
    tuple
        (format_name, confidence_score, error_message)
    """
    try:
        if not os.path.exists(file_path):
            return "unknown", 0.0, "File not found"
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return "unknown", 0.0, "Empty file"
        
        # Check file extension first
        file_ext = Path(file_path).suffix.lower()
        
        # Read first few lines for content analysis
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    lines.append(line.strip())
                    if i >= 50:  # Read first 50 lines
                        break
        except UnicodeDecodeError:
            return "unknown", 0.0, "File is not text-based or has encoding issues"
        
        # Analyze content
        if file_ext == '.txt':
            return analyze_txt_format(lines, file_path)
        elif file_ext in ['.vcf', '.vcf.gz']:
            return analyze_vcf_format(lines)
        elif file_ext in ['.csv', '.tsv']:
            return analyze_csv_tsv_format(lines, file_ext)
        else:
            # Try to detect format from content
            return analyze_content_only(lines, file_path)
            
    except Exception as e:
        logger.error(f"Error detecting file format: {e}")
        return "unknown", 0.0, f"Analysis error: {str(e)}"

def analyze_txt_format(lines: list, file_path: str) -> Tuple[str, float, Optional[str]]:
    """
    Analyze .txt file to determine specific format.
    
    Parameters
    ----------
    lines : list
        List of file lines.
    file_path : str
        File path for additional validation.
        
    Returns
    -------
    tuple
        (format_name, confidence_score, error_message)
    """
    # Check for 23andMe format
    score_23andme = 0.0
    
    # Look for header comments
    header_lines = [line for line in lines if line.startswith('#')]
    if header_lines:
        score_23andme += 0.3
        
        # Check for 23andMe specific headers
        header_text = ' '.join(header_lines).lower()
        if '23andme' in header_text:
            score_23andme += 0.4
        if 'rsid' in header_text:
            score_23andme += 0.2
    
    # Look for data format
    data_lines = [line for line in lines if not line.startswith('#') and line.strip()]
    if data_lines:
        first_data_line = data_lines[0]
        columns = first_data_line.split('\t')
        
        # 23andMe should have 4 tab-separated columns
        if len(columns) == 4:
            score_23andme += 0.3
            
            # Check if first column looks like rsID
            if columns[0].startswith('rs') and columns[0][2:].isdigit():
                score_23andme += 0.3
                
            # Check if third column is numeric (position)
            try:
                int(columns[2])
                score_23andme += 0.2
            except ValueError:
                pass
                
            # Check if fourth column looks like genotype
            genotype = columns[3].strip()
            if len(genotype) <= 2 and all(c in 'ATCG-' for c in genotype):
                score_23andme += 0.2
    
    if score_23andme >= 0.7:
        # Additional validation
        from app.services.variant_parser import validate_23andme_format
        is_valid, error = validate_23andme_format(file_path)
        if is_valid:
            return "23andme_txt", min(score_23andme, 0.95), None
        else:
            return "23andme_txt", score_23andme, error
    
    return "unknown_txt", score_23andme, "Could not determine specific txt format"

def analyze_vcf_format(lines: list) -> Tuple[str, float, Optional[str]]:
    """
    Analyze VCF file format.
    
    Parameters
    ----------
    lines : list
        List of file lines.
        
    Returns
    -------
    tuple
        (format_name, confidence_score, error_message)
    """
    score = 0.0
    
    # VCF should start with ##fileformat=VCF
    if lines and lines[0].startswith('##fileformat=VCF'):
        score += 0.5
    
    # Look for required VCF headers
    header_count = 0
    for line in lines:
        if line.startswith('##'):
            header_count += 1
        elif line.startswith('#CHROM'):
            score += 0.3
            break
    
    if header_count > 0:
        score += 0.2
    
    if score >= 0.7:
        return "vcf", score, None
    else:
        return "unknown_vcf", score, "Invalid VCF format"

def analyze_csv_tsv_format(lines: list, file_ext: str) -> Tuple[str, float, Optional[str]]:
    """
    Analyze CSV/TSV file format.
    
    Parameters
    ----------
    lines : list
        List of file lines.
    file_ext : str
        File extension.
        
    Returns
    -------
    tuple
        (format_name, confidence_score, error_message)
    """
    if not lines:
        return "unknown", 0.0, "Empty file"
    
    delimiter = ',' if file_ext == '.csv' else '\t'
    
    # Check first line for headers
    first_line = lines[0]
    columns = first_line.split(delimiter)
    
    if len(columns) >= 3:
        # Look for genomic-related headers
        header_text = first_line.lower()
        score = 0.3
        
        genomic_terms = ['chr', 'pos', 'ref', 'alt', 'rsid', 'variant', 'genotype']
        for term in genomic_terms:
            if term in header_text:
                score += 0.1
        
        return f"genomic_{file_ext[1:]}", min(score, 0.9), None
    
    return f"generic_{file_ext[1:]}", 0.3, "Generic delimited file"

def analyze_content_only(lines: list, file_path: str) -> Tuple[str, float, Optional[str]]:
    """
    Analyze file content without relying on extension.
    
    Parameters
    ----------
    lines : list
        List of file lines.
    file_path : str
        File path.
        
    Returns
    -------
    tuple
        (format_name, confidence_score, error_message)
    """
    if not lines:
        return "unknown", 0.0, "Empty file"
    
    # Try different format detectors
    formats_to_try = [
        lambda: analyze_txt_format(lines, file_path),
        lambda: analyze_vcf_format(lines),
        lambda: ("unknown", 0.0, "Could not determine format")
    ]
    
    best_format = ("unknown", 0.0, "Could not determine format")
    
    for detector in formats_to_try:
        try:
            result = detector()
            if result[1] > best_format[1]:  # Better confidence score
                best_format = result
        except Exception as e:
            logger.warning(f"Format detector failed: {e}")
            continue
    
    return best_format

def validate_genomic_file(file_path: str) -> Dict[str, Any]:
    """
    Comprehensive validation of genomic file.
    
    Parameters
    ----------
    file_path : str
        Path to file to validate.
        
    Returns
    -------
    dict
        Validation results.
    """
    try:
        # Basic file checks
        if not os.path.exists(file_path):
            return {
                'valid': False,
                'format': 'unknown',
                'confidence': 0.0,
                'error': 'File not found',
                'file_size': 0,
                'line_count': 0
            }
        
        file_size = os.path.getsize(file_path)
        
        # Size limits
        if file_size > 100 * 1024 * 1024:  # 100MB
            return {
                'valid': False,
                'format': 'unknown',
                'confidence': 0.0,
                'error': 'File too large (>100MB)',
                'file_size': file_size,
                'line_count': 0
            }
        
        if file_size < 100:  # 100 bytes minimum
            return {
                'valid': False,
                'format': 'unknown',
                'confidence': 0.0,
                'error': 'File too small (<100 bytes)',
                'file_size': file_size,
                'line_count': 0
            }
        
        # Count lines
        try:
            with open(file_path, 'r') as f:
                line_count = sum(1 for _ in f)
        except Exception:
            line_count = 0
        
        # Detect format
        format_name, confidence, error = detect_file_format(file_path)
        
        # Determine if file is valid
        is_valid = confidence >= 0.7 and error is None
        
        result = {
            'valid': is_valid,
            'format': format_name,
            'confidence': confidence,
            'error': error,
            'file_size': file_size,
            'line_count': line_count,
            'file_path': file_path
        }
        
        # Add format-specific validation
        if format_name == '23andme_txt' and is_valid:
            from app.services.variant_parser import get_file_statistics
            stats = get_file_statistics(file_path)
            result['statistics'] = stats
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating genomic file: {e}")
        return {
            'valid': False,
            'format': 'unknown',
            'confidence': 0.0,
            'error': f'Validation error: {str(e)}',
            'file_size': 0,
            'line_count': 0
        } 