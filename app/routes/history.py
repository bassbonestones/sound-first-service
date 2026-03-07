"""History and analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import datetime

from app.db import get_db
from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt
from app.models.capability_schema import Capability, UserCapability
from app.spaced_repetition import (
    build_sr_item_from_db,
    get_review_stats,
    estimate_mastery_level,
    prioritize_materials,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/summary")
def get_history_summary(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get practice history summary with spaced repetition stats."""
    from app.curriculum import JourneyMetrics, estimate_journey_stage

    # Get all attempts
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()

    # Build attempt history by material
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "fatigue": a.fatigue,
        })

    # Build SR items and mastery counts
    sr_items = []
    mastered_count = 0
    familiar_count = 0
    stabilizing_count = 0
    learning_count = 0

    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, mat_attempts)
        sr_items.append(sr_item)

        if mat_attempts:
            mastery = estimate_mastery_level(sr_item)
            if mastery == "mastered":
                mastered_count += 1
            elif mastery == "familiar":
                familiar_count += 1
            elif mastery == "stabilizing":
                stabilizing_count += 1
            elif mastery in ("learning", "new"):
                learning_count += 1

    # Get review stats
    stats = get_review_stats(sr_items)

    # Calculate streaks
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).order_by(PracticeSession.started_at.desc()).all()

    # Calculate current streak (consecutive days with practice)
    current_streak = 0
    if sessions:
        today = datetime.datetime.now().date()
        check_date = today
        session_dates = set(s.started_at.date() for s in sessions if s.started_at)

        while check_date in session_dates:
            current_streak += 1
            check_date -= datetime.timedelta(days=1)

    # Calculate days since first session
    days_since_first = 0
    if sessions:
        first_session = min(s.started_at for s in sessions if s.started_at)
        if first_session:
            days_since_first = (datetime.datetime.now() - first_session).days

    # Total practice time (estimate based on sessions)
    total_sessions = len(sessions)
    total_attempts = len(attempts)

    # Average rating
    ratings = [a.rating for a in attempts if a.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    # Count unique keys practiced
    unique_keys = set()
    mini_sessions = db.query(MiniSession).join(PracticeSession).filter(
        PracticeSession.user_id == user_id
    ).all()
    for ms in mini_sessions:
        if ms.key:
            unique_keys.add(ms.key)

    # Count capabilities mastered (V2)
    cap_progress = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.mastered_at.isnot(None)
    ).count()

    # Count self-directed sessions
    self_directed_count = len([s for s in sessions if s.practice_mode == "self_directed"])

    # Build journey metrics
    metrics = JourneyMetrics(
        total_sessions=total_sessions,
        total_attempts=total_attempts,
        days_since_first_session=days_since_first,
        average_rating=avg_rating,
        mastered_count=mastered_count,
        familiar_count=familiar_count,
        stabilizing_count=stabilizing_count,
        learning_count=learning_count,
        unique_keys_practiced=len(unique_keys),
        capabilities_introduced=cap_progress,
        self_directed_sessions=self_directed_count,
        current_streak_days=current_streak,
    )

    # Estimate journey stage
    stage_num, stage_name, factors = estimate_journey_stage(metrics)

    return {
        "total_sessions": total_sessions,
        "total_attempts": total_attempts,
        "current_streak_days": current_streak,
        "average_rating": round(avg_rating, 2),
        "spaced_repetition": stats,
        "journey_stage": {
            "stage": stage_num,
            "stage_name": stage_name,
        },
    }


@router.get("/materials")
def get_material_history(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get practice history for each material with mastery level."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()

    # Build attempt history by material
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "id": a.id,
            "rating": a.rating,
            "timestamp": a.timestamp,
            "fatigue": a.fatigue,
            "key": a.key,
        })

    result = []
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, [
            {"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts
        ])

        # Calculate stats for this material
        ratings = [a["rating"] for a in mat_attempts]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        last_practiced = max((a["timestamp"] for a in mat_attempts if a["timestamp"]), default=None)

        result.append({
            "material_id": m.id,
            "material_title": m.title,
            "attempt_count": len(mat_attempts),
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "last_practiced": last_practiced.isoformat() if last_practiced else None,
            "mastery_level": estimate_mastery_level(sr_item),
            "ease_factor": round(sr_item.ease_factor, 2),
            "interval_days": sr_item.interval,
            "next_review": sr_item.next_review.isoformat() if sr_item.next_review else None,
            "is_due": sr_item.is_due(),
        })

    # Sort by due status, then by overdue-ness
    result.sort(key=lambda x: (not x["is_due"], x.get("next_review") or "9999"))

    return result


