"""Audio generation endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.core import Material
from app.schemas.user_schemas import AudioStatusOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])

# Response documentation for binary audio endpoints
AUDIO_RESPONSES = {
    200: {
        "description": "Audio file (WAV or MIDI fallback)",
        "content": {
            "audio/wav": {},
            "audio/midi": {},
        }
    },
    400: {"description": "Invalid request parameters"},
    404: {"description": "Resource not found"},
    422: {"description": "Processing error"},
    503: {"description": "Audio library unavailable"},
}


@router.get(
    "/material/{material_id}",
    responses=AUDIO_RESPONSES,
    status_code=200,
    description="Generate transposed audio for a material (WAV or MIDI fallback)",
)  # type: ignore[arg-type]
def get_material_audio(
    material_id: int,
    key: str = Query(..., description="Target key for transposition (e.g., 'Bb major')"),
    instrument: str = Query(default="piano", description="Instrument for soundfont"),
    db: Session = Depends(get_db)
) -> Response:
    """
    Generate audio for a material transposed to the specified key.
    
    Uses music21 to transpose MusicXML and FluidSynth to render audio.
    Returns WAV audio if soundfont available, otherwise MIDI.
    
    Error responses include structured error info with codes:
    - music21_not_installed: Audio library missing
    - soundfont_not_found: No .sf2 file available (returns MIDI)
    - invalid_musicxml: Bad notation content
    - midi_conversion_failed: MusicXML parsing failed
    - audio_render_failed: FluidSynth error (returns MIDI)
    """
    from app.audio import (
        generate_audio_with_result, 
        AudioErrorCode
    )
    
    # Get material
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        return JSONResponse(
            status_code=404,
            content={
                "error": True,
                "code": "material_not_found",
                "message": f"Material {material_id} not found",
                "detail": None
            }
        )
    
    # Check for MusicXML content
    if not material.musicxml_canonical:
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "code": "no_musicxml",
                "message": "Material has no notation content",
                "detail": f"Material '{material.title}' does not have MusicXML data"
            }
        )
    
    # Generate audio
    result = generate_audio_with_result(
        musicxml_content=material.musicxml_canonical,  # type: ignore[arg-type]
        original_key=material.original_key_center or "C major",  # type: ignore[arg-type]
        target_key=key,
        instrument=instrument,
        material_id=material_id,
    )
    
    # Handle complete failure
    if not result.success and result.data is None:
        error = result.error
        # Map error codes to HTTP status codes
        status_map = {
            AudioErrorCode.MUSIC21_NOT_INSTALLED: 503,
            AudioErrorCode.INVALID_MUSICXML: 400,
            AudioErrorCode.MIDI_CONVERSION_FAILED: 422,
        }
        status_code = status_map.get(error.code, 500) if error else 500
        
        return JSONResponse(
            status_code=status_code,
            content=error.to_dict() if error else {"error": True, "message": "Unknown error"}
        )
    
    # Determine filename
    safe_title = material.title.replace(" ", "_").replace("/", "-")[:30]
    safe_key = key.replace(" ", "_")
    
    if result.content_type == "audio/wav":
        filename = f"{safe_title}_{safe_key}.wav"
    else:
        filename = f"{safe_title}_{safe_key}.mid"
    
    # Add warning header if returning fallback MIDI
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "no-cache",
    }
    if result.is_fallback and result.error:
        headers["X-Audio-Warning"] = result.error.message
        headers["X-Audio-Fallback"] = "true"
    
    return Response(
        content=result.data,
        media_type=result.content_type,
        headers=headers
    )


@router.get(
    "/note/{note}",
    responses=AUDIO_RESPONSES,
    status_code=200,
    description="Generate audio for a single sustained note",
)  # type: ignore[arg-type]
def get_single_note_audio(
    note: str,
    instrument: str = Query(default="piano", description="Instrument for soundfont"),
    duration: int = Query(default=3, description="Duration in beats (3 = 3 seconds at 60 BPM)"),
    octave: Optional[int] = Query(default=None, description="Override octave (1-8)")
) -> Response:
    """
    Generate audio for a single sustained note.
    
    Used for Day 0 first-note experience - plays a whole note for the user's
    resonant pitch so they can listen, sing, and match it.
    
    Examples:
    - /audio/note/Bb4?instrument=trombone
    - /audio/note/F%233?instrument=trumpet (F#3 URL-encoded)
    - /audio/note/Eb?octave=3&instrument=tuba
    
    Returns WAV audio if soundfont available, otherwise MIDI fallback.
    """
    from app.audio import generate_single_note_audio, AudioErrorCode
    
    # Validate octave if provided
    if octave is not None and (octave < 1 or octave > 8):
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "code": "invalid_octave",
                "message": "Octave must be between 1 and 8",
                "detail": f"Got octave={octave}"
            }
        )
    
    # Generate audio
    result = generate_single_note_audio(
        note_name=note,
        instrument=instrument,
        duration_beats=duration,
        octave=octave
    )
    
    # Handle complete failure
    if not result.success and result.data is None:
        error = result.error
        status_map = {
            AudioErrorCode.MUSIC21_NOT_INSTALLED: 503,
            AudioErrorCode.MIDI_CONVERSION_FAILED: 400,
        }
        status_code = status_map.get(error.code, 500) if error else 500
        
        return JSONResponse(
            status_code=status_code,
            content=error.to_dict() if error else {"error": True, "message": "Unknown error"}
        )
    
    # Determine filename
    safe_note = note.replace("#", "sharp").replace("b", "flat")[:10]
    
    if result.content_type == "audio/wav":
        filename = f"note_{safe_note}.wav"
    else:
        filename = f"note_{safe_note}.mid"
    
    # Add headers
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "public, max-age=3600",  # Cache single notes longer
    }
    if result.is_fallback and result.error:
        headers["X-Audio-Warning"] = result.error.message
        headers["X-Audio-Fallback"] = "true"
    
    return Response(
        content=result.data,
        media_type=result.content_type,
        headers=headers
    )


@router.get(
    "/status",
    response_model=AudioStatusOut,
    description="Check audio generation capability and soundfont status",
)
def get_audio_status() -> AudioStatusOut:
    """Check audio generation capability."""
    from app.audio import (
        MUSIC21_AVAILABLE, 
        FLUIDSYNTH_AVAILABLE, 
        get_soundfont_path,
        get_cache_stats
    )
    from app.config import USE_DIRECT_FLUIDSYNTH
    
    soundfont = get_soundfont_path()
    
    return {  # type: ignore[return-value]
        "music21_available": MUSIC21_AVAILABLE,
        "fluidsynth_available": FLUIDSYNTH_AVAILABLE,
        "use_direct_fluidsynth": USE_DIRECT_FLUIDSYNTH,
        "soundfont_found": soundfont is not None,
        "soundfont_path": str(soundfont) if soundfont else None,
        "can_render_audio": MUSIC21_AVAILABLE and FLUIDSYNTH_AVAILABLE and soundfont is not None,
        "can_render_midi": MUSIC21_AVAILABLE,
        "cache": get_cache_stats(),
    }
