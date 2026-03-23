"""Generation API endpoints.

Provides endpoints for generating musical content (scales, arpeggios, licks)
using the content generation engine.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.models.capability_schema import Capability, UserCapability
from app.schemas.generation_schemas import (
    ArpeggioType,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
    MusicalKey,
    RhythmType,
    ScalePattern,
    ArpeggioPattern,
    ScaleType,
    SCALE_PATTERN_CONSTRAINTS,
    ValidPoolResponse,
)
from app.services.generation.scale_definitions import ASYMMETRIC_SCALES
from app.services.generation import get_generation_service
from app.services.generation.valid_pool_calculator import get_valid_pool_calculator


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("", response_model=GenerationResponse)
def generate_content(
    request: GenerationRequest = Body(...),
) -> GenerationResponse:
    """Generate musical content from the provided parameters.
    
    The generation engine produces pitch sequences based on the request:
    - **content_type**: scale, arpeggio, or lick
    - **definition**: specific type (e.g., "dorian", "maj7")
    - **octaves**: 1, 2, or 3 octaves
    - **pattern**: optional pattern algorithm (e.g., "in_3rds", "groups_of_4")
    - **rhythm**: duration template (e.g., "quarter_notes", "eighth_notes")
    - **key**: target key for transposition (default: C)
    
    Example request:
    ```json
    {
        "content_type": "scale",
        "definition": "dorian",
        "octaves": 2,
        "pattern": "in_3rds",
        "rhythm": "eighth_notes",
        "key": "F"
    }
    ```
    """
    service = get_generation_service()
    
    try:
        response = service.generate(request)
        logger.info(
            f"Generated {request.content_type.value} '{request.definition}' "
            f"in {request.key.value}, {len(response.events)} events"
        )
        return response
    except ValueError as e:
        logger.warning(f"Generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during generation: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during generation",
        )


@router.post("/musicxml", response_class=Response)
def generate_musicxml(
    request: GenerationRequest = Body(...),
    title: Optional[str] = Query(
        default=None,
        description="Optional title for the MusicXML document",
    ),
) -> Response:
    """Generate musical content and return as MusicXML.
    
    Returns the generated content in MusicXML format, suitable for
    import into notation software or playback systems.
    
    The response Content-Type is `application/vnd.recordare.musicxml+xml`.
    """
    service = get_generation_service()
    
    try:
        musicxml = service.generate_musicxml(request, title=title)
        logger.info(
            f"Generated MusicXML for {request.content_type.value} "
            f"'{request.definition}' in {request.key.value}"
        )
        return Response(
            content=musicxml,
            media_type="application/vnd.recordare.musicxml+xml",
            headers={
                "Content-Disposition": f'attachment; filename="{request.definition}_{request.key.value}.musicxml"'
            },
        )
    except ValueError as e:
        logger.warning(f"MusicXML generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during MusicXML generation: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during generation",
        )


@router.get("/scale-types", response_model=List[str])
def get_scale_types() -> List[str]:
    """Get list of all available scale types.
    
    Returns the enum values for all supported scale types that can
    be used in the `definition` field when `content_type` is "scale".
    """
    return [s.value for s in ScaleType]


@router.get("/arpeggio-types", response_model=List[str])
def get_arpeggio_types() -> List[str]:
    """Get list of all available arpeggio types.
    
    Returns the enum values for all supported arpeggio types that can
    be used in the `definition` field when `content_type` is "arpeggio".
    """
    return [a.value for a in ArpeggioType]


@router.get("/scale-patterns", response_model=List[str])
def get_scale_patterns() -> List[str]:
    """Get list of all available scale patterns.
    
    Returns the enum values for all supported scale patterns that can
    be used in the `pattern` field when `content_type` is "scale".
    """
    return [p.value for p in ScalePattern]


@router.get("/scale-patterns-with-constraints")
def get_scale_patterns_with_constraints() -> Dict[str, Dict[str, Any]]:
    """Get scale patterns with their constraints.
    
    Returns a dictionary mapping pattern names to their constraints.
    Patterns not in the dict have no constraints.
    
    Constraint fields:
    - max_octaves: Maximum number of octaves this pattern supports
    - requires_symmetric: If true, incompatible with asymmetric scales
      (e.g., melodic_minor_classical)
    
    Example response:
    ```json
    {
        "broken_thirds_neighbor": {"max_octaves": 1, "requires_symmetric": true},
        "diatonic_7ths": {"max_octaves": 2}
    }
    ```
    """
    return SCALE_PATTERN_CONSTRAINTS


@router.get("/asymmetric-scales", response_model=List[str])
def get_asymmetric_scales() -> List[str]:
    """Get list of asymmetric scales.
    
    Asymmetric scales have different pitches ascending vs descending
    (e.g., melodic_minor_classical). Some patterns that constantly
    reverse direction are incompatible with these scales.
    """
    return [s.value for s in ASYMMETRIC_SCALES]


@router.get("/arpeggio-patterns", response_model=List[str])
def get_arpeggio_patterns() -> List[str]:
    """Get list of all available arpeggio patterns.
    
    Returns the enum values for all supported arpeggio patterns that can
    be used in the `pattern` field when `content_type` is "arpeggio".
    """
    return [p.value for p in ArpeggioPattern]


@router.get("/rhythm-types", response_model=List[str])
def get_rhythm_types() -> List[str]:
    """Get list of all available rhythm types.
    
    Returns the enum values for all supported rhythm types that can
    be used in the `rhythm` field.
    """
    return [r.value for r in RhythmType]


@router.get("/keys", response_model=List[str])
def get_keys() -> List[str]:
    """Get list of all available keys.
    
    Returns the enum values for all supported musical keys that can
    be used in the `key` field for transposition.
    """
    return [k.value for k in MusicalKey]


@router.get("/valid-pool", response_model=ValidPoolResponse)
def get_valid_pool(
    user_id: int = Query(..., description="User ID to check capabilities for"),
    db: DbSession = Depends(get_db),
) -> ValidPoolResponse:
    """Get valid generation options based on user's mastered capabilities.
    
    Returns the pool of valid scale types, arpeggio types, patterns, rhythms,
    and keys that the user can practice based on their mastered capabilities.
    
    This endpoint is designed for the practice session to query upfront to know
    its possible pool, ensuring generated content never requires capabilities
    the user hasn't mastered.
    
    Example response:
    ```json
    {
        "scale_types": ["ionian", "dorian", "aeolian"],
        "arpeggio_types": ["major", "minor"],
        "rhythms": ["quarter_notes", "eighth_notes"],
        "keys": ["C", "G", "F"],
        "scale_patterns": {
            "ionian": ["straight_up", "straight_down", "in_3rds"]
        },
        "arpeggio_patterns": {
            "major": ["straight_up", "straight_down"]
        }
    }
    ```
    """
    # Get user's mastered capability names
    user_caps = _get_user_mastered_capabilities(user_id, db)
    
    # Calculate valid pool
    calculator = get_valid_pool_calculator()
    pool = calculator.get_full_valid_pool(user_caps)
    
    return ValidPoolResponse(**pool.to_dict())


def _get_user_mastered_capabilities(user_id: int, db: DbSession) -> Set[str]:
    """Get set of capability names that user has mastered.
    
    A capability is considered mastered if:
    - mastered_at is not None
    - is_active is True
    
    Args:
        user_id: The user ID.
        db: Database session.
        
    Returns:
        Set of capability names (strings).
    """
    results = (
        db.query(Capability.name)
        .join(UserCapability, Capability.id == UserCapability.capability_id)
        .filter(
            UserCapability.user_id == user_id,
            UserCapability.mastered_at.isnot(None),
            UserCapability.is_active == True,  # noqa: E712
        )
        .all()
    )
    return {row[0] for row in results}
