"""Materials endpoints for upload, analysis, and ingestion."""
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models.core import Material
from app.schemas import (
    MaterialUpload,
    MaterialAnalysisResponse,
    BatchIngestionRequest,
    BatchIngestionResponse,
    ReanalyzeRequest,
    ReanalyzeResponse,
    BatchReanalyzeRequest,
    BatchReanalyzeResponse,
)
from app.schemas.material_schemas import (
    MaterialBasicOut, MaterialFullAnalysisOut, ExportMessageOut
)
from app.services import MaterialService, get_material_service

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=List[MaterialBasicOut])
def get_materials(db: Session = Depends(get_db)) -> List[MaterialBasicOut]:
    """List all materials with basic info."""
    materials = db.query(Material).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "allowed_keys": m.allowed_keys.split(",") if m.allowed_keys else [],
            "original_key_center": m.original_key_center,
            "pitch_reference_type": m.pitch_reference_type
        }
        for m in materials
    ]


@router.post("/upload", response_model=MaterialAnalysisResponse)
def upload_material(
    data: MaterialUpload = Body(...),
    db: Session = Depends(get_db)
) -> MaterialAnalysisResponse:
    """
    Upload a new material from MusicXML content.
    
    Parses MusicXML, extracts capabilities, creates MaterialCapability records,
    creates MaterialAnalysis with range/density info, and computes bitmasks.
    """
    service = get_material_service()
    
    try:
        extraction_result, capability_names = service.analyze_musicxml(data.musicxml_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze MusicXML: {str(e)}")
    
    allowed_keys = data.allowed_keys or ["C", "G", "F", "D", "Bb", "A", "Eb"]
    
    # Create material record
    material = service.create_material_record(
        db=db,
        title=data.title or extraction_result.title or "Untitled",
        musicxml_content=data.musicxml_content,
        original_key_center=data.original_key_center,
        allowed_keys=allowed_keys,
    )
    
    # Link capabilities and compute bitmasks
    bit_indices, warnings = service.link_capabilities(db, material.id, capability_names)
    service.compute_and_store_bitmasks(material, bit_indices)
    
    # Create analysis record
    service.create_material_analysis(db, material.id, extraction_result)
    
    db.commit()
    
    return MaterialAnalysisResponse(
        material_id=material.id,
        title=material.title,
        extracted_capabilities=capability_names,
        range_analysis=extraction_result.range_analysis.__dict__ if extraction_result.range_analysis else None,
        chromatic_complexity=extraction_result.chromatic_complexity_score,
        measure_count=extraction_result.measure_count,
        warnings=warnings,
    )


@router.get("/{material_id}/analysis", response_model=MaterialFullAnalysisOut)
def get_material_analysis(material_id: int, db: Session = Depends(get_db)) -> MaterialFullAnalysisOut:
    """Get the analysis data for a material."""
    from app.models.capability_schema import MaterialAnalysis, MaterialCapability, Capability
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    analysis = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
    
    mat_caps = db.query(MaterialCapability).filter_by(material_id=material_id).all()
    cap_ids = [mc.capability_id for mc in mat_caps]
    caps = db.query(Capability).filter(Capability.id.in_(cap_ids)).all() if cap_ids else []
    
    return {
        "material_id": material_id,
        "title": material.title,
        "capabilities": [
            {"id": c.id, "name": c.name, "display_name": c.display_name, "domain": c.domain}
            for c in caps
        ],
        "analysis": {
            "lowest_pitch": analysis.lowest_pitch if analysis else None,
            "highest_pitch": analysis.highest_pitch if analysis else None,
            "range_semitones": analysis.range_semitones if analysis else None,
            "pitch_density": {
                "low": analysis.pitch_density_low,
                "mid": analysis.pitch_density_mid,
                "high": analysis.pitch_density_high,
            } if analysis else None,
            "chromatic_complexity": analysis.chromatic_complexity if analysis else None,
            "tempo_marking": analysis.tempo_marking if analysis else None,
            "tempo_bpm": analysis.tempo_bpm if analysis else None,
            "measure_count": analysis.measure_count if analysis else None,
        } if analysis else None,
    }


@router.post("/analyze")
def analyze_material_preview(data: MaterialUpload = Body(...)):
    """
    Preview material analysis without saving to database.
    
    Returns full analysis including capabilities, range, soft gates, and unified scores.
    """
    from app.services import get_analysis_service
    
    try:
        service = get_analysis_service()
        result = service.analyze_musicxml(data.musicxml_content, data.title)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")


@router.post("/ingest-batch", response_model=BatchIngestionResponse)
def ingest_materials_batch(data: BatchIngestionRequest = Body(...)) -> BatchIngestionResponse:
    """
    Batch analyze MusicXML files and update materials.json.
    
    Scans resources/materials/*.musicxml, compares against materials.json,
    and analyzes new/changed files.
    """
    from app.material_ingestion_service import MaterialIngestionService
    
    try:
        service = MaterialIngestionService()
        
        if data.specific_metrics:
            result = service.analyze_specific_metrics(
                metrics=data.specific_metrics,
                file_filter=data.specific_files,
            )
        else:
            result = service.ingest_batch(
                analyze_missing_only=data.analyze_missing_only,
                overwrite=data.overwrite,
                specific_files=data.specific_files,
            )
        
        return BatchIngestionResponse(
            files_scanned=result.files_scanned,
            files_analyzed=result.files_analyzed,
            files_skipped=result.files_skipped,
            orphans_removed=result.orphans_removed,
            errors=result.errors,
            analyzed_materials=result.analyzed_materials,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/export-json", response_model=ExportMessageOut)
def export_materials_to_json() -> ExportMessageOut:
    """Export current materials data to materials.json."""
    from app.material_ingestion_service import MaterialIngestionService
    
    try:
        service = MaterialIngestionService()
        path = service.export_to_json()
        return {"message": "Materials exported", "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/{material_id}/reanalyze", response_model=ReanalyzeResponse)
def reanalyze_single_material(
    material_id: int,
    data: ReanalyzeRequest = Body(default=ReanalyzeRequest()),
    db: Session = Depends(get_db)
) -> ReanalyzeResponse:
    """
    Re-analyze a single material and update its analysis data.
    
    Args:
        material_id: Material to re-analyze
        metrics: Optional list of specific metrics to update:
            - "capabilities": Re-detect capabilities
            - "soft_gates": Recalculate soft gate metrics
            - "range": Recalculate range analysis
            - "unified_scores": Recalculate unified domain scores
            - If None, updates all metrics
    """
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not material.musicxml_canonical:
        raise HTTPException(status_code=400, detail="Material has no MusicXML content")
    
    service = get_material_service()
    result = service.reanalyze_material(db, material, data.metrics)
    
    db.commit()
    
    return ReanalyzeResponse(
        material_id=result.material_id,
        title=result.title,
        metrics_updated=result.metrics_updated,
        capabilities_count=result.capabilities_count,
        soft_gates=result.soft_gates,
        range_analysis=result.range_analysis,
    )


@router.post("/reanalyze-all", response_model=BatchReanalyzeResponse)
def reanalyze_all_materials(
    data: BatchReanalyzeRequest = Body(default=BatchReanalyzeRequest()),
    db: Session = Depends(get_db)
) -> BatchReanalyzeResponse:
    """
    Re-analyze multiple materials in batch.
    
    Args:
        metrics: Specific metrics to update (capabilities, soft_gates, range)
        material_ids: Specific materials to update (None = all)
    """
    query = db.query(Material)
    if data.material_ids:
        query = query.filter(Material.id.in_(data.material_ids))
    
    materials = query.all()
    
    service = get_material_service()
    result = service.reanalyze_batch(db, materials, data.metrics)
    
    db.commit()
    
    return BatchReanalyzeResponse(
        total_materials=result.total_materials,
        materials_updated=result.materials_updated,
        materials_failed=result.materials_failed,
        errors=result.errors,
    )
