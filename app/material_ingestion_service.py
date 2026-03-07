"""
Material Ingestion Service for Sound First

Manages the material ingestion pipeline:
- Scans MusicXML files in resources/materials/
- Detects capabilities using CapabilityRegistry
- Computes soft gate metrics
- Syncs with materials.json
- Provides batch analysis APIs
"""

import json
import os
import shutil
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

try:
    from music21 import converter
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

from app.musicxml_analyzer import MusicXMLAnalyzer, ExtractionResult
from app.capability_registry import CapabilityRegistry, DetectionEngine
from app.soft_gate_calculator import SoftGateCalculator, SoftGateMetrics

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MaterialEntry:
    """Represents a material entry in materials.json."""
    title: str
    musicxml_file: str
    original_key_center: Optional[str] = None
    allowed_keys: str = ""
    required_capability_ids: str = ""
    scaffolding_capability_ids: str = ""
    pitch_reference_type: str = "TONAL"
    pitch_ref_json: str = "{}"
    spelling_policy: str = "from_key"
    
    # Analysis results (generated)
    detected_capabilities: List[str] = None
    soft_gates: Dict[str, Any] = None
    range_analysis: Dict[str, Any] = None


@dataclass
class IngestionResult:
    """Result of an ingestion run."""
    files_scanned: int
    files_analyzed: int
    files_skipped: int
    orphans_removed: int
    errors: List[str]
    analyzed_materials: List[str]


# =============================================================================
# MATERIAL INGESTION SERVICE
# =============================================================================

