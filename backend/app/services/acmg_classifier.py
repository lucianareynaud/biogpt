"""
ACMG-2015 simplified classifier for genomic variants.
"""

from typing import Dict, Any, List, Optional
import logging
from app.models.schemas import VariantClassification

logger = logging.getLogger(__name__)

def classify_variant(
    variant: Dict[str, Any], 
    clinvar_info: Optional[Dict[str, Any]] = None, 
    gnomad_freq: Optional[float] = None
) -> str:
    """
    Classifica variante com base em ACMG-2015 simplificado.
    
    Parameters
    ----------
    variant : dict
        Variante parseada (rsID, genótipo, etc.).
    clinvar_info : dict, optional
        Informações do ClinVar.
    gnomad_freq : float, optional
        Frequência alélica no gnomAD.
        
    Returns
    -------
    str
        Classificação (ex.: Patogênica, Benigna, VUS).
    """
    try:
        logger.debug(f"Classifying variant: {variant.get('rsID', 'unknown')}")
        
        # Extract genotype information
        genotype = variant.get('genotype', '')
        rsid = variant.get('rsID', '')
        
        # Apply ACMG criteria in order of priority
        
        # 1. Strong pathogenic evidence from ClinVar
        if clinvar_info:
            clinical_sig = clinvar_info.get('clinical_significance', '').lower()
            review_status = clinvar_info.get('review_status', '').lower()
            
            # High confidence pathogenic classifications
            if any(term in clinical_sig for term in ['pathogenic', 'likely pathogenic']):
                if any(term in review_status for term in ['reviewed by expert panel', 'practice guideline']):
                    return VariantClassification.PATHOGENIC.value
                elif 'likely pathogenic' in clinical_sig:
                    return VariantClassification.LIKELY_PATHOGENIC.value
                elif 'pathogenic' in clinical_sig:
                    return VariantClassification.PATHOGENIC.value
            
            # High confidence benign classifications
            if any(term in clinical_sig for term in ['benign', 'likely benign']):
                if any(term in review_status for term in ['reviewed by expert panel', 'practice guideline']):
                    return VariantClassification.BENIGN.value
                elif 'likely benign' in clinical_sig:
                    return VariantClassification.LIKELY_BENIGN.value
                elif 'benign' in clinical_sig:
                    return VariantClassification.BENIGN.value
        
        # 2. Population frequency evidence (BA1/BS1 criteria)
        if gnomad_freq is not None:
            # BA1: Allele frequency >5% in any general population
            if gnomad_freq > 0.05:
                return VariantClassification.BENIGN.value
            
            # BS1: Allele frequency >1% in population with low disease prevalence
            elif gnomad_freq > 0.01:
                return VariantClassification.LIKELY_BENIGN.value
        
        # 3. Genotype-specific analysis
        classification_score = 0
        criteria_applied = []
        
        # Check if variant is homozygous for alternate allele
        if is_homozygous_alternate(genotype):
            # More likely to be significant if homozygous
            classification_score += 1
            criteria_applied.append("Homozygous alternate")
        
        # 4. Gene-specific considerations (simplified)
        if clinvar_info:
            gene_symbol = clinvar_info.get('gene_symbol', '')
            molecular_consequence = clinvar_info.get('molecular_consequence', '')
            
            # Check for high-impact molecular consequences
            if any(term in molecular_consequence.lower() for term in [
                'stop_gained', 'frameshift', 'splice_acceptor', 'splice_donor'
            ]):
                classification_score += 2
                criteria_applied.append("High-impact molecular consequence")
            
            # Check for moderate-impact consequences
            elif any(term in molecular_consequence.lower() for term in [
                'missense', 'inframe_deletion', 'inframe_insertion'
            ]):
                classification_score += 1
                criteria_applied.append("Moderate-impact molecular consequence")
        
        # 5. Final classification based on accumulated evidence
        if classification_score >= 3:
            return VariantClassification.LIKELY_PATHOGENIC.value
        elif classification_score >= 2:
            return VariantClassification.VUS.value
        elif classification_score == 1:
            return VariantClassification.VUS.value
        else:
            # Low evidence, but check for very rare variants
            if gnomad_freq is not None and gnomad_freq < 0.0001:
                return VariantClassification.VUS.value
            else:
                return VariantClassification.LIKELY_BENIGN.value
        
    except Exception as e:
        logger.error(f"Error classifying variant {variant.get('rsID', 'unknown')}: {e}")
        return VariantClassification.VUS.value

