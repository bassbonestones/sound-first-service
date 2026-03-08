"""
Material management service.

Handles business logic for material upload, analysis, and reanalysis operations.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
import json

from sqlalchemy.orm import Session as DbSession

from app.models.core import Material
from app.models.capability_schema import Capability, MaterialCapability, MaterialAnalysis


@dataclass
class UploadResult:
    """Result from uploading a new material."""
    material_id: int
    title: str
    extracted_capabilities: List[str]
    range_analysis: Optional[Dict] = None
    chromatic_complexity: Optional[float] = None
    measure_count: Optional[int] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ReanalyzeResult:
    """Result from reanalyzing a material."""
    material_id: int
    title: str
    metrics_updated: List[str]
    capabilities_count: Optional[int] = None
    soft_gates: Optional[Dict] = None
    range_analysis: Optional[Dict] = None
    unified_scores: Optional[Dict] = None
    unified_scores_error: Optional[str] = None
    difficulty_scores: Optional[Dict] = None


@dataclass
class BatchReanalyzeResult:
    """Result from batch reanalysis."""
    total_materials: int
    materials_updated: int
    materials_failed: int
    errors: List[str] = field(default_factory=list)


class MaterialService:
    """Service for managing material operations."""
    
    @staticmethod
    def analyze_musicxml(musicxml_content: str):
        """Analyze MusicXML content and return extraction result."""
        from app.musicxml_analyzer import MusicXMLAnalyzer
        
        analyzer = MusicXMLAnalyzer()
        extraction_result = analyzer.analyze(musicxml_content)
        capability_names = analyzer.get_capability_names(extraction_result)
        return extraction_result, capability_names
    
    @classmethod
    def detect_all_capabilities(cls, musicxml_content: str, extraction_result=None) -> Set[str]:
        """Detect all capabilities using both legacy and registry-based detection."""
        from app.musicxml_analyzer import MusicXMLAnalyzer
        from app.capability_registry import CapabilityRegistry, DetectionEngine
        
        if extraction_result is None:
            analyzer = MusicXMLAnalyzer()
            extraction_result = analyzer.analyze(musicxml_content)
        
        # Legacy detection
        analyzer = MusicXMLAnalyzer()
        legacy_caps = analyzer.get_capability_names(extraction_result)
        
        # Registry-based detection
        registry = CapabilityRegistry()
        detection_engine = DetectionEngine(registry)
        detected_caps = detection_engine.detect_capabilities(extraction_result)
        
        return set(legacy_caps) | set(detected_caps)
    
    @classmethod
    def create_material_record(
        cls,
        db: DbSession,
        title: str,
        musicxml_content: str,
        original_key_center: Optional[str] = None,
        allowed_keys: Optional[List[str]] = None
    ) -> Material:
        """Create a new Material record."""
        if not allowed_keys:
            allowed_keys = ["C", "G", "F", "D", "Bb", "A", "Eb"]
        
        material = Material(
            title=title,
            musicxml_canonical=musicxml_content,
            original_key_center=original_key_center,
            allowed_keys=",".join(allowed_keys),
            pitch_reference_type="TONAL",
            spelling_policy="from_key",
        )
        db.add(material)
        db.flush()
        return material
    
    @classmethod
    def link_capabilities(
        cls,
        db: DbSession,
        material_id: int,
        capability_names: List[str]
    ) -> tuple[List[int], List[str]]:
        """
        Link capabilities to a material, creating new capabilities if needed.
        
        Returns (bit_indices, warnings)
        """
        warnings = []
        capability_bit_indices = []
        
        for cap_name in capability_names:
            cap = db.query(Capability).filter_by(name=cap_name).first()
            
            if not cap:
                # Create placeholder capability
                domain = cap_name.split("_")[0] if "_" in cap_name else "other"
                max_bit = db.query(db.func.max(Capability.bit_index)).scalar() or -1
                new_bit_index = max_bit + 1
                
                if new_bit_index >= 512:
                    warnings.append(f"Capability '{cap_name}' exceeds bitmask capacity")
                    new_bit_index = None
                
                cap = Capability(
                    name=cap_name,
                    display_name=cap_name.replace("_", " ").title(),
                    domain=domain,
                    bit_index=new_bit_index,
                )
                db.add(cap)
                db.flush()
            
            mat_cap = MaterialCapability(
                material_id=material_id,
                capability_id=cap.id,
                is_required=True,
            )
            db.add(mat_cap)
            
            if cap.bit_index is not None:
                capability_bit_indices.append(cap.bit_index)
        
        return capability_bit_indices, warnings
    
    @staticmethod
    def compute_and_store_bitmasks(material: Material, bit_indices: List[int]):
        """Compute capability bitmasks and store on material."""
        from app.musicxml_analyzer import compute_capability_bitmask
        
        masks = compute_capability_bitmask(bit_indices)
        material.req_cap_mask_0 = masks[0]
        material.req_cap_mask_1 = masks[1]
        material.req_cap_mask_2 = masks[2]
        material.req_cap_mask_3 = masks[3]
        material.req_cap_mask_4 = masks[4]
        material.req_cap_mask_5 = masks[5]
        material.req_cap_mask_6 = masks[6]
        material.req_cap_mask_7 = masks[7]
    
    @classmethod
    def create_material_analysis(
        cls,
        db: DbSession,
        material_id: int,
        extraction_result
    ) -> MaterialAnalysis:
        """Create MaterialAnalysis record from extraction result."""
        range_data = extraction_result.range_analysis
        
        analysis = MaterialAnalysis(
            material_id=material_id,
            lowest_pitch=range_data.lowest_pitch if range_data else None,
            highest_pitch=range_data.highest_pitch if range_data else None,
            range_semitones=range_data.range_semitones if range_data else None,
            pitch_density_low=range_data.density_low if range_data else None,
            pitch_density_mid=range_data.density_mid if range_data else None,
            pitch_density_high=range_data.density_high if range_data else None,
            trill_lowest=range_data.trill_lowest if range_data else None,
            trill_highest=range_data.trill_highest if range_data else None,
            chromatic_complexity=extraction_result.chromatic_complexity_score,
            tempo_marking=list(extraction_result.tempo_markings)[0] if extraction_result.tempo_markings else None,
            tempo_bpm=extraction_result.tempo_bpm,
            measure_count=extraction_result.measure_count,
            raw_extraction_json=json.dumps(extraction_result.to_dict()),
        )
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
        from app.musicxml_analyzer import compute_capability_bitmask
        
        # Clear existing links
        db.query(MaterialCapability).filter_by(material_id=material.id).delete()
        
        # Create new links
        capability_bit_indices = []
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
                    capability_bit_indices.append(cap.bit_index)
        
        # Update bitmasks
        cls.compute_and_store_bitmasks(material, capability_bit_indices)
        return len(capability_names)
    
    @classmethod
    def persist_unified_scores(
        cls,
        analysis: MaterialAnalysis,
        soft_gates,
        extraction_result
    ) -> Optional[Dict]:
        """
        Calculate and persist unified domain scores with composite difficulty.
        
        Returns the composite difficulty dict or None if failed.
        """
        from app.soft_gate_calculator import calculate_unified_domain_scores
        from app.difficulty_interactions import calculate_composite_difficulty
        
        try:
            # Build extraction dict for unified scoring
            extraction_dict = {
                'note_values': dict(extraction_result.note_values) if extraction_result.note_values else {},
                'tuplets': dict(extraction_result.tuplets) if extraction_result.tuplets else {},
                'dotted_notes': list(extraction_result.dotted_notes) if extraction_result.dotted_notes else [],
                'has_ties': extraction_result.has_ties,
            }
            if extraction_result.rhythm_pattern_analysis:
                extraction_dict['rhythm_measure_uniqueness_ratio'] = extraction_result.rhythm_pattern_analysis.rhythm_measure_uniqueness_ratio
                extraction_dict['rhythm_measure_repetition_ratio'] = extraction_result.rhythm_pattern_analysis.rhythm_measure_repetition_ratio
            
            tempo_profile_dict = extraction_result.tempo_profile.to_dict() if extraction_result.tempo_profile else None
            range_analysis_dict = extraction_result.range_analysis.__dict__ if extraction_result.range_analysis else None
            
            # Calculate unified domain scores
            domain_results = calculate_unified_domain_scores(
                metrics=soft_gates,
                tempo_profile=tempo_profile_dict,
                range_analysis=range_analysis_dict,
                extraction=extraction_dict,
            )
            
            # Persist JSON columns
            analysis.analysis_schema_version = 1
            analysis.interval_analysis_json = json.dumps(domain_results['interval'].to_dict()) if 'interval' in domain_results else None
            analysis.rhythm_analysis_json = json.dumps(domain_results['rhythm'].to_dict()) if 'rhythm' in domain_results else None
            analysis.tonal_analysis_json = json.dumps(domain_results['tonal'].to_dict()) if 'tonal' in domain_results else None
            analysis.tempo_analysis_json = json.dumps(domain_results['tempo'].to_dict()) if 'tempo' in domain_results else None
            analysis.range_analysis_json = json.dumps(domain_results['range'].to_dict()) if 'range' in domain_results else None
            analysis.throughput_analysis_json = json.dumps(domain_results['throughput'].to_dict()) if 'throughput' in domain_results else None
            
            # Persist indexed primary scores
            for domain in ['interval', 'rhythm', 'tonal', 'tempo', 'range', 'throughput']:
                if domain in domain_results and domain_results[domain].scores:
                    setattr(analysis, f'{domain}_primary_score', domain_results[domain].scores.get('primary'))
            
            # Compute and persist composite scores
            all_scores = {name: dr.scores for name, dr in domain_results.items()}
            composite = calculate_composite_difficulty(all_scores)
            analysis.overall_score = composite.get('overall')
            analysis.interaction_bonus = composite.get('interaction_bonus')
            
            return composite
        except Exception as e:
            raise e
    
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
            material_id=material.id,
            title=material.title,
            metrics_updated=[]
        )
        
        # Parse MusicXML once
        extraction_result, legacy_caps = cls.analyze_musicxml(material.musicxml_canonical)
        
        # Get or create MaterialAnalysis record
        analysis = db.query(MaterialAnalysis).filter_by(material_id=material.id).first()
        if not analysis:
            analysis = MaterialAnalysis(material_id=material.id)
            db.add(analysis)
        
        # Re-analyze capabilities
        if "capabilities" in metrics:
            all_cap_names = list(cls.detect_all_capabilities(
                material.musicxml_canonical, 
                extraction_result
            ))
            result.capabilities_count = cls.relink_capabilities(db, material, all_cap_names)
            metrics_updated.append("capabilities")
        
        # Re-analyze soft gates
        soft_gates = None
        if "soft_gates" in metrics:
            calculator = SoftGateCalculator()
            soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)
            result.soft_gates = cls.update_soft_gates(analysis, soft_gates)
            metrics_updated.append("soft_gates")
        
        # Persist unified scores
        if "unified_scores" in metrics or "soft_gates" in metrics:
            if soft_gates is None:
                calculator = SoftGateCalculator()
                soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)
            try:
                cls.persist_unified_scores(analysis, soft_gates, extraction_result)
                metrics_updated.append("unified_scores")
            except Exception as e:
                result.unified_scores_error = str(e)
        
        # Re-analyze range
        if "range" in metrics:
            result.range_analysis = cls.update_range_analysis(analysis, extraction_result)
            metrics_updated.append("range")
        
        # Store raw extraction data
        analysis.raw_extraction_json = json.dumps(extraction_result.to_dict())
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
    
    @classmethod 
    def update_soft_gates(cls, analysis: MaterialAnalysis, soft_gates) -> Dict:
        """Update MaterialAnalysis with soft gate metrics."""
        analysis.tonal_complexity_stage = soft_gates.tonal_complexity_stage
        analysis.interval_size_stage = soft_gates.interval_size_stage
        analysis.interval_sustained_stage = soft_gates.interval_sustained_stage
        analysis.interval_hazard_stage = soft_gates.interval_hazard_stage
        analysis.legacy_interval_size_stage = soft_gates.legacy_interval_size_stage
        
        if soft_gates.interval_profile:
            analysis.interval_step_ratio = soft_gates.interval_profile.step_ratio
            analysis.interval_skip_ratio = soft_gates.interval_profile.skip_ratio
            analysis.interval_leap_ratio = soft_gates.interval_profile.leap_ratio
            analysis.interval_large_leap_ratio = soft_gates.interval_profile.large_leap_ratio
            analysis.interval_extreme_leap_ratio = soft_gates.interval_profile.extreme_leap_ratio
            analysis.interval_p50 = soft_gates.interval_profile.interval_p50
            analysis.interval_p75 = soft_gates.interval_profile.interval_p75
            analysis.interval_p90 = soft_gates.interval_profile.interval_p90
        
        if soft_gates.interval_local_difficulty:
            analysis.interval_max_large_in_window = soft_gates.interval_local_difficulty.max_large_leaps_in_window
            analysis.interval_max_extreme_in_window = soft_gates.interval_local_difficulty.max_extreme_leaps_in_window
            analysis.interval_hardest_measures = json.dumps(soft_gates.interval_local_difficulty.hardest_measure_numbers)
        
        analysis.rhythm_complexity_stage = soft_gates.rhythm_complexity_score
        analysis.rhythm_complexity_peak = soft_gates.rhythm_complexity_peak
        analysis.rhythm_complexity_p95 = soft_gates.rhythm_complexity_p95
        analysis.range_usage_stage = soft_gates.range_usage_stage
        analysis.density_notes_per_second = soft_gates.density_notes_per_second
        analysis.note_density_per_measure = soft_gates.note_density_per_measure
        analysis.tempo_difficulty_score = soft_gates.tempo_difficulty_score
        analysis.interval_velocity_score = soft_gates.interval_velocity_score
        analysis.interval_velocity_peak = soft_gates.interval_velocity_peak
        analysis.interval_velocity_p95 = soft_gates.interval_velocity_p95
        analysis.unique_pitch_count = soft_gates.unique_pitch_count
        analysis.largest_interval_semitones = soft_gates.largest_interval_semitones
        
        return {
            "tonal_complexity_stage": soft_gates.tonal_complexity_stage,
            "interval_size_stage": soft_gates.interval_size_stage,
            "interval_sustained_stage": soft_gates.interval_sustained_stage,
            "interval_hazard_stage": soft_gates.interval_hazard_stage,
            "legacy_interval_size_stage": soft_gates.legacy_interval_size_stage,
            "rhythm_complexity_score": round(soft_gates.rhythm_complexity_score, 3),
            "rhythm_complexity_peak": round(soft_gates.rhythm_complexity_peak, 3) if soft_gates.rhythm_complexity_peak else None,
            "rhythm_complexity_p95": round(soft_gates.rhythm_complexity_p95, 3) if soft_gates.rhythm_complexity_p95 else None,
            "range_usage_stage": soft_gates.range_usage_stage,
            "density_notes_per_second": round(soft_gates.density_notes_per_second, 3),
            "tempo_difficulty_score": round(soft_gates.tempo_difficulty_score, 3) if soft_gates.tempo_difficulty_score else None,
            "interval_velocity_score": round(soft_gates.interval_velocity_score, 3),
        }
    
    @classmethod
    def update_unified_scores(cls, analysis: MaterialAnalysis, soft_gates) -> Dict:
        """Calculate and store unified domain scores."""
        from app.soft_gate_calculator import calculate_unified_domain_scores
        
        scores = calculate_unified_domain_scores(soft_gates)
        analysis.rhythm_domain_score = scores.rhythm_score
        analysis.interval_domain_score = scores.interval_score
        analysis.range_domain_score = scores.range_score
        analysis.throughput_domain_score = scores.throughput_score
        analysis.tonality_domain_score = scores.tonality_score
        
        return {
            "rhythm_domain_score": round(scores.rhythm_score, 2),
            "interval_domain_score": round(scores.interval_score, 2),
            "range_domain_score": round(scores.range_score, 2),
            "throughput_domain_score": round(scores.throughput_score, 2),
            "tonality_domain_score": round(scores.tonality_score, 2),
        }
    
    @classmethod
    def calculate_difficulty_scores(cls, analysis: MaterialAnalysis) -> Dict:
        """Calculate and store composite difficulty scores."""
        from app.difficulty_interactions import calculate_composite_difficulty
        
        diff = calculate_composite_difficulty(analysis)
        analysis.physical_difficulty = diff.physical_difficulty
        analysis.cognitive_difficulty = diff.cognitive_difficulty
        analysis.combined_difficulty = diff.combined_difficulty
        
        return {
            "physical_difficulty": round(diff.physical_difficulty, 2),
            "cognitive_difficulty": round(diff.cognitive_difficulty, 2),
            "combined_difficulty": round(diff.combined_difficulty, 2),
        }
    
    @classmethod
    def update_range_analysis(cls, analysis: MaterialAnalysis, extraction_result) -> Dict:
        """Update range analysis fields from extraction result."""
        range_data = extraction_result.range_analysis
        if not range_data:
            return {}
        
        analysis.lowest_pitch = range_data.lowest_pitch
        analysis.highest_pitch = range_data.highest_pitch
        analysis.range_semitones = range_data.range_semitones
        analysis.pitch_density_low = range_data.density_low
        analysis.pitch_density_mid = range_data.density_mid
        analysis.pitch_density_high = range_data.density_high
        analysis.trill_lowest = range_data.trill_lowest
        analysis.trill_highest = range_data.trill_highest
        
        return {
            "lowest_pitch": range_data.lowest_pitch,
            "highest_pitch": range_data.highest_pitch,
            "range_semitones": range_data.range_semitones,
        }


# Module-level singleton
_material_service = None


def get_material_service() -> MaterialService:
    """Get or create the material service singleton."""
    global _material_service
    if _material_service is None:
        _material_service = MaterialService()
    return _material_service
