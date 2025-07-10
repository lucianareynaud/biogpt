"""
Chat router for RAG-based genomic analysis conversations.
"""

import uuid
import httpx
from typing import Optional, List
from fastapi import APIRouter, HTTPException
import logging

from app.models.schemas import ChatRequest, ChatResponse, ChatSession, ChatMessage, MessageType
from app.services.rag_engine import query_knowledge_base, get_relevant_context
from app.dependencies import get_database, get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_analysis(request: ChatRequest):
    """
    Chat about genomic analysis results using RAG.
    
    Parameters
    ----------
    request : ChatRequest
        Chat request with message and context.
        
    Returns
    -------
    ChatResponse
        AI response with sources and suggestions.
    """
    try:
        upload_id = request.upload_id
        user_message = request.message
        session_id = request.session_id
        
        # Verify upload exists
        db = get_database()
        upload_result = db.execute("""
            SELECT filename, processing_status
            FROM user_uploads 
            WHERE upload_id = ?
        """, [upload_id]).fetchone()
        
        if not upload_result:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        filename, processing_status = upload_result
        
        if processing_status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Analysis not completed. Status: {processing_status}"
            )
        
        # Create or get existing chat session
        if not session_id:
            session_id = str(uuid.uuid4())
            
            # Create new chat session
            db.execute("""
                INSERT INTO chat_sessions (session_id, upload_id)
                VALUES (?, ?)
            """, [session_id, upload_id])
        else:
            # Verify session exists and belongs to upload
            session_result = db.execute("""
                SELECT upload_id FROM chat_sessions 
                WHERE session_id = ?
            """, [session_id]).fetchone()
            
            if not session_result:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            if session_result[0] != upload_id:
                raise HTTPException(status_code=400, detail="Session does not belong to this upload")
        
        # Store user message
        user_message_id = str(uuid.uuid4())
        db.execute("""
            INSERT INTO chat_messages (
                message_id, session_id, message_type, content
            ) VALUES (?, ?, ?, ?)
        """, [user_message_id, session_id, MessageType.USER.value, user_message])
        
        # Get analysis context for RAG
        analysis_context = get_analysis_context(upload_id, db)
        
        # Query knowledge base using RAG
        rag_results = await query_knowledge_base(user_message, analysis_context)
        
        # Generate response using LLM service
        llm_response = await generate_llm_response(
            user_message, 
            rag_results['context'],
            analysis_context
        )
        
        # Store assistant response
        assistant_message_id = str(uuid.uuid4())
        sources = rag_results.get('sources', [])
        
        db.execute("""
            INSERT INTO chat_messages (
                message_id, session_id, message_type, content, sources
            ) VALUES (?, ?, ?, ?, ?)
        """, [
            assistant_message_id, session_id, MessageType.ASSISTANT.value, 
            llm_response, sources
        ])
        
        # Generate suggested follow-up questions
        suggested_questions = generate_suggested_questions(user_message, analysis_context)
        
        logger.info(f"Chat response generated for session {session_id}")
        
        return ChatResponse(
            session_id=session_id,
            message_id=assistant_message_id,
            content=llm_response,
            sources=sources,
            suggested_questions=suggested_questions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat processing: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_history(session_id: str):
    """
    Get chat history for a session.
    
    Parameters
    ----------
    session_id : str
        Chat session ID.
        
    Returns
    -------
    dict
        Chat history.
    """
    try:
        db = get_database()
        
        # Verify session exists
        session_result = db.execute("""
            SELECT upload_id, created_at
            FROM chat_sessions 
            WHERE session_id = ?
        """, [session_id]).fetchone()
        
        if not session_result:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        upload_id, created_at = session_result
        
        # Get messages
        messages_result = db.execute("""
            SELECT 
                message_id, message_type, content, sources, timestamp
            FROM chat_messages 
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, [session_id]).fetchall()
        
        messages = []
        for msg in messages_result:
            message = {
                'message_id': msg[0],
                'message_type': msg[1],
                'content': msg[2],
                'sources': msg[3] if msg[3] else [],
                'timestamp': msg[4]
            }
            messages.append(message)
        
        return {
            'session_id': session_id,
            'upload_id': upload_id,
            'created_at': created_at,
            'messages': messages,
            'message_count': len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@router.get("/chat/sessions")
async def list_chat_sessions(upload_id: Optional[str] = None):
    """
    List chat sessions, optionally filtered by upload ID.
    
    Parameters
    ----------
    upload_id : str, optional
        Filter by upload ID.
        
    Returns
    -------
    dict
        List of chat sessions.
    """
    try:
        db = get_database()
        
        if upload_id:
            query = """
                SELECT cs.session_id, cs.upload_id, cs.created_at,
                       COUNT(cm.message_id) as message_count
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
                WHERE cs.upload_id = ?
                GROUP BY cs.session_id, cs.upload_id, cs.created_at
                ORDER BY cs.created_at DESC
            """
            results = db.execute(query, [upload_id]).fetchall()
        else:
            query = """
                SELECT cs.session_id, cs.upload_id, cs.created_at,
                       COUNT(cm.message_id) as message_count
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
                GROUP BY cs.session_id, cs.upload_id, cs.created_at
                ORDER BY cs.created_at DESC
                LIMIT 50
            """
            results = db.execute(query).fetchall()
        
        sessions = []
        for result in results:
            session = {
                'session_id': result[0],
                'upload_id': result[1],
                'created_at': result[2],
                'message_count': result[3]
            }
            sessions.append(session)
        
        return {
            'sessions': sessions,
            'total': len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list chat sessions")

def get_analysis_context(upload_id: str, db) -> dict:
    """
    Get analysis context for RAG.
    
    Parameters
    ----------
    upload_id : str
        Upload ID.
    db : connection
        Database connection.
        
    Returns
    -------
    dict
        Analysis context.
    """
    try:
        # Get upload info
        upload_info = db.execute("""
            SELECT filename, upload_timestamp
            FROM user_uploads 
            WHERE upload_id = ?
        """, [upload_id]).fetchone()
        
        # Get analysis summary
        analysis_results = db.execute("""
            SELECT 
                classification, COUNT(*) as count
            FROM variant_analyses 
            WHERE upload_id = ?
            GROUP BY classification
        """, [upload_id]).fetchall()
        
        summary = {result[0]: result[1] for result in analysis_results}
        
        # Get significant variants
        significant_variants = db.execute("""
            SELECT 
                rsID, chromosome, position, genotype, classification,
                confidence_score, clinical_interpretation
            FROM variant_analyses 
            WHERE upload_id = ? 
            AND classification IN ('Patogênica', 'Provavelmente Patogênica', 'VUS')
            ORDER BY 
                CASE classification
                    WHEN 'Patogênica' THEN 1
                    WHEN 'Provavelmente Patogênica' THEN 2
                    WHEN 'VUS' THEN 3
                    ELSE 4
                END,
                confidence_score DESC
            LIMIT 20
        """, [upload_id]).fetchall()
        
        variants = []
        for variant in significant_variants:
            variant_data = {
                'rsID': variant[0],
                'chromosome': variant[1],
                'position': variant[2],
                'genotype': variant[3],
                'classification': variant[4],
                'confidence_score': variant[5],
                'clinical_interpretation': variant[6]
            }
            variants.append(variant_data)
        
        context = {
            'upload_id': upload_id,
            'filename': upload_info[0] if upload_info else 'unknown',
            'upload_timestamp': upload_info[1] if upload_info else None,
            'summary': summary,
            'significant_variants': variants,
            'total_variants': sum(summary.values())
        }
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting analysis context: {e}")
        return {}

async def generate_llm_response(user_message: str, context: str, analysis_context: dict) -> str:
    """
    Generate response using LLM service.
    
    Parameters
    ----------
    user_message : str
        User's message.
    context : str
        RAG context.
    analysis_context : dict
        Analysis context.
        
    Returns
    -------
    str
        Generated response.
    """
    try:
        # Build prompt for PubMedBERT
        prompt = build_chat_prompt(user_message, context, analysis_context)
        
        # Call LLM service
        llm_service_url = "http://llm:8001"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{llm_service_url}/generate",
                json={
                    "prompt": prompt,
                    "max_length": 512,
                    "temperature": 0.3
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"LLM service error: {response.status_code}")
                return "Desculpe, não foi possível gerar uma resposta no momento. Tente novamente."
            
            result = response.json()
            return result.get("generated_text", "Erro na geração da resposta.")
        
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente."

def build_chat_prompt(user_message: str, context: str, analysis_context: dict) -> str:
    """
    Build prompt for genomic chat.
    
    Parameters
    ----------
    user_message : str
        User's message.
    context : str
        RAG context.
    analysis_context : dict
        Analysis context.
        
    Returns
    -------
    str
        Formatted prompt.
    """
    summary = analysis_context.get('summary', {})
    filename = analysis_context.get('filename', 'arquivo genômico')
    
    prompt = f"""
Você é um assistente especializado em genética médica. Responda à pergunta do usuário com base na análise genômica realizada e no contexto científico fornecido.

ANÁLISE REALIZADA:
- Arquivo: {filename}
- Total de variantes: {analysis_context.get('total_variants', 0)}
- Variantes patogênicas: {summary.get('Patogênica', 0)}
- Variantes provavelmente patogênicas: {summary.get('Provavelmente Patogênica', 0)}
- Variantes VUS: {summary.get('VUS', 0)}

CONTEXTO CIENTÍFICO:
{context}

PERGUNTA DO USUÁRIO:
{user_message}

INSTRUÇÕES:
1. Responda de forma clara e acessível
2. Use terminologia médica quando apropriado, mas explique conceitos complexos
3. Cite evidências científicas quando relevante
4. Sempre mencione que interpretações devem ser validadas por profissional médico
5. Seja objetivo e preciso

RESPOSTA:
"""
    
    return prompt

def generate_suggested_questions(user_message: str, analysis_context: dict) -> List[str]:
    """
    Generate suggested follow-up questions.
    
    Parameters
    ----------
    user_message : str
        User's message.
    analysis_context : dict
        Analysis context.
        
    Returns
    -------
    list
        Suggested questions.
    """
    summary = analysis_context.get('summary', {})
    
    suggestions = []
    
    # Context-aware suggestions
    if summary.get('Patogênica', 0) > 0 or summary.get('Provavelmente Patogênica', 0) > 0:
        suggestions.extend([
            "Quais são as implicações clínicas das variantes patogênicas encontradas?",
            "Que exames complementares são recomendados?",
            "Como essas variantes podem afetar minha saúde?"
        ])
    
    if summary.get('VUS', 0) > 0:
        suggestions.extend([
            "O que significam as variantes de significado incerto (VUS)?",
            "As variantes VUS podem se tornar significativas no futuro?"
        ])
    
    # General suggestions
    suggestions.extend([
        "Como interpretar os resultados desta análise?",
        "Quais são as limitações desta análise genética?",
        "Devo compartilhar esses resultados com minha família?",
        "Com que frequência devo reavaliar estes resultados?"
    ])
    
    # Return first 3-4 relevant suggestions
    return suggestions[:4] 