def is_homozygous_alternate(genotype: str) -> bool:
    """
    Check if genotype represents homozygous alternate allele.
    
    Parameters
    ----------
    genotype : str
        Genotype string (e.g., 'AA', 'AG', 'GG').
        
    Returns
    -------
    bool
        True if homozygous for alternate allele.
    """
    if not genotype or len(genotype) != 2:
        return False
    
    # For 23andMe data, we don't know reference vs alternate
    # So we consider non-reference homozygotes as potentially significant
    return genotype[0] == genotype[1] and genotype != '--'

def get_acmg_criteria_details(
    variant: Dict[str, Any],
    clinvar_info: Optional[Dict[str, Any]] = None,
    gnomad_freq: Optional[float] = None
) -> Dict[str, Any]:
    """
    Get detailed ACMG criteria analysis for a variant.
    
    Parameters
    ----------
    variant : dict
        Variant information.
    clinvar_info : dict, optional
        ClinVar information.
    gnomad_freq : float, optional
        gnomAD frequency.
        
    Returns
    -------
    dict
        Detailed ACMG analysis.
    """
    criteria = {
        'pathogenic': [],
        'benign': [],
        'uncertain': [],
        'supporting_evidence': [],
        'conflicting_evidence': []
    }
    
    try:
        # Population frequency criteria
        if gnomad_freq is not None:
            if gnomad_freq > 0.05:
                criteria['benign'].append({
                    'code': 'BA1',
                    'description': 'Allele frequency >5% in general population',
                    'evidence': f'gnomAD frequency: {gnomad_freq:.4f}'
                })
            elif gnomad_freq > 0.01:
                criteria['benign'].append({
                    'code': 'BS1',
                    'description': 'Allele frequency >1% in population',
                    'evidence': f'gnomAD frequency: {gnomad_freq:.4f}'
                })
            elif gnomad_freq < 0.0001:
                criteria['supporting_evidence'].append({
                    'code': 'PM2_Supporting',
                    'description': 'Very rare variant in population',
                    'evidence': f'gnomAD frequency: {gnomad_freq:.6f}'
                })
        
        # ClinVar evidence
        if clinvar_info:
            clinical_sig = clinvar_info.get('clinical_significance', '').lower()
            review_status = clinvar_info.get('review_status', '').lower()
            
            if 'pathogenic' in clinical_sig:
                if 'reviewed by expert panel' in review_status:
                    criteria['pathogenic'].append({
                        'code': 'PS1',
                        'description': 'Expert panel reviewed pathogenic',
                        'evidence': f'ClinVar: {clinical_sig}'
                    })
                else:
                    criteria['supporting_evidence'].append({
                        'code': 'PP5',
                        'description': 'Reported as pathogenic in ClinVar',
                        'evidence': f'ClinVar: {clinical_sig}'
                    })
            
            elif 'benign' in clinical_sig:
                criteria['benign'].append({
                    'code': 'BP6',
                    'description': 'Reported as benign in ClinVar',
                    'evidence': f'ClinVar: {clinical_sig}'
                })
            
            # Molecular consequence evidence
            molecular_consequence = clinvar_info.get('molecular_consequence', '').lower()
            if molecular_consequence:
                if any(term in molecular_consequence for term in [
                    'stop_gained', 'frameshift'
                ]):
                    criteria['pathogenic'].append({
                        'code': 'PVS1',
                        'description': 'Null variant in gene where LOF is pathogenic',
                        'evidence': f'Consequence: {molecular_consequence}'
                    })
                elif any(term in molecular_consequence for term in [
                    'synonymous', 'intron'
                ]):
                    criteria['benign'].append({
                        'code': 'BP7',
                        'description': 'Silent/intronic variant with no impact',
                        'evidence': f'Consequence: {molecular_consequence}'
                    })
        
        # Genotype analysis
        genotype = variant.get('genotype', '')
        if is_homozygous_alternate(genotype):
            criteria['supporting_evidence'].append({
                'code': 'Genotype',
                'description': 'Homozygous alternate genotype',
                'evidence': f'Genotype: {genotype}'
            })
        
        return criteria
        
    except Exception as e:
        logger.error(f"Error getting ACMG criteria: {e}")
        return criteria

