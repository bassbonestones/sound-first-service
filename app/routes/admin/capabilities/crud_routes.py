"""CRUD endpoints for capability management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.db import get_db
from app.models.capability_schema import Capability

from .schemas import (
    CapabilityCreateRequest,
    CapabilityUpdateRequest,
    VALID_REQUIREMENT_TYPES,
    VALID_MASTERY_TYPES,
    MIN_RATING,
    MAX_RATING,
    MIN_DIFFICULTY_WEIGHT,
    MAX_DIFFICULTY_WEIGHT,
)
from .helpers import check_circular_dependency, parse_prerequisite_ids, parse_soft_gate_requirements


router = APIRouter()


@router.post("/capabilities/{capability_id}/archive")
def admin_archive_capability(capability_id: int, db: Session = Depends(get_db)):
    """Archive a capability by setting is_active=False."""
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if not cap.is_active:
        return {"success": True, "message": f"Capability '{cap.name}' is already archived", "capability_id": capability_id, "is_active": False}
    
    cap.is_active = False
    db.commit()
    
    return {"success": True, "message": f"Archived capability '{cap.name}'", "capability_id": capability_id, "is_active": False}


@router.post("/capabilities/{capability_id}/restore")
def admin_restore_capability(capability_id: int, db: Session = Depends(get_db)):
    """Restore an archived capability by setting is_active=True."""
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if cap.is_active:
        return {"success": True, "message": f"Capability '{cap.name}' is already active", "capability_id": capability_id, "is_active": True}
    
    cap.is_active = True
    db.commit()
    
    return {"success": True, "message": f"Restored capability '{cap.name}'", "capability_id": capability_id, "is_active": True}


@router.delete("/capabilities/{capability_id}")
def admin_delete_capability(capability_id: int, db: Session = Depends(get_db)):
    """Permanently delete a capability and shift bit_indexes."""
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    cap_name = cap.name
    cap_domain = cap.domain
    deleted_bit_index = cap.bit_index
    
    all_caps = db.query(Capability).all()
    prereqs_cleaned = 0
    for c in all_caps:
        prereq_list = parse_prerequisite_ids(c)
        if capability_id in prereq_list:
            prereq_list = [pid for pid in prereq_list if pid != capability_id]
            c.prerequisite_ids = json.dumps(prereq_list) if prereq_list else None
            prereqs_cleaned += 1
    
    caps_after = [c for c in all_caps if c.bit_index is not None and c.bit_index > deleted_bit_index]
    db.delete(cap)
    
    if caps_after:
        for c in caps_after:
            c.bit_index = -(c.bit_index)
        db.flush()
        for c in caps_after:
            c.bit_index = -(c.bit_index) - 1
    
    db.commit()
    
    remaining_in_domain = db.query(Capability).filter_by(domain=cap_domain).count()
    domain_removed = remaining_in_domain == 0
    
    return {
        "success": True,
        "message": f"Deleted capability '{cap_name}'",
        "capability_id": capability_id,
        "shifted_count": len(caps_after),
        "prereqs_cleaned": prereqs_cleaned,
        "domain_removed": domain_removed,
        "domain": cap_domain
    }


@router.post("/capabilities")
def admin_create_capability(create_data: CapabilityCreateRequest, db: Session = Depends(get_db)):
    """Create a new capability at the correct position."""
    existing = db.query(Capability).filter_by(name=create_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Capability with name '{create_data.name}' already exists")
    
    all_caps = db.query(Capability).order_by(Capability.bit_index).all()
    existing_domains = sorted(set(c.domain for c in all_caps))
    target_domain = create_data.domain
    
    if target_domain in existing_domains:
        domain_caps = [c for c in all_caps if c.domain == target_domain]
        if domain_caps:
            max_bit_in_domain = max(c.bit_index for c in domain_caps)
            insert_bit_index = max_bit_in_domain + 1
        else:
            insert_bit_index = 0
    else:
        insert_bit_index = None
        for existing_domain in existing_domains:
            if existing_domain > target_domain:
                domain_caps = [c for c in all_caps if c.domain == existing_domain]
                if domain_caps:
                    insert_bit_index = min(c.bit_index for c in domain_caps)
                break
        
        if insert_bit_index is None:
            max_bit = db.query(func.max(Capability.bit_index)).scalar() or -1
            insert_bit_index = max_bit + 1
    
    caps_to_shift = [c for c in all_caps if c.bit_index >= insert_bit_index]
    original_indexes = {c.id: c.bit_index for c in caps_to_shift}
    for cap in caps_to_shift:
        cap.bit_index = -(cap.bit_index + 1)
    db.flush()
    for cap in caps_to_shift:
        cap.bit_index = original_indexes[cap.id] + 1
    
    # Serialize detection rule if provided
    detection_json = None
    if create_data.detection_rule:
        detection_json = json.dumps(create_data.detection_rule.model_dump(exclude_none=True))
    
    cap = Capability(
        name=create_data.name,
        display_name=create_data.display_name,
        domain=create_data.domain,
        subdomain=create_data.subdomain,
        requirement_type=create_data.requirement_type,
        bit_index=insert_bit_index,
        difficulty_tier=create_data.difficulty_tier,
        mastery_type=create_data.mastery_type,
        mastery_count=create_data.mastery_count,
        evidence_required_count=create_data.evidence_required_count,
        evidence_distinct_materials=create_data.evidence_distinct_materials,
        evidence_acceptance_threshold=create_data.evidence_acceptance_threshold,
        difficulty_weight=create_data.difficulty_weight,
        prerequisite_ids=json.dumps(create_data.prerequisite_ids) if create_data.prerequisite_ids else None,
        soft_gate_requirements=json.dumps(create_data.soft_gate_requirements) if create_data.soft_gate_requirements else None,
        music21_detection_json=detection_json,
        is_active=True
    )
    
    db.add(cap)
    db.commit()
    db.refresh(cap)
    
    return {
        "success": True,
        "message": f"Created capability '{cap.name}' at bit_index {cap.bit_index}",
        "capability": {"id": cap.id, "name": cap.name, "display_name": cap.display_name, "domain": cap.domain, "bit_index": cap.bit_index},
        "shifted_count": len(caps_to_shift)
    }


@router.put("/capabilities/{capability_id}")
def admin_update_capability(capability_id: int, update_data: CapabilityUpdateRequest, db: Session = Depends(get_db)):
    """Update an existing capability with validation."""
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    errors = []
    
    name = update_data.name.strip() if update_data.name else ""
    if not name:
        errors.append("name: Name is required")
    elif not all(c.islower() or c.isdigit() or c == '_' for c in name):
        errors.append("name: Must be lowercase alphanumeric with underscores only")
    else:
        existing = db.query(Capability).filter(Capability.name == name, Capability.id != capability_id).first()
        if existing:
            errors.append(f"name: A capability with name '{name}' already exists (id={existing.id})")
    
    domain = update_data.domain.strip() if update_data.domain else ""
    if not domain:
        errors.append("domain: Domain is required")
    
    if update_data.requirement_type not in VALID_REQUIREMENT_TYPES:
        errors.append(f"requirement_type: Must be one of {VALID_REQUIREMENT_TYPES}")
    
    if update_data.mastery_type not in VALID_MASTERY_TYPES:
        errors.append(f"mastery_type: Must be one of {VALID_MASTERY_TYPES}")
    
    if update_data.difficulty_tier < 1 or update_data.difficulty_tier > 5:
        errors.append("difficulty_tier: Must be between 1 and 5")
    
    if update_data.difficulty_weight < MIN_DIFFICULTY_WEIGHT or update_data.difficulty_weight > MAX_DIFFICULTY_WEIGHT:
        errors.append(f"difficulty_weight: Must be between {MIN_DIFFICULTY_WEIGHT} and {MAX_DIFFICULTY_WEIGHT}")
    
    if update_data.mastery_count < 1:
        errors.append("mastery_count: Must be at least 1")
    
    if update_data.evidence_required_count < 1:
        errors.append("evidence_required_count: Must be at least 1")
    
    if update_data.evidence_acceptance_threshold < MIN_RATING or update_data.evidence_acceptance_threshold > MAX_RATING:
        errors.append(f"evidence_acceptance_threshold: Must be between {MIN_RATING} and {MAX_RATING}")
    
    if update_data.prerequisite_ids is not None:
        prereq_ids = update_data.prerequisite_ids
        
        if capability_id in prereq_ids:
            errors.append("prerequisite_ids: Cannot set self as a prerequisite")
        
        if prereq_ids:
            existing_ids = [c.id for c in db.query(Capability.id).filter(Capability.id.in_(prereq_ids)).all()]
            missing_ids = set(prereq_ids) - set(existing_ids)
            if missing_ids:
                errors.append(f"prerequisite_ids: The following capability IDs do not exist: {list(missing_ids)}")
        
        if not errors:
            cycle_path = check_circular_dependency(capability_id, prereq_ids, db)
            if cycle_path:
                cycle_str = " → ".join(cycle_path)
                errors.append(f"prerequisite_ids: Would create circular dependency: {cycle_str}")
    
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Validation failed", "errors": errors})
    
    try:
        cap.name = name
        cap.display_name = update_data.display_name.strip() if update_data.display_name else None
        cap.domain = domain
        cap.subdomain = update_data.subdomain.strip() if update_data.subdomain else None
        cap.requirement_type = update_data.requirement_type
        cap.difficulty_tier = update_data.difficulty_tier
        cap.mastery_type = update_data.mastery_type
        cap.mastery_count = update_data.mastery_count
        cap.evidence_required_count = update_data.evidence_required_count
        cap.evidence_distinct_materials = update_data.evidence_distinct_materials
        cap.evidence_acceptance_threshold = update_data.evidence_acceptance_threshold
        cap.difficulty_weight = update_data.difficulty_weight
        
        if update_data.prerequisite_ids is not None:
            cap.prerequisite_ids = json.dumps(update_data.prerequisite_ids) if update_data.prerequisite_ids else None
        
        if update_data.soft_gate_requirements is not None:
            cap.soft_gate_requirements = json.dumps(update_data.soft_gate_requirements) if update_data.soft_gate_requirements else None
        
        # Handle detection rule update
        if update_data.detection_rule is not None:
            cap.music21_detection_json = json.dumps(update_data.detection_rule.model_dump(exclude_none=True)) if update_data.detection_rule else None
        
        db.commit()
        db.refresh(cap)
        
        prereq_ids_list = parse_prerequisite_ids(cap)
        prereq_names = []
        if prereq_ids_list:
            prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids_list)).all()
            prereq_map = {p.id: p for p in prereqs}
            prereq_names = [{"id": pid, "name": prereq_map[pid].name, "domain": prereq_map[pid].domain} for pid in prereq_ids_list if pid in prereq_map]
        
        soft_gate_reqs = parse_soft_gate_requirements(cap)
        
        return {
            "success": True,
            "message": "Capability updated successfully",
            "capability": {
                "id": cap.id, "name": cap.name, "display_name": cap.display_name, "domain": cap.domain,
                "subdomain": cap.subdomain, "bit_index": cap.bit_index, "requirement_type": cap.requirement_type,
                "difficulty_tier": cap.difficulty_tier, "difficulty_weight": cap.difficulty_weight,
                "mastery_type": cap.mastery_type, "mastery_count": cap.mastery_count,
                "evidence_required_count": cap.evidence_required_count, "evidence_distinct_materials": cap.evidence_distinct_materials,
                "evidence_acceptance_threshold": cap.evidence_acceptance_threshold, "soft_gate_requirements": soft_gate_reqs,
                "prerequisite_names": prereq_names,
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={"message": "Failed to save capability", "error": str(e)})
