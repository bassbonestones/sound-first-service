"""Analysis helpers for material ingestion."""
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

from app.musicxml_analyzer import MusicXMLAnalyzer, ExtractionResult
from app.capability_registry import CapabilityRegistry, DetectionEngine
from app.soft_gate_calculator import SoftGateCalculator, SoftGateMetrics


def format_soft_gates(soft_gates: SoftGateMetrics) -> Dict[str, Any]:
    """Format soft gate metrics for JSON output."""
    return {
        "tonal_complexity_stage": soft_gates.tonal_complexity_stage,
        "interval_size_stage": soft_gates.interval_size_stage,
        "rhythm_complexity_score": round(soft_gates.rhythm_complexity_score, 3),
        "range_usage_stage": soft_gates.range_usage_stage,
        "density_notes_per_second": round(soft_gates.density_notes_per_second, 3),
        "note_density_per_measure": round(soft_gates.note_density_per_measure, 3),
        "tempo_difficulty_score": round(soft_gates.tempo_difficulty_score, 3),
        "interval_velocity_score": round(soft_gates.interval_velocity_score, 3),
        "unique_pitch_count": soft_gates.unique_pitch_count,
        "largest_interval_semitones": soft_gates.largest_interval_semitones,
    }


def analyze_material(
    musicxml_path: Path,
    musicxml_analyzer: MusicXMLAnalyzer,
    detection_engine: DetectionEngine,
    soft_gate_calculator: SoftGateCalculator,
    tempo_bpm: Optional[int] = None
) -> Dict[str, Any]:
    """
    Analyze a single MusicXML file.
    
    Args:
        musicxml_path: Path to MusicXML file
        musicxml_analyzer: Analyzer instance
        detection_engine: Detection engine instance
        soft_gate_calculator: Soft gate calculator instance
        tempo_bpm: Override tempo BPM for soft gate calculations
        
    Returns:
        Dict with title, capabilities, soft_gates, range_analysis
    """
    with musicxml_path.open("r", encoding="utf-8") as f:
        content = f.read()
    
    # Basic extraction
    extraction_result = musicxml_analyzer.analyze(content)
    
    # Capability detection
    detected_capabilities = detection_engine.detect_capabilities(extraction_result)
    
    # Also include capabilities from the old mapping system
    legacy_capabilities = musicxml_analyzer.get_capability_names(extraction_result)
    all_capabilities = list(set(detected_capabilities) | set(legacy_capabilities))
    
    # Soft gate metrics
    soft_gates = soft_gate_calculator.calculate_from_musicxml(content, tempo_bpm)
    
    # Range analysis
    range_analysis = None
    if extraction_result.range_analysis:
        range_analysis = asdict(extraction_result.range_analysis)
    
    return {
        "title": extraction_result.title or musicxml_path.stem,
        "detected_capabilities": sorted(all_capabilities),
        "soft_gates": format_soft_gates(soft_gates),
        "range_analysis": range_analysis,
        "measure_count": extraction_result.measure_count,
        "tempo_bpm": extraction_result.tempo_bpm,
    }


def detect_all_capabilities(
    content: str,
    musicxml_analyzer: MusicXMLAnalyzer,
    detection_engine: DetectionEngine,
) -> List[str]:
    """
    Detect all capabilities from MusicXML content.
    
    Args:
        content: MusicXML content string
        musicxml_analyzer: Analyzer instance
        detection_engine: Detection engine instance
        
    Returns:
        Sorted list of capability names
    """
    extraction = musicxml_analyzer.analyze(content)
    detected = detection_engine.detect_capabilities(extraction)
    legacy = musicxml_analyzer.get_capability_names(extraction)
    return sorted(set(detected) | set(legacy))
