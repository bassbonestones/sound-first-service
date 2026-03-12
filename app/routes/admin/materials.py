"""Admin materials endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.db import get_db
from app.models.core import User, Material
from app.models.capability_schema import (
    Capability, UserCapability, SoftGateRule, UserSoftGateState,
    MaterialCapability, MaterialTeachesCapability, MaterialAnalysis
)


router = APIRouter(tags=["admin-materials"])


# --- Response Models ---

class MaterialItem(BaseModel):
    id: int
    title: str
    original_key_center: Optional[str]
    allowed_keys: Optional[str]
    required_capabilities: List[str]
    teaches_capabilities: List[str]
    lowest_pitch: Optional[str] = None
    highest_pitch: Optional[str] = None
    range_semitones: Optional[int] = None
    chromatic_complexity: Optional[float] = None
    rhythmic_complexity: Optional[float] = None
    reading_complexity: Optional[float] = None
    measure_count: Optional[int] = None
    estimated_duration_seconds: Optional[float] = None
    tonal_complexity_stage: Optional[int] = None
    interval_size_stage: Optional[int] = None
    interval_sustained_stage: Optional[int] = None
    interval_hazard_stage: Optional[int] = None
    legacy_interval_size_stage: Optional[int] = None
    rhythm_complexity_stage: Optional[int] = None
    range_usage_stage: Optional[int] = None
    difficulty_index: Optional[float] = None


class MaterialsListResponse(BaseModel):
    materials: List[MaterialItem]
    count: int


class GateCheckResponse(BaseModel):
    material_id: int
    material_title: str
    user_id: int
    passes_hard_gates: bool
    hard_gate_failures: List[str]
    passes_soft_envelope: bool
    soft_envelope_failures: List[str]
    overall_eligible: bool


class AnalysisResponse(BaseModel):
    message: str
    analysis: Dict[str, Any]


@router.get("/materials", response_model=MaterialsListResponse)
def admin_get_materials(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get all materials with analysis data."""
    materials = db.query(Material).all()
    
    result = []
    for mat in materials:
        analysis = db.query(MaterialAnalysis).filter_by(material_id=mat.id).first()
        
        req_caps = db.query(MaterialCapability, Capability).join(
            Capability, MaterialCapability.capability_id == Capability.id
        ).filter(MaterialCapability.material_id == mat.id).all()
        required_capabilities = [c.name for _, c in req_caps]
        
        teach_caps = db.query(MaterialTeachesCapability, Capability).join(
            Capability, MaterialTeachesCapability.capability_id == Capability.id
        ).filter(MaterialTeachesCapability.material_id == mat.id).all()
        teaches_capabilities = [c.name for _, c in teach_caps]
        
        mat_data = {
            "id": mat.id, "title": mat.title, "original_key_center": mat.original_key_center,
            "allowed_keys": mat.allowed_keys, "required_capabilities": required_capabilities,
            "teaches_capabilities": teaches_capabilities,
        }
        
        if analysis:
            mat_data.update({
                "lowest_pitch": analysis.lowest_pitch, "highest_pitch": analysis.highest_pitch,
                "range_semitones": analysis.range_semitones, "chromatic_complexity": analysis.chromatic_complexity,
                "rhythmic_complexity": analysis.rhythmic_complexity, "reading_complexity": analysis.reading_complexity,
                "measure_count": analysis.measure_count, "estimated_duration_seconds": analysis.estimated_duration_seconds,
                "tonal_complexity_stage": analysis.tonal_complexity_stage, "interval_size_stage": analysis.interval_size_stage,
                "interval_sustained_stage": analysis.interval_sustained_stage, "interval_hazard_stage": analysis.interval_hazard_stage,
                "legacy_interval_size_stage": analysis.legacy_interval_size_stage,
                "rhythm_complexity_stage": analysis.rhythm_complexity_stage, "range_usage_stage": analysis.range_usage_stage,
                "difficulty_index": analysis.difficulty_index,
            })
        
        result.append(mat_data)
    
    return {"materials": result, "count": len(result)}


@router.get("/materials/{material_id}/gate-check", response_model=GateCheckResponse)
def admin_check_material_gates(material_id: int, user_id: int = Query(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Check if a material passes hard gates and soft envelope for a user."""
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    hard_gate_failures = []
    req_caps = db.query(MaterialCapability, Capability).join(
        Capability, MaterialCapability.capability_id == Capability.id
    ).filter(MaterialCapability.material_id == material_id, MaterialCapability.is_required == True).all()
    
    for mat_cap, cap in req_caps:
        user_cap = db.query(UserCapability).filter_by(user_id=user_id, capability_id=cap.id, is_active=True).first()
        if not user_cap or not user_cap.mastered_at:
            hard_gate_failures.append(cap.name)
    
    passes_hard_gates = len(hard_gate_failures) == 0
    
    soft_envelope_failures = []
    analysis = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
    
    if analysis:
        soft_rules = db.query(SoftGateRule).all()
        dimension_mapping = {
            "tonal_complexity_stage": analysis.tonal_complexity_stage,
            "interval_size_stage": analysis.interval_size_stage,
            "interval_sustained_stage": analysis.interval_sustained_stage,
            "interval_hazard_stage": analysis.interval_hazard_stage,
            "rhythm_complexity_stage": analysis.rhythm_complexity_stage,
            "range_usage_stage": analysis.range_usage_stage,
        }
        
        for rule in soft_rules:
            material_value = dimension_mapping.get(rule.dimension_name)
            if material_value is None:
                continue
            
            user_state = db.query(UserSoftGateState).filter_by(user_id=user_id, dimension_name=rule.dimension_name).first()
            comfort = user_state.comfortable_value if user_state else 0
            max_allowed = comfort + rule.frontier_buffer
            
            if material_value > max_allowed:
                soft_envelope_failures.append(f"{rule.dimension_name}: material={material_value}, max_allowed={max_allowed}")
    
    passes_soft_envelope = len(soft_envelope_failures) == 0
    
    return {
        "material_id": material_id, "material_title": material.title, "user_id": user_id,
        "passes_hard_gates": passes_hard_gates, "hard_gate_failures": hard_gate_failures,
        "passes_soft_envelope": passes_soft_envelope, "soft_envelope_failures": soft_envelope_failures,
        "overall_eligible": passes_hard_gates and passes_soft_envelope,
    }


@router.post("/materials/{material_id}/analyze", response_model=AnalysisResponse)
def admin_trigger_analysis(material_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Trigger re-analysis of a material's MusicXML."""
    from app.musicxml_analyzer import analyze_musicxml
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not material.musicxml_canonical:
        raise HTTPException(status_code=400, detail="Material has no MusicXML content")
    
    try:
        analysis_result = analyze_musicxml(material.musicxml_canonical)
        
        existing = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
        if existing:
            for key, value in analysis_result.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            analysis = MaterialAnalysis(material_id=material_id, **analysis_result)
            db.add(analysis)
        
        db.commit()
        return {"message": "Analysis completed", "analysis": analysis_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
