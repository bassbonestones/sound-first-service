"""Admin capabilities endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional, Dict
import datetime
import json
import os
import shutil

from app.db import get_db
from app.models.capability_schema import (
    Capability, MaterialCapability, MaterialTeachesCapability
)
from app.capability_registry import CUSTOM_DETECTORS


router = APIRouter(tags=["admin-capabilities"])


# --- Pydantic Models ---

# Detection rule type enum for dropdown
DETECTION_TYPES = ["element", "value_match", "compound", "interval", "text_match", "time_signature", "range", "custom"]

# Valid sources for value_match/text_match
DETECTION_SOURCES = ["notes", "dynamics", "tempos", "expressions", "articulations", "clefs", "key_signatures", "time_signatures", "intervals", "ornaments", "rests"]

# Custom detection functions (populated from capability_registry)
CUSTOM_DETECTION_FUNCTIONS = list(CUSTOM_DETECTORS.keys())


class DetectionRuleConfig(BaseModel):
    """Detection rule configuration."""
    type: str  # element, value_match, compound, interval, text_match, time_signature, range, custom
    # For element type
    element_class: Optional[str] = None  # e.g., "music21.articulations.Staccato"
    # For value_match type
    source: Optional[str] = None  # notes, dynamics, etc.
    field: Optional[str] = None  # e.g., "type", "value"
    eq: Optional[str] = None  # exact match value
    gte: Optional[float] = None  # >= comparison
    lte: Optional[float] = None  # <= comparison
    contains: Optional[str] = None  # substring match
    # For interval type
    quality: Optional[str] = None  # e.g., "M3", "P5", "m2"
    melodic: Optional[bool] = True  # True for melodic, False for harmonic
    # For time_signature type
    numerator: Optional[int] = None
    denominator: Optional[int] = None
    # For range type
    min_semitones: Optional[int] = None
    max_semitones: Optional[int] = None
    # For custom type
    function: Optional[str] = None  # custom function name


class CapabilityCreateRequest(BaseModel):
    """Request model for creating a new capability."""
    name: str
    display_name: Optional[str] = None
    domain: str
    subdomain: Optional[str] = None
    requirement_type: str = "required"
    difficulty_tier: int = 1
    mastery_type: str = "single"
    mastery_count: int = 1
    evidence_required_count: int = 1
    evidence_distinct_materials: bool = False
    evidence_acceptance_threshold: int = 4
    difficulty_weight: float = 1.0
    prerequisite_ids: Optional[List[int]] = None
    soft_gate_requirements: Optional[Dict[str, float]] = None
    detection_rule: Optional[DetectionRuleConfig] = None


class ReorderCapabilitiesRequest(BaseModel):
    """Request model for reordering capabilities within a domain."""
    domain: str
    capability_ids: List[int]


class RenameDomainRequest(BaseModel):
    """Request model for renaming a domain."""
    old_name: str
    new_name: str


class CapabilityUpdateRequest(BaseModel):
    """Request model for updating a capability."""
    name: str
    display_name: Optional[str] = None
    domain: str
    subdomain: Optional[str] = None
    requirement_type: str = "required"
    difficulty_tier: int = 1
    mastery_type: str = "single"
    mastery_count: int = 1
    evidence_required_count: int = 1
    evidence_distinct_materials: bool = False
    evidence_acceptance_threshold: int = 4
    difficulty_weight: float = 1.0
    prerequisite_ids: Optional[List[int]] = None
    soft_gate_requirements: Optional[Dict[str, float]] = None
    detection_rule: Optional[DetectionRuleConfig] = None


# --- Constants ---
VALID_REQUIREMENT_TYPES = ["required", "learnable_in_context"]
VALID_MASTERY_TYPES = ["single", "any_of_pool", "multiple"]
MIN_RATING = 1
MAX_RATING = 5
MIN_DIFFICULTY_WEIGHT = 0.1
MAX_DIFFICULTY_WEIGHT = 10.0


# --- Helper Functions ---
def check_circular_dependency(capability_id: int, new_prereq_ids: List[int], db) -> Optional[List[str]]:
    """
    Check if setting new_prereq_ids on capability_id would create a circular dependency.
    Returns None if no cycle, or a list of capability names forming the cycle path.
    """
    if not new_prereq_ids:
        return None
    
    all_caps = db.query(Capability).all()
    cap_map = {c.id: c for c in all_caps}
    prereq_map = {}
    for c in all_caps:
        try:
            prereq_map[c.id] = json.loads(c.prerequisite_ids) if c.prerequisite_ids else []
        except:
            prereq_map[c.id] = []
    
    prereq_map[capability_id] = new_prereq_ids
    visited = set()
    
    def dfs(current_id, path_so_far):
        if current_id in visited:
            return None
        if current_id == capability_id and len(path_so_far) > 0:
            return path_so_far + [cap_map[current_id].name if current_id in cap_map else f"id:{current_id}"]
        
        visited.add(current_id)
        path_so_far = path_so_far + [cap_map[current_id].name if current_id in cap_map else f"id:{current_id}"]
        
        for prereq_id in prereq_map.get(current_id, []):
            if prereq_id == capability_id:
                prereq_name = cap_map[prereq_id].name if prereq_id in cap_map else f"id:{prereq_id}"
                return path_so_far + [prereq_name]
            result = dfs(prereq_id, path_so_far)
            if result:
                return result
        return None
    
    for prereq_id in new_prereq_ids:
        if prereq_id == capability_id:
            return [cap_map[capability_id].name, cap_map[capability_id].name]
        
        visited.clear()
        result = dfs(prereq_id, [cap_map[capability_id].name])
        if result:
            return result
    
    return None


# --- Endpoints ---
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
        
        prereq_names = []
        prereq_ids_list = []
        if cap.prerequisite_ids:
            try:
                prereq_ids_list = json.loads(cap.prerequisite_ids) if isinstance(cap.prerequisite_ids, str) else cap.prerequisite_ids
                if prereq_ids_list:
                    prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids_list)).all()
                    prereq_names = [p.name for p in prereqs]
            except:
                prereq_ids_list = []
        
        soft_gate_reqs = None
        if cap.soft_gate_requirements:
            try:
                soft_gate_reqs = json.loads(cap.soft_gate_requirements) if isinstance(cap.soft_gate_requirements, str) else cap.soft_gate_requirements
            except:
                pass
        
        # Parse detection rule
        detection_rule = None
        if cap.music21_detection_json:
            try:
                detection_rule = json.loads(cap.music21_detection_json) if isinstance(cap.music21_detection_json, str) else cap.music21_detection_json
            except:
                pass
        
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
    if cap.prerequisite_ids:
        try:
            prereq_ids = json.loads(cap.prerequisite_ids) if isinstance(cap.prerequisite_ids, str) else cap.prerequisite_ids
            if prereq_ids:
                prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids)).all()
                depends_on = [p.name for p in prereqs]
        except:
            pass
    
    all_caps = db.query(Capability).all()
    required_by = []
    for other_cap in all_caps:
        if other_cap.prerequisite_ids:
            try:
                prereq_ids = json.loads(other_cap.prerequisite_ids) if isinstance(other_cap.prerequisite_ids, str) else other_cap.prerequisite_ids
                if prereq_ids and capability_id in prereq_ids:
                    required_by.append(other_cap.name)
            except:
                pass
    
    return {
        "capability": cap.name,
        "depends_on": depends_on,
        "required_by": required_by,
    }


@router.post("/capabilities/export")
def admin_export_capabilities(db: Session = Depends(get_db)):
    """Export all capabilities to capabilities.json.
    
    Preserves existing music21_detection rules from the current file.
    """
    capabilities = db.query(Capability).order_by(Capability.domain, Capability.bit_index, Capability.name).all()
    cap_id_to_name = {cap.id: cap.name for cap in capabilities}
    
    # Load existing detection rules to preserve them
    resources_dir = os.path.join(os.path.dirname(__file__), "..", "..", "resources")
    current_file = os.path.join(resources_dir, "capabilities.json")
    existing_detection_rules = {}
    
    if os.path.exists(current_file):
        try:
            with open(current_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            for cap in existing_data.get("capabilities", []):
                if cap.get("music21_detection"):
                    existing_detection_rules[cap["name"]] = cap["music21_detection"]
        except Exception:
            pass  # If we can't read existing file, proceed without preserving rules
    
    exported = []
    for cap in capabilities:
        prereq_names = []
        if cap.prerequisite_ids:
            try:
                prereq_ids = json.loads(cap.prerequisite_ids) if isinstance(cap.prerequisite_ids, str) else cap.prerequisite_ids
                if prereq_ids:
                    prereq_names = [cap_id_to_name[pid] for pid in prereq_ids if pid in cap_id_to_name]
            except:
                pass
        
        evidence_qualifier = {}
        if cap.evidence_qualifier_json:
            try:
                evidence_qualifier = json.loads(cap.evidence_qualifier_json) if isinstance(cap.evidence_qualifier_json, str) else cap.evidence_qualifier_json
            except:
                pass
        
        soft_gate_reqs = None
        if cap.soft_gate_requirements:
            try:
                soft_gate_reqs = json.loads(cap.soft_gate_requirements) if isinstance(cap.soft_gate_requirements, str) else cap.soft_gate_requirements
            except:
                pass
        
        # Parse detection rule from DB
        db_detection_rule = None
        if cap.music21_detection_json:
            try:
                db_detection_rule = json.loads(cap.music21_detection_json) if isinstance(cap.music21_detection_json, str) else cap.music21_detection_json
            except:
                pass
        
        cap_data = {
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "subdomain": cap.subdomain,
            "requirement_type": cap.requirement_type or "required",
            "prerequisite_names": prereq_names,
            "difficulty_tier": cap.difficulty_tier or 1,
            "mastery_type": cap.mastery_type or "single",
            "mastery_count": cap.mastery_count or 1,
            "evidence_required_count": cap.evidence_required_count or 1,
            "evidence_distinct_materials": cap.evidence_distinct_materials or False,
            "evidence_acceptance_threshold": cap.evidence_acceptance_threshold or 4,
            "evidence_qualifier_json": evidence_qualifier,
            "difficulty_weight": cap.difficulty_weight or 1.0,
            "soft_gate_requirements": soft_gate_reqs,
            "bit_index": cap.bit_index
        }
        
        # DB detection rule takes precedence, fall back to existing file rule
        if db_detection_rule:
            cap_data["music21_detection"] = db_detection_rule
        elif cap.name in existing_detection_rules:
            cap_data["music21_detection"] = existing_detection_rules[cap.name]
        
        exported.append(cap_data)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "version": f"capabilities_{timestamp}",
        "count": len(exported),
        "capabilities": exported
    }
    
    history_dir = os.path.join(resources_dir, "capability_history")
    
    try:
        os.makedirs(history_dir, exist_ok=True)
        
        archived_file = None
        if os.path.exists(current_file):
            archive_filename = f"capabilities_{timestamp}.json"
            archive_path = os.path.join(history_dir, archive_filename)
            shutil.copy2(current_file, archive_path)
            archived_file = archive_filename
        
        with open(current_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=1, ensure_ascii=False)
        
        rules_preserved = len([1 for c in exported if c.get("music21_detection")])
        message = f"Exported {len(exported)} capabilities ({rules_preserved} detection rules preserved)"
        if archived_file:
            message += f" (archived previous to capability_history/{archived_file})"
        
        return {
            "success": True,
            "message": message,
            "filename": "capabilities.json",
            "archived": archived_file,
            "detection_rules_preserved": rules_preserved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to export capabilities", "error": str(e)})


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
        if c.prerequisite_ids:
            try:
                prereq_list = json.loads(c.prerequisite_ids) if isinstance(c.prerequisite_ids, str) else c.prerequisite_ids
                if capability_id in prereq_list:
                    prereq_list = [pid for pid in prereq_list if pid != capability_id]
                    c.prerequisite_ids = json.dumps(prereq_list) if prereq_list else None
                    prereqs_cleaned += 1
            except:
                pass
    
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


@router.post("/capabilities/reorder")
def admin_reorder_capabilities(reorder_data: ReorderCapabilitiesRequest, db: Session = Depends(get_db)):
    """Reorder capabilities within a domain."""
    domain = reorder_data.domain
    capability_ids = reorder_data.capability_ids
    
    domain_caps = db.query(Capability).filter_by(domain=domain).all()
    domain_cap_ids = {c.id for c in domain_caps}
    
    provided_ids = set(capability_ids)
    if provided_ids != domain_cap_ids:
        missing = domain_cap_ids - provided_ids
        extra = provided_ids - domain_cap_ids
        errors = []
        if missing:
            errors.append(f"Missing capability IDs from domain: {list(missing)}")
        if extra:
            errors.append(f"Capability IDs not in domain '{domain}': {list(extra)}")
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    min_bit = min(c.bit_index for c in domain_caps if c.bit_index is not None)
    cap_by_id = {c.id: c for c in domain_caps}
    
    for i, cap_id in enumerate(capability_ids):
        cap_by_id[cap_id].bit_index = -(i + 1)
    db.flush()
    for i, cap_id in enumerate(capability_ids):
        cap_by_id[cap_id].bit_index = min_bit + i
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Reordered {len(capability_ids)} capabilities in domain '{domain}'",
        "domain": domain,
        "new_order": [{"id": cap_id, "bit_index": min_bit + i} for i, cap_id in enumerate(capability_ids)]
    }


@router.post("/domains/rename")
def admin_rename_domain(rename_data: RenameDomainRequest, db: Session = Depends(get_db)):
    """Rename a domain and re-sort capabilities."""
    old_name = rename_data.old_name.strip()
    new_name = rename_data.new_name.strip()
    
    if not new_name:
        raise HTTPException(status_code=400, detail="New domain name cannot be empty")
    
    caps_in_domain = db.query(Capability).filter_by(domain=old_name).all()
    if not caps_in_domain:
        raise HTTPException(status_code=404, detail=f"Domain '{old_name}' not found")
    
    if old_name.lower() != new_name.lower():
        existing = db.query(Capability).filter_by(domain=new_name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Domain '{new_name}' already exists")
    
    for cap in caps_in_domain:
        cap.domain = new_name
    
    all_caps = db.query(Capability).all()
    caps_by_domain = {}
    for cap in all_caps:
        if cap.domain not in caps_by_domain:
            caps_by_domain[cap.domain] = []
        caps_by_domain[cap.domain].append(cap)
    
    for domain in caps_by_domain:
        caps_by_domain[domain].sort(key=lambda c: c.bit_index)
    
    new_order = []
    for domain in sorted(caps_by_domain.keys()):
        new_order.extend(caps_by_domain[domain])
    
    for i, cap in enumerate(new_order):
        cap.bit_index = -(i + 1)
    db.flush()
    for i, cap in enumerate(new_order):
        cap.bit_index = i
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Renamed domain '{old_name}' to '{new_name}' ({len(caps_in_domain)} capabilities updated)",
        "old_name": old_name,
        "new_name": new_name,
        "capabilities_updated": len(caps_in_domain)
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
        
        prereq_ids_list = json.loads(cap.prerequisite_ids) if cap.prerequisite_ids else []
        prereq_names = []
        if prereq_ids_list:
            prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids_list)).all()
            prereq_map = {p.id: p for p in prereqs}
            prereq_names = [{"id": pid, "name": prereq_map[pid].name, "domain": prereq_map[pid].domain} for pid in prereq_ids_list if pid in prereq_map]
        
        soft_gate_reqs = None
        if cap.soft_gate_requirements:
            try:
                soft_gate_reqs = json.loads(cap.soft_gate_requirements) if isinstance(cap.soft_gate_requirements, str) else cap.soft_gate_requirements
            except:
                pass
        
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
