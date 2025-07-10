"""
Report generator service for creating PDF reports from analysis results.
"""

import os
from typing import Dict, Any
from datetime import datetime
import logging
from jinja2 import Template
import markdown
from weasyprint import HTML, CSS
from io import StringIO

logger = logging.getLogger(__name__)

def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """
    Generate markdown content for genomic analysis report.
    
    Parameters
    ----------
    report_data : dict
        Report data including variants and summary.
        
    Returns
    -------
    str
        Markdown content.
    """
    try:
        language = report_data.get('language', 'pt-BR')
        
        if language == 'pt-BR':
            template = get_portuguese_template()
        else:
            template = get_english_template()
        
        jinja_template = Template(template)
        markdown_content = jinja_template.render(**report_data)
        
        return markdown_content
        
    except Exception as e:
        logger.error(f"Error generating markdown report: {e}")
        raise e

def generate_pdf_report(markdown_content: str, output_path: str, language: str = 'pt-BR') -> bool:
    """
    Generate PDF report from markdown content.
    
    Parameters
    ----------
    markdown_content : str
        Markdown content to convert.
    output_path : str
        Path to save PDF file.
    language : str
        Report language for styling.
        
    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'codehilite', 'toc']
        )
        
        # Wrap in HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Relatório de Análise Genômica</title>
            <style>
                {get_pdf_css()}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF
        HTML(string=full_html).write_pdf(output_path)
        
        logger.info(f"PDF report generated: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        return False

def get_portuguese_template() -> str:
    """Get Portuguese report template."""
    return """
# Relatório de Análise Genômica

**Data de Geração:** {{ datetime.now().strftime('%d/%m/%Y %H:%M') }}  
**Arquivo Analisado:** {{ filename }}  
**ID da Análise:** {{ upload_id }}  

---

## Resumo Executivo

Esta análise genômica foi realizada sobre o arquivo **{{ filename }}** utilizando dados do 23andMe. O relatório apresenta a classificação de {{ summary.total_variants }} variantes genéticas de acordo com as diretrizes ACMG-2015 simplificadas.

### Estatísticas Gerais

| Classificação | Quantidade | Percentual |
|--------------|------------|-------------|
| **Patogênica** | {{ summary.pathogenic }} | {{ "%.1f"|format((summary.pathogenic / summary.total_variants) * 100) }}% |
| **Provavelmente Patogênica** | {{ summary.likely_pathogenic }} | {{ "%.1f"|format((summary.likely_pathogenic / summary.total_variants) * 100) }}% |
| **VUS (Significado Incerto)** | {{ summary.vus }} | {{ "%.1f"|format((summary.vus / summary.total_variants) * 100) }}% |
| **Provavelmente Benigna** | {{ summary.likely_benign }} | {{ "%.1f"|format((summary.likely_benign / summary.total_variants) * 100) }}% |
| **Benigna** | {{ summary.benign }} | {{ "%.1f"|format((summary.benign / summary.total_variants) * 100) }}% |

---

## Variantes de Significado Clínico

{% set significant_variants = variants | selectattr("classification", "in", ["Patogênica", "Provavelmente Patogênica"]) | list %}

{% if significant_variants %}
### Variantes Patogênicas e Provavelmente Patogênicas

{% for variant in significant_variants[:10] %}
#### {{ variant.rsID }} - {{ variant.classification }}

**Localização:** Cromossomo {{ variant.chromosome }}, posição {{ variant.position }}  
**Genótipo:** {{ variant.genotype }}  
**Nível de Confiança:** {{ "%.1f"|format(variant.confidence_score * 100) }}%

{{ variant.clinical_interpretation }}

---
{% endfor %}

{% if significant_variants|length > 10 %}
*Nota: Este relatório mostra as primeiras 10 variantes significativas. O total de variantes patogênicas/provavelmente patogênicas é {{ significant_variants|length }}.*
{% endif %}

{% else %}
### Nenhuma Variante Patogênica Identificada

Não foram identificadas variantes classificadas como patogênicas ou provavelmente patogênicas nesta análise.

{% endif %}

---

## Variantes de Significado Incerto (VUS)

