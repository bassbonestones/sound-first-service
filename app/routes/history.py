"""History and analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession
import datetime

from app.db import get_db
from app.models.core import Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt
from app.models.capability_schema import Capability, UserCapability
from app.spaced_repetition import (
    build_sr_item_from_db,
    get_review_stats,
    estimate_mastery_level,
    prioritize_materials,
)
from app.services import UserService

router = APIRouter(prefix="/history", tags=["history"])


def _build_attempt_history(attempts):
    """Build attempt history dict from list of attempts."""
    history = {}
    for a in attempts:
        if a.material_id not in history:
            history[a.material_id] = []
        history[a.material_id].append({
            "id": getattr(a, 'id', None),
            "rating": a.rating,
            "timestamp": a.timestamp,
            "fatigue": a.fatigue,
            "key": getattr(a, 'key', None),
        })
    return history


@router.get("/summary")
def get_history_summary(user_id: int = Query(...), db: DbSession = Depends(get_db)):
    """Get practice history summary with spaced repetition stats."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()
    
    attempt_history = _build_attempt_history(attempts)
    
    # Build SR items and calculate mastery stats
    sr_items = []
    mastery_counts = {"mastered": 0, "familiar": 0, "stabilizing": 0, "learning": 0}
    
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_data = [{"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts]
        sr_item = build_sr_item_from_db(m.id, sr_data)
        sr_items.append(sr_item)
        
        if mat_attempts:
            mastery = estimate_mastery_level(sr_item)
            if mastery in mastery_counts:
                mastery_counts[mastery] += 1
            elif mastery == "new":
                mastery_counts["learning"] += 1
    
    # Use UserService for journey metrics
    journey_result = UserService.estimate_journey_stage(user_id, db)
    
    # Calculate current streak
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
    current_streak = _calculate_streak(sessions)
    
    ratings = [a.rating for a in attempts if a.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    return {
        "total_sessions": len(sessions),
        "total_attempts": len(attempts),
        "current_streak_days": current_streak,
        "average_rating": round(avg_rating, 2),
        "spaced_repetition": get_review_stats(sr_items),
        "journey_stage": {
            "stage": journey_result.stage,
            "stage_name": journey_result.stage_name,
        },
    }


def _calculate_streak(sessions):
    """Calculate current practice streak."""
    if not sessions:
        return 0
    
    today = datetime.datetime.now().date()
    session_dates = {s.started_at.date() for s in sessions if s.started_at}
    
    streak = 0
    check_date = today
    while check_date in session_dates:
        streak += 1
        check_date -= datetime.timedelta(days=1)
    
    return streak


@router.get("/materials")
def get_material_history(user_id: int = Query(...), db: DbSession = Depends(get_db)):
    """Get practice history for each material with mastery level."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()
    
    attempt_history = _build_attempt_history(attempts)
    
    result = []
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_data = [{"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts]
        sr_item = build_sr_item_from_db(m.id, sr_data)
        
        ratings = [a["rating"] for a in mat_attempts if a["rating"] is not None]
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
    
    result.sort(key=lambda x: (not x["is_due"], x.get("next_review") or "9999"))
    return result


@router.get("/timeline")
def get_practice_timeline(
    user_id: int = Query(...),
    days: int = Query(default=30),
    db: DbSession = Depends(get_db)
):
    """Get practice activity over time for visualization."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user_id,
        PracticeAttempt.timestamp >= cutoff
    ).order_by(PracticeAttempt.timestamp).all()
    
    daily_stats = {}
    for a in attempts:
        if not a.timestamp:
            continue
        date_str = a.timestamp.date().isoformat()
        if date_str not in daily_stats:
            daily_stats[date_str] = {"attempts": 0, "total_rating": 0, "fatigue_sum": 0}
        daily_stats[date_str]["attempts"] += 1
        daily_stats[date_str]["total_rating"] += a.rating or 0
        daily_stats[date_str]["fatigue_sum"] += a.fatigue or 0
    
    return [
        {
            "date": date_str,
            "attempts": stats["attempts"],
            "avg_rating": round(stats["total_rating"] / stats["attempts"], 2) if stats["attempts"] else 0,
            "avg_fatigue": round(stats["fatigue_sum"] / stats["attempts"], 2) if stats["attempts"] else 0,
        }
        for date_str, stats in sorted(daily_stats.items())
    ]


@router.get("/focus-cards")
def get_focus_card_history(user_id: int = Query(...), db: DbSession = Depends(get_db)):
    """Get practice history grouped by focus card."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    focus_cards = db.query(FocusCard).all()
    fc_map = {fc.id: fc for fc in focus_cards}
    
    fc_stats = {}
    for a in attempts:
        fc_id = a.focus_card_id
        if fc_id not in fc_stats:
            fc = fc_map.get(fc_id)
            fc_stats[fc_id] = {
                "focus_card_id": fc_id,
                "focus_card_name": fc.name if fc else "Unknown",
                "category": fc.category if fc else "",
                "ratings": [],
            }
        fc_stats[fc_id]["ratings"].append(a.rating)
    
    result = []
    for fc_id, stats in fc_stats.items():
        ratings = [r for r in stats["ratings"] if r is not None]
        result.append({
            "focus_card_id": fc_id,
            "focus_card_name": stats["focus_card_name"],
            "category": stats["category"],
            "attempt_count": len(stats["ratings"]),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "best_rating": max(ratings) if ratings else None,
            "recent_trend": _calculate_trend(ratings),
        })
    
    result.sort(key=lambda x: x["attempt_count"], reverse=True)
    return result


def _calculate_trend(values):
    """Calculate trend from list of values."""
    if len(values) < 3:
        return "stable"
    if values[-1] > values[-3]:
        return "improving"
    if values[-1] < values[-3]:
        return "declining"
    return "stable"


@router.get("/due-items")
def get_due_items(user_id: int = Query(...), limit: int = Query(default=10), db: DbSession = Depends(get_db)):
    """Get materials due for review based on spaced repetition."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()
    
    attempt_history = {a.material_id: [] for a in attempts}
    for a in attempts:
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        })
    
    mat_map = {m.id: m for m in materials}
    sr_items = [build_sr_item_from_db(m.id, attempt_history.get(m.id, [])) for m in materials]
    
    prioritized = prioritize_materials(sr_items, limit=limit)
    
    return [
        {
            "material_id": sr_item.material_id,
            "material_title": mat_map[sr_item.material_id].title if sr_item.material_id in mat_map else "Unknown",
            "mastery_level": estimate_mastery_level(sr_item),
            "days_overdue": round(sr_item.days_overdue(), 1),
            "is_due": sr_item.is_due(),
            "interval_days": sr_item.interval,
            "ease_factor": round(sr_item.ease_factor, 2),
        }
        for sr_item in prioritized
        if sr_item.material_id in mat_map
    ]


