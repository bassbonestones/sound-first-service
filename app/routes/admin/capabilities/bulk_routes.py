"""Bulk operation endpoints for capabilities (export, reorder, rename)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import datetime
import json
import os
import shutil

from app.db import get_db
from app.models.capability_schema import Capability

from .schemas import (
    ReorderCapabilitiesRequest, RenameDomainRequest,
    ExportResponse, ReorderResponse, RenameDomainResponse,
)
from .helpers import parse_json_field


router = APIRouter()


@router.post("/capabilities/export", response_model=ExportResponse)
def admin_export_capabilities(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Export all capabilities to capabilities.json.
    
    Preserves existing music21_detection rules from the current file.
    """
    capabilities = db.query(Capability).order_by(Capability.domain, Capability.bit_index, Capability.name).all()
    cap_id_to_name = {cap.id: cap.name for cap in capabilities}
    
    # Load existing detection rules to preserve them
    resources_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources")
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
        prereq_ids = parse_json_field(cap.prerequisite_ids, [])
        if prereq_ids:
            prereq_names = [cap_id_to_name[pid] for pid in prereq_ids if pid in cap_id_to_name]
        
        evidence_qualifier = parse_json_field(cap.evidence_qualifier_json, {})
        soft_gate_reqs = parse_json_field(cap.soft_gate_requirements)
        db_detection_rule = parse_json_field(cap.music21_detection_json)
        
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


@router.post("/capabilities/reorder", response_model=ReorderResponse)
def admin_reorder_capabilities(reorder_data: ReorderCapabilitiesRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
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


@router.post("/domains/rename", response_model=RenameDomainResponse)
def admin_rename_domain(rename_data: RenameDomainRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
