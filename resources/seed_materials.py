#!/usr/bin/env python3
"""
Seed materials from materials/materials.json

The materials.json file references MusicXML files stored in the same folder.
Each material entry can specify either:
  - "musicxml_file": filename of a .musicxml file in the materials folder
  - "musicxml_canonical": inline MusicXML content

Usage:
    PYTHONPATH=. python resources/seed_materials.py
"""
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.core import Material
from app.db import SessionLocal


MATERIALS_DIR = Path(__file__).parent / "materials"


def load_materials_json():
    """Load materials from JSON file."""
    json_path = MATERIALS_DIR / "materials.json"
    with json_path.open("r") as f:
        data = json.load(f)
    return data.get("materials", [])


def load_musicxml_file(filename):
    """Load MusicXML content from a file in the materials folder."""
    file_path = MATERIALS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"MusicXML file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        return f.read()


def seed_materials(session=None):
    """Seed materials from materials.json. Replaces all existing materials."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    
    try:
        materials_data = load_materials_json()
        
        # Delete all existing materials - materials.json is the source of truth
        deleted_count = session.query(Material).delete()
        if deleted_count > 0:
            print(f"Cleared {deleted_count} existing materials")
        
        inserted_count = 0
        updated_count = 0
        
        for mat_data in materials_data:
            # Load MusicXML content - either from file or inline
            if "musicxml_file" in mat_data:
                musicxml_content = load_musicxml_file(mat_data["musicxml_file"])
            else:
                musicxml_content = mat_data.get("musicxml_canonical", "")
            
            existing = session.query(Material).filter_by(title=mat_data["title"]).first()
            
            if not existing:
                mat = Material(
                    title=mat_data["title"],
                    allowed_keys=mat_data.get("allowed_keys", ""),
                    required_capability_ids=mat_data.get("required_capability_ids", ""),
                    scaffolding_capability_ids=mat_data.get("scaffolding_capability_ids", ""),
                    musicxml_canonical=musicxml_content,
                    original_key_center=mat_data.get("original_key_center"),
                    pitch_reference_type=mat_data.get("pitch_reference_type", "TONAL"),
                    pitch_ref_json=mat_data.get("pitch_ref_json", "{}"),
                    spelling_policy=mat_data.get("spelling_policy", "from_key")
                )
                session.add(mat)
                inserted_count += 1
            else:
                # Update existing material
                existing.allowed_keys = mat_data.get("allowed_keys", "")
                existing.required_capability_ids = mat_data.get("required_capability_ids", "")
                existing.scaffolding_capability_ids = mat_data.get("scaffolding_capability_ids", "")
                existing.musicxml_canonical = musicxml_content
                existing.original_key_center = mat_data.get("original_key_center")
                existing.pitch_reference_type = mat_data.get("pitch_reference_type", "TONAL")
                existing.pitch_ref_json = mat_data.get("pitch_ref_json", "{}")
                existing.spelling_policy = mat_data.get("spelling_policy", "from_key")
                updated_count += 1
        
        session.commit()
        print(f"Materials seeded: {inserted_count} inserted, {updated_count} updated")
        return inserted_count + updated_count
        
    except Exception as e:
        session.rollback()
        print(f"Error seeding materials: {e}")
        raise
    finally:
        if close_session:
            session.close()


def main():
    """Main entry point."""
    print("=== Seeding Materials ===")
    seed_materials()


if __name__ == "__main__":
    main()