@router.get("/analytics")
def get_session_analytics(user_id: int = Query(...), db: DbSession = Depends(get_db)):
    """Comprehensive session history analytics."""
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).order_by(PracticeAttempt.timestamp).all()
    mini_sessions = db.query(MiniSession).join(PracticeSession).filter(PracticeSession.user_id == user_id).all()
    
    # Time stats
    time_stats = _calculate_time_stats(sessions)
    
    # Capability progress
    cap_stats = _calculate_capability_stats(user_id, db)
    
    # Quality metrics
    quality_metrics = _calculate_quality_metrics(attempts, mini_sessions)
    
    # Completion stats
    completed = sum(1 for ms in mini_sessions if ms.is_completed)
    total = len(mini_sessions)
    
    # Practice by day of week
    practice_by_day = _calculate_practice_by_day(sessions)
    
    return {
        "time_stats": time_stats,
        "capability_progress": cap_stats,
        "quality_metrics": quality_metrics,
        "completion_stats": {
            "completed_mini_sessions": completed,
            "total_mini_sessions": total,
            "completion_rate": round(completed / total * 100, 1) if total else 0,
        },
        "practice_by_day": practice_by_day,
    }


def _calculate_time_stats(sessions):
    """Calculate time-related statistics."""
    total_minutes = 0
    session_durations = []
    
    for s in sessions:
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            if 0 < duration < 180:
                total_minutes += duration
                session_durations.append(duration)
    
    return {
        "total_minutes": round(total_minutes, 1),
        "total_sessions": len(sessions),
        "avg_session_minutes": round(sum(session_durations) / len(session_durations), 1) if session_durations else 0,
    }


