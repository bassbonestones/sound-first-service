"""Materials endpoints for upload, analysis, and ingestion."""
import logging
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
    MaterialBasicOut, MaterialFullAnalysisOut, ExportMessageOut, AnalysisPreviewOut,
    LearningPathRequest, LearningPathResponse
)
from app.services import MaterialService, get_material_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=List[MaterialBasicOut])
def get_materials(db: Session = Depends(get_db)) -> List[MaterialBasicOut]:
    """List all materials with basic info."""
    materials = db.query(Material).all()
    result = [
        {
            "id": m.id,
            "title": m.title,
            "allowed_keys": str(m.allowed_keys).split(",") if m.allowed_keys else [],
            "original_key_center": m.original_key_center,
            "pitch_reference_type": m.pitch_reference_type
        }
        for m in materials
    ]
    return result  # type: ignore[return-value]


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
        logger.error(f"MusicXML analysis failed for upload: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to analyze MusicXML: {str(e)}")
    
    allowed_keys = data.allowed_keys or ["C", "G", "F", "D", "Bb", "A", "Eb"]
    
    # Create material record
    material = service.create_material_record(
        db=db,
        title=data.title or extraction_result.title or "Untitled",
        musicxml_content=data.musicxml_content,
    )
    
    # Link capabilities and compute bitmasks
    bit_indices = service.link_capabilities(db, material, list(capability_names))
    service.compute_and_store_bitmasks(material, bit_indices)
    
    # Create analysis record
    service.create_material_analysis(db, material, extraction_result)
    
    db.commit()
    
    return MaterialAnalysisResponse(
        material_id=int(material.id),
        title=str(material.title),
        extracted_capabilities=list(capability_names),
        range_analysis=extraction_result.range_analysis.__dict__ if extraction_result.range_analysis else None,
        chromatic_complexity=extraction_result.chromatic_complexity_score,
        measure_count=extraction_result.measure_count,
        warnings=[],
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
    }  # type: ignore[return-value]


@router.post("/analyze", response_model=AnalysisPreviewOut, status_code=200)
def analyze_material_preview(data: MaterialUpload = Body(...)) -> AnalysisPreviewOut:
    """
    Preview material analysis without saving to database.
    
    Returns full analysis including capabilities, range, soft gates, and unified scores.
    """
    from app.services import get_analysis_service
    
    try:
        service = get_analysis_service()
        result = service.analyze_musicxml(data.musicxml_content, data.title)
        return result.to_dict()  # type: ignore[return-value]
    except Exception as e:
        logger.error(f"Material analysis preview failed: {e}")
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
        logger.error(f"Batch ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/export-json", response_model=ExportMessageOut)
def export_materials_to_json() -> ExportMessageOut:
    """Export current materials data to materials.json."""
    from app.material_ingestion_service import MaterialIngestionService
    
    try:
        service = MaterialIngestionService()
        path = service.export_to_json()
        return {"message": "Materials exported", "path": str(path)}  # type: ignore[return-value]
    except Exception as e:
        logger.error(f"Material JSON export failed: {e}")
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


# === Learning Path Generation ===


