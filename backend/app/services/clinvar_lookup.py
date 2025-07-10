"""
ClinVar lookup service for variant annotation.
"""

from typing import Dict, Any, Optional, List
import logging
from app.dependencies import get_database

logger = logging.getLogger(__name__)

def lookup_clinvar_variant(rsid: str) -> Optional[Dict[str, Any]]:
    """
    Look up variant information in ClinVar database.
    
    Parameters
    ----------
    rsid : str
        rsID to lookup.
        
    Returns
    -------
    dict or None
        ClinVar variant information if found.
    """
    try:
        db = get_database()
        
        query = """
        SELECT 
            rsID,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            clinical_significance,
            review_status,
            phenotype,
            gene_symbol,
            hgvs_c,
            hgvs_p,
            molecular_consequence
        FROM clinvar_variants 
        WHERE rsID = ?
        """
        
        result = db.execute(query, [rsid]).fetchone()
        
        if result:
            # Convert to dictionary
            columns = [
                'rsID', 'chromosome', 'position', 'reference_allele',
                'alternate_allele', 'clinical_significance', 'review_status',
                'phenotype', 'gene_symbol', 'hgvs_c', 'hgvs_p', 'molecular_consequence'
            ]
            
            variant_info = {col: result[i] for i, col in enumerate(columns)}
            logger.debug(f"Found ClinVar variant: {rsid}")
            return variant_info
        else:
            logger.debug(f"ClinVar variant not found: {rsid}")
            return None
            
    except Exception as e:
        logger.error(f"Error looking up ClinVar variant {rsid}: {e}")
        return None

