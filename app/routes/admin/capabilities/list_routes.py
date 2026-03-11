"""GET endpoints for capability listing and queries."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.models.capability_schema import (
    Capability, MaterialCapability, MaterialTeachesCapability
)

from .schemas import DETECTION_TYPES, DETECTION_SOURCES, CUSTOM_DETECTION_FUNCTIONS
from .helpers import parse_prerequisite_ids, parse_soft_gate_requirements, parse_detection_rule


router = APIRouter()


@router.get("/detection-rule-options")
def get_detection_rule_options():
    """Get available options for configuring detection rules."""
    return {
        "types": DETECTION_TYPES,
        "sources": DETECTION_SOURCES,
        "custom_functions": CUSTOM_DETECTION_FUNCTIONS,
        "schema": {
            "element": {
                "required": ["source"],
                "optional": ["element_type", "threshold"]
            },
            "value_match": {
                "required": ["source", "value"],
                "optional": ["threshold"]
            },
            "compound": {
                "required": ["rules"],
                "description": "Array of nested detection rules"
            },
            "interval": {
                "required": ["source", "semitones"],
                "optional": ["threshold", "direction"]
            },
            "text_match": {
                "required": ["source", "pattern"],
                "optional": ["threshold", "match_type"]
            },
            "time_signature": {
                "required": ["numerator", "denominator"],
                "optional": ["threshold"]
            },
            "range": {
                "required": ["source", "min", "max"],
                "optional": ["threshold"]
            },
            "custom": {
                "required": ["custom_function"],
                "optional": ["threshold"]
            }
        }
    }


@router.get("/capabilities")
def admin_get_capabilities(
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all capabilities with extended admin info."""
    query = db.query(Capability)
    if domain:
        query = query.filter(Capability.domain == domain)
    
    capabilities = query.order_by(Capability.domain, Capability.bit_index, Capability.name).all()
    
    result = []
    for cap in capabilities:
        requires_count = db.query(MaterialCapability).filter_by(capability_id=cap.id).count()
        teaches_count = db.query(MaterialTeachesCapability).filter_by(capability_id=cap.id).count()
        
        prereq_ids_list = parse_prerequisite_ids(cap)
        prereq_names = []
        if prereq_ids_list:
            prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids_list)).all()
            prereq_names = [p.name for p in prereqs]
        
        soft_gate_reqs = parse_soft_gate_requirements(cap)
        detection_rule = parse_detection_rule(cap)
        
        result.append({
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "subdomain": cap.subdomain,
            "bit_index": cap.bit_index,
            "requirement_type": cap.requirement_type,
            "difficulty_tier": cap.difficulty_tier,
            "difficulty_weight": cap.difficulty_weight,
            "mastery_type": cap.mastery_type,
            "mastery_count": cap.mastery_count,
            "evidence_required_count": cap.evidence_required_count,
            "evidence_distinct_materials": cap.evidence_distinct_materials,
            "evidence_acceptance_threshold": cap.evidence_acceptance_threshold,
            "soft_gate_requirements": soft_gate_reqs,
            "detection_rule": detection_rule,
            "is_active": cap.is_active if cap.is_active is not None else True,
            "is_global": cap.is_global if cap.is_global is not None else True,
            "prerequisite_ids": prereq_ids_list,
            "prerequisite_names": prereq_names,
            "materials_requiring": requires_count,
            "materials_teaching": teaches_count,
        })
    
    return {"capabilities": result, "count": len(result)}


@router.get("/capabilities/{capability_id}/graph")
def admin_get_capability_graph(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """Get dependency graph for a capability."""
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    depends_on = []
    prereq_ids = parse_prerequisite_ids(cap)
    if prereq_ids:
        prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids)).all()
        depends_on = [p.name for p in prereqs]
    
    all_caps = db.query(Capability).all()
    required_by = []
    for other_cap in all_caps:
        other_prereq_ids = parse_prerequisite_ids(other_cap)
        if other_prereq_ids and capability_id in other_prereq_ids:
            required_by.append(other_cap.name)
    
    return {
        "capability": cap.name,
        "depends_on": depends_on,
        "required_by": required_by,
    }


@router.get("/day0-capabilities")
def get_day0_capabilities():
    """Get the list of capability names granted when Day 0 completes."""
    from app.services.user_service import DAY0_BASE_CAPABILITIES
    
    # Include both clef options since we don't know user's instrument here
    return {
        "base_capabilities": DAY0_BASE_CAPABILITIES,
        "clef_capabilities": ["clef_treble", "clef_bass"],
        "all": DAY0_BASE_CAPABILITIES + ["clef_treble", "clef_bass"],
    }
