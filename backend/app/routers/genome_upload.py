"""
Genome upload router for handling 23andMe file uploads and processing.
"""

import os
import uuid
import shutil
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import logging

from app.models.schemas import (
    UploadResponse, UploadStatus, VariantAnalysisResponse, 
    ProcessingStatus, VariantAnalysis, ClinVarVariant, GnomADFrequency
)
from app.services.format_detector import validate_genomic_file
from app.services.variant_parser import parse_23andme_txt, convert_to_standard_format
from app.services.acmg_classifier import classify_variant, get_acmg_criteria_details, generate_clinical_interpretation
from app.services.clinvar_lookup import batch_lookup_clinvar_variants, batch_lookup_gnomad_frequencies
from app.dependencies import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for upload status (in production, use Redis or database)
upload_status_store: Dict[str, Dict[str, Any]] = {}

@router.post("/genome-upload", response_model=UploadResponse)
async def upload_genome_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and process a 23andMe genome file.
    
    Parameters
    ----------
    file : UploadFile
        Uploaded genome file.
        
    Returns
    -------
    UploadResponse
        Upload confirmation with processing information.
    """
    try:
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not file.filename.lower().endswith('.txt'):
            raise HTTPException(
                status_code=400, 
                detail="Only .txt files are supported (23andMe format)"
            )
        
        # Create upload directory
        upload_dir = os.getenv("UPLOADS_DIR", "/app/uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(upload_dir, f"{upload_id}_{file.filename}")
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
        
        file_size = os.path.getsize(file_path)
        
        # Validate file format
        validation_result = validate_genomic_file(file_path)
        if not validation_result['valid']:
            # Clean up invalid file
            os.remove(file_path)
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file format: {validation_result['error']}"
            )
        
        # Store upload information in database
        db = get_database()
        db.execute("""
            INSERT INTO uploads (id, filename, file_path, file_size, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, [upload_id, file.filename, file_path, file_size, "anonymous"])
        
        # Initialize status tracking
        upload_status_store[upload_id] = {
            'upload_id': upload_id,
            'filename': file.filename,
            'status': ProcessingStatus.PENDING,
            'progress': 0.0,
            'message': 'File uploaded successfully, starting processing...',
            'variants_processed': 0,
            'total_variants': 0,
            'errors': []
        }
        
        # Start background processing
        background_tasks.add_task(process_genome_file, upload_id, file_path)
        
        logger.info(f"File uploaded successfully: {upload_id}")
        
        return UploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            status=ProcessingStatus.PENDING,
            message="File uploaded successfully. Processing started.",
            processing_url=f"/api/v1/genome-upload/{upload_id}/status"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in genome upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/genome-upload/{upload_id}/status", response_model=UploadStatus)
async def get_upload_status(upload_id: str):
    """
    Get the processing status of an uploaded genome file.
    
    Parameters
    ----------
    upload_id : str
        Upload ID to check status for.
        
    Returns
    -------
    UploadStatus
        Current processing status.
    """
    if upload_id not in upload_status_store:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    status = upload_status_store[upload_id]
    return UploadStatus(**status)

