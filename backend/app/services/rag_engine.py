"""
RAG (Retrieval-Augmented Generation) engine for genomic knowledge.
"""

import httpx
from typing import Dict, Any, List, Optional
import logging
from app.dependencies import get_vector_store
from app.services.clinvar_lookup import get_pathogenic_variants

logger = logging.getLogger(__name__)

async def query_knowledge_base(user_query: str, analysis_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query the knowledge base using RAG for genomic information.
    
    Parameters
    ----------
    user_query : str
        User's question.
    analysis_context : dict
        Analysis context with variants and summary.
        
    Returns
    -------
    dict
        RAG results with context and sources.
    """
    try:
        # Get relevant context from multiple sources
        contexts = []
        sources = []
        
        # 1. Get context from user's analysis results
        analysis_context_text = build_analysis_context(analysis_context)
        if analysis_context_text:
            contexts.append(analysis_context_text)
            sources.append("Resultados da sua análise genômica")
        
        # 2. Search vector database for relevant genomic knowledge
        vector_context = await search_vector_database(user_query)
        if vector_context:
            contexts.extend(vector_context['contexts'])
            sources.extend(vector_context['sources'])
        
        # 3. Get relevant ClinVar information
        clinvar_context = get_clinvar_context(user_query, analysis_context)
        if clinvar_context:
            contexts.append(clinvar_context)
            sources.append("Base de dados ClinVar")
        
        # Combine all contexts
        combined_context = "\n\n".join(contexts[:5])  # Limit to avoid token overflow
        
        return {
            'context': combined_context,
            'sources': sources[:5],
            'query': user_query
        }
        
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        return {
            'context': "Contexto limitado disponível devido a erro técnico.",
            'sources': [],
            'query': user_query
        }

async def search_vector_database(query: str) -> Optional[Dict[str, Any]]:
    """
    Search the vector database for relevant documents.
    
    Parameters
    ----------
    query : str
        Search query.
        
    Returns
    -------
    dict or None
        Search results with contexts and sources.
    """
    try:
        # Get embeddings for the query
        embeddings = await get_query_embeddings(query)
        if not embeddings:
            return None
        
        # Search vector database
        vector_store = get_vector_store()
        
        # Try to get or create collection
        try:
            collection = vector_store.get_collection("genomic_knowledge")
        except Exception:
            # Collection doesn't exist yet
            logger.info("Genomic knowledge collection not found, creating empty response")
            return None
        
        # Query the collection
        results = collection.query(
            query_embeddings=[embeddings],
            n_results=5,
            include=['documents', 'metadatas']
        )
        
        if not results['documents'] or not results['documents'][0]:
            return None
        
        contexts = []
        sources = []
        
        for i, doc in enumerate(results['documents'][0]):
            contexts.append(doc)
            
            # Get source from metadata if available
            if results['metadatas'] and results['metadatas'][0] and i < len(results['metadatas'][0]):
                metadata = results['metadatas'][0][i]
                source = metadata.get('source', 'Conhecimento genômico')
            else:
                source = 'Conhecimento genômico'
            
            sources.append(source)
        
        return {
            'contexts': contexts,
            'sources': sources
        }
        
    except Exception as e:
        logger.error(f"Error searching vector database: {e}")
        return None

async def get_query_embeddings(query: str) -> Optional[List[float]]:
    """
    Get embeddings for a query using the LLM service.
    
    Parameters
    ----------
    query : str
        Query text.
        
    Returns
    -------
    list or None
        Query embeddings.
    """
    try:
        llm_service_url = "http://llm:8001"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{llm_service_url}/embeddings",
                json={"texts": [query]},
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Embeddings service error: {response.status_code}")
                return None
            
            result = response.json()
            embeddings = result.get("embeddings", [])
            
            if embeddings:
                return embeddings[0]
            
            return None
        
    except Exception as e:
        logger.error(f"Error getting query embeddings: {e}")
        return None

def build_analysis_context(analysis_context: Dict[str, Any]) -> str:
    """
    Build context text from analysis results.
    
    Parameters
    ----------
    analysis_context : dict
        Analysis context.
        
    Returns
    -------
    str
        Formatted context text.
    """
    try:
        filename = analysis_context.get('filename', 'arquivo')
        summary = analysis_context.get('summary', {})
        significant_variants = analysis_context.get('significant_variants', [])
        
        context_parts = []
        
        # Summary information
        context_parts.append(f"Análise do arquivo {filename}:")
        context_parts.append(f"- Total de variantes analisadas: {analysis_context.get('total_variants', 0)}")
        
        for classification, count in summary.items():
            context_parts.append(f"- {classification}: {count} variantes")
        
        # Significant variants details
        if significant_variants:
            context_parts.append("\nVariantes de interesse clínico identificadas:")
            
            for variant in significant_variants[:5]:  # Limit to first 5
                rsid = variant.get('rsID', 'desconhecido')
                classification = variant.get('classification', 'desconhecida')
                genotype = variant.get('genotype', 'desconhecido')
                interpretation = variant.get('clinical_interpretation', '')
                
                variant_text = f"- {rsid} (genótipo {genotype}): classificada como {classification}"
                if interpretation:
                    # Truncate interpretation to avoid too much text
                    short_interpretation = interpretation[:200] + "..." if len(interpretation) > 200 else interpretation
                    variant_text += f". {short_interpretation}"
                
                context_parts.append(variant_text)
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error building analysis context: {e}")
        return "Contexto da análise não disponível."

def get_clinvar_context(query: str, analysis_context: Dict[str, Any]) -> Optional[str]:
    """
    Get relevant ClinVar context based on query and analysis.
    
    Parameters
    ----------
    query : str
        User's query.
    analysis_context : dict
        Analysis context.
        
    Returns
    -------
    str or None
        ClinVar context.
    """
    try:
        # Extract relevant RSIDs from user's analysis
        significant_variants = analysis_context.get('significant_variants', [])
        
        if not significant_variants:
            # If no significant variants, get general pathogenic variants
            pathogenic_variants = get_pathogenic_variants(limit=10)
            
            if pathogenic_variants:
                context_parts = ["Exemplos de variantes patogênicas conhecidas no ClinVar:"]
                
                for variant in pathogenic_variants[:5]:
                    rsid = variant.get('rsID', 'desconhecido')
                    gene = variant.get('gene_symbol', 'gene desconhecido')
                    significance = variant.get('clinical_significance', 'significado desconhecido')
                    phenotype = variant.get('phenotype', 'fenótipo não especificado')
                    
                    context_parts.append(
                        f"- {rsid} no gene {gene}: {significance}. Associado a {phenotype}"
                    )
                
                return "\n".join(context_parts)
        else:
            # Use variants from user's analysis
            context_parts = ["Informações ClinVar sobre suas variantes:"]
            
            for variant in significant_variants[:3]:
                rsid = variant.get('rsID', '')
                classification = variant.get('classification', '')
                
                if rsid and classification in ['Patogênica', 'Provavelmente Patogênica']:
                    context_parts.append(
                        f"- {rsid}: classificada como {classification} com base em evidências do ClinVar"
                    )
            
            if len(context_parts) > 1:
                return "\n".join(context_parts)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting ClinVar context: {e}")
        return None

async def add_document_to_knowledge_base(
    document: str, 
    metadata: Dict[str, Any], 
    collection_name: str = "genomic_knowledge"
) -> bool:
    """
    Add a document to the vector knowledge base.
    
    Parameters
    ----------
    document : str
        Document text.
    metadata : dict
        Document metadata.
    collection_name : str
        Collection name.
        
    Returns
    -------
    bool
        Success status.
    """
    try:
        # Get embeddings for the document
        embeddings = await get_query_embeddings(document)
        if not embeddings:
            return False
        
        # Get or create collection
        vector_store = get_vector_store()
        
        try:
            collection = vector_store.get_collection(collection_name)
        except Exception:
            # Create collection if it doesn't exist
            collection = vector_store.create_collection(
                name=collection_name,
                metadata={"description": "Genomic knowledge base for RAG"}
            )
        
        # Generate unique ID
        import uuid
        doc_id = str(uuid.uuid4())
        
        # Add document
        collection.add(
            documents=[document],
            embeddings=[embeddings],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        logger.info(f"Added document to knowledge base: {doc_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding document to knowledge base: {e}")
        return False

async def populate_knowledge_base_with_clinvar():
    """
    Populate the knowledge base with ClinVar information.
    """
    try:
        logger.info("Populating knowledge base with ClinVar data...")
        
        # Get pathogenic variants
        pathogenic_variants = get_pathogenic_variants(limit=100)
        
        added_count = 0
        for variant in pathogenic_variants:
            try:
                # Create document text
                rsid = variant.get('rsID', '')
                gene = variant.get('gene_symbol', '')
                significance = variant.get('clinical_significance', '')
                phenotype = variant.get('phenotype', '')
                consequence = variant.get('molecular_consequence', '')
                
                document = f"""
                Variante genética {rsid} no gene {gene}.
                Significado clínico: {significance}.
                Fenótipo associado: {phenotype}.
                Consequência molecular: {consequence}.
                Fonte: ClinVar
                """
                
                metadata = {
                    'source': 'ClinVar',
                    'rsID': rsid,
                    'gene': gene,
                    'significance': significance,
                    'type': 'variant_annotation'
                }
                
                success = await add_document_to_knowledge_base(document, metadata)
                if success:
                    added_count += 1
                
            except Exception as e:
                logger.warning(f"Error adding variant {variant.get('rsID', 'unknown')}: {e}")
                continue
        
        logger.info(f"Added {added_count} ClinVar documents to knowledge base")
        return added_count
        
    except Exception as e:
        logger.error(f"Error populating knowledge base: {e}")
        return 0

def get_relevant_context(query: str, context_type: str = "general") -> str:
    """
    Get relevant context for specific types of queries.
    
    Parameters
    ----------
    query : str
        User query.
    context_type : str
        Type of context needed.
        
    Returns
    -------
    str
        Relevant context.
    """
    try:
        query_lower = query.lower()
        
        # ACMG guidelines context
        if any(term in query_lower for term in ['acmg', 'classificação', 'critérios', 'guidelines']):
            return """
            As diretrizes ACMG-2015 (American College of Medical Genetics) estabelecem critérios padronizados 
            para classificação de variantes genéticas em cinco categorias:
            1. Patogênica: Variante que causa doença
            2. Provavelmente Patogênica: Evidência forte de patogenicidade
            3. VUS (Variante de Significado Incerto): Evidência insuficiente
            4. Provavelmente Benigna: Evidência de que não causa doença
            5. Benigna: Variante normal na população
            
            Os critérios incluem evidência populacional, computacional, funcional e segregação familiar.
            """
        
        # 23andMe limitations context
        if any(term in query_lower for term in ['23andme', 'limitações', 'limitations']):
            return """
            Limitações dos dados 23andMe:
            - Cobertura limitada do genoma (aproximadamente 600.000 variantes)
            - Foco em SNPs comuns, não incluindo indels ou variantes estruturais
            - Não substitui sequenciamento clínico completo
            - Dados podem ter taxa de erro de genotipagem
            - Interpretação requer validação clínica
            """
        
        # General genomics context
        return """
        A análise genômica moderna utiliza bancos de dados como ClinVar e gnomAD para interpretar variantes.
        ClinVar fornece classificações clínicas de variantes, enquanto gnomAD oferece frequências populacionais.
        A interpretação deve sempre considerar o contexto clínico e histórico familiar.
        """
        
    except Exception as e:
        logger.error(f"Error getting relevant context: {e}")
        return "Contexto genômico geral não disponível." 