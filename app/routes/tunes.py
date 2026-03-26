"""Tune management endpoints for user-composed tunes.

Provides CRUD operations for tunes with chord progression support.
"""
import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.core import Tune, User
from ..schemas.tune_schemas import (
    TuneCreate,
    TuneUpdate,
    TuneResponse,
    TuneListItem,
    TuneListResponse,
    TimeSignature,
    ChordProgression,
    DisplaySettings,
    PlaybackSettings,
    ChordInferenceRequest,
    ChordInferenceResponse,
    ChordAnalyzeRequest,
)
from ..services.chord_inference import ChordInferenceService

router = APIRouter(prefix="/tunes", tags=["tunes"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    """Get user by ID or raise 404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _parse_json_field(value: str, default: dict | list) -> dict | list:
    """Parse JSON string field, returning default on error."""
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _tune_to_response(tune: Tune) -> TuneResponse:
    """Convert Tune model to TuneResponse."""
    time_sig_dict = _parse_json_field(tune.time_signature_json, {"beats": 4, "beatUnit": 4})
    chord_progs = _parse_json_field(tune.chord_progressions_json, [])
    display = _parse_json_field(tune.display_settings_json, {"showChordSymbols": True})
    playback = _parse_json_field(tune.playback_settings_json, {})
    
    return TuneResponse(
        id=tune.id,
        user_id=tune.user_id,
        title=tune.title,
        clef=tune.clef,
        key_signature=tune.key_signature,
        time_signature=TimeSignature(**time_sig_dict),
        tempo=tune.tempo,
        measures_json=tune.measures_json,
        chord_progressions=[ChordProgression(**cp) for cp in chord_progs],
        display_settings=DisplaySettings(**display),
        playback_settings=PlaybackSettings(**playback),
        imported_from=tune.imported_from,
        created_at=tune.created_at,
        updated_at=tune.updated_at,
        is_archived=tune.is_archived or False,
    )


def _tune_to_list_item(tune: Tune) -> TuneListItem:
    """Convert Tune model to TuneListItem (lightweight)."""
    measures = _parse_json_field(tune.measures_json, [])
    chord_progs = _parse_json_field(tune.chord_progressions_json, [])
    
    # Count measures
    measure_count = len(measures) if isinstance(measures, list) else 0
    
    # Check if any progression has chords
    has_chords = any(
        len(cp.get("chords", [])) > 0 
        for cp in chord_progs 
        if isinstance(cp, dict)
    )
    
    return TuneListItem(
        id=tune.id,
        title=tune.title,
        clef=tune.clef,
        key_signature=tune.key_signature,
        tempo=tune.tempo,
        measure_count=measure_count,
        has_chord_progressions=has_chords,
        imported_from=tune.imported_from,
        created_at=tune.created_at,
        updated_at=tune.updated_at,
    )


@router.post("/analyze-chords", response_model=ChordInferenceResponse)
def analyze_chords(
    request: ChordAnalyzeRequest,
) -> ChordInferenceResponse:
    """Analyze melody data and infer chord progression.
    
    This endpoint analyzes raw melody data without requiring a saved tune.
    Use this for the Tune Composer to infer chords before saving.
    
    Args:
        request: Melody data with inference options.
        
    Returns:
        Inferred chord progression with confidence scores.
    """
    time_sig_dict = {
        "beats": request.time_signature.beats,
        "beatUnit": request.time_signature.beatUnit,
    }
    
    service = ChordInferenceService()
    inferred_chords = service.infer_chords_from_measures(
        measures_json=request.measures_json,
        key_signature=request.key_signature,
        time_signature=time_sig_dict,
        use_seventh_chords=request.use_seventh_chords,
        chords_per_measure=request.chords_per_measure,
    )
    
    progression_dict = service.to_chord_progression_dict(
        inferred_chords,
        name="Auto-Inferred"
    )
    
    return ChordInferenceResponse(
        progression=ChordProgression(**progression_dict),
        chord_count=len(inferred_chords),
    )


@router.post("", response_model=TuneResponse, status_code=201)
def create_tune(
    data: TuneCreate,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> TuneResponse:
    """Create a new tune for the specified user."""
    user = _get_user_or_404(db, user_id)
    now = datetime.utcnow()
    
    tune = Tune(
        user_id=user.id,
        title=data.title,
        clef=data.clef,
        key_signature=data.key_signature,
        time_signature_json=json.dumps(data.time_signature.model_dump()),
        tempo=data.tempo,
        measures_json=data.measures_json,
        chord_progressions_json=json.dumps([cp.model_dump() for cp in data.chord_progressions]),
        display_settings_json=json.dumps(data.display_settings.model_dump()),
        playback_settings_json=json.dumps(data.playback_settings.model_dump()),
        imported_from=data.imported_from,
        created_at=now,
        updated_at=now,
        is_archived=False,
    )
    
    db.add(tune)
    db.commit()
    db.refresh(tune)
    
    return _tune_to_response(tune)


@router.get("", response_model=TuneListResponse)
def list_tunes(
    user_id: int = Query(..., description="User ID"),
    include_archived: bool = Query(False, description="Include archived tunes"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> TuneListResponse:
    """List tunes for the specified user."""
    _get_user_or_404(db, user_id)  # Verify user exists
    query = db.query(Tune).filter(Tune.user_id == user_id)
    
    if not include_archived:
        query = query.filter((Tune.is_archived == False) | (Tune.is_archived == None))
    
    total = query.count()
    tunes = query.order_by(Tune.updated_at.desc()).offset(offset).limit(limit).all()
    
    return TuneListResponse(
        tunes=[_tune_to_list_item(t) for t in tunes],
        total_count=total,
    )


@router.get("/{tune_id}", response_model=TuneResponse)
def get_tune(
    tune_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> TuneResponse:
    """Get a specific tune by ID."""
    tune = db.query(Tune).filter(
        Tune.id == tune_id,
        Tune.user_id == user_id,
    ).first()
    
    if not tune:
        raise HTTPException(status_code=404, detail="Tune not found")
    
    return _tune_to_response(tune)


@router.put("/{tune_id}", response_model=TuneResponse)
def update_tune(
    tune_id: int,
    data: TuneUpdate,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> TuneResponse:
    """Update an existing tune."""
    tune = db.query(Tune).filter(
        Tune.id == tune_id,
        Tune.user_id == user_id,
    ).first()
    
    if not tune:
        raise HTTPException(status_code=404, detail="Tune not found")
    
    # Update only provided fields
    if data.title is not None:
        tune.title = data.title
    if data.clef is not None:
        tune.clef = data.clef
    if data.key_signature is not None:
        tune.key_signature = data.key_signature
    if data.time_signature is not None:
        tune.time_signature_json = json.dumps(data.time_signature.model_dump())
    if data.tempo is not None:
        tune.tempo = data.tempo
    if data.measures_json is not None:
        tune.measures_json = data.measures_json
    if data.chord_progressions is not None:
        tune.chord_progressions_json = json.dumps([cp.model_dump() for cp in data.chord_progressions])
    if data.display_settings is not None:
        tune.display_settings_json = json.dumps(data.display_settings.model_dump())
    if data.playback_settings is not None:
        tune.playback_settings_json = json.dumps(data.playback_settings.model_dump())
    
    tune.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tune)
    
    return _tune_to_response(tune)


@router.delete("/{tune_id}", status_code=204)
def delete_tune(
    tune_id: int,
    user_id: int = Query(..., description="User ID"),
    permanent: bool = Query(False, description="Permanently delete instead of archive"),
    db: Session = Depends(get_db),
) -> None:
    """Delete (archive) a tune."""
    tune = db.query(Tune).filter(
        Tune.id == tune_id,
        Tune.user_id == user_id,
    ).first()
    
    if not tune:
        raise HTTPException(status_code=404, detail="Tune not found")
    
    if permanent:
        db.delete(tune)
    else:
        tune.is_archived = True
        tune.updated_at = datetime.utcnow()
    
    db.commit()


@router.post("/{tune_id}/restore", response_model=TuneResponse)
def restore_tune(
    tune_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> TuneResponse:
    """Restore an archived tune."""
    tune = db.query(Tune).filter(
        Tune.id == tune_id,
        Tune.user_id == user_id,
    ).first()
    
    if not tune:
        raise HTTPException(status_code=404, detail="Tune not found")
    
    tune.is_archived = False
    tune.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tune)
    
    return _tune_to_response(tune)


@router.post("/{tune_id}/duplicate", response_model=TuneResponse, status_code=201)
def duplicate_tune(
    tune_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> TuneResponse:
    """Create a copy of an existing tune."""
    original = db.query(Tune).filter(
        Tune.id == tune_id,
        Tune.user_id == user_id,
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Tune not found")
    
    now = datetime.utcnow()
    
    duplicate = Tune(
        user_id=user_id,
        title=f"{original.title} (Copy)",
        clef=original.clef,
        key_signature=original.key_signature,
        time_signature_json=original.time_signature_json,
        tempo=original.tempo,
        measures_json=original.measures_json,
        chord_progressions_json=original.chord_progressions_json,
        display_settings_json=original.display_settings_json,
        playback_settings_json=original.playback_settings_json,
        imported_from=None,  # Clear import source for duplicates
        created_at=now,
        updated_at=now,
        is_archived=False,
    )
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return _tune_to_response(duplicate)


@router.post("/{tune_id}/infer-chords", response_model=ChordInferenceResponse)
def infer_chords(
    tune_id: int,
    request: ChordInferenceRequest,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> ChordInferenceResponse:
    """Infer chord progression from tune melody.
    
    Analyzes the melody notes to suggest harmonically appropriate chords.
    Returns a ChordProgression with isAutoInferred=True that can be added
    to the tune's chord_progressions array.
    
    Args:
        tune_id: ID of the tune to analyze.
        request: Inference options (seventh chords, chords per measure).
        user_id: Owner of the tune.
        
    Returns:
        Inferred chord progression with confidence scores.
    """
    tune = db.query(Tune).filter(
        Tune.id == tune_id,
        Tune.user_id == user_id,
    ).first()
    
    if not tune:
        raise HTTPException(status_code=404, detail="Tune not found")
    
    # Parse time signature
    time_sig_dict = _parse_json_field(
        tune.time_signature_json, 
        {"beats": 4, "beatUnit": 4}
    )
    
    # Run inference
    service = ChordInferenceService()
    inferred_chords = service.infer_chords_from_measures(
        measures_json=tune.measures_json,
        key_signature=tune.key_signature,
        time_signature=time_sig_dict,
        use_seventh_chords=request.use_seventh_chords,
        chords_per_measure=request.chords_per_measure,
    )
    
    # Convert to progression dict
    progression_dict = service.to_chord_progression_dict(
        inferred_chords, 
        name="Auto-Inferred"
    )
    
    return ChordInferenceResponse(
        progression=ChordProgression(**progression_dict),
        chord_count=len(inferred_chords),
    )