def batch_lookup_clinvar_variants(rsids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Batch lookup of multiple variants in ClinVar.
    
    Parameters
    ----------
    rsids : list
        List of rsIDs to lookup.
        
    Returns
    -------
    dict
        Dictionary mapping rsID to variant information.
    """
    try:
        db = get_database()
        
        # Create placeholders for IN clause
        placeholders = ','.join(['?'] * len(rsids))
        
        query = f"""
        SELECT 
            rsID,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            clinical_significance,
            review_status,
            phenotype,
            gene_symbol,
            hgvs_c,
            hgvs_p,
            molecular_consequence
        FROM clinvar_variants 
        WHERE rsID IN ({placeholders})
        """
        
        results = db.execute(query, rsids).fetchall()
        
        # Convert to dictionary
        variants = {}
        columns = [
            'rsID', 'chromosome', 'position', 'reference_allele',
            'alternate_allele', 'clinical_significance', 'review_status',
            'phenotype', 'gene_symbol', 'hgvs_c', 'hgvs_p', 'molecular_consequence'
        ]
        
        for result in results:
            variant_info = {col: result[i] for i, col in enumerate(columns)}
            variants[variant_info['rsID']] = variant_info
        
        logger.info(f"Found {len(variants)} ClinVar variants out of {len(rsids)} requested")
        return variants
        
    except Exception as e:
        logger.error(f"Error in batch ClinVar lookup: {e}")
        return {}

def get_clinvar_statistics() -> Dict[str, Any]:
    """
    Get statistics about ClinVar database.
    
    Returns
    -------
    dict
        Database statistics.
    """
    try:
        db = get_database()
        
        stats = {}
        
        # Total variants
        result = db.execute("SELECT COUNT(*) FROM clinvar_variants").fetchone()
        stats['total_variants'] = result[0] if result else 0
        
        # Variants by clinical significance
        significance_query = """
        SELECT clinical_significance, COUNT(*) as count
        FROM clinvar_variants 
        GROUP BY clinical_significance
        ORDER BY count DESC
        """
        results = db.execute(significance_query).fetchall()
        stats['by_significance'] = {row[0]: row[1] for row in results}
        
        # Variants by chromosome
        chromosome_query = """
        SELECT chromosome, COUNT(*) as count
        FROM clinvar_variants 
        GROUP BY chromosome
        ORDER BY 
            CASE 
                WHEN chromosome GLOB '[0-9]*' THEN CAST(chromosome AS INTEGER)
                ELSE 999 
            END,
            chromosome
        """
        results = db.execute(chromosome_query).fetchall()
        stats['by_chromosome'] = {row[0]: row[1] for row in results}
        
        # Variants by review status
        review_query = """
        SELECT review_status, COUNT(*) as count
        FROM clinvar_variants 
        GROUP BY review_status
        ORDER BY count DESC
        """
        results = db.execute(review_query).fetchall()
        stats['by_review_status'] = {row[0]: row[1] for row in results}
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting ClinVar statistics: {e}")
        return {'error': str(e)}

def search_clinvar_by_gene(gene_symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search ClinVar variants by gene symbol.
    
    Parameters
    ----------
    gene_symbol : str
        Gene symbol to search for.
    limit : int
        Maximum number of results to return.
        
    Returns
    -------
    list
        List of variant information.
    """
    try:
        db = get_database()
        
        query = """
        SELECT 
            rsID,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            clinical_significance,
            review_status,
            phenotype,
            gene_symbol,
            hgvs_c,
            hgvs_p,
            molecular_consequence
        FROM clinvar_variants 
        WHERE gene_symbol = ?
        ORDER BY position
        LIMIT ?
        """
        
        results = db.execute(query, [gene_symbol, limit]).fetchall()
        
        # Convert to list of dictionaries
        variants = []
        columns = [
            'rsID', 'chromosome', 'position', 'reference_allele',
            'alternate_allele', 'clinical_significance', 'review_status',
            'phenotype', 'gene_symbol', 'hgvs_c', 'hgvs_p', 'molecular_consequence'
        ]
        
        for result in results:
            variant_info = {col: result[i] for i, col in enumerate(columns)}
            variants.append(variant_info)
        
        logger.info(f"Found {len(variants)} ClinVar variants for gene {gene_symbol}")
        return variants
        
    except Exception as e:
        logger.error(f"Error searching ClinVar by gene {gene_symbol}: {e}")
        return []

def get_pathogenic_variants(limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get pathogenic and likely pathogenic variants from ClinVar.
    
    Parameters
    ----------
    limit : int
        Maximum number of results to return.
        
    Returns
    -------
    list
        List of pathogenic variants.
    """
    try:
        db = get_database()
        
        query = """
        SELECT 
            rsID,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            clinical_significance,
            review_status,
            phenotype,
            gene_symbol,
            hgvs_c,
            hgvs_p,
            molecular_consequence
        FROM clinvar_variants 
        WHERE clinical_significance LIKE '%athogenic%'
        ORDER BY 
            CASE 
                WHEN clinical_significance LIKE '%Pathogenic%' THEN 1
                WHEN clinical_significance LIKE '%Likely_pathogenic%' THEN 2
                ELSE 3
            END,
            gene_symbol,
            position
        LIMIT ?
        """
        
        results = db.execute(query, [limit]).fetchall()
        
        # Convert to list of dictionaries
        variants = []
        columns = [
            'rsID', 'chromosome', 'position', 'reference_allele',
            'alternate_allele', 'clinical_significance', 'review_status',
            'phenotype', 'gene_symbol', 'hgvs_c', 'hgvs_p', 'molecular_consequence'
        ]
        
        for result in results:
            variant_info = {col: result[i] for i, col in enumerate(columns)}
            variants.append(variant_info)
        
        logger.info(f"Found {len(variants)} pathogenic ClinVar variants")
        return variants
        
    except Exception as e:
        logger.error(f"Error getting pathogenic variants: {e}")
        return []

# gnomAD lookup functions
def lookup_gnomad_frequency(rsid: str) -> Optional[Dict[str, Any]]:
    """
    Look up variant frequency information in gnomAD database.
    
    Parameters
    ----------
    rsid : str
        rsID to lookup.
        
    Returns
    -------
    dict or None
        gnomAD frequency information if found.
    """
    try:
        db = get_database()
        
        query = """
        SELECT 
            rsid,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            allele_frequency,
            allele_count,
            allele_number,
            homozygote_count,
            population_frequencies
        FROM gnomad_frequencies 
        WHERE rsid = ?
        """
        
        result = db.execute(query, [rsid]).fetchone()
        
        if result:
            # Convert to dictionary
            columns = [
                'rsid', 'chromosome', 'position', 'reference_allele',
                'alternate_allele', 'allele_frequency', 'allele_count',
                'allele_number', 'homozygote_count', 'population_frequencies'
            ]
            
            freq_info = {col: result[i] for i, col in enumerate(columns)}
            logger.debug(f"Found gnomAD frequency: {rsid} - {freq_info['allele_frequency']}")
            return freq_info
        else:
            logger.debug(f"gnomAD frequency not found: {rsid}")
            return None
            
    except Exception as e:
        logger.error(f"Error looking up gnomAD frequency {rsid}: {e}")
        return None

def batch_lookup_gnomad_frequencies(rsids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Batch lookup of multiple variants in gnomAD.
    
    Parameters
    ----------
    rsids : list
        List of rsIDs to lookup.
        
    Returns
    -------
    dict
        Dictionary mapping rsID to frequency information.
    """
    try:
        db = get_database()
        
        # Create placeholders for IN clause
        placeholders = ','.join(['?'] * len(rsids))
        
        query = f"""
        SELECT 
            rsid,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            allele_frequency,
            allele_count,
            allele_number,
            homozygote_count,
            population_frequencies
        FROM gnomad_frequencies 
        WHERE rsid IN ({placeholders})
        """
        
        results = db.execute(query, rsids).fetchall()
        
        # Convert to dictionary
        frequencies = {}
        columns = [
            'rsid', 'chromosome', 'position', 'reference_allele',
            'alternate_allele', 'allele_frequency', 'allele_count',
            'allele_number', 'homozygote_count', 'population_frequencies'
        ]
        
        for result in results:
            freq_info = {col: result[i] for i, col in enumerate(columns)}
            frequencies[freq_info['rsid']] = freq_info
        
        logger.info(f"Found {len(frequencies)} gnomAD frequencies out of {len(rsids)} requested")
        return frequencies
        
    except Exception as e:
        logger.error(f"Error in batch gnomAD lookup: {e}")
        return {}

def get_rare_variants(max_frequency: float = 0.01, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get rare variants from gnomAD (frequency below threshold).
    
    Parameters
    ----------
    max_frequency : float
        Maximum allele frequency threshold.
    limit : int
        Maximum number of results to return.
        
    Returns
    -------
    list
        List of rare variants.
    """
    try:
        db = get_database()
        
        query = """
        SELECT 
            rsid,
            chromosome,
            position,
            reference_allele,
            alternate_allele,
            allele_frequency,
            allele_count,
            allele_number,
            homozygote_count,
            population_frequencies
        FROM gnomad_frequencies 
        WHERE allele_frequency <= ? AND allele_frequency > 0
        ORDER BY allele_frequency ASC
        LIMIT ?
        """
        
        results = db.execute(query, [max_frequency, limit]).fetchall()
        
        # Convert to list of dictionaries
        variants = []
        columns = [
            'rsid', 'chromosome', 'position', 'reference_allele',
            'alternate_allele', 'allele_frequency', 'allele_count',
            'allele_number', 'homozygote_count', 'population_frequencies'
        ]
        
        for result in results:
            freq_info = {col: result[i] for i, col in enumerate(columns)}
            variants.append(freq_info)
        
        logger.info(f"Found {len(variants)} rare variants (frequency <= {max_frequency})")
        return variants
        
    except Exception as e:
        logger.error(f"Error getting rare variants: {e}")
        return [] 