def generate_clinical_interpretation(
    classification: str,
    criteria: Dict[str, Any],
    variant: Dict[str, Any],
    language: str = 'pt-BR'
) -> str:
    """
    Generate clinical interpretation text.
    
    Parameters
    ----------
    classification : str
        Variant classification.
    criteria : dict
        ACMG criteria analysis.
    variant : dict
        Variant information.
    language : str
        Language for interpretation ('pt-BR' or 'en').
        
    Returns
    -------
    str
        Clinical interpretation text.
    """
    try:
        rsid = variant.get('rsID', 'unknown')
        genotype = variant.get('genotype', 'unknown')
        
        if language == 'pt-BR':
            templates = {
                VariantClassification.PATHOGENIC.value: (
                    f"A variante {rsid} (genótipo: {genotype}) foi classificada como "
                    f"PATOGÊNICA com base nos critérios ACMG-2015. Esta variante está "
                    f"associada a risco aumentado de desenvolvimento de condições genéticas. "
                    f"Recomenda-se acompanhamento médico especializado."
                ),
                VariantClassification.LIKELY_PATHOGENIC.value: (
                    f"A variante {rsid} (genótipo: {genotype}) foi classificada como "
                    f"PROVAVELMENTE PATOGÊNICA. Existe evidência sugestiva de que esta "
                    f"variante possa estar associada a risco de condições genéticas. "
                    f"Recomenda-se consulta com geneticista."
                ),
                VariantClassification.VUS.value: (
                    f"A variante {rsid} (genótipo: {genotype}) foi classificada como "
                    f"VARIANTE DE SIGNIFICADO INCERTO (VUS). Não há evidência suficiente "
                    f"para determinar o impacto clínico desta variante. Reavaliação "
                    f"periódica pode ser necessária conforme novas evidências emergem."
                ),
                VariantClassification.LIKELY_BENIGN.value: (
                    f"A variante {rsid} (genótipo: {genotype}) foi classificada como "
                    f"PROVAVELMENTE BENIGNA. É improvável que esta variante cause "
                    f"condições genéticas significativas."
                ),
                VariantClassification.BENIGN.value: (
                    f"A variante {rsid} (genótipo: {genotype}) foi classificada como "
                    f"BENIGNA. Esta variante não está associada a risco de condições "
                    f"genéticas e é considerada uma variação normal."
                )
            }
        else:  # English
            templates = {
                VariantClassification.PATHOGENIC.value: (
                    f"Variant {rsid} (genotype: {genotype}) was classified as "
                    f"PATHOGENIC based on ACMG-2015 criteria. This variant is "
                    f"associated with increased risk of genetic conditions. "
                    f"Specialized medical follow-up is recommended."
                ),
                VariantClassification.LIKELY_PATHOGENIC.value: (
                    f"Variant {rsid} (genotype: {genotype}) was classified as "
                    f"LIKELY PATHOGENIC. There is suggestive evidence that this "
                    f"variant may be associated with risk of genetic conditions. "
                    f"Consultation with a geneticist is recommended."
                ),
                VariantClassification.VUS.value: (
                    f"Variant {rsid} (genotype: {genotype}) was classified as "
                    f"VARIANT OF UNCERTAIN SIGNIFICANCE (VUS). There is insufficient "
                    f"evidence to determine the clinical impact of this variant. "
                    f"Periodic reassessment may be necessary as new evidence emerges."
                ),
                VariantClassification.LIKELY_BENIGN.value: (
                    f"Variant {rsid} (genotype: {genotype}) was classified as "
                    f"LIKELY BENIGN. This variant is unlikely to cause significant "
                    f"genetic conditions."
                ),
                VariantClassification.BENIGN.value: (
                    f"Variant {rsid} (genotype: {genotype}) was classified as "
                    f"BENIGN. This variant is not associated with risk of genetic "
                    f"conditions and is considered normal variation."
                )
            }
        
        base_interpretation = templates.get(classification, "Classificação indeterminada.")
        
        # Add supporting evidence
        evidence_count = (
            len(criteria.get('pathogenic', [])) +
            len(criteria.get('benign', [])) +
            len(criteria.get('supporting_evidence', []))
        )
        
        if language == 'pt-BR':
            evidence_text = f"\n\nEsta classificação é baseada em {evidence_count} critério(s) ACMG."
        else:
            evidence_text = f"\n\nThis classification is based on {evidence_count} ACMG criteria."
        
        return base_interpretation + evidence_text
        
    except Exception as e:
        logger.error(f"Error generating clinical interpretation: {e}")
        if language == 'pt-BR':
            return f"Erro na geração da interpretação clínica para a variante {rsid}."
        else:
            return f"Error generating clinical interpretation for variant {rsid}." 