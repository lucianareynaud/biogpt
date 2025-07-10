"""
Report router for generating genomic analysis reports.
"""

import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import logging

from app.models.schemas import ReportRequest, ReportResponse, ReportLanguage
from app.services.report_generator import generate_pdf_report, generate_markdown_report
from app.dependencies import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    Generate a PDF report from genome analysis results.
    
    Parameters
    ----------
    request : ReportRequest
        Report generation request.
        
    Returns
    -------
    ReportResponse
        Information about the generated report.
    """
    try:
        upload_id = request.upload_id
        language = request.language
        
        # Verify upload exists and is completed
        db = get_database()
        
        upload_result = db.execute("""
            SELECT filename, processing_status, upload_timestamp
            FROM user_uploads 
            WHERE upload_id = ?
        """, [upload_id]).fetchone()
        
        if not upload_result:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        filename, processing_status, upload_timestamp = upload_result
        
        if processing_status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Analysis not completed. Status: {processing_status}"
            )
        
        # Get analysis results
        analysis_results = db.execute("""
            SELECT 
                analysis_id, rsID, chromosome, position, genotype,
                classification, confidence_score, clinical_interpretation
            FROM variant_analyses 
            WHERE upload_id = ?
            ORDER BY 
                CASE 
                    WHEN chromosome GLOB '[0-9]*' THEN CAST(chromosome AS INTEGER)
                    ELSE 999 
                END,
                position
        """, [upload_id]).fetchall()
        
        if not analysis_results:
            raise HTTPException(status_code=404, detail="No analysis results found")
        
        # Prepare report data
        report_data = {
            'upload_id': upload_id,
            'filename': filename,
            'upload_timestamp': upload_timestamp,
            'language': language,
            'total_variants': len(analysis_results),
            'variants': []
        }
        
        # Convert results to report format
        for result in analysis_results:
            variant_data = {
                'analysis_id': result[0],
                'rsID': result[1],
                'chromosome': result[2],
                'position': result[3],
                'genotype': result[4],
                'classification': result[5],
                'confidence_score': result[6],
                'clinical_interpretation': result[7]
            }
            report_data['variants'].append(variant_data)
        
        # Generate summary statistics
        classifications = [v['classification'] for v in report_data['variants']]
        summary = {
            'total_variants': len(classifications),
            'pathogenic': sum(1 for c in classifications if 'Patogênica' in c and 'Provavelmente' not in c),
            'likely_pathogenic': sum(1 for c in classifications if 'Provavelmente Patogênica' in c),
            'vus': sum(1 for c in classifications if c == 'VUS'),
            'likely_benign': sum(1 for c in classifications if 'Provavelmente Benigna' in c),
            'benign': sum(1 for c in classifications if 'Benigna' in c and 'Provavelmente' not in c)
        }
        report_data['summary'] = summary
        
        # Generate markdown content
        markdown_content = generate_markdown_report(report_data)
        
        # Generate PDF report
        reports_dir = os.getenv("REPORTS_DIR", "/app/reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        report_id = str(uuid.uuid4())
        pdf_filename = f"report_{upload_id}_{language}_{report_id}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)
        
        pdf_success = generate_pdf_report(markdown_content, pdf_path, language)
        
        if not pdf_success:
            raise HTTPException(status_code=500, detail="Failed to generate PDF report")
        
        # Store report information in database
        db.execute("""
            INSERT INTO reports (
                report_id, upload_id, report_type, language, 
                pdf_path, markdown_content
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            report_id, upload_id, "genomic_analysis", 
            language.value, pdf_path, markdown_content
        ])
        
        # Generate URLs
        pdf_url = f"/api/v1/reports/{report_id}/download"
        download_url = f"/api/v1/reports/{report_id}/pdf"
        
        logger.info(f"Report generated successfully: {report_id}")
        
        return ReportResponse(
            report_id=report_id,
            upload_id=upload_id,
            report_type="genomic_analysis",
            language=language,
            pdf_url=pdf_url,
            download_url=download_url,
            generated_at=datetime.now(),
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    """
    Download a generated report PDF.
    
    Parameters
    ----------
    report_id : str
        Report ID to download.
        
    Returns
    -------
    FileResponse
        PDF file download.
    """
    try:
        db = get_database()
        
        result = db.execute("""
            SELECT pdf_path, upload_id, language
            FROM reports 
            WHERE report_id = ?
        """, [report_id]).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        pdf_path, upload_id, language = result
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # Generate appropriate filename
        filename = f"genomic_report_{upload_id}_{language}.pdf"
        
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail="Failed to download report")