def _calculate_capability_stats(user_id: int, db: DbSession):
    """Calculate capability progress statistics."""
    cap_progress = db.query(UserCapability).filter_by(user_id=user_id).all()
    capabilities = db.query(Capability).all()
    cap_map = {c.id: c for c in capabilities}
    
    introduced = len([cp for cp in cap_progress if cp.introduced_at])
    mastered = len([cp for cp in cap_progress if cp.mastered_at])
    
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
    
    return {
        "total_introduced": introduced,
        "total_available": len(capabilities),
        "total_mastered": mastered,
        "mastery_rate": round(mastered / introduced * 100, 1) if introduced else 0,
        "by_domain": domain_stats,
    }


def _calculate_quality_metrics(attempts, mini_sessions):
    """Calculate quality-related metrics."""
    ratings = [a.rating for a in attempts if a.rating is not None]
    fatigues = [a.fatigue for a in attempts if a.fatigue is not None]
    
    overall_rating = sum(ratings) / len(ratings) if ratings else 0
    recent_ratings = ratings[-10:] if len(ratings) >= 10 else ratings
    recent_rating = sum(recent_ratings) / len(recent_ratings) if recent_ratings else 0
    
    overall_fatigue = sum(fatigues) / len(fatigues) if fatigues else 0
    recent_fatigues = fatigues[-10:] if len(fatigues) >= 10 else fatigues
    recent_fatigue = sum(recent_fatigues) / len(recent_fatigues) if recent_fatigues else 0
    
    strain_count = sum(1 for ms in mini_sessions if ms.strain_detected)
    total_mini = len(mini_sessions)
    
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if r in rating_dist:
            rating_dist[r] += 1
    
    return {
        "overall_avg_rating": round(overall_rating, 2),
        "recent_avg_rating": round(recent_rating, 2),
        "rating_trend": "improving" if recent_rating > overall_rating + 0.1 else (
            "declining" if recent_rating < overall_rating - 0.1 else "stable"),
        "overall_avg_fatigue": round(overall_fatigue, 2),
        "recent_avg_fatigue": round(recent_fatigue, 2),
        "fatigue_trend": "increasing" if recent_fatigue > overall_fatigue + 0.2 else (
            "decreasing" if recent_fatigue < overall_fatigue - 0.2 else "stable"),
        "strain_count": strain_count,
        "strain_rate": round(strain_count / total_mini * 100, 1) if total_mini else 0,
        "rating_distribution": rating_dist,
    }


def _calculate_practice_by_day(sessions):
    """Calculate practice statistics by day of week."""
    day_stats = {i: {"count": 0, "minutes": 0} for i in range(7)}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for s in sessions:
        if s.started_at:
            dow = s.started_at.weekday()
            day_stats[dow]["count"] += 1
            if s.ended_at:
                duration = (s.ended_at - s.started_at).total_seconds() / 60
                if 0 < duration < 180:
                    day_stats[dow]["minutes"] += duration
    
    return [
        {"day": day_names[i], "sessions": day_stats[i]["count"], "minutes": round(day_stats[i]["minutes"], 1)}
        for i in range(7)
    ]
