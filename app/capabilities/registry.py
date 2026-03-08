"""
Capability Registry for Sound First.

Manages capability detection rules loaded from capabilities.json.
Validates rules at startup and provides lookup functionality.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .types import DetectionRule, DetectionType
from .validation import validate_detection_rule

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    Registry for capability detection rules.
    
    Loads rules from capabilities.json, validates them at startup,
    and provides detection against MusicXML extraction results.
    """
    
    def __init__(self, capabilities_path: Optional[str] = None):
        """
        Initialize the registry.
        
        Args:
            capabilities_path: Path to capabilities.json. If None, uses default.
        """
        self.capabilities_path = capabilities_path or self._default_path()
        self.rules: Dict[str, DetectionRule] = {}
        self.capabilities_by_domain: Dict[str, List[str]] = {}
        self.capability_bit_index: Dict[str, int] = {}
        self._loaded = False
    
    def _default_path(self) -> str:
        """Get default path to capabilities.json."""
        base = Path(__file__).parent.parent.parent
        return str(base / "resources" / "capabilities.json")
    
    def load(self) -> Dict[str, List[str]]:
        """
        Load and validate all capability detection rules.
        
        Returns:
            Dict of validation issues: {"warnings": [...], "errors": [...]}
        """
        issues = {"warnings": [], "errors": []}
        
        try:
            with open(self.capabilities_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            issues["errors"].append(f"Failed to load capabilities.json: {e}")
            return issues
        
        capabilities = data.get("capabilities", [])
        
        for cap in capabilities:
            name = cap.get("name")
            if not name:
                issues["errors"].append(f"Capability missing 'name': {cap}")
                continue
            
            # Get detection rule (may be None/missing)
            detection_config = cap.get("music21_detection")
            
            # Validate the rule
            rule = validate_detection_rule(name, detection_config)
            self.rules[name] = rule
            
            # Track by domain
            domain = cap.get("domain", "unknown")
            if domain not in self.capabilities_by_domain:
                self.capabilities_by_domain[domain] = []
            self.capabilities_by_domain[domain].append(name)
            
            # Track bit_index for ordering
            bit_index = cap.get("bit_index")
            if bit_index is not None:
                self.capability_bit_index[name] = bit_index
            
            # Log validation issues
            if not rule.is_valid:
                for error in rule.validation_errors:
                    msg = f"Capability '{name}': {error}"
                    issues["warnings"].append(msg)
                    logger.warning(msg)
        
        self._loaded = True
        
        # Summary
        total = len(self.rules)
        detectable = sum(1 for r in self.rules.values() if r.detection_type is not None)
        invalid = sum(1 for r in self.rules.values() if not r.is_valid)
        
        logger.info(f"Loaded {total} capabilities: {detectable} detectable, {total - detectable} not auto-detectable, {invalid} invalid rules")
        
        return issues
    
    def get_rule(self, capability_name: str) -> Optional[DetectionRule]:
        """Get detection rule for a capability."""
        return self.rules.get(capability_name)
    
    def get_detectable_capabilities(self) -> List[str]:
        """Get list of capabilities that have valid detection rules."""
        return [
            name for name, rule in self.rules.items()
            if rule.detection_type is not None and rule.is_valid
        ]
    
    def get_capabilities_by_type(self, detection_type: DetectionType) -> List[str]:
        """Get capabilities using a specific detection type."""
        return [
            name for name, rule in self.rules.items()
            if rule.detection_type == detection_type and rule.is_valid
        ]
