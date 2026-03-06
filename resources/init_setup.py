#!/usr/bin/env python3
"""
Full database initialization for Sound First.

Usage:
    PYTHONPATH=. python resources/init_setup.py

This script:
1. Removes existing SQLite database
2. Runs Alembic migrations
3. Seeds all data (capabilities, focus cards, materials, soft gates)

WARNING: This will DELETE all existing data!
"""
import os
import subprocess
import sys

# Get the service root directory
SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SERVICE_ROOT, "sound_first.db")


def main():
    print("=" * 50)
    print("Sound First - Full Database Initialization")
    print("=" * 50)
    
    # Step 1: Remove existing database
    print("\n[1/3] Removing existing database...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  Deleted: {DB_PATH}")
    else:
        print(f"  No existing database found at {DB_PATH}")
    
    # Step 2: Run Alembic migrations
    print("\n[2/3] Running Alembic migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ERROR: Alembic failed!\n{result.stderr}")
        sys.exit(1)
    print("  Migrations applied successfully")
    
    # Step 3: Seed all data
    print("\n[3/3] Seeding database...")
    from resources.seed_all import main as seed_all
    seed_all()
    
    print("\n" + "=" * 50)
    print("Initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
