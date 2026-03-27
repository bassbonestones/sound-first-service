#!/usr/bin/env python3
"""Debug session generation state."""
import sys
sys.path.insert(0, '.')

from app.db import SessionLocal
from app.models import User
from app.models.capability_schema import Capability, UserCapability
from app.routes.sessions import _get_available_teaching_modules

db = SessionLocal()
try:
    user_id = 1
    
    # Check mastered capabilities
    mastered = db.query(Capability, UserCapability).join(
        UserCapability, Capability.id == UserCapability.capability_id
    ).filter(
        UserCapability.user_id == user_id,
        UserCapability.is_active == True,
        UserCapability.mastered_at != None
    ).all()
    
    print(f"=== Mastered capabilities for user {user_id}: {len(mastered)} ===")
    for cap, uc in mastered:
        print(f"  {cap.name} (instrument_id={uc.instrument_id})")
    
    # Check user day0_completed
    user = db.query(User).filter(User.id == user_id).first()
    print(f"\n=== User day0_completed: {user.day0_completed} ===")
    
    # Call the actual function
    print(f"\n=== Available modules (from _get_available_teaching_modules) ===")
    available = _get_available_teaching_modules(db, user_id)
    print(f"Count: {len(available)}")
    for module, lesson in available:
        print(f"  {module.display_name} -> first lesson: {lesson.id}")
    
finally:
    db.close()
