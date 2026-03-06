#!/usr/bin/env python3
"""
Master seed script for Sound First.

Usage:
    PYTHONPATH=. python resources/seed_all.py

This script seeds all tables in the correct order:
1. Capabilities (from capabilities.json)
2. Focus Cards & Materials (from seed_data.py)
3. Soft Gate Rules (from soft_gate_rules.json)

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


def seed_focus_cards_and_materials():
    """Seed focus cards, materials, and test user"""
    print("\n=== Seeding Focus Cards, Materials & Test User ===")
    from resources.seed_data import seed_all as seed_data_all
    seed_data_all()


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


def main():
    """Run all seed scripts in order."""
    print("=" * 50)
    print("Sound First - Full Database Seed")
    print("=" * 50)
    
    seed_capabilities()
    seed_focus_cards_and_materials()
    seed_soft_gates()
    
    print("\n" + "=" * 50)
    print("All seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
