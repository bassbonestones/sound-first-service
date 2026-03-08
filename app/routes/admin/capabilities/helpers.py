"""Helper functions for capability admin endpoints."""
import json
from typing import List, Optional

from app.models.capability_schema import Capability


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


def parse_json_field(value, default=None):
    """Parse a JSON field that might be string or already parsed."""
    if value is None:
        return default
    try:
        return json.loads(value) if isinstance(value, str) else value
    except:
        return default


def parse_prerequisite_ids(cap) -> List[int]:
    """Parse prerequisite_ids from a Capability."""
    return parse_json_field(cap.prerequisite_ids, [])


def parse_soft_gate_requirements(cap):
    """Parse soft_gate_requirements from a Capability."""
    return parse_json_field(cap.soft_gate_requirements)


def parse_detection_rule(cap):
    """Parse music21_detection_json from a Capability."""
    return parse_json_field(cap.music21_detection_json)