@router.get("/timeline")
def get_practice_timeline(
    user_id: int = Query(...),
    days: int = Query(default=30),
    db: Session = Depends(get_db)
):
    """Get practice activity over time for visualization."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)

    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user_id,
        PracticeAttempt.timestamp >= cutoff
    ).order_by(PracticeAttempt.timestamp).all()

    # Group by date
    daily_stats = {}
    for a in attempts:
        if not a.timestamp:
            continue
        date_str = a.timestamp.date().isoformat()
        if date_str not in daily_stats:
            daily_stats[date_str] = {"date": date_str, "attempts": 0, "total_rating": 0, "avg_fatigue": 0, "fatigue_sum": 0}
        daily_stats[date_str]["attempts"] += 1
        daily_stats[date_str]["total_rating"] += a.rating
        daily_stats[date_str]["fatigue_sum"] += a.fatigue

    # Calculate averages
    result = []
    for date_str, stats in sorted(daily_stats.items()):
        count = stats["attempts"]
        result.append({
            "date": date_str,
            "attempts": count,
            "avg_rating": round(stats["total_rating"] / count, 2) if count else 0,
            "avg_fatigue": round(stats["fatigue_sum"] / count, 2) if count else 0,
        })

    return result


@router.get("/focus-cards")
def get_focus_card_history(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get practice history grouped by focus card."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    focus_cards = db.query(FocusCard).all()
    fc_map = {fc.id: fc for fc in focus_cards}

    # Group by focus card
    fc_stats = {}
    for a in attempts:
        fc_id = a.focus_card_id
        if fc_id not in fc_stats:
            fc = fc_map.get(fc_id)
            fc_stats[fc_id] = {
                "focus_card_id": fc_id,
                "focus_card_name": fc.name if fc else "Unknown",
                "category": fc.category if fc else "",
                "attempts": 0,
                "ratings": [],
            }
        fc_stats[fc_id]["attempts"] += 1
        fc_stats[fc_id]["ratings"].append(a.rating)

    result = []
    for fc_id, stats in fc_stats.items():
        ratings = stats["ratings"]
        result.append({
            "focus_card_id": fc_id,
            "focus_card_name": stats["focus_card_name"],
            "category": stats["category"],
            "attempt_count": stats["attempts"],
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "best_rating": max(ratings) if ratings else None,
            "recent_trend": "improving" if len(ratings) >= 3 and ratings[-1] > ratings[-3] else (
                "declining" if len(ratings) >= 3 and ratings[-1] < ratings[-3] else "stable"
            ),
        })

    result.sort(key=lambda x: x["attempt_count"], reverse=True)
    return result


@router.get("/due-items")
def get_due_items(user_id: int = Query(...), limit: int = Query(default=10), db: Session = Depends(get_db)):
    """Get materials due for review based on spaced repetition."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()

    # Build attempt history
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        })

    # Build SR items
    sr_items = []
    mat_map = {m.id: m for m in materials}
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, mat_attempts)
        sr_items.append(sr_item)

    # Prioritize by due status
    prioritized = prioritize_materials(sr_items, limit=limit)

    result = []
    for sr_item in prioritized:
        mat = mat_map.get(sr_item.material_id)
        if not mat:
            continue
        result.append({
            "material_id": sr_item.material_id,
            "material_title": mat.title,
            "mastery_level": estimate_mastery_level(sr_item),
            "days_overdue": round(sr_item.days_overdue(), 1),
            "is_due": sr_item.is_due(),
            "interval_days": sr_item.interval,
            "ease_factor": round(sr_item.ease_factor, 2),
        })

    return result


