"""
Spaced Repetition Algorithm for Sound First
Based on SM-2 algorithm with musical practice adaptations.

Key concepts:
- Ease Factor (EF): How easy/difficult material is for the user (starts at 2.5)
- Interval: Days until next review
- Quality: User's rating (1-5) converted to quality score (0-5)
- Musical adaptations: Factor in fatigue, capability type, range safety
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Default values
DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
DEFAULT_INTERVAL = 1  # days


@dataclass
class SpacedRepetitionItem:
    """Represents an item's spaced repetition state."""
    material_id: int
    ease_factor: float = DEFAULT_EASE_FACTOR
    interval: int = DEFAULT_INTERVAL  # in days
    repetitions: int = 0
    last_reviewed: Optional[datetime] = None
    next_review: Optional[datetime] = None
    
    def is_due(self, now: datetime = None) -> bool:
        """Check if item is due for review."""
        if now is None:
            now = datetime.now()
        if self.next_review is None:
            return True
        return now >= self.next_review
    
    def days_overdue(self, now: datetime = None) -> float:
        """How many days overdue (negative if not yet due)."""
        if now is None:
            now = datetime.now()
        if self.next_review is None:
            return 9999.0  # Never reviewed - use large finite number
        return (now - self.next_review).total_seconds() / 86400


def rating_to_quality(rating: int) -> int:
    """
    Convert 1-5 rating to SM-2 quality score (0-5).
    
    Rating 1 = quality 0 (complete blackout)
    Rating 2 = quality 2 (incorrect, but upon seeing correct answer, it seemed easy)
    Rating 3 = quality 3 (correct with serious difficulty)
    Rating 4 = quality 4 (correct after hesitation)
    Rating 5 = quality 5 (perfect response)
    """
    mapping = {1: 0, 2: 2, 3: 3, 4: 4, 5: 5}
    return mapping.get(rating, 3)


def calculate_new_interval(
    quality: int,
    ease_factor: float,
    interval: int,
    repetitions: int
) -> Tuple[int, float, int]:
    """
    SM-2 algorithm calculation.
    
    Returns: (new_interval, new_ease_factor, new_repetitions)
    """
    # Update ease factor
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(MIN_EASE_FACTOR, new_ef)
    
    if quality < 3:
        # Failed - reset repetitions, short interval
        return (1, new_ef, 0)
    
    # Passed - calculate new interval
    if repetitions == 0:
        new_interval = 1
    elif repetitions == 1:
        new_interval = 6
    else:
        new_interval = round(interval * new_ef)
    
    return (new_interval, new_ef, repetitions + 1)


def update_item_after_review(
    item: SpacedRepetitionItem,
    rating: int,
    reviewed_at: datetime = None
) -> SpacedRepetitionItem:
    """
    Update an item's spaced repetition state after a review.
    """
    if reviewed_at is None:
        reviewed_at = datetime.now()
    
    quality = rating_to_quality(rating)
    new_interval, new_ef, new_reps = calculate_new_interval(
        quality, item.ease_factor, item.interval, item.repetitions
    )
    
    item.ease_factor = new_ef
    item.interval = new_interval
    item.repetitions = new_reps
    item.last_reviewed = reviewed_at
    item.next_review = reviewed_at + timedelta(days=new_interval)
    
    return item


def prioritize_materials(
    items: List[SpacedRepetitionItem],
    now: datetime = None,
    limit: int = 10
) -> List[SpacedRepetitionItem]:
    """
    Sort materials by review priority.
    
    Priority order:
    1. Most overdue items first
    2. Never-reviewed items second
    3. Items due today third
    4. Future items last (but included if needed)
    """
    if now is None:
        now = datetime.now()
    
    def priority_score(item: SpacedRepetitionItem) -> float:
        if item.next_review is None:
            return -1000  # Never reviewed - high priority
        
        days_overdue = item.days_overdue(now)
        if days_overdue > 0:
            return -days_overdue * 100  # More overdue = lower score = higher priority
        else:
            return -days_overdue  # Future items get positive scores
    
    sorted_items = sorted(items, key=priority_score)
    return sorted_items[:limit]


def get_review_stats(items: List[SpacedRepetitionItem], now: datetime = None) -> Dict:
    """
    Calculate review statistics.
    """
    if now is None:
        now = datetime.now()
    
    due_today = sum(1 for item in items if item.is_due(now))
    overdue = sum(1 for item in items if item.days_overdue(now) > 1)
    never_reviewed = sum(1 for item in items if item.next_review is None)
    
    # Average ease factor (excluding never-reviewed)
    reviewed_items = [item for item in items if item.repetitions > 0]
    avg_ease = sum(item.ease_factor for item in reviewed_items) / len(reviewed_items) if reviewed_items else DEFAULT_EASE_FACTOR
    
    # Items by interval bucket
    short_interval = sum(1 for item in items if item.interval <= 3 and item.repetitions > 0)
    medium_interval = sum(1 for item in items if 3 < item.interval <= 14 and item.repetitions > 0)
    long_interval = sum(1 for item in items if item.interval > 14 and item.repetitions > 0)
    
    return {
        "total_items": len(items),
        "due_today": due_today,
        "overdue": overdue,
        "never_reviewed": never_reviewed,
        "avg_ease_factor": round(avg_ease, 2),
        "short_interval_count": short_interval,  # Learning phase
        "medium_interval_count": medium_interval,  # Stabilizing
        "long_interval_count": long_interval,  # Mastered
    }


