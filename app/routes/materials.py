"""Materials endpoints for upload, analysis, and ingestion."""
from fastapi import APIRouter, Depends, Body, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from app.db import get_db
from app.models.core import Material
from app.schemas import (
    MaterialUpload,
    MaterialAnalysisResponse,
    BatchIngestionRequest,
    BatchIngestionResponse,
    ReanalyzeRequest,
    ReanalyzeResponse,
    BatchReanalyzeRequest,
    BatchReanalyzeResponse,
)

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("")
def get_materials(db: Session = Depends(get_db)):
    """List all materials with basic info."""
    materials = db.query(Material).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "allowed_keys": m.allowed_keys.split(",") if m.allowed_keys else [],
            "original_key_center": m.original_key_center,
            "pitch_reference_type": m.pitch_reference_type
        }
        for m in materials
    ]


@router.post("/upload", response_model=MaterialAnalysisResponse)
def upload_material(
    data: MaterialUpload = Body(...),
    db: Session = Depends(get_db)
):
    """
    Upload a new material from MusicXML content.
    
    This endpoint:
    1. Parses the MusicXML using music21
    2. Extracts all musical capabilities (clefs, rhythms, intervals, etc.)
    3. Creates MaterialCapability records
    4. Creates MaterialAnalysis with range/density info
    5. Computes and stores bitmask for fast eligibility checking
    """
    from app.musicxml_analyzer import MusicXMLAnalyzer, compute_capability_bitmask
    from app.models.capability_schema import Capability, MaterialCapability, MaterialAnalysis
    
    warnings = []
    
    # Analyze the MusicXML
    try:
        analyzer = MusicXMLAnalyzer()
        extraction_result = analyzer.analyze(data.musicxml_content)
        capability_names = analyzer.get_capability_names(extraction_result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze MusicXML: {str(e)}")
    
    # Determine allowed keys
    allowed_keys = data.allowed_keys
    if not allowed_keys:
        # Default to common keys based on original key
        allowed_keys = ["C", "G", "F", "D", "Bb", "A", "Eb"]
    
    # Create the Material record
    material = Material(
        title=data.title or extraction_result.title or "Untitled",
        musicxml_canonical=data.musicxml_content,
        original_key_center=data.original_key_center,
        allowed_keys=",".join(allowed_keys),
        pitch_reference_type="TONAL",
        spelling_policy="from_key",
    )
    db.add(material)
    db.flush()  # Get the ID
    
    # Look up or create capabilities, then link to material
    capability_ids_for_bitmask = []
    
    for cap_name in capability_names:
        # Try to find existing capability
        cap = db.query(Capability).filter_by(name=cap_name).first()
        
        if not cap:
            # Capability doesn't exist - create a placeholder
            domain = cap_name.split("_")[0] if "_" in cap_name else "other"
            
            # Find next available bit_index
            max_bit = db.query(db.func.max(Capability.bit_index)).scalar() or -1
            new_bit_index = max_bit + 1
            
            if new_bit_index >= 512:
                warnings.append(f"Capability '{cap_name}' exceeds bitmask capacity, created without bit_index")
                new_bit_index = None
            
            cap = Capability(
                name=cap_name,
                display_name=cap_name.replace("_", " ").title(),
                domain=domain,
                bit_index=new_bit_index,
            )
            db.add(cap)
            db.flush()
        
        # Create MaterialCapability link
        mat_cap = MaterialCapability(
            material_id=material.id,
            capability_id=cap.id,
            is_required=True,  # Default to required
        )
        db.add(mat_cap)
        
        if cap.bit_index is not None:
            capability_ids_for_bitmask.append(cap.bit_index)
    
    # Compute and store bitmasks on the material
    masks = compute_capability_bitmask(capability_ids_for_bitmask)
    material.req_cap_mask_0 = masks[0]
    material.req_cap_mask_1 = masks[1]
    material.req_cap_mask_2 = masks[2]
    material.req_cap_mask_3 = masks[3]
    material.req_cap_mask_4 = masks[4]
    material.req_cap_mask_5 = masks[5]
    material.req_cap_mask_6 = masks[6]
    material.req_cap_mask_7 = masks[7]
    
    # Create MaterialAnalysis record
    range_data = extraction_result.range_analysis
    analysis = MaterialAnalysis(
        material_id=material.id,
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
    
    db.commit()
    
    return MaterialAnalysisResponse(
        material_id=material.id,
        title=material.title,
        extracted_capabilities=capability_names,
        range_analysis=range_data.__dict__ if range_data else None,
        chromatic_complexity=extraction_result.chromatic_complexity_score,
        measure_count=extraction_result.measure_count,
        warnings=warnings,
    )


@router.get("/{material_id}/analysis")
def get_material_analysis(material_id: int, db: Session = Depends(get_db)):
    """Get the analysis data for a material."""
    from app.models.capability_schema import MaterialAnalysis, MaterialCapability, Capability
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    analysis = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
    
    # Get linked capabilities
    mat_caps = db.query(MaterialCapability).filter_by(material_id=material_id).all()
    cap_ids = [mc.capability_id for mc in mat_caps]
    caps = db.query(Capability).filter(Capability.id.in_(cap_ids)).all() if cap_ids else []
    
    return {
        "material_id": material_id,
        "title": material.title,
        "capabilities": [
            {
                "id": c.id,
                "name": c.name,
                "display_name": c.display_name,
                "domain": c.domain,
            }
            for c in caps
        ],
        "analysis": {
            "lowest_pitch": analysis.lowest_pitch if analysis else None,
            "highest_pitch": analysis.highest_pitch if analysis else None,
            "range_semitones": analysis.range_semitones if analysis else None,
            "pitch_density": {
                "low": analysis.pitch_density_low,
                "mid": analysis.pitch_density_mid,
                "high": analysis.pitch_density_high,
            } if analysis else None,
            "chromatic_complexity": analysis.chromatic_complexity if analysis else None,
            "tempo_marking": analysis.tempo_marking if analysis else None,
            "tempo_bpm": analysis.tempo_bpm if analysis else None,
            "measure_count": analysis.measure_count if analysis else None,
        } if analysis else None,
    }


@router.post("/analyze")
def analyze_material_preview(data: MaterialUpload = Body(...)):
    """
    Preview material analysis without saving to database.
    
    Returns full analysis including:
    - Extracted capabilities
    - Range analysis
    - Soft gate metrics (D1-D5, IVS, tempo difficulty)
    - Unified scores (new schema: profile -> facet_scores -> scores -> bands)
    
    Useful for previewing a material before committing to the database.
    """
    from app.musicxml_analyzer import MusicXMLAnalyzer
    from app.soft_gate_calculator import SoftGateCalculator
    from app.capability_registry import CapabilityRegistry, DetectionEngine
    
    try:
        # Basic analysis
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(data.musicxml_content)
        capabilities = analyzer.get_capability_names(result)
        
        # Soft gate metrics
        soft_gate_data = {}
        try:
            calculator = SoftGateCalculator()
            metrics = calculator.calculate_from_musicxml(data.musicxml_content)
            soft_gate_data = {
                "tonal_complexity_stage": metrics.tonal_complexity_stage,
                "interval_size_stage": metrics.interval_size_stage,  # DEPRECATED
                # NEW: Interval profile stages
                "interval_sustained_stage": metrics.interval_sustained_stage,
                "interval_hazard_stage": metrics.interval_hazard_stage,
                "legacy_interval_size_stage": metrics.legacy_interval_size_stage,
                # Interval profile data
                "interval_profile": {
                    "total_intervals": metrics.interval_profile.total_intervals if metrics.interval_profile else 0,
                    "step_ratio": round(metrics.interval_profile.step_ratio, 3) if metrics.interval_profile else 0,
                    "skip_ratio": round(metrics.interval_profile.skip_ratio, 3) if metrics.interval_profile else 0,
                    "leap_ratio": round(metrics.interval_profile.leap_ratio, 3) if metrics.interval_profile else 0,
                    "large_leap_ratio": round(metrics.interval_profile.large_leap_ratio, 3) if metrics.interval_profile else 0,
                    "extreme_leap_ratio": round(metrics.interval_profile.extreme_leap_ratio, 3) if metrics.interval_profile else 0,
                    "p50": metrics.interval_profile.interval_p50 if metrics.interval_profile else 0,
                    "p75": metrics.interval_profile.interval_p75 if metrics.interval_profile else 0,
                    "p90": metrics.interval_profile.interval_p90 if metrics.interval_profile else 0,
                    "max": metrics.interval_profile.interval_max if metrics.interval_profile else 0,
                } if metrics.interval_profile else None,
                "interval_local_difficulty": {
                    "max_large_in_window": metrics.interval_local_difficulty.max_large_leaps_in_window,
                    "max_extreme_in_window": metrics.interval_local_difficulty.max_extreme_leaps_in_window,
                    "hardest_measures": metrics.interval_local_difficulty.hardest_measure_numbers,
                    "window_count": metrics.interval_local_difficulty.window_count,
                } if metrics.interval_local_difficulty else None,
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
            soft_gate_data = {"error": str(e)}
        
        # Enhanced capability detection via registry
        detected_capabilities = []
        capabilities_by_domain = {}
        try:
            registry = CapabilityRegistry()
            registry.load()
            engine = DetectionEngine(registry)
            detected_capabilities = list(engine.detect_capabilities(result))
            
            # Build domain lookup from registry (domain -> [cap_names])
            # Invert it to get cap_name -> domain
            domain_lookup = {}
            for domain, cap_names in registry.capabilities_by_domain.items():
                for cap_name in cap_names:
                    domain_lookup[cap_name] = domain
            
            # Group detected capabilities by domain
            for cap_name in detected_capabilities:
                domain = domain_lookup.get(cap_name, "unknown")
                if domain not in capabilities_by_domain:
                    capabilities_by_domain[domain] = []
                capabilities_by_domain[domain].append(cap_name)
            
            # Sort capabilities within each domain by bit_index
            for domain in capabilities_by_domain:
                capabilities_by_domain[domain].sort(
                    key=lambda c: registry.capability_bit_index.get(c, 9999)
                )
        except Exception as e:
            detected_capabilities = capabilities  # Fallback to basic detection
            capabilities_by_domain = {"unknown": detected_capabilities}
        
        # Build tempo response (new profile + legacy fields)
        tempo_response = {
            # LEGACY: Use tempo_profile for new code
            "tempo_bpm": result.tempo_bpm,
            "tempo_marking": list(result.tempo_markings)[0] if result.tempo_markings else None,
        }
        if result.tempo_profile:
            tempo_response["tempo_profile"] = result.tempo_profile.to_dict()
        
        # =================================================================
        # UNIFIED SCORES (Facet-Aware Architecture)
        # =================================================================
        unified_scores = {}
        try:
            from app.soft_gate_calculator import calculate_unified_domain_scores
            from app.difficulty_interactions import calculate_composite_difficulty
            
            # Build tempo profile dict
            tempo_profile_dict = None
            if result.tempo_profile:
                tempo_profile_dict = result.tempo_profile.to_dict()
            
            # Build range analysis dict
            range_analysis_dict = None
            if result.range_analysis:
                range_analysis_dict = result.range_analysis.__dict__
            
            # Build extraction dict with note values and other details
            extraction_dict = {
                'note_values': dict(result.note_values) if result.note_values else {},
                'tuplets': dict(result.tuplets) if result.tuplets else {},
                'dotted_notes': list(result.dotted_notes) if result.dotted_notes else [],
                'has_ties': result.has_ties,
            }
            if result.rhythm_pattern_analysis:
                extraction_dict['rhythm_measure_uniqueness_ratio'] = result.rhythm_pattern_analysis.rhythm_measure_uniqueness_ratio
                extraction_dict['rhythm_measure_repetition_ratio'] = result.rhythm_pattern_analysis.rhythm_measure_repetition_ratio
            
            # Compute domain results using unified scoring
            domain_results = calculate_unified_domain_scores(
                metrics=metrics,
                tempo_profile=tempo_profile_dict,
                range_analysis=range_analysis_dict,
                extraction=extraction_dict,
            )
            
            # Compute composite difficulty
            all_scores = {
                name: dr.scores for name, dr in domain_results.items()
            }
            composite = calculate_composite_difficulty(all_scores)
            
            unified_scores = {
                name: dr.to_dict() for name, dr in domain_results.items()
            }
            unified_scores['composite'] = composite
            
        except Exception as e:
            import traceback
            unified_scores = {"error": str(e), "traceback": traceback.format_exc()}
        
        return {
            "title": result.title or data.title,
            "capabilities": detected_capabilities,
            "capabilities_by_domain": capabilities_by_domain,
            "capability_count": len(detected_capabilities),
            "range_analysis": result.range_analysis.__dict__ if result.range_analysis else None,
            "chromatic_complexity": result.chromatic_complexity_score,
            "measure_count": result.measure_count,
            "tempo_bpm": result.tempo_bpm,  # LEGACY: Use tempo_profile.effective_bpm
            "tempo_marking": list(result.tempo_markings)[0] if result.tempo_markings else None,
            "tempo_profile": result.tempo_profile.to_dict() if result.tempo_profile else None,
            "soft_gates": soft_gate_data,
            "unified_scores": unified_scores,
            "detailed_extraction": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")


@router.post("/ingest-batch", response_model=BatchIngestionResponse)
def ingest_materials_batch(
    data: BatchIngestionRequest = Body(...)
):
    """
    Batch analyze MusicXML files and update materials.json.
    
    Behaviors:
    - Scans resources/materials/*.musicxml
    - Compares against materials.json
    - analyze_missing_only=true (default): only analyzes new files
    - overwrite=true: re-analyzes all files
    - Removes orphaned JSON entries (file no longer exists)
    - If specific_metrics provided, only recalculates those metrics
    """
    from app.material_ingestion_service import MaterialIngestionService
    
    try:
        service = MaterialIngestionService()
        
        if data.specific_metrics:
            result = service.analyze_specific_metrics(
                metrics=data.specific_metrics,
                file_filter=data.specific_files,
            )
        else:
            result = service.ingest_batch(
                analyze_missing_only=data.analyze_missing_only,
                overwrite=data.overwrite,
                specific_files=data.specific_files,
            )
        
        return BatchIngestionResponse(
            files_scanned=result.files_scanned,
            files_analyzed=result.files_analyzed,
            files_skipped=result.files_skipped,
            orphans_removed=result.orphans_removed,
            errors=result.errors,
            analyzed_materials=result.analyzed_materials,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/export-json")
def export_materials_to_json():
    """
    Export current materials data to materials.json.
    
    Archives the previous version before overwriting.
    """
    from app.material_ingestion_service import MaterialIngestionService
    
    try:
        service = MaterialIngestionService()
        path = service.export_to_json()
        return {"message": "Materials exported", "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/{material_id}/reanalyze", response_model=ReanalyzeResponse)
def reanalyze_single_material(
    material_id: int,
    data: ReanalyzeRequest = Body(default=ReanalyzeRequest()),
    db: Session = Depends(get_db)
):
    """
    Re-analyze a single material and update its analysis data.
    
    Args:
        material_id: Material to re-analyze
        metrics: Optional list of specific metrics to update:
            - "capabilities": Re-detect capabilities
            - "soft_gates": Recalculate soft gate metrics
            - "range": Recalculate range analysis
            - If None, updates all metrics
    """
    from app.musicxml_analyzer import MusicXMLAnalyzer, compute_capability_bitmask
    from app.capability_registry import CapabilityRegistry, DetectionEngine
    from app.soft_gate_calculator import SoftGateCalculator, calculate_unified_domain_scores
    from app.difficulty_interactions import calculate_composite_difficulty
    from app.models.capability_schema import Capability, MaterialCapability, MaterialAnalysis
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not material.musicxml_canonical:
        raise HTTPException(status_code=400, detail="Material has no MusicXML content")
    
    # Determine which metrics to update
    metrics = data.metrics or ["capabilities", "soft_gates", "range", "unified_scores"]
    metrics_updated = []
    
    # Initialize analyzers as needed
    analyzer = MusicXMLAnalyzer()
    extraction_result = analyzer.analyze(material.musicxml_canonical)
    
    # Get or create MaterialAnalysis record
    analysis = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
    if not analysis:
        analysis = MaterialAnalysis(material_id=material_id)
        db.add(analysis)
    
    result_data = {
        "material_id": material_id,
        "title": material.title,
        "metrics_updated": [],
    }
    
    # Re-analyze capabilities
    if "capabilities" in metrics:
        registry = CapabilityRegistry()
        detection_engine = DetectionEngine(registry)
        
        # Detect capabilities
        detected_caps = detection_engine.detect_capabilities(extraction_result)
        legacy_caps = analyzer.get_capability_names(extraction_result)
        all_cap_names = list(set(detected_caps) | set(legacy_caps))
        
        # Clear existing MaterialCapability links
        db.query(MaterialCapability).filter_by(material_id=material_id).delete()
        
        # Create new links
        capability_ids_for_bitmask = []
        for cap_name in all_cap_names:
            cap = db.query(Capability).filter_by(name=cap_name).first()
            if cap:
                mat_cap = MaterialCapability(
                    material_id=material_id,
                    capability_id=cap.id,
                    is_required=True,
                )
                db.add(mat_cap)
                if cap.bit_index is not None:
                    capability_ids_for_bitmask.append(cap.bit_index)
        
        # Update bitmasks
        masks = compute_capability_bitmask(capability_ids_for_bitmask)
        material.req_cap_mask_0 = masks[0]
        material.req_cap_mask_1 = masks[1]
        material.req_cap_mask_2 = masks[2]
        material.req_cap_mask_3 = masks[3]
        material.req_cap_mask_4 = masks[4]
        material.req_cap_mask_5 = masks[5]
        material.req_cap_mask_6 = masks[6]
        material.req_cap_mask_7 = masks[7]
        
        result_data["capabilities_count"] = len(all_cap_names)
        metrics_updated.append("capabilities")
    
    # Re-analyze soft gates
    soft_gates = None
    if "soft_gates" in metrics:
        calculator = SoftGateCalculator()
        soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)
        
        # Update analysis record
        analysis.tonal_complexity_stage = soft_gates.tonal_complexity_stage
        analysis.interval_size_stage = soft_gates.interval_size_stage  # DEPRECATED
        # NEW: Interval profile stages
        analysis.interval_sustained_stage = soft_gates.interval_sustained_stage
        analysis.interval_hazard_stage = soft_gates.interval_hazard_stage
        analysis.legacy_interval_size_stage = soft_gates.legacy_interval_size_stage
        # Interval profile data
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
        
        result_data["soft_gates"] = {
            "tonal_complexity_stage": soft_gates.tonal_complexity_stage,
            "interval_size_stage": soft_gates.interval_size_stage,  # DEPRECATED
            # NEW: Interval profile stages
            "interval_sustained_stage": soft_gates.interval_sustained_stage,
            "interval_hazard_stage": soft_gates.interval_hazard_stage,
            "legacy_interval_size_stage": soft_gates.legacy_interval_size_stage,
            "rhythm_complexity_score": round(soft_gates.rhythm_complexity_score, 3),
            "rhythm_complexity_peak": round(soft_gates.rhythm_complexity_peak, 3) if soft_gates.rhythm_complexity_peak is not None else None,
            "rhythm_complexity_p95": round(soft_gates.rhythm_complexity_p95, 3) if soft_gates.rhythm_complexity_p95 is not None else None,
            "range_usage_stage": soft_gates.range_usage_stage,
            "density_notes_per_second": round(soft_gates.density_notes_per_second, 3),
            "tempo_difficulty_score": round(soft_gates.tempo_difficulty_score, 3) if soft_gates.tempo_difficulty_score is not None else None,
            "interval_velocity_score": round(soft_gates.interval_velocity_score, 3),
            "interval_velocity_peak": round(soft_gates.interval_velocity_peak, 3) if soft_gates.interval_velocity_peak is not None else None,
            "interval_velocity_p95": round(soft_gates.interval_velocity_p95, 3) if soft_gates.interval_velocity_p95 is not None else None,
        }
        metrics_updated.append("soft_gates")
    
    # Persist unified scores (Phase 4)
    if "unified_scores" in metrics or "soft_gates" in metrics:
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
            
            # Build inputs for calculate_unified_domain_scores
            tempo_profile_dict = extraction_result.tempo_profile.to_dict() if extraction_result.tempo_profile else None
            range_analysis_dict = extraction_result.range_analysis.__dict__ if extraction_result.range_analysis else None
            
            # Need soft_gates for unified scoring
            if soft_gates is None:
                calculator = SoftGateCalculator()
                soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)
            
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
            analysis.interval_primary_score = domain_results['interval'].scores.get('primary') if 'interval' in domain_results and domain_results['interval'].scores else None
            analysis.rhythm_primary_score = domain_results['rhythm'].scores.get('primary') if 'rhythm' in domain_results and domain_results['rhythm'].scores else None
            analysis.tonal_primary_score = domain_results['tonal'].scores.get('primary') if 'tonal' in domain_results and domain_results['tonal'].scores else None
            analysis.tempo_primary_score = domain_results['tempo'].scores.get('primary') if 'tempo' in domain_results and domain_results['tempo'].scores else None
            analysis.range_primary_score = domain_results['range'].scores.get('primary') if 'range' in domain_results and domain_results['range'].scores else None
            analysis.throughput_primary_score = domain_results['throughput'].scores.get('primary') if 'throughput' in domain_results and domain_results['throughput'].scores else None
            
            # Compute and persist composite scores
            all_scores = {name: dr.scores for name, dr in domain_results.items()}
            composite = calculate_composite_difficulty(all_scores)
            analysis.overall_score = composite.get('overall')
            analysis.interaction_bonus = composite.get('interaction_bonus')
            
            metrics_updated.append("unified_scores")
        except Exception as e:
            # Don't fail the whole reanalyze if unified scores fail
            import traceback
            result_data["unified_scores_error"] = str(e)
    
    # Re-analyze range
    if "range" in metrics:
        range_data = extraction_result.range_analysis
        if range_data:
            analysis.lowest_pitch = range_data.lowest_pitch
            analysis.highest_pitch = range_data.highest_pitch
            analysis.range_semitones = range_data.range_semitones
            analysis.pitch_density_low = range_data.density_low
            analysis.pitch_density_mid = range_data.density_mid
            analysis.pitch_density_high = range_data.density_high
            analysis.trill_lowest = range_data.trill_lowest
            analysis.trill_highest = range_data.trill_highest
            
            result_data["range_analysis"] = {
                "lowest_pitch": range_data.lowest_pitch,
                "highest_pitch": range_data.highest_pitch,
                "range_semitones": range_data.range_semitones,
            }
        metrics_updated.append("range")
    
    # Store raw extraction
    analysis.raw_extraction_json = json.dumps(extraction_result.to_dict())
    analysis.chromatic_complexity = extraction_result.chromatic_complexity_score
    analysis.measure_count = extraction_result.measure_count
    analysis.tempo_marking = list(extraction_result.tempo_markings)[0] if extraction_result.tempo_markings else None
    analysis.tempo_bpm = extraction_result.tempo_bpm
    
    db.commit()
    
    result_data["metrics_updated"] = metrics_updated
    return ReanalyzeResponse(**result_data)


@router.post("/reanalyze-all", response_model=BatchReanalyzeResponse)
def reanalyze_all_materials(
    data: BatchReanalyzeRequest = Body(default=BatchReanalyzeRequest()),
    db: Session = Depends(get_db)
):
    """
    Re-analyze multiple materials in batch.
    
    Args:
        metrics: Specific metrics to update (capabilities, soft_gates, range)
        material_ids: Specific materials to update (None = all)
    """
    from app.musicxml_analyzer import MusicXMLAnalyzer, compute_capability_bitmask
    from app.capability_registry import CapabilityRegistry, DetectionEngine
    from app.soft_gate_calculator import SoftGateCalculator, calculate_unified_domain_scores
    from app.difficulty_interactions import calculate_composite_difficulty
    from app.models.capability_schema import Capability, MaterialCapability, MaterialAnalysis
    
    # Get materials to process
    query = db.query(Material)
    if data.material_ids:
        query = query.filter(Material.id.in_(data.material_ids))
    
    materials = query.all()
    
    metrics = data.metrics or ["capabilities", "soft_gates", "range"]
    
    # Initialize analyzers once
    analyzer = MusicXMLAnalyzer()
    registry = CapabilityRegistry() if "capabilities" in metrics else None
    detection_engine = DetectionEngine(registry) if registry else None
    calculator = SoftGateCalculator() if "soft_gates" in metrics else None
    
    result = {
        "total_materials": len(materials),
        "materials_updated": 0,
        "materials_failed": 0,
        "errors": [],
    }
    
    for material in materials:
        if not material.musicxml_canonical:
            result["errors"].append(f"Material {material.id} has no MusicXML content")
            result["materials_failed"] += 1
            continue
        
        try:
            extraction_result = analyzer.analyze(material.musicxml_canonical)
            
            # Get or create analysis record
            analysis = db.query(MaterialAnalysis).filter_by(material_id=material.id).first()
            if not analysis:
                analysis = MaterialAnalysis(material_id=material.id)
                db.add(analysis)
            
            if "capabilities" in metrics and detection_engine:
                detected_caps = detection_engine.detect_capabilities(extraction_result)
                legacy_caps = analyzer.get_capability_names(extraction_result)
                all_cap_names = list(set(detected_caps) | set(legacy_caps))
                
                db.query(MaterialCapability).filter_by(material_id=material.id).delete()
                
                capability_ids_for_bitmask = []
                for cap_name in all_cap_names:
                    cap = db.query(Capability).filter_by(name=cap_name).first()
                    if cap:
                        mat_cap = MaterialCapability(
                            material_id=material.id,
                            capability_id=cap.id,
                            is_required=True,
                        )
                        db.add(mat_cap)
                        if cap.bit_index is not None:
                            capability_ids_for_bitmask.append(cap.bit_index)
                
                masks = compute_capability_bitmask(capability_ids_for_bitmask)
                material.req_cap_mask_0 = masks[0]
                material.req_cap_mask_1 = masks[1]
                material.req_cap_mask_2 = masks[2]
                material.req_cap_mask_3 = masks[3]
                material.req_cap_mask_4 = masks[4]
                material.req_cap_mask_5 = masks[5]
                material.req_cap_mask_6 = masks[6]
                material.req_cap_mask_7 = masks[7]
            
            if "soft_gates" in metrics and calculator:
                soft_gates = calculator.calculate_from_musicxml(material.musicxml_canonical)
                analysis.tonal_complexity_stage = soft_gates.tonal_complexity_stage
                analysis.interval_size_stage = soft_gates.interval_size_stage  # DEPRECATED
                # NEW: Interval profile stages
                analysis.interval_sustained_stage = soft_gates.interval_sustained_stage
                analysis.interval_hazard_stage = soft_gates.interval_hazard_stage
                analysis.legacy_interval_size_stage = soft_gates.legacy_interval_size_stage
                # Interval profile data
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
                
                # Persist unified scores (Phase 4)
                try:
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
                    
                    domain_results = calculate_unified_domain_scores(
                        metrics=soft_gates,
                        tempo_profile=tempo_profile_dict,
                        range_analysis=range_analysis_dict,
                        extraction=extraction_dict,
                    )
                    
                    analysis.analysis_schema_version = 1
                    analysis.interval_analysis_json = json.dumps(domain_results['interval'].to_dict()) if 'interval' in domain_results else None
                    analysis.rhythm_analysis_json = json.dumps(domain_results['rhythm'].to_dict()) if 'rhythm' in domain_results else None
                    analysis.tonal_analysis_json = json.dumps(domain_results['tonal'].to_dict()) if 'tonal' in domain_results else None
                    analysis.tempo_analysis_json = json.dumps(domain_results['tempo'].to_dict()) if 'tempo' in domain_results else None
                    analysis.range_analysis_json = json.dumps(domain_results['range'].to_dict()) if 'range' in domain_results else None
                    analysis.throughput_analysis_json = json.dumps(domain_results['throughput'].to_dict()) if 'throughput' in domain_results else None
                    
                    analysis.interval_primary_score = domain_results['interval'].scores.get('primary') if 'interval' in domain_results and domain_results['interval'].scores else None
                    analysis.rhythm_primary_score = domain_results['rhythm'].scores.get('primary') if 'rhythm' in domain_results and domain_results['rhythm'].scores else None
                    analysis.tonal_primary_score = domain_results['tonal'].scores.get('primary') if 'tonal' in domain_results and domain_results['tonal'].scores else None
                    analysis.tempo_primary_score = domain_results['tempo'].scores.get('primary') if 'tempo' in domain_results and domain_results['tempo'].scores else None
                    analysis.range_primary_score = domain_results['range'].scores.get('primary') if 'range' in domain_results and domain_results['range'].scores else None
                    analysis.throughput_primary_score = domain_results['throughput'].scores.get('primary') if 'throughput' in domain_results and domain_results['throughput'].scores else None
                    
                    all_scores = {name: dr.scores for name, dr in domain_results.items()}
                    composite = calculate_composite_difficulty(all_scores)
                    analysis.overall_score = composite.get('overall')
                    analysis.interaction_bonus = composite.get('interaction_bonus')
                except Exception:
                    pass  # Don't fail batch on unified score errors
            
            if "range" in metrics:
                range_data = extraction_result.range_analysis
                if range_data:
                    analysis.lowest_pitch = range_data.lowest_pitch
                    analysis.highest_pitch = range_data.highest_pitch
                    analysis.range_semitones = range_data.range_semitones
                    analysis.pitch_density_low = range_data.density_low
                    analysis.pitch_density_mid = range_data.density_mid
                    analysis.pitch_density_high = range_data.density_high
            
            analysis.raw_extraction_json = json.dumps(extraction_result.to_dict())
            analysis.chromatic_complexity = extraction_result.chromatic_complexity_score
            analysis.measure_count = extraction_result.measure_count
            analysis.tempo_bpm = extraction_result.tempo_bpm
            
            result["materials_updated"] += 1
            
        except Exception as e:
            result["errors"].append(f"Material {material.id}: {str(e)}")
            result["materials_failed"] += 1
    
    db.commit()
    
    return BatchReanalyzeResponse(**result)