@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(report_id: str):
    """
    Get report PDF for viewing.
    
    Parameters
    ----------
    report_id : str
        Report ID.
        
    Returns
    -------
    FileResponse
        PDF file for viewing.
    """
    try:
        db = get_database()
        
        result = db.execute("""
            SELECT pdf_path
            FROM reports 
            WHERE report_id = ?
        """, [report_id]).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        pdf_path = result[0]
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to get report PDF")

@router.get("/reports/{report_id}/markdown")
async def get_report_markdown(report_id: str):
    """
    Get report content in Markdown format.
    
    Parameters
    ----------
    report_id : str
        Report ID.
        
    Returns
    -------
    dict
        Markdown content.
    """
    try:
        db = get_database()
        
        result = db.execute("""
            SELECT markdown_content, upload_id, language, generated_at
            FROM reports 
            WHERE report_id = ?
        """, [report_id]).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        markdown_content, upload_id, language, generated_at = result
        
        return {
            'report_id': report_id,
            'upload_id': upload_id,
            'language': language,
            'generated_at': generated_at,
            'content': markdown_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report markdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to get report markdown")

@router.get("/reports")
async def list_reports(
    upload_id: Optional[str] = Query(None, description="Filter by upload ID"),
    language: Optional[ReportLanguage] = Query(None, description="Filter by language"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
):
    """
    List generated reports.
    
    Parameters
    ----------
    upload_id : str, optional
        Filter by upload ID.
    language : ReportLanguage, optional
        Filter by language.
    limit : int
        Maximum number of results.
        
    Returns
    -------
    dict
        List of reports.
    """
    try:
        db = get_database()
        
        # Build query with filters
        query = """
            SELECT 
                r.report_id, r.upload_id, r.report_type, r.language,
                r.generated_at, u.filename
            FROM reports r
            LEFT JOIN user_uploads u ON r.upload_id = u.upload_id
            WHERE 1=1
        """
        params = []
        
        if upload_id:
            query += " AND r.upload_id = ?"
            params.append(upload_id)
        
        if language:
            query += " AND r.language = ?"
            params.append(language.value)
        
        query += " ORDER BY r.generated_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.execute(query, params).fetchall()
        
        reports = []
        for result in results:
            report_info = {
                'report_id': result[0],
                'upload_id': result[1],
                'report_type': result[2],
                'language': result[3],
                'generated_at': result[4],
                'filename': result[5],
                'download_url': f"/api/v1/reports/{result[0]}/download",
                'pdf_url': f"/api/v1/reports/{result[0]}/pdf"
            }
            reports.append(report_info)
        
        return {
            'reports': reports,
            'total': len(reports),
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to list reports")

@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """
    Delete a generated report.
    
    Parameters
    ----------
    report_id : str
        Report ID to delete.
        
    Returns
    -------
    dict
        Deletion confirmation.
    """
    try:
        db = get_database()
        
        # Get report info
        result = db.execute("""
            SELECT pdf_path
            FROM reports 
            WHERE report_id = ?
        """, [report_id]).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        pdf_path = result[0]
        
        # Delete PDF file if it exists
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                logger.info(f"Deleted report file: {pdf_path}")
            except Exception as e:
                logger.warning(f"Failed to delete report file {pdf_path}: {e}")
        
        # Delete from database
        db.execute("DELETE FROM reports WHERE report_id = ?", [report_id])
        
        logger.info(f"Report deleted: {report_id}")
        
        return {
            'message': 'Report deleted successfully',
            'report_id': report_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete report") 