class MaterialIngestionService:
    """
    Service for batch material analysis and JSON management.
    
    Usage:
        service = MaterialIngestionService()
        result = service.ingest_batch(analyze_missing_only=True)
        service.export_to_json()
    """
    
    MATERIALS_DIR = Path(__file__).parent.parent / "resources" / "materials"
    
    def __init__(self, materials_dir: Optional[Path] = None):
        """
        Initialize the ingestion service.
        
        Args:
            materials_dir: Override default materials directory
        """
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for material ingestion")
        
        self.materials_dir = materials_dir or self.MATERIALS_DIR
        self.json_path = self.materials_dir / "materials.json"
        self.archive_dir = self.materials_dir / ".archive"
        
        # Initialize analyzers
        self.musicxml_analyzer = MusicXMLAnalyzer()
        self.capability_registry = CapabilityRegistry()
        self.detection_engine = DetectionEngine(self.capability_registry)
        self.soft_gate_calculator = SoftGateCalculator()
        
        # Load existing materials.json
        self.materials_data = self._load_materials_json()
    
    def _load_materials_json(self) -> Dict:
        """Load materials.json or create empty structure."""
        if self.json_path.exists():
            with self.json_path.open("r") as f:
                return json.load(f)
        return {"materials": [], "last_updated": None}
    
    def _save_materials_json(self, data: Dict):
        """Save materials.json with archive backup."""
        # Create archive if file exists
        if self.json_path.exists():
            self.archive_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = self.archive_dir / f"materials_{timestamp}.json"
            shutil.copy(self.json_path, archive_path)
            logger.info(f"Archived previous materials.json to {archive_path}")
        
        # Update timestamp and save
        data["last_updated"] = datetime.now().isoformat()
        with self.json_path.open("w") as f:
            json.dump(data, f, indent=2)
        
        self.materials_data = data
    
    def scan_musicxml_files(self) -> List[Path]:
        """
        Scan the materials directory for MusicXML files.
        
        Returns:
            List of MusicXML file paths
        """
        musicxml_files = []
        
        for root, dirs, files in os.walk(self.materials_dir):
            # Skip archive and hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'test']
            
            for file in files:
                if file.endswith('.musicxml') or file.endswith('.xml'):
                    musicxml_files.append(Path(root) / file)
        
        return musicxml_files
    
    def get_existing_entries(self) -> Dict[str, Dict]:
        """
        Get a map of musicxml_file -> material entry from JSON.
        
        Returns:
            Dict mapping filenames to their entry data
        """
        entries = {}
        for mat in self.materials_data.get("materials", []):
            if "musicxml_file" in mat:
                entries[mat["musicxml_file"]] = mat
        return entries
    
    def analyze_material(
        self,
        musicxml_path: Path,
        tempo_bpm: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single MusicXML file.
        
        Args:
            musicxml_path: Path to MusicXML file
            tempo_bpm: Override tempo BPM for soft gate calculations
            
        Returns:
            Dict with title, capabilities, soft_gates, range_analysis
        """
        with musicxml_path.open("r", encoding="utf-8") as f:
            content = f.read()
        
        # Basic extraction
        extraction_result = self.musicxml_analyzer.analyze(content)
        
        # Capability detection
        detected_capabilities = self.detection_engine.detect_capabilities(extraction_result)
        
        # Also include capabilities from the old mapping system
        legacy_capabilities = self.musicxml_analyzer.get_capability_names(extraction_result)
        all_capabilities = list(set(detected_capabilities) | set(legacy_capabilities))
        
        # Soft gate metrics
        soft_gates = self.soft_gate_calculator.calculate_from_musicxml(content, tempo_bpm)
        
        # Range analysis
        range_analysis = None
        if extraction_result.range_analysis:
            range_analysis = asdict(extraction_result.range_analysis)
        
        return {
            "title": extraction_result.title or musicxml_path.stem,
            "detected_capabilities": sorted(all_capabilities),
            "soft_gates": {
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
            },
            "range_analysis": range_analysis,
            "measure_count": extraction_result.measure_count,
            "tempo_bpm": extraction_result.tempo_bpm,
        }
    
    def ingest_batch(
        self,
        analyze_missing_only: bool = True,
        overwrite: bool = False,
        specific_files: Optional[List[str]] = None,
    ) -> IngestionResult:
        """
        Batch analyze MusicXML files and update materials.json.
        
        Args:
            analyze_missing_only: Only analyze files not in materials.json
            overwrite: Re-analyze all files even if present
            specific_files: Only analyze these specific files
            
        Returns:
            IngestionResult with summary
        """
        result = IngestionResult(
            files_scanned=0,
            files_analyzed=0,
            files_skipped=0,
            orphans_removed=0,
            errors=[],
            analyzed_materials=[],
        )
        
        # Scan for files
        musicxml_files = self.scan_musicxml_files()
        result.files_scanned = len(musicxml_files)
        
        # Get existing entries
        existing_entries = self.get_existing_entries()
        
        # Track files on disk
        files_on_disk = set()
        for path in musicxml_files:
            rel_path = str(path.relative_to(self.materials_dir))
            files_on_disk.add(rel_path)
        
        # Filter files to analyze
        files_to_analyze = []
        for path in musicxml_files:
            rel_path = str(path.relative_to(self.materials_dir))
            
            # Apply specific_files filter
            if specific_files and rel_path not in specific_files:
                continue
            
            # Check if should analyze
            if overwrite:
                files_to_analyze.append(path)
            elif analyze_missing_only and rel_path not in existing_entries:
                files_to_analyze.append(path)
            elif not analyze_missing_only:
                files_to_analyze.append(path)
            else:
                result.files_skipped += 1
        
        # Analyze files
        new_entries = []
        updated_entries = {}
        
        for path in files_to_analyze:
            rel_path = str(path.relative_to(self.materials_dir))
            
            try:
                analysis = self.analyze_material(path)
                
                # Create entry
                entry = {
                    "title": analysis["title"],
                    "musicxml_file": rel_path,
                    "detected_capabilities": analysis["detected_capabilities"],
                    "soft_gates": analysis["soft_gates"],
                    "range_analysis": analysis["range_analysis"],
                    "measure_count": analysis["measure_count"],
                    "tempo_bpm": analysis["tempo_bpm"],
                }
                
                # Preserve manual fields from existing entry
                if rel_path in existing_entries:
                    existing = existing_entries[rel_path]
                    for field in ["allowed_keys", "required_capability_ids", 
                                  "scaffolding_capability_ids", "original_key_center",
                                  "pitch_reference_type", "pitch_ref_json", "spelling_policy"]:
                        if field in existing:
                            entry[field] = existing[field]
                    updated_entries[rel_path] = entry
                else:
                    # Default values for new entries
                    entry.setdefault("allowed_keys", "C,G,F,D,Bb")
                    entry.setdefault("pitch_reference_type", "TONAL")
                    entry.setdefault("pitch_ref_json", "{}")
                    entry.setdefault("spelling_policy", "from_key")
                    new_entries.append(entry)
                
                result.files_analyzed += 1
                result.analyzed_materials.append(rel_path)
                logger.info(f"Analyzed: {rel_path}")
                
            except Exception as e:
                error_msg = f"Error analyzing {rel_path}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
        
        # Build final materials list
        final_materials = []
        
        for mat in self.materials_data.get("materials", []):
            rel_path = mat.get("musicxml_file")
            
            # Remove orphans (in JSON but not on disk)
            if rel_path and rel_path not in files_on_disk:
                result.orphans_removed += 1
                logger.info(f"Removed orphan: {rel_path}")
                continue
            
            # Use updated entry if available
            if rel_path in updated_entries:
                final_materials.append(updated_entries[rel_path])
            else:
                final_materials.append(mat)
        
        # Add new entries
        final_materials.extend(new_entries)
        
        # Save updated JSON
        self._save_materials_json({"materials": final_materials})
        
        logger.info(
            f"Ingestion complete: {result.files_analyzed} analyzed, "
            f"{result.files_skipped} skipped, {result.orphans_removed} orphans removed"
        )
        
        return result
    
    def export_to_json(self, output_path: Optional[Path] = None) -> Path:
        """
        Export current materials data to JSON.
        
        Args:
            output_path: Override default path
            
        Returns:
            Path to exported file
        """
        path = output_path or self.json_path
        self._save_materials_json(self.materials_data)
        return path
    
    def analyze_specific_metrics(
        self,
        metrics: List[str],
        file_filter: Optional[List[str]] = None,
    ) -> IngestionResult:
        """
        Re-analyze only specific metrics for materials.
        
        Args:
            metrics: List of metrics to recalculate ("capabilities", "soft_gates", etc.)
            file_filter: Only analyze these files
            
        Returns:
            IngestionResult
        """
        result = IngestionResult(
            files_scanned=0,
            files_analyzed=0,
            files_skipped=0,
            orphans_removed=0,
            errors=[],
            analyzed_materials=[],
        )
        
        materials = self.materials_data.get("materials", [])
        updated_materials = []
        
        for mat in materials:
            musicxml_file = mat.get("musicxml_file")
            
            if not musicxml_file:
                updated_materials.append(mat)
                continue
            
            # Apply filter
            if file_filter and musicxml_file not in file_filter:
                updated_materials.append(mat)
                result.files_skipped += 1
                continue
            
            result.files_scanned += 1
            
            # Load and analyze
            path = self.materials_dir / musicxml_file
            if not path.exists():
                result.errors.append(f"File not found: {musicxml_file}")
                continue
            
            try:
                with path.open("r", encoding="utf-8") as f:
                    content = f.read()
                
                if "capabilities" in metrics:
                    extraction = self.musicxml_analyzer.analyze(content)
                    detected = self.detection_engine.detect_capabilities(extraction)
                    legacy = self.musicxml_analyzer.get_capability_names(extraction)
                    mat["detected_capabilities"] = sorted(set(detected) | set(legacy))
                
                if "soft_gates" in metrics:
                    soft_gates = self.soft_gate_calculator.calculate_from_musicxml(content)
                    mat["soft_gates"] = {
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
                
                result.files_analyzed += 1
                result.analyzed_materials.append(musicxml_file)
                
            except Exception as e:
                result.errors.append(f"Error analyzing {musicxml_file}: {str(e)}")
            
            updated_materials.append(mat)
        
        self._save_materials_json({"materials": updated_materials})
        
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def ingest_materials(
    analyze_missing_only: bool = True,
    overwrite: bool = False,
) -> IngestionResult:
    """
    Convenience function for batch material ingestion.
    
    Args:
        analyze_missing_only: Only analyze new files
        overwrite: Re-analyze all files
        
    Returns:
        IngestionResult
    """
    service = MaterialIngestionService()
    return service.ingest_batch(analyze_missing_only, overwrite)


def export_materials_json() -> Path:
    """Export materials to JSON with archive backup."""
    service = MaterialIngestionService()
    return service.export_to_json()