{% set vus_variants = variants | selectattr("classification", "equalto", "VUS") | list %}

{% if vus_variants %}
Foram identificadas {{ vus_variants|length }} variantes de significado incerto (VUS). Estas variantes requerem mais evidências científicas para determinação de seu impacto clínico.

### Primeiras 5 Variantes VUS

{% for variant in vus_variants[:5] %}
- **{{ variant.rsID }}** (Chr{{ variant.chromosome }}:{{ variant.position }}) - Genótipo: {{ variant.genotype }}
{% endfor %}

{% if vus_variants|length > 5 %}
*E mais {{ vus_variants|length - 5 }} variantes VUS...*
{% endif %}

{% endif %}

---

## Metodologia

### Dados Utilizados
- **Fonte dos Dados:** Arquivo 23andMe (.txt)
- **Banco de Dados de Referência:** ClinVar, gnomAD
- **Diretrizes de Classificação:** ACMG-2015 (versão simplificada)
- **Modelo de IA:** PubMedBERT para interpretação clínica

### Limitações
1. Esta análise utiliza uma versão simplificada das diretrizes ACMG-2015
2. Os dados do 23andMe possuem limitações em comparação com sequenciamento clínico
3. Interpretações clínicas são geradas por IA e devem ser validadas por profissional habilitado
4. Variantes raras podem não ter dados suficientes para classificação definitiva

---

## Recomendações

{% if summary.pathogenic > 0 or summary.likely_pathogenic > 0 %}
⚠️ **IMPORTANTE:** Foram identificadas variantes potencialmente significativas. Recomenda-se:

1. Consulta com médico geneticista
2. Validação por sequenciamento clínico
3. Aconselhamento genético familiar
4. Acompanhamento médico especializado
{% else %}
✅ **Resultado Favorável:** Não foram identificadas variantes patogênicas conhecidas. 

**Recomendações:**
1. Manter acompanhamento médico de rotina
2. Reavaliar periodicamente conforme novas evidências científicas
3. Considerar histórico familiar para decisões clínicas
{% endif %}

---

## Considerações Importantes

Este relatório é baseado em análise computacional de dados genéticos e **NÃO substitui consulta médica especializada**. As interpretações apresentadas devem ser validadas por profissional habilitado antes de qualquer decisão clínica.

Para mais informações ou dúvidas sobre este relatório, utilize o sistema de chat disponível na plataforma.

---

*Relatório gerado pelo sistema Genomic-LLM v1.0 em {{ datetime.now().strftime('%d/%m/%Y às %H:%M') }}*
"""

def get_english_template() -> str:
    """Get English report template."""
    return """
# Genomic Analysis Report

**Generation Date:** {{ datetime.now().strftime('%m/%d/%Y %H:%M') }}  
**Analyzed File:** {{ filename }}  
**Analysis ID:** {{ upload_id }}  

---

## Executive Summary

This genomic analysis was performed on the file **{{ filename }}** using 23andMe data. The report presents the classification of {{ summary.total_variants }} genetic variants according to simplified ACMG-2015 guidelines.

### General Statistics

| Classification | Count | Percentage |
|---------------|-------|------------|
| **Pathogenic** | {{ summary.pathogenic }} | {{ "%.1f"|format((summary.pathogenic / summary.total_variants) * 100) }}% |
| **Likely Pathogenic** | {{ summary.likely_pathogenic }} | {{ "%.1f"|format((summary.likely_pathogenic / summary.total_variants) * 100) }}% |
| **VUS (Uncertain Significance)** | {{ summary.vus }} | {{ "%.1f"|format((summary.vus / summary.total_variants) * 100) }}% |
| **Likely Benign** | {{ summary.likely_benign }} | {{ "%.1f"|format((summary.likely_benign / summary.total_variants) * 100) }}% |
| **Benign** | {{ summary.benign }} | {{ "%.1f"|format((summary.benign / summary.total_variants) * 100) }}% |

---

## Clinically Significant Variants

{% set significant_variants = variants | selectattr("classification", "in", ["Pathogenic", "Likely Pathogenic", "Patogênica", "Provavelmente Patogênica"]) | list %}

