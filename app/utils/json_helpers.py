"""JSON parsing utilities for the application."""

import json
from typing import Any, List, Union


def parse_focus_card_json_field(value: Any) -> Union[List, dict]:
    """Parse a JSON string field, returning empty structure if invalid.
    
    Args:
        value: A JSON string to parse, or None/empty string.
        
    Returns:
        The parsed JSON structure, or an empty list if parsing fails.
    """
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []
