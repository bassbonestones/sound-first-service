"""
Material Service

Main MaterialService class for material management operations.
"""

import json
from typing import List, Dict, Optional, Set, Tuple, Any

from sqlalchemy.orm import Session as DbSession

from app.models.core import Material
from app.models.capability_schema import Capability, MaterialCapability, MaterialAnalysis

from .models import UploadResult, ReanalyzeResult, BatchReanalyzeResult
from .updaters import (
    update_soft_gates,
    update_unified_scores,
    calculate_difficulty_scores,
    update_range_analysis,
    persist_unified_scores,
)


class MaterialService:
    """Service for managing material operations."""
    
    @staticmethod
    def analyze_musicxml(musicxml_content: str) -> Tuple[Any, Set[str]]:
        """Analyze MusicXML content and return extraction result."""
        from app.musicxml_analyzer import MusicXMLAnalyzer  # type: ignore[attr-defined]
        
        analyzer = MusicXMLAnalyzer()
        extraction_result = analyzer.analyze(musicxml_content)
        capability_names: Set[str] = set(analyzer.get_capability_names(extraction_result))
        return extraction_result, capability_names
    
    @classmethod
    def detect_all_capabilities(cls, musicxml_content: str, extraction_result: Any = None) -> Set[str]:
        """Detect all capabilities using both legacy and registry-based detection."""
        from app.musicxml_analyzer import MusicXMLAnalyzer  # type: ignore[attr-defined]
        from app.capability_registry import CapabilityRegistry, DetectionEngine
        
        if extraction_result is None:
            analyzer = MusicXMLAnalyzer()
            extraction_result = analyzer.analyze(musicxml_content)
        
        # Legacy detection
        analyzer = MusicXMLAnalyzer()
        legacy_caps: Set[str] = set(analyzer.get_capability_names(extraction_result))
        
        # Registry-based detection
        registry = CapabilityRegistry()
        detection_engine = DetectionEngine(registry)
        registry_caps: Set[str] = detection_engine.detect_all_capabilities(extraction_result)  # type: ignore[attr-defined]
        
        # Combine both sources
        return legacy_caps | registry_caps
    
    @classmethod
    def create_material_record(
        cls,
        db: DbSession,
        title: str,
        musicxml_content: str,
        tempo_bpm: Optional[int] = None,
        composer: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Material:
        """
        Create a new Material record (without capabilities).
        
        Returns the created Material.
        """
        material = Material(
            title=title,
            musicxml_canonical=musicxml_content,
            tempo_bpm=tempo_bpm,
            composer=composer,
            source=source,
        )
        db.add(material)
        db.flush()  # Get the ID
        return material
    
    @classmethod
    def link_capabilities(
        cls,
        db: DbSession,
        material: Material,
        capability_names: List[str],
    ) -> List[int]:
        """
        Link capabilities to a material.
        
        Returns list of bit indices for the linked capabilities.
        """
        capability_bit_indices: List[int] = []
        
        for cap_name in capability_names:
            cap = db.query(Capability).filter_by(name=cap_name).first()
            if cap:
                mat_cap = MaterialCapability(
                    material_id=material.id,
                    capability_id=cap.id,
                    is_required=True,
                )
                db.add(mat_cap)
                if cap.bit_index is not None:
                    capability_bit_indices.append(int(cap.bit_index))
        
        # Update bitmasks on material
        cls.compute_and_store_bitmasks(material, capability_bit_indices)
        
        return capability_bit_indices
    
    @staticmethod
    def compute_and_store_bitmasks(material: Material, bit_indices: List[int]) -> None:
        """
        Compute and store capability bitmasks on a Material.
        
        Uses the bit_indices of linked capabilities.
        """
        from app.musicxml_analyzer import compute_capability_bitmask  # type: ignore[attr-defined]
        
        if bit_indices:
            bitmask_int: int = compute_capability_bitmask(bit_indices)  # type: ignore[assignment]
            material.capability_bitmask_low = bitmask_int & ((1 << 64) - 1)  # type: ignore[attr-defined]
            material.capability_bitmask_high = bitmask_int >> 64  # type: ignore[attr-defined]
        else:
            material.capability_bitmask_low = 0  # type: ignore[attr-defined]
            material.capability_bitmask_high = 0  # type: ignore[attr-defined]
    
    @classmethod
    def create_material_analysis(
        cls,
        db: DbSession,
        material: Material,
        extraction_result: Any,
        soft_gates: Any = None,
    ) -> MaterialAnalysis:
        """
        Create initial MaterialAnalysis record for a material.
        
        Returns the created analysis.
        """
        analysis = MaterialAnalysis(
            material_id=material.id,
            raw_extraction_json=json.dumps(extraction_result.to_dict()),
            chromatic_complexity=extraction_result.chromatic_complexity_score,
            measure_count=extraction_result.measure_count,
            tempo_marking=list(extraction_result.tempo_markings)[0] if extraction_result.tempo_markings else None,
            tempo_bpm=extraction_result.tempo_bpm,
        )
        
        # Range analysis
        if extraction_result.range_analysis:
            ra = extraction_result.range_analysis
            analysis.lowest_pitch = ra.lowest_pitch
            analysis.highest_pitch = ra.highest_pitch
            analysis.range_semitones = ra.range_semitones
        
        # Soft gates if provided
        if soft_gates:
            update_soft_gates(analysis, soft_gates)
        
        db.add(analysis)
        return analysis
    
    @classmethod
    def relink_capabilities(
        cls,
        db: DbSession,
        material: Material,
        capability_names: List[str]
    ) -> int:
        """
        Clear and rebuild capability links for a material.
        
        Returns count of capabilities linked.
        """
        from app.musicxml_analyzer import compute_capability_bitmask  # type: ignore[attr-defined]
        
        # Clear existing links
        db.query(MaterialCapability).filter_by(material_id=material.id).delete()
        
        # Create new links
        capability_bit_indices: List[int] = []
        for cap_name in capability_names:
            cap = db.query(Capability).filter_by(name=cap_name).first()
            if cap:
                mat_cap = MaterialCapability(
                    material_id=material.id,
                    capability_id=cap.id,
                    is_required=True,
                )
                db.add(mat_cap)
                if cap.bit_index is not None:
                    capability_bit_indices.append(int(cap.bit_index))
        
        # Update bitmasks
        cls.compute_and_store_bitmasks(material, capability_bit_indices)
        return len(capability_names)
    
    @classmethod
    def persist_unified_scores(
        cls,
        analysis: MaterialAnalysis,
        soft_gates: Any,
        extraction_result: Any
    ) -> Optional[Dict[str, Any]]:
        """Calculate and persist unified domain scores with composite difficulty."""
        return persist_unified_scores(analysis, soft_gates, extraction_result)
    
    @classmethod
    def reanalyze_material(
        cls,
        db: DbSession,
        material: Material,
        metrics: Optional[List[str]] = None
    ) -> ReanalyzeResult:
        """
        Full reanalysis of a material with specified metrics.
        
        Args:
            db: Database session
            material: Material to reanalyze
            metrics: List of metrics to update (capabilities, soft_gates, range, unified_scores)
                    Defaults to all metrics if None.
        
        Returns:
            ReanalyzeResult with updated metrics info
        """
        from app.soft_gate_calculator import SoftGateCalculator
        
        if metrics is None:
            metrics = ["capabilities", "soft_gates", "range", "unified_scores"]
        
        metrics_updated = []
        result = ReanalyzeResult(
            material_id=material.id,  # type: ignore[arg-type]
            title=material.title,  # type: ignore[arg-type]
            metrics_updated=[]
        )
        
        # Parse MusicXML once
        extraction_result, legacy_caps = cls.analyze_musicxml(material.musicxml_canonical)  # type: ignore[arg-type]
        
        # Get or create MaterialAnalysis record
        analysis = db.query(MaterialAnalysis).filter_by(material_id=material.id).first()
        if not analysis:
            analysis = MaterialAnalysis(material_id=material.id)
            db.add(analysis)
        
        # Re-analyze capabilities
        if "capabilities" in metrics:
            all_cap_names = list(cls.detect_all_capabilities(
                material.musicxml_canonical,  # type: ignore[arg-type]
                extraction_result
            ))
            result.capabilities_count = cls.relink_capabilities(db, material, all_cap_names)
            metrics_updated.append("capabilities")
        
        # Re-analyze soft gates
        soft_gates = None
        if "soft_gates" in metrics:
            calculator = SoftGateCalculator()
            soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)  # type: ignore[arg-type]
            result.soft_gates = update_soft_gates(analysis, soft_gates)
            metrics_updated.append("soft_gates")
        
        # Persist unified scores
        if "unified_scores" in metrics or "soft_gates" in metrics:
            if soft_gates is None:
                calculator = SoftGateCalculator()
                soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)  # type: ignore[arg-type]
            try:
                cls.persist_unified_scores(analysis, soft_gates, extraction_result)
                metrics_updated.append("unified_scores")
            except Exception as e:
                result.unified_scores_error = str(e)
        
        # Re-analyze range
        if "range" in metrics:
            result.range_analysis = update_range_analysis(analysis, extraction_result)
            metrics_updated.append("range")
        
        # Store raw extraction data
        analysis.raw_extraction_json = json.dumps(extraction_result.to_dict())  # type: ignore[assignment]
        analysis.chromatic_complexity = extraction_result.chromatic_complexity_score
        analysis.measure_count = extraction_result.measure_count
        analysis.tempo_marking = list(extraction_result.tempo_markings)[0] if extraction_result.tempo_markings else None
        analysis.tempo_bpm = extraction_result.tempo_bpm
        
        result.metrics_updated = metrics_updated
        return result
    
    @classmethod
    def reanalyze_batch(
        cls,
        db: DbSession,
        materials: List[Material],
        metrics: Optional[List[str]] = None
    ) -> BatchReanalyzeResult:
        """
        Batch reanalyze multiple materials.
        
        Returns BatchReanalyzeResult with success/failure counts.
        """
        result = BatchReanalyzeResult(
            total_materials=len(materials),
            materials_updated=0,
            materials_failed=0
        )
        
        for material in materials:
            if not material.musicxml_canonical:
                result.errors.append(f"Material {material.id} has no MusicXML content")
                result.materials_failed += 1
                continue
            
            try:
                cls.reanalyze_material(db, material, metrics)
                result.materials_updated += 1
            except Exception as e:
                result.errors.append(f"Material {material.id}: {str(e)}")
                result.materials_failed += 1
        
        return result
    
    # Expose updater functions as class methods for backward compatibility
    @classmethod
    def update_soft_gates(cls, analysis: MaterialAnalysis, soft_gates: Any) -> Dict[str, Any]:
        """Update MaterialAnalysis with soft gate metrics."""
        return update_soft_gates(analysis, soft_gates)
    
    @classmethod
    def update_unified_scores(cls, analysis: MaterialAnalysis, soft_gates: Any) -> Dict[str, Any]:
        """Calculate and store unified domain scores."""
        return update_unified_scores(analysis, soft_gates)
    
    @classmethod
    def calculate_difficulty_scores(cls, analysis: MaterialAnalysis) -> Dict[str, Any]:
        """Calculate and store composite difficulty scores."""
        return calculate_difficulty_scores(analysis)
    
    @classmethod
    def update_range_analysis(cls, analysis: MaterialAnalysis, extraction_result: Any) -> Dict[str, Any]:
        """Update range analysis fields from extraction result."""
        return update_range_analysis(analysis, extraction_result)


# Module-level singleton
_material_service = None


def get_material_service() -> MaterialService:
    """Get or create the material service singleton."""
    global _material_service
    if _material_service is None:
        _material_service = MaterialService()
    return _material_service