def estimate_mastery_level(item: SpacedRepetitionItem) -> str:
    """
    Estimate mastery level based on spaced repetition state.
    """
    if item.repetitions == 0:
        return "new"
    elif item.interval <= 3:
        return "learning"
    elif item.interval <= 14:
        return "stabilizing"
    elif item.interval <= 30:
        return "familiar"
    else:
        return "mastered"


def get_capability_weight_adjustment(item: SpacedRepetitionItem) -> float:
    """
    Adjust selection weight based on SR state.
    Due/overdue items get higher weight.
    """
    if item.next_review is None:
        return 1.5  # New items slightly boosted
    
    days_overdue = item.days_overdue()
    if days_overdue > 7:
        return 3.0  # Very overdue - high priority
    elif days_overdue > 1:
        return 2.0  # Overdue
    elif days_overdue >= 0:
        return 1.5  # Due today
    elif days_overdue > -3:
        return 0.8  # Coming up soon
    else:
        return 0.3  # Not due for a while


# ============================================================
# Database Integration Helpers
# ============================================================

def build_sr_item_from_db(material_id: int, attempts: List[Dict]) -> SpacedRepetitionItem:
    """
    Build SpacedRepetitionItem from practice attempt history.
    
    This reconstructs SR state from the attempt log, simulating
    what the state would be if SR was applied to each review.
    """
    item = SpacedRepetitionItem(material_id=material_id)
    
    # Sort attempts by timestamp
    sorted_attempts = sorted(attempts, key=lambda a: a.get('timestamp') or datetime.min)
    
    for attempt in sorted_attempts:
        rating = attempt.get('rating', 3)
        timestamp = attempt.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                timestamp = datetime.now()
        item = update_item_after_review(item, rating, timestamp)
    
    return item


def select_materials_with_sr(
    all_materials: List[Dict],
    attempt_history: Dict[int, List[Dict]],
    count: int = 5,
    novelty_ratio: float = 0.2
) -> List[Dict]:
    """
    Select materials using spaced repetition prioritization.
    
    Args:
        all_materials: List of material dicts with 'id' key
        attempt_history: Dict mapping material_id -> list of attempts
        count: Number of materials to select
        novelty_ratio: Fraction of selections to be new materials
    
    Returns:
        List of selected material dicts
    """
    import random
    
    # Build SR items for all materials
    sr_items = {}
    for mat in all_materials:
        mat_id = mat['id']
        attempts = attempt_history.get(mat_id, [])
        sr_items[mat_id] = build_sr_item_from_db(mat_id, attempts)
    
    # Split into new vs reviewed
    new_materials = [m for m in all_materials if sr_items[m['id']].repetitions == 0]
    reviewed_materials = [m for m in all_materials if sr_items[m['id']].repetitions > 0]
    
    # Calculate how many of each to select
    novelty_count = max(1, int(count * novelty_ratio)) if new_materials else 0
    review_count = count - novelty_count
    
    selected = []
    
    # Select new materials (novelty)
    if novelty_count > 0 and new_materials:
        selected.extend(random.sample(new_materials, min(novelty_count, len(new_materials))))
    
    # Select review materials (weighted by SR priority)
    if review_count > 0 and reviewed_materials:
        # Weight by overdue-ness
        weights = [get_capability_weight_adjustment(sr_items[m['id']]) for m in reviewed_materials]
        total_weight = sum(weights)
        if total_weight > 0:
            probs = [w / total_weight for w in weights]
            # Sample without replacement
            review_count = min(review_count, len(reviewed_materials))
            indices = list(range(len(reviewed_materials)))
            chosen_indices = []
            for _ in range(review_count):
                if not indices:
                    break
                # Weighted choice
                r = random.random() * sum(probs[i] for i in indices)
                cumsum = 0
                for i in indices:
                    cumsum += probs[i]
                    if r <= cumsum:
                        chosen_indices.append(i)
                        indices.remove(i)
                        break
            selected.extend([reviewed_materials[i] for i in chosen_indices])
    
    # If we still need more, add from remaining
    remaining_count = count - len(selected)
    if remaining_count > 0:
        remaining = [m for m in all_materials if m not in selected]
        if remaining:
            selected.extend(random.sample(remaining, min(remaining_count, len(remaining))))
    
    return selected
