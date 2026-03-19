"""
Material Analysis Service for Sound First

Provides clean API for analyzing MusicXML content without database operations.
Used by routes/materials.py for preview analysis and other analysis endpoints.
"""

from typing import Dict, Any, List, Optional, Tuple, cast
from dataclasses import dataclass, field

from app.musicxml_analyzer import MusicXMLAnalyzer, ExtractionResult  # type: ignore[attr-defined]
from app.soft_gate_calculator import SoftGateCalculator, SoftGateMetrics
from app.capability_registry import CapabilityRegistry, DetectionEngine


@dataclass
class AnalysisResult:
    """Complete analysis result for a material."""
    title: str
    capabilities: List[str]
    capabilities_by_domain: Dict[str, List[str]]
    capability_count: int
    range_analysis: Optional[Dict[str, Any]]
    chromatic_complexity: Optional[float]
    measure_count: int
    tempo_bpm: Optional[int]
    tempo_marking: Optional[str]
    tempo_profile: Optional[Dict[str, Any]]
    soft_gates: Dict[str, Any]
    unified_scores: Dict[str, Any]
    detailed_extraction: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "capabilities": self.capabilities,
            "capabilities_by_domain": self.capabilities_by_domain,
            "capability_count": self.capability_count,
            "range_analysis": self.range_analysis,
            "chromatic_complexity": self.chromatic_complexity,
            "measure_count": self.measure_count,
            "tempo_bpm": self.tempo_bpm,
            "tempo_marking": self.tempo_marking,
            "tempo_profile": self.tempo_profile,
            "soft_gates": self.soft_gates,
            "unified_scores": self.unified_scores,
            "detailed_extraction": self.detailed_extraction,
        }


