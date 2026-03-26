"""Chord inference service for analyzing melodies and suggesting chord progressions."""

from app.services.chord_inference.chord_inference_service import (
    ChordInferenceService,
    InferredChord,
)

__all__ = [
    "ChordInferenceService",
    "InferredChord",
]
