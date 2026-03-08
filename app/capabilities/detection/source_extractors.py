"""
Source Data Extractors

Extracts data from ExtractionResult for rule matching.
"""

from typing import Any, Dict, List


# Note type mappings for normalizing between music21 and detection rules
NOTE_TYPE_MAP = {
    "thirty_second": "32nd",
    "sixty_fourth": "64th",
    "16th": "sixteenth",  # music21 uses "16th", rules use "sixteenth"
}


def get_source_data(source: str, result) -> List[Any]:
    """Get source data from ExtractionResult as a list of items."""
    if source == "notes":
        return _extract_notes(result)
    elif source == "dynamics":
        return [{"value": d.replace("dynamic_", "")} for d in result.dynamics]
    elif source == "rests":
        return _extract_rests(result)
    elif source == "articulations":
        return [{"name": a.replace("articulation_", "")} for a in result.articulations]
    elif source == "ornaments":
        return [{"name": o.replace("ornament_", "")} for o in result.ornaments]
    elif source == "clefs":
        return [{"name": c.replace("clef_", "")} for c in result.clefs]
    elif source == "time_signatures":
        return _extract_time_signatures(result)
    elif source == "key_signatures":
        return [{"name": k} for k in result.key_signatures]
    elif source == "intervals":
        return _extract_intervals(result)
    return []


def _extract_notes(result) -> List[Dict]:
    """Extract note value info as pseudo-objects."""
    items = []
    
    for note_type, count in result.note_values.items():
        clean_type = note_type.replace("note_", "")
        normalized = NOTE_TYPE_MAP.get(clean_type, clean_type)
        items.append({"type": normalized, "count": count, "dots": 0})
    
    # Add dotted notes - provide BOTH formats to support different rule styles:
    # 1. Rules using type: "dotted_half" (basic dotted rhythm detection)
    # 2. Rules using type: "half" + dots >= 1 (compound conditions)
    for dotted in result.dotted_notes:
        # Add full name format (e.g., "dotted_half", "double_dotted_half")
        full_name = dotted
        for old, new in [("16th", "sixteenth"), ("32nd", "thirty_second")]:
            full_name = full_name.replace(old, new)
        items.append({"type": full_name, "dots": 1 if "double" not in dotted else 2})
        
        # Also add parsed format (e.g., type: "half", dots: 1)
        if dotted.startswith("double_dotted_"):
            base_type = dotted.replace("double_dotted_", "")
            normalized_base = NOTE_TYPE_MAP.get(base_type, base_type)
            items.append({"type": normalized_base, "dots": 2})
        elif dotted.startswith("dotted_"):
            base_type = dotted.replace("dotted_", "")
            normalized_base = NOTE_TYPE_MAP.get(base_type, base_type)
            items.append({"type": normalized_base, "dots": 1})
    
    return items


def _extract_rests(result) -> List[Dict]:
    """Extract rest value info."""
    items = []
    for rest_type, count in result.rest_values.items():
        clean_type = rest_type.replace("rest_", "")
        normalized = NOTE_TYPE_MAP.get(clean_type, clean_type)
        items.append({"type": normalized, "count": count})
    return items


def _extract_time_signatures(result) -> List[Dict]:
    """Extract time signature info."""
    items = []
    for ts in result.time_signatures:
        # Parse "time_sig_4_4" -> {"numerator": 4, "denominator": 4}
        parts = ts.replace("time_sig_", "").split("_")
        if len(parts) == 2:
            items.append({"numerator": int(parts[0]), "denominator": int(parts[1])})
    return items


def _extract_intervals(result) -> List[Dict]:
    """Extract interval info from melodic and harmonic intervals."""
    items = []
    
    for key, info in result.melodic_intervals.items():
        items.append({
            "name": info.name,
            "direction": info.direction,
            "semitones": info.semitones,
            "quality": info.quality,
            "is_melodic": True,
        })
    
    for key, info in result.harmonic_intervals.items():
        items.append({
            "name": info.name,
            "semitones": info.semitones,
            "quality": info.quality,
            "is_melodic": False,
        })
    
    return items
