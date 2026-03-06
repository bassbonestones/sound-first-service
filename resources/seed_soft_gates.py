"""
Seed soft gate rules and initialize user soft gate state.

Usage:
    python resources/seed_soft_gates.py resources/soft_gate_rules.json

This script:
- Upserts soft_gate_rules from JSON
- Backfills user_soft_gate_state for any users that don't have it
- Is idempotent (safe to re-run)
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.db import SessionLocal
from app.models.capability_schema import SoftGateRule, UserSoftGateState
from app.models.core import User


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _upsert_soft_gate_rules(session, rules: List[Dict[str, Any]]) -> int:
    """Upsert soft gate rules. Returns count of inserted/updated."""
    existing = {r.dimension_name: r for r in session.query(SoftGateRule).all()}
    count = 0
    
    for rule_data in rules:
        dimension_name = rule_data["dimension_name"]
        
        if dimension_name in existing:
            row = existing[dimension_name]
        else:
            row = SoftGateRule()
            row.dimension_name = dimension_name
            session.add(row)
        
        # Update all fields
        row.frontier_buffer = rule_data["frontier_buffer"]
        row.promotion_step = rule_data["promotion_step"]
        row.min_attempts = rule_data["min_attempts"]
        row.success_rating_threshold = rule_data.get("success_rating_threshold", 4)
        row.success_required_count = rule_data["success_required_count"]
        row.success_window_count = rule_data.get("success_window_count")
        row.decay_halflife_days = rule_data.get("decay_halflife_days")
        
        count += 1
    
    return count


def _backfill_user_soft_gates(session, default_state: Dict[str, Any]) -> int:
    """Ensure all users have soft gate state for all dimensions. Returns users updated."""
    users = session.query(User).all()
    dimension_names = list(default_state.keys())
    updated_count = 0
    
    for user in users:
        # Get existing state for this user
        existing = {
            s.dimension_name: s 
            for s in session.query(UserSoftGateState).filter_by(user_id=user.id).all()
        }
        
        user_updated = False
        for dim_name in dimension_names:
            if dim_name not in existing:
                defaults = default_state[dim_name]
                state = UserSoftGateState(
                    user_id=user.id,
                    dimension_name=dim_name,
                    comfortable_value=defaults["comfortable_value"],
                    max_demonstrated_value=defaults["max_demonstrated_value"],
                    frontier_success_ema=defaults["frontier_success_ema"],
                    frontier_attempt_count_since_last_promo=defaults["frontier_attempt_count_since_last_promo"],
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(state)
                user_updated = True
        
        if user_updated:
            updated_count += 1
    
    return updated_count


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python resources/seed_soft_gates.py resources/soft_gate_rules.json")
        sys.exit(2)
    
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        raise FileNotFoundError(str(json_path))
    
    payload = _load_json(json_path)
    
    if "soft_gate_rules" not in payload:
        raise ValueError("JSON must contain 'soft_gate_rules' array")
    
    session = SessionLocal()
    try:
        # Upsert rules
        rules_count = _upsert_soft_gate_rules(session, payload["soft_gate_rules"])
        print(f"Upserted {rules_count} soft gate rules.")
        
        # Backfill user state
        if "default_user_state" in payload:
            users_count = _backfill_user_soft_gates(session, payload["default_user_state"])
            print(f"Backfilled soft gate state for {users_count} users.")
        
        session.commit()
        print("Soft gate seed complete.")
    
    finally:
        session.close()


if __name__ == "__main__":
    main()
