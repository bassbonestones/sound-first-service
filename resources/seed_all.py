#!/usr/bin/env python3
"""
Master seed script for Sound First.

Usage:
    PYTHONPATH=. python resources/seed_all.py

This script seeds all tables in the correct order:
1. Capabilities (from capabilities.json)
2. Focus Cards (from focus_cards.json)
3. Materials (from materials/materials.json)
4. Test User (user 1)
5. Soft Gate Rules (from soft_gate_rules.json)
6. Teaching Modules (from seed_teaching_modules.py)

Each sub-script is idempotent (safe to re-run).
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seed_capabilities():
    """Seed capabilities from capabilities.json"""
    print("\n=== Seeding Capabilities ===")
    from resources.seed_capabilities import main as seed_caps
    seed_caps()


def seed_focus_cards():
    """Seed focus cards from focus_cards.json"""
    print("\n=== Seeding Focus Cards ===")
    from resources.seed_focus_cards import seed_focus_cards as do_seed
    do_seed()


def seed_materials():
    """Seed materials from materials/materials.json"""
    print("\n=== Seeding Materials ===")
    from resources.seed_materials import seed_materials as do_seed
    do_seed()


def seed_test_user():
    """Seed test user (user 1)"""
    print("\n=== Seeding Test User ===")
    from app.models.core import User
    from app.db import SessionLocal
    
    session = SessionLocal()
    try:
        existing_user = session.query(User).filter_by(id=1).first()
        if not existing_user:
            user = User(
                id=1,
                email="user1@example.com",
                instrument=None,
                resonant_note=None,
                range_low=None,
                range_high=None,
                comfortable_capabilities=None,
                day0_completed=False,
                day0_stage=0
            )
            session.add(user)
            print("Created test user (id=1)")
        else:
            existing_user.instrument = None
            existing_user.resonant_note = None
            existing_user.range_low = None
            existing_user.range_high = None
            existing_user.comfortable_capabilities = None
            existing_user.day0_completed = False
            existing_user.day0_stage = 0
            print("Reset test user (id=1)")
        session.commit()
    finally:
        session.close()


def seed_soft_gates():
    """Seed soft gate rules and user state"""
    print("\n=== Seeding Soft Gate Rules ===")
    import json
    from pathlib import Path
    from resources.seed_soft_gates import _upsert_soft_gate_rules, _backfill_user_soft_gates
    from app.db import SessionLocal
    
    json_path = Path(__file__).parent / "soft_gate_rules.json"
    with json_path.open("r") as f:
        data = json.load(f)
    
    session = SessionLocal()
    try:
        rules_count = _upsert_soft_gate_rules(session, data["soft_gate_rules"])
        session.commit()
        print(f"Upserted {rules_count} soft gate rules.")
        
        users_count = _backfill_user_soft_gates(session, data["default_user_state"])
        session.commit()
        print(f"Backfilled soft gate state for {users_count} users.")
    finally:
        session.close()


def seed_teaching_modules():
    """Seed teaching modules and lessons"""
    print("\n=== Seeding Teaching Modules ===")
    from resources.seed_teaching_modules import main as do_seed
    do_seed()

def main():
    """Run all seed scripts in order."""
    print("=" * 50)
    print("Sound First - Full Database Seed")
    print("=" * 50)
    
    seed_capabilities()
    seed_focus_cards()
    seed_materials()
    seed_test_user()
    seed_soft_gates()
    seed_teaching_modules()
    
    print("\n" + "=" * 50)
    print("All seeding complete!")
    print("=" * 50)


# Alias for test import compatibility
seed_all = main


if __name__ == "__main__":
    main()
