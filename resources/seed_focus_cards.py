#!/usr/bin/env python3
"""
Seed focus cards from focus_cards.json

Usage:
    PYTHONPATH=. python resources/seed_focus_cards.py
"""
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.core import FocusCard
from app.db import SessionLocal


def load_focus_cards_json():
    """Load focus cards from JSON file."""
    json_path = Path(__file__).parent / "focus_cards.json"
    with json_path.open("r") as f:
        data = json.load(f)
    return data.get("focus_cards", [])


def seed_focus_cards(session=None):
    """Seed focus cards from focus_cards.json. Idempotent - updates existing records."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    
    try:
        focus_cards_data = load_focus_cards_json()
        
        inserted_count = 0
        updated_count = 0
        
        for fc_data in focus_cards_data:
            existing = session.query(FocusCard).filter_by(name=fc_data["name"]).first()
            
            if not existing:
                fc = FocusCard(
                    name=fc_data["name"],
                    description=fc_data["description"],
                    category=fc_data["category"],
                    attention_cue=fc_data["attention_cue"],
                    micro_cues=json.dumps(fc_data["micro_cues"]),
                    prompts=json.dumps(fc_data["prompts"])
                )
                session.add(fc)
                inserted_count += 1
            else:
                # Update existing focus card
                existing.description = fc_data["description"]
                existing.category = fc_data["category"]
                existing.attention_cue = fc_data["attention_cue"]
                existing.micro_cues = json.dumps(fc_data["micro_cues"])
                existing.prompts = json.dumps(fc_data["prompts"])
                updated_count += 1
        
        session.commit()
        print(f"Focus cards seeded: {inserted_count} inserted, {updated_count} updated")
        return inserted_count + updated_count
        
    except Exception as e:
        session.rollback()
        print(f"Error seeding focus cards: {e}")
        raise
    finally:
        if close_session:
            session.close()


def main():
    """Main entry point."""
    print("=== Seeding Focus Cards ===")
    seed_focus_cards()


if __name__ == "__main__":
    main()