@router.get("/analytics")
def get_session_analytics(user_id: int = Query(...), db: Session = Depends(get_db)):
    """
    Comprehensive session history analytics with capability progress and time spent.

    Returns aggregate stats on:
    - Practice time (total minutes, average session duration)
    - Capability progress (introduced, mastered, by domain)
    - Quality metrics (rating trends, fatigue trends, strain occurrences)
    - Completion stats (mini-session completion rate)
    """
    # --- Time Stats ---
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()

    total_minutes = 0
    session_durations = []
    for s in sessions:
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            if 0 < duration < 180:  # Cap at 3 hours to filter outliers
                total_minutes += duration
                session_durations.append(duration)

    avg_session_minutes = sum(session_durations) / len(session_durations) if session_durations else 0

    # --- Capability Progress (V2) ---
    cap_progress = db.query(UserCapability).filter_by(user_id=user_id).all()
    capabilities = db.query(Capability).all()
    cap_map = {c.id: c for c in capabilities}

    capabilities_introduced = len([cp for cp in cap_progress if cp.introduced_at])
    capabilities_mastered = len([cp for cp in cap_progress if cp.mastered_at])
    mastery_rate = (capabilities_mastered / capabilities_introduced * 100) if capabilities_introduced else 0

    # Group by domain
    domain_stats = {}
    for cp in cap_progress:
        cap = cap_map.get(cp.capability_id)
        if cap:
            domain = cap.domain or "other"
            if domain not in domain_stats:
                domain_stats[domain] = {"introduced": 0, "mastered": 0, "refreshed": 0}
            domain_stats[domain]["introduced"] += 1
            if cp.mastered_at:
                domain_stats[domain]["mastered"] += 1
            domain_stats[domain]["refreshed"] += cp.times_refreshed or 0

    # --- Quality Metrics ---
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).order_by(
        PracticeAttempt.timestamp
    ).all()

    ratings = [a.rating for a in attempts if a.rating is not None]
    fatigues = [a.fatigue for a in attempts if a.fatigue is not None]

    # Recent vs overall rating trend
    overall_avg_rating = sum(ratings) / len(ratings) if ratings else 0
    recent_ratings = ratings[-10:] if len(ratings) >= 10 else ratings
    recent_avg_rating = sum(recent_ratings) / len(recent_ratings) if recent_ratings else 0

    # Fatigue trend
    overall_avg_fatigue = sum(fatigues) / len(fatigues) if fatigues else 0
    recent_fatigues = fatigues[-10:] if len(fatigues) >= 10 else fatigues
    recent_avg_fatigue = sum(recent_fatigues) / len(recent_fatigues) if recent_fatigues else 0

    # Strain occurrences
    mini_sessions = db.query(MiniSession).join(PracticeSession).filter(
        PracticeSession.user_id == user_id
    ).all()
    total_mini_sessions = len(mini_sessions)
    strain_count = sum(1 for ms in mini_sessions if ms.strain_detected)
    strain_rate = (strain_count / total_mini_sessions * 100) if total_mini_sessions else 0

    # --- Completion Stats ---
    completed_mini_sessions = sum(1 for ms in mini_sessions if ms.is_completed)
    completion_rate = (completed_mini_sessions / total_mini_sessions * 100) if total_mini_sessions else 0

    # --- Practice by Day of Week ---
    day_of_week_stats = {i: {"count": 0, "minutes": 0} for i in range(7)}  # 0=Mon, 6=Sun
    for s in sessions:
        if s.started_at:
            dow = s.started_at.weekday()
            day_of_week_stats[dow]["count"] += 1
            if s.ended_at:
                duration = (s.ended_at - s.started_at).total_seconds() / 60
                if 0 < duration < 180:
                    day_of_week_stats[dow]["minutes"] += duration

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    practice_by_day = [
        {"day": day_names[i], "sessions": day_of_week_stats[i]["count"],
         "minutes": round(day_of_week_stats[i]["minutes"], 1)}
        for i in range(7)
    ]

    # --- Rating Distribution ---
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if r in rating_distribution:
            rating_distribution[r] += 1

    return {
        "time_stats": {
            "total_minutes": round(total_minutes, 1),
            "total_sessions": len(sessions),
            "avg_session_minutes": round(avg_session_minutes, 1),
            "total_mini_sessions": total_mini_sessions,
        },
        "capability_progress": {
            "total_introduced": capabilities_introduced,
            "total_available": len(capabilities),
            "total_mastered": capabilities_mastered,
            "mastery_rate": round(mastery_rate, 1),
            "by_domain": domain_stats,
        },
        "quality_metrics": {
            "overall_avg_rating": round(overall_avg_rating, 2),
            "recent_avg_rating": round(recent_avg_rating, 2),
            "rating_trend": "improving" if recent_avg_rating > overall_avg_rating + 0.1 else (
                "declining" if recent_avg_rating < overall_avg_rating - 0.1 else "stable"
            ),
            "overall_avg_fatigue": round(overall_avg_fatigue, 2),
            "recent_avg_fatigue": round(recent_avg_fatigue, 2),
            "fatigue_trend": "increasing" if recent_avg_fatigue > overall_avg_fatigue + 0.2 else (
                "decreasing" if recent_avg_fatigue < overall_avg_fatigue - 0.2 else "stable"
            ),
            "strain_count": strain_count,
            "strain_rate": round(strain_rate, 1),
            "rating_distribution": rating_distribution,
        },
        "completion_stats": {
            "completed_mini_sessions": completed_mini_sessions,
            "total_mini_sessions": total_mini_sessions,
            "completion_rate": round(completion_rate, 1),
        },
        "practice_by_day": practice_by_day,
    }