@router.post("/learning-path", response_model=LearningPathResponse)
def generate_learning_path(
    data: LearningPathRequest = Body(...),
    db: Session = Depends(get_db)
) -> LearningPathResponse:
    """
    Generate a learning path from capabilities found in an imported score.
    
    Takes capability names detected in the score and the user ID,
    returns an ordered list of capabilities the user needs to learn,
    sorted by prerequisites (learn prerequisites first).
    
    Args:
        capability_names: List of capability names from the imported score
        user_id: User ID to check mastery against
    
    Returns:
        Learning path with capabilities ordered by prerequisite depth,
        indicating which capabilities the user already knows and which
        they need to learn.
    """
    from app.models.capability_schema import Capability, UserCapability
    from app.models.core import User
    import json
    from collections import defaultdict
    
    # Verify user exists
    user = db.query(User).filter_by(id=data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all requested capabilities
    capabilities = db.query(Capability).filter(
        Capability.name.in_(data.capability_names)
    ).all()
    
    cap_by_name = {c.name: c for c in capabilities}
    cap_by_id = {c.id: c for c in capabilities}
    
    # Get user's mastered capabilities (all, not just those in the score)
    user_caps = db.query(UserCapability).filter(
        UserCapability.user_id == data.user_id,
        UserCapability.is_active == True,
        UserCapability.mastered_at != None
    ).all()
    mastered_cap_ids = {uc.capability_id for uc in user_caps}
    
    # Also load all capabilities referenced as prerequisites
    # (we might need them even if not in the original list)
    all_prereq_ids: set = set()
    for cap in capabilities:
        if cap.prerequisite_ids:
            prereq_ids = json.loads(str(cap.prerequisite_ids))
            all_prereq_ids.update(prereq_ids)
    
    # Load any prerequisite capabilities not already loaded
    missing_prereq_ids = all_prereq_ids - set(cap_by_id.keys())
    if missing_prereq_ids:
        prereq_caps = db.query(Capability).filter(
            Capability.id.in_(missing_prereq_ids)
        ).all()
        for pc in prereq_caps:
            cap_by_id[pc.id] = pc
            cap_by_name[pc.name] = pc
            
        # Recursively load prerequisites of prerequisites
        def load_all_prereqs(cap_ids: set, loaded: dict) -> None:
            new_ids: set = set()
            for cid in cap_ids:
                if cid in loaded and loaded[cid].prerequisite_ids:
                    prereqs = json.loads(str(loaded[cid].prerequisite_ids))
                    for pid in prereqs:
                        if pid not in loaded:
                            new_ids.add(pid)
            if new_ids:
                new_caps = db.query(Capability).filter(Capability.id.in_(new_ids)).all()
                for nc in new_caps:
                    loaded[nc.id] = nc
                    cap_by_name[nc.name] = nc
                load_all_prereqs(new_ids, loaded)
        
        load_all_prereqs(missing_prereq_ids, cap_by_id)
    
    # Calculate depth for each capability (distance from no unmastered prerequisites)
    def calculate_depth(cap_id: int, depth_cache: dict, visited: set) -> int:
        """Calculate prerequisite depth (0 = no unmastered prereqs)."""
        if cap_id in depth_cache:
            return depth_cache[cap_id]
        
        if cap_id in visited:
            return 0  # Circular dependency - treat as 0
        
        visited.add(cap_id)
        
        cap = cap_by_id.get(cap_id)
        if not cap or not cap.prerequisite_ids:
            depth_cache[cap_id] = 0
            return 0
        
        prereq_ids = json.loads(str(cap.prerequisite_ids))
        max_prereq_depth = 0
        
        for prereq_id in prereq_ids:
            # Only count unmastered prerequisites
            if prereq_id not in mastered_cap_ids:
                prereq_depth = calculate_depth(prereq_id, depth_cache, visited)
                max_prereq_depth = max(max_prereq_depth, prereq_depth + 1)
        
        depth_cache[cap_id] = max_prereq_depth
        return max_prereq_depth
    
    depth_cache: dict = {}
    
    # Build learning path
    learning_path = []
    mastered_count = 0
    
    # Include original score capabilities AND their unmastered prerequisites
    caps_to_include = set(cap_by_name.keys())
    for cap in capabilities:
        if cap.prerequisite_ids:
            prereq_ids = json.loads(str(cap.prerequisite_ids))
            for pid in prereq_ids:
                if pid not in mastered_cap_ids and pid in cap_by_id:
                    caps_to_include.add(cap_by_id[pid].name)
    
    for cap_name in caps_to_include:
        cap = cap_by_name.get(cap_name)
        if not cap:
            continue
        
        is_mastered = cap.id in mastered_cap_ids
        if is_mastered:
            mastered_count += 1
        
        # Get prerequisite names
        prereq_names = []
        if cap.prerequisite_ids:
            prereq_ids = json.loads(str(cap.prerequisite_ids))
            prereq_names = [
                cap_by_id[pid].name 
                for pid in prereq_ids 
                if pid in cap_by_id
            ]
        
        depth = calculate_depth(cap.id, depth_cache, set())
        
        learning_path.append({
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "difficulty_tier": cap.difficulty_tier or 1,
            "is_mastered": is_mastered,
            "prerequisite_names": prereq_names,
            "depth": depth,
        })
    
    # Sort by: not mastered first, then by depth (lower first), then by name
    learning_path.sort(key=lambda x: (x["is_mastered"], x["depth"], x["name"]))
    
    # Group by domain for UI convenience
    path_by_domain: dict = defaultdict(list)
    for cap_data in learning_path:
        if not cap_data["is_mastered"]:
            path_by_domain[cap_data["domain"]].append(cap_data)
    
    return {  # type: ignore[return-value]
        "user_id": data.user_id,
        "total_capabilities_in_score": len(data.capability_names),
        "capabilities_already_mastered": mastered_count,
        "capabilities_to_learn": len([c for c in learning_path if not c["is_mastered"]]),
        "learning_path": learning_path,
        "path_by_domain": dict(path_by_domain),
    }