class MaterialAnalysisService:
    """Service for analyzing MusicXML content."""
    
    def __init__(self) -> None:
        self.analyzer = MusicXMLAnalyzer()
        self.soft_gate_calculator = SoftGateCalculator()
        self.registry: Optional[CapabilityRegistry] = None
        self.engine: Optional[DetectionEngine] = None
    
    def _ensure_registry_loaded(self) -> None:
        """Lazily load capability registry."""
        if self.registry is None:
            self.registry = CapabilityRegistry()
            self.registry.load()
            self.engine = DetectionEngine(self.registry)
    
    def analyze_musicxml(
        self, 
        musicxml_content: str, 
        title: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze MusicXML content and return complete analysis.
        
        Args:
            musicxml_content: Raw MusicXML string
            title: Optional title override
            
        Returns:
            AnalysisResult with all analysis data
        """
        # Basic analysis - get both result and score for custom detector use
        result, score = self.analyzer.analyze_with_score(musicxml_content)
        basic_capabilities = self.analyzer.get_capability_names(result)
        
        # Soft gate metrics
        soft_gate_data = self._compute_soft_gates(musicxml_content)
        
        # Capability detection via registry (pass score for custom detectors)
        detected_capabilities, capabilities_by_domain = self._detect_capabilities(
            result, basic_capabilities, score
        )
        
        # Unified scores
        metrics = None
        if "error" not in soft_gate_data:
            metrics = self.soft_gate_calculator.calculate_from_musicxml(musicxml_content)
        unified_scores = self._compute_unified_scores(result, metrics)
        
        return AnalysisResult(
            title=title or result.title or "Untitled",
            capabilities=detected_capabilities,
            capabilities_by_domain=capabilities_by_domain,
            capability_count=len(detected_capabilities),
            range_analysis=result.range_analysis.__dict__ if result.range_analysis else None,
            chromatic_complexity=result.chromatic_complexity_score,
            measure_count=result.measure_count,
            tempo_bpm=result.tempo_bpm,
            tempo_marking=list(result.tempo_markings)[0] if result.tempo_markings else None,
            tempo_profile=result.tempo_profile.to_dict() if result.tempo_profile else None,
            soft_gates=soft_gate_data,
            unified_scores=unified_scores,
            detailed_extraction=result.to_dict(),
        )
    
    def _compute_soft_gates(self, musicxml_content: str) -> Dict[str, Any]:
        """Compute soft gate metrics from MusicXML."""
        try:
            metrics = self.soft_gate_calculator.calculate_from_musicxml(musicxml_content)
            return {
                "tonal_complexity_stage": metrics.tonal_complexity_stage,
                "interval_size_stage": metrics.interval_size_stage,
                "interval_sustained_stage": metrics.interval_sustained_stage,
                "interval_hazard_stage": metrics.interval_hazard_stage,
                "legacy_interval_size_stage": metrics.legacy_interval_size_stage,
                "interval_profile": self._format_interval_profile(metrics),
                "interval_local_difficulty": self._format_interval_local_difficulty(metrics),
                "rhythm_complexity_score": round(metrics.rhythm_complexity_score, 3),
                "rhythm_complexity_peak": round(metrics.rhythm_complexity_peak, 3) if metrics.rhythm_complexity_peak is not None else None,
                "rhythm_complexity_p95": round(metrics.rhythm_complexity_p95, 3) if metrics.rhythm_complexity_p95 is not None else None,
                "range_usage_stage": metrics.range_usage_stage,
                "density_notes_per_second": round(metrics.density_notes_per_second, 2) if metrics.density_notes_per_second else None,
                "density_notes_per_measure": round(metrics.note_density_per_measure, 2) if metrics.note_density_per_measure else None,
                "interval_velocity_score": round(metrics.interval_velocity_score, 3),
                "interval_velocity_peak": round(metrics.interval_velocity_peak, 3) if metrics.interval_velocity_peak is not None else None,
                "interval_velocity_p95": round(metrics.interval_velocity_p95, 3) if metrics.interval_velocity_p95 is not None else None,
                "tempo_difficulty_score": round(metrics.tempo_difficulty_score, 3) if metrics.tempo_difficulty_score is not None else None,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _format_interval_profile(self, metrics: SoftGateMetrics) -> Optional[Dict[str, Any]]:
        """Format interval profile for response."""
        if not metrics.interval_profile:
            return None
        ip = metrics.interval_profile
        return {
            "total_intervals": ip.total_intervals,
            "step_ratio": round(ip.step_ratio, 3),
            "skip_ratio": round(ip.skip_ratio, 3),
            "leap_ratio": round(ip.leap_ratio, 3),
            "large_leap_ratio": round(ip.large_leap_ratio, 3),
            "extreme_leap_ratio": round(ip.extreme_leap_ratio, 3),
            "p50": ip.interval_p50,
            "p75": ip.interval_p75,
            "p90": ip.interval_p90,
            "max": ip.interval_max,
        }
    
    def _format_interval_local_difficulty(self, metrics: SoftGateMetrics) -> Optional[Dict[str, Any]]:
        """Format interval local difficulty for response."""
        if not metrics.interval_local_difficulty:
            return None
        ild = metrics.interval_local_difficulty
        return {
            "max_large_in_window": ild.max_large_leaps_in_window,
            "max_extreme_in_window": ild.max_extreme_leaps_in_window,
            "hardest_measures": ild.hardest_measure_numbers,
            "window_count": ild.window_count,
        }
    
    def _detect_capabilities(
        self, 
        result: ExtractionResult, 
        fallback_capabilities: List[str],
        score: Any = None
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """Detect capabilities using registry."""
        try:
            self._ensure_registry_loaded()
            if self.engine is None or self.registry is None:
                return fallback_capabilities, {"unknown": fallback_capabilities}
            detected_capabilities = list(self.engine.detect_capabilities(result, score))
            
            # Build domain lookup
            domain_lookup: Dict[str, str] = {}
            for domain, cap_names in self.registry.capabilities_by_domain.items():
                for cap_name in cap_names:
                    domain_lookup[cap_name] = domain
            
            # Group by domain
            capabilities_by_domain: Dict[str, List[str]] = {}
            for cap_name in detected_capabilities:
                domain = domain_lookup.get(cap_name, "unknown")
                if domain not in capabilities_by_domain:
                    capabilities_by_domain[domain] = []
                capabilities_by_domain[domain].append(cap_name)
            
            # Sort within domains
            for domain in capabilities_by_domain:
                capabilities_by_domain[domain].sort(
                    key=lambda c: self.registry.capability_bit_index.get(c, 9999) if self.registry else 9999
                )
            
            return detected_capabilities, capabilities_by_domain
        except Exception:
            return fallback_capabilities, {"unknown": fallback_capabilities}
    
    def _compute_unified_scores(
        self, 
        result: ExtractionResult, 
        metrics: Optional[SoftGateMetrics]
    ) -> Dict[str, Any]:
        """Compute unified domain scores."""
        try:
            from app.soft_gate_calculator import calculate_unified_domain_scores
            from app.difficulty_interactions import calculate_composite_difficulty
            
            if metrics is None:
                return {"error": "No metrics available"}
            
            # Build tempo profile dict
            tempo_profile_dict = None
            if result.tempo_profile:
                tempo_profile_dict = result.tempo_profile.to_dict()
            
            # Build range analysis dict
            range_analysis_dict = None
            if result.range_analysis:
                range_analysis_dict = result.range_analysis.__dict__
            
            # Build extraction dict
            extraction_dict = {
                'note_values': dict(result.note_values) if result.note_values else {},
                'tuplets': dict(result.tuplets) if result.tuplets else {},
                'dotted_notes': list(result.dotted_notes) if result.dotted_notes else [],
                'has_ties': result.has_ties,
            }
            if result.rhythm_pattern_analysis:
                extraction_dict['rhythm_measure_uniqueness_ratio'] = result.rhythm_pattern_analysis.rhythm_measure_uniqueness_ratio
                extraction_dict['rhythm_measure_repetition_ratio'] = result.rhythm_pattern_analysis.rhythm_measure_repetition_ratio
            
            # Compute domain results
            domain_results = calculate_unified_domain_scores(
                metrics=metrics,
                tempo_profile=tempo_profile_dict,
                range_analysis=range_analysis_dict,
                extraction=extraction_dict,
            )
            
            # Compute composite
            all_scores: Dict[str, Dict[str, float]] = {
                name: cast(Dict[str, float], dr.scores) 
                for name, dr in domain_results.items()
            }
            composite = calculate_composite_difficulty(all_scores)
            
            unified_scores = {name: dr.to_dict() for name, dr in domain_results.items()}
            unified_scores['composite'] = composite
            return unified_scores
            
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}


# Singleton instance for convenience
_analysis_service = None

def get_analysis_service() -> MaterialAnalysisService:
    """Get singleton analysis service instance."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = MaterialAnalysisService()
    return _analysis_service