@router.get("/genome-upload/{upload_id}/results", response_model=VariantAnalysisResponse)
async def get_analysis_results(upload_id: str):
    """
    Get the analysis results for a processed genome file.
    
    Parameters
    ----------
    upload_id : str
        Upload ID to get results for.
        
    Returns
    -------
    VariantAnalysisResponse
        Analysis results.
    """
    try:
        # Check if upload exists and is completed
        if upload_id not in upload_status_store:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        status = upload_status_store[upload_id]
        if status['status'] != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=202, 
                detail=f"Analysis not completed. Current status: {status['status']}"
            )
        
        # Retrieve analysis results from database
        db = get_database()
        
        # First get the analysis ID for this upload
        analysis_result = db.execute("""
            SELECT id FROM analyses WHERE upload_id = ?
        """, [upload_id]).fetchone()
        
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        analysis_id = analysis_result[0]
        
        results = db.execute("""
            SELECT 
                id, rsid, chromosome, position, genotype,
                acmg_classification, confidence_score, interpretation,
                gnomad_frequency, gene_symbol, clinical_significance
            FROM variant_results 
            WHERE analysis_id = ?
            ORDER BY chromosome, position
        """, [analysis_id]).fetchall()
        
        if not results:
            raise HTTPException(status_code=404, detail="No analysis results found")
        
        # Convert to VariantAnalysis objects
        analyses = []
        for result in results:
            # Create ClinVar info if available
            clinvar_info = None
            if result[9] and result[10]:  # gene_symbol and clinical_significance
                clinvar_info = ClinVarVariant(
                    rsID=result[1],
                    chromosome=result[2],
                    position=result[3],
                    reference_allele="",  # Not stored in our result
                    alternate_allele="",  # Not stored in our result
                    clinical_significance=result[10],
                    review_status="",  # Not stored in our result
                    gene_symbol=result[9]
                )
            
            # Create gnomAD info if available
            gnomad_info = None
            if result[8] is not None:  # gnomad_frequency
                gnomad_info = GnomADFrequency(
                    rsID=result[1],
                    chromosome=result[2],
                    position=result[3],
                    reference_allele="",  # Not stored in our result
                    alternate_allele="",  # Not stored in our result
                    allele_frequency=result[8],
                    allele_count=0,  # Not stored in our result
                    allele_number=0   # Not stored in our result
                )
            
            analysis = VariantAnalysis(
                analysis_id=result[0],  # This is actually the variant ID
                rsID=result[1],
                chromosome=result[2],
                position=result[3],
                genotype=result[4],
                classification=result[5],
                confidence_score=result[6],
                clinical_interpretation=result[7],
                acmg_criteria=[],  # Not stored yet
                clinvar_info=clinvar_info,
                gnomad_info=gnomad_info
            )
            analyses.append(analysis)
        
        # Generate summary
        total_variants = len(analyses)
        summary = {
            'total': total_variants,
            'pathogenic': sum(1 for a in analyses if 'Patogênica' in a.classification),
            'likely_pathogenic': sum(1 for a in analyses if 'Provavelmente Patogênica' in a.classification),
            'vus': sum(1 for a in analyses if a.classification == 'VUS'),
            'likely_benign': sum(1 for a in analyses if 'Provavelmente Benigna' in a.classification),
            'benign': sum(1 for a in analyses if 'Benigna' in a.classification and 'Provavelmente' not in a.classification)
        }
        
        return VariantAnalysisResponse(
            upload_id=upload_id,
            total_variants=total_variants,
            analyzed_variants=total_variants,
            analyses=analyses,
            processing_time=status.get('processing_time', 0.0),
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis results: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve results")

async def process_genome_file(upload_id: str, file_path: str):
    """
    Background task to process uploaded genome file.
    
    Parameters
    ----------
    upload_id : str
        Upload ID.
    file_path : str
        Path to uploaded file.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting processing for upload {upload_id}")
        
        # Update status to processing
        upload_status_store[upload_id].update({
            'status': ProcessingStatus.PROCESSING,
            'message': 'Parsing genome file...',
            'progress': 10.0
        })
        
        # Parse the 23andMe file
        try:
            variants = parse_23andme_txt(file_path)
            standardized_variants = convert_to_standard_format(variants)
        except Exception as e:
            logger.error(f"Error parsing genome file: {e}")
            upload_status_store[upload_id].update({
                'status': ProcessingStatus.FAILED,
                'message': f'Failed to parse genome file: {str(e)}',
                'errors': [str(e)]
            })
            return
        
        total_variants = len(standardized_variants)
        upload_status_store[upload_id].update({
            'total_variants': total_variants,
            'message': f'Found {total_variants} variants. Starting analysis...',
            'progress': 20.0
        })
        
        # Batch lookup ClinVar and gnomAD information
        rsids = [v['rsID'] for v in standardized_variants]
        upload_status_store[upload_id].update({
            'message': 'Looking up ClinVar annotations...',
            'progress': 30.0
        })
        
        clinvar_data = batch_lookup_clinvar_variants(rsids)
        
        upload_status_store[upload_id].update({
            'message': 'Looking up gnomAD frequencies...',
            'progress': 35.0
        })
        
        gnomad_data = batch_lookup_gnomad_frequencies(rsids)
        
        # Create analysis record
        analysis_id = str(uuid.uuid4())
        db = get_database()
        db.execute("""
            INSERT INTO analyses (id, upload_id, total_variants, status)
            VALUES (?, ?, ?, ?)
        """, [analysis_id, upload_id, total_variants, 'processing'])
        
        # Process variants in batches
        batch_size = 100
        processed_count = 0
        
        upload_status_store[upload_id].update({
            'message': 'Classifying variants...',
            'progress': 40.0
        })
        
        for i in range(0, len(standardized_variants), batch_size):
            batch = standardized_variants[i:i + batch_size]
            
            for variant in batch:
                try:
                    rsid = variant['rsID']
                    
                    # Get ClinVar and gnomAD information
                    clinvar_info = clinvar_data.get(rsid)
                    gnomad_info = gnomad_data.get(rsid)
                    gnomad_freq = gnomad_info.get('allele_frequency') if gnomad_info else None
                    
                    # Classify variant
                    classification = classify_variant(variant, clinvar_info, gnomad_freq)
                    
                    # Get detailed ACMG criteria
                    criteria = get_acmg_criteria_details(variant, clinvar_info, gnomad_freq)
                    
                    # Generate clinical interpretation
                    interpretation = generate_clinical_interpretation(
                        classification, criteria, variant, 'pt-BR'
                    )
                    
                    # Calculate confidence score
                    confidence_score = calculate_confidence_score(criteria)
                    
                    # Store variant result
                    variant_id = str(uuid.uuid4())
                    gene_symbol = clinvar_info.get('gene_symbol') if clinvar_info else None
                    clinical_significance = clinvar_info.get('clinical_significance') if clinvar_info else None
                    
                    db.execute("""
                        INSERT INTO variant_results (
                            id, analysis_id, rsid, chromosome, position,
                            genotype, acmg_classification, confidence_score,
                            interpretation, gnomad_frequency, gene_symbol,
                            clinical_significance
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        variant_id, analysis_id, rsid, variant['chromosome'],
                        variant['position'], variant['genotype'], classification,
                        confidence_score, interpretation, gnomad_freq, gene_symbol,
                        clinical_significance
                    ])
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing variant {variant.get('rsID', 'unknown')}: {e}")
                    upload_status_store[upload_id]['errors'].append(f"Variant {variant.get('rsID')}: {str(e)}")
                    continue
            
            # Update progress
            progress = 40.0 + (processed_count / total_variants) * 50.0
            upload_status_store[upload_id].update({
                'variants_processed': processed_count,
                'progress': min(progress, 90.0),
                'message': f'Processed {processed_count}/{total_variants} variants...'
            })
        
        # Update analysis and upload status to completed
        processing_time = (datetime.now() - start_time).total_seconds()
        
        db.execute("""
            UPDATE analyses 
            SET status = ?, completed_at = CURRENT_TIMESTAMP, processed_variants = ?
            WHERE id = ?
        """, ['completed', processed_count, analysis_id])
        
        db.execute("""
            UPDATE uploads 
            SET status = ?
            WHERE id = ?
        """, ['completed', upload_id])
        
        upload_status_store[upload_id].update({
            'status': ProcessingStatus.COMPLETED,
            'progress': 100.0,
            'message': f'Processing completed. Analyzed {processed_count} variants.',
            'processing_time': processing_time
        })
        
        logger.info(f"Processing completed for upload {upload_id} in {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Unexpected error in genome processing: {e}")
        upload_status_store[upload_id].update({
            'status': ProcessingStatus.FAILED,
            'message': f'Processing failed: {str(e)}',
            'errors': [str(e)]
        })
        
        # Update database status
        try:
            db = get_database()
            db.execute("""
                UPDATE uploads 
                SET status = ?
                WHERE id = ?
            """, ['error', upload_id])
        except Exception as db_error:
            logger.error(f"Failed to update database status: {db_error}")

def calculate_confidence_score(criteria: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on ACMG criteria.
    
    Parameters
    ----------
    criteria : dict
        ACMG criteria analysis.
        
    Returns
    -------
    float
        Confidence score between 0.0 and 1.0.
    """
    score = 0.5  # Base score
    
    # Add points for strong evidence
    pathogenic_count = len(criteria.get('pathogenic', []))
    benign_count = len(criteria.get('benign', []))
    supporting_count = len(criteria.get('supporting_evidence', []))
    
    # Strong pathogenic evidence
    score += pathogenic_count * 0.2
    
    # Strong benign evidence  
    score += benign_count * 0.15
    
    # Supporting evidence
    score += supporting_count * 0.1
    
    # Subtract for conflicting evidence
    conflicting_count = len(criteria.get('conflicting_evidence', []))
    score -= conflicting_count * 0.1
    
    return max(0.0, min(1.0, score)) 