{% if significant_variants %}
### Pathogenic and Likely Pathogenic Variants

{% for variant in significant_variants[:10] %}
#### {{ variant.rsID }} - {{ variant.classification }}

**Location:** Chromosome {{ variant.chromosome }}, position {{ variant.position }}  
**Genotype:** {{ variant.genotype }}  
**Confidence Level:** {{ "%.1f"|format(variant.confidence_score * 100) }}%

{{ variant.clinical_interpretation }}

---
{% endfor %}

{% if significant_variants|length > 10 %}
*Note: This report shows the first 10 significant variants. Total pathogenic/likely pathogenic variants: {{ significant_variants|length }}.*
{% endif %}

{% else %}
### No Pathogenic Variants Identified

No variants classified as pathogenic or likely pathogenic were identified in this analysis.

{% endif %}

---

## Variants of Uncertain Significance (VUS)

{% set vus_variants = variants | selectattr("classification", "equalto", "VUS") | list %}

{% if vus_variants %}
{{ vus_variants|length }} variants of uncertain significance (VUS) were identified. These variants require more scientific evidence to determine their clinical impact.

### First 5 VUS Variants

{% for variant in vus_variants[:5] %}
- **{{ variant.rsID }}** (Chr{{ variant.chromosome }}:{{ variant.position }}) - Genotype: {{ variant.genotype }}
{% endfor %}

{% if vus_variants|length > 5 %}
*And {{ vus_variants|length - 5 }} more VUS variants...*
{% endif %}

{% endif %}

---

## Methodology

### Data Sources
- **Data Source:** 23andMe file (.txt)
- **Reference Databases:** ClinVar, gnomAD
- **Classification Guidelines:** ACMG-2015 (simplified version)
- **AI Model:** PubMedBERT for clinical interpretation

### Limitations
1. This analysis uses a simplified version of ACMG-2015 guidelines
2. 23andMe data has limitations compared to clinical sequencing
3. Clinical interpretations are AI-generated and should be validated by qualified professionals
4. Rare variants may lack sufficient data for definitive classification

---

## Recommendations

{% if summary.pathogenic > 0 or summary.likely_pathogenic > 0 %}
⚠️ **IMPORTANT:** Potentially significant variants were identified. Recommendations:

1. Consultation with medical geneticist
2. Validation through clinical sequencing
3. Family genetic counseling
4. Specialized medical follow-up
{% else %}
✅ **Favorable Result:** No known pathogenic variants were identified.

**Recommendations:**
1. Maintain routine medical follow-up
2. Periodic reassessment as new scientific evidence emerges
3. Consider family history for clinical decisions
{% endif %}

---

## Important Considerations

This report is based on computational analysis of genetic data and **DOES NOT replace specialized medical consultation**. The interpretations presented should be validated by qualified professionals before any clinical decision.

For more information or questions about this report, use the chat system available on the platform.

---

*Report generated by Genomic-LLM system v1.0 on {{ datetime.now().strftime('%m/%d/%Y at %H:%M') }}*
"""

def get_pdf_css() -> str:
    """Get CSS styling for PDF generation."""
    return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-right {
                content: "Página " counter(page) " de " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }
        
        body {
            font-family: 'Arial', 'Helvetica', sans-serif;
            font-size: 11px;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
        }
        
        h1 {
            font-size: 24px;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        h2 {
            font-size: 18px;
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        
        h3 {
            font-size: 14px;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        h4 {
            font-size: 12px;
            color: #e74c3c;
            margin-top: 15px;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        p {
            margin-bottom: 10px;
            text-align: justify;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10px;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .info {
            background-color: #e3f2fd;
            border: 1px solid #bbdefb;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        
        ul, ol {
            margin-left: 20px;
            margin-bottom: 15px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        strong {
            color: #2c3e50;
        }
        
        em {
            color: #7f8c8d;
            font-style: italic;
        }
        
        hr {
            border: none;
            height: 1px;
            background-color: #ecf0f1;
            margin: 25px 0;
        }
        
        .page-break {
            page-break-before: always;
        }
        
        .no-break {
            page-break-inside: avoid;
        }
    """ 