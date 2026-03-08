"""
Value Matchers

Utility functions for checking value conditions in detection rules.
"""

from typing import Any, Dict


def check_value_condition(item: Any, field_path: str, config: Dict) -> bool:
    """Check a single value condition against an item."""
    value = get_nested_value(item, field_path)
    
    if value is None:
        return False
    
    # Check conditions
    if "eq" in config:
        return value == config["eq"]
    if "contains" in config:
        return config["contains"].lower() in str(value).lower()
    if "gte" in config:
        return value >= config["gte"]
    if "lte" in config:
        return value <= config["lte"]
    
    return False


def get_nested_value(item: Any, field_path: str) -> Any:
    """Get value from item using dot-notation path."""
    if not field_path:
        return item
    
    parts = field_path.split(".")
    current = item
    
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
        
        if current is None:
            return None
    
    return current
