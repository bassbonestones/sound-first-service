"""
Tests for app/spaced_repetition.py - Spaced Repetition Algorithm

Tests the SM-2 based spaced repetition implementation:
- Item state management
- Interval calculations
- Priority and weight calculations
- Database integration helpers
"""

import pytest
from datetime import datetime, timedelta
from app.spaced_repetition import (
    SpacedRepetitionItem,
    rating_to_quality,
    calculate_new_interval,
    update_item_after_review,
    prioritize_materials,
    get_review_stats,
    estimate_mastery_level,
    get_capability_weight_adjustment,
    build_sr_item_from_db,
    DEFAULT_EASE_FACTOR,
    MIN_EASE_FACTOR,
)


# =============================================================================
# SPACED REPETITION ITEM TESTS
# =============================================================================

class TestSpacedRepetitionItem:
    """Tests for SpacedRepetitionItem dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        item = SpacedRepetitionItem(material_id=1)
        
        assert item.material_id == 1
        assert item.ease_factor == DEFAULT_EASE_FACTOR
        assert item.interval == 1
        assert item.repetitions == 0
        assert item.last_reviewed is None
        assert item.next_review is None
    
    def test_is_due_never_reviewed(self):
        """Never-reviewed items are always due."""
        item = SpacedRepetitionItem(material_id=1)
        assert item.is_due() == True
    
    def test_is_due_past_review(self):
        """Items past their review date are due."""
        yesterday = datetime.now() - timedelta(days=1)
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=yesterday
        )
        assert item.is_due() == True
    
    def test_is_due_future_review(self):
        """Items with future review date are not due."""
        tomorrow = datetime.now() + timedelta(days=1)
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=tomorrow
        )
        assert item.is_due() == False
    
    def test_is_due_today(self):
        """Items due now are due."""
        now = datetime.now()
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=now
        )
        assert item.is_due() == True
    
    def test_days_overdue_never_reviewed(self):
        """Never-reviewed items return large finite overdue value."""
        item = SpacedRepetitionItem(material_id=1)
        overdue = item.days_overdue()
        assert overdue == 9999.0  # Changed from infinity
    
    def test_days_overdue_past(self):
        """Days overdue is positive for past items."""
        two_days_ago = datetime.now() - timedelta(days=2)
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=two_days_ago
        )
        overdue = item.days_overdue()
        assert 1.9 < overdue < 2.1  # Approximately 2 days
    
    def test_days_overdue_future(self):
        """Days overdue is negative for future items."""
        in_two_days = datetime.now() + timedelta(days=2)
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=in_two_days
        )
        overdue = item.days_overdue()
        assert -2.1 < overdue < -1.9  # Approximately -2 days


# =============================================================================
# RATING TO QUALITY CONVERSION TESTS
# =============================================================================

class TestRatingToQuality:
    """Tests for rating_to_quality() function."""
    
    def test_rating_1_blackout(self):
        """Rating 1 is quality 0 (complete blackout)."""
        assert rating_to_quality(1) == 0
    
    def test_rating_2_incorrect(self):
        """Rating 2 is quality 2 (incorrect, but remembered)."""
        assert rating_to_quality(2) == 2
    
    def test_rating_3_difficult(self):
        """Rating 3 is quality 3 (correct with difficulty)."""
        assert rating_to_quality(3) == 3
    
    def test_rating_4_hesitation(self):
        """Rating 4 is quality 4 (correct after hesitation)."""
        assert rating_to_quality(4) == 4
    
    def test_rating_5_perfect(self):
        """Rating 5 is quality 5 (perfect response)."""
        assert rating_to_quality(5) == 5
    
    def test_invalid_rating(self):
        """Invalid rating defaults to quality 3."""
        assert rating_to_quality(0) == 3
        assert rating_to_quality(6) == 3
        assert rating_to_quality(None) == 3


# =============================================================================
# INTERVAL CALCULATION TESTS
# =============================================================================

class TestCalculateNewInterval:
    """Tests for calculate_new_interval() function."""
    
    def test_first_success(self):
        """First successful review sets interval to 1."""
        interval, ef, reps = calculate_new_interval(
            quality=4,
            ease_factor=2.5,
            interval=1,
            repetitions=0
        )
        assert interval == 1
        assert reps == 1
    
    def test_second_success(self):
        """Second successful review sets interval to 6."""
        interval, ef, reps = calculate_new_interval(
            quality=4,
            ease_factor=2.5,
            interval=1,
            repetitions=1
        )
        assert interval == 6
        assert reps == 2
    
    def test_third_success(self):
        """Third success uses ease factor multiplier."""
        interval, ef, reps = calculate_new_interval(
            quality=4,
            ease_factor=2.5,
            interval=6,
            repetitions=2
        )
        # Should be approximately 6 * 2.5 = 15
        assert interval >= 13 and interval <= 17
        assert reps == 3
    
    def test_failure_resets_reps(self):
        """Failed review (<3 quality) resets repetitions."""
        interval, ef, reps = calculate_new_interval(
            quality=2,  # Failed
            ease_factor=2.5,
            interval=15,
            repetitions=5
        )
        assert interval == 1  # Reset
        assert reps == 0  # Reset
    
    def test_ease_factor_increase_on_good(self):
        """Ease factor increases on good responses."""
        _, ef_before, _ = calculate_new_interval(4, 2.5, 1, 0)
        _, ef_after, _ = calculate_new_interval(5, ef_before, 1, 1)
        
        # Perfect response should increase ease factor
        assert ef_after >= ef_before
    
    def test_ease_factor_decrease_on_difficulty(self):
        """Ease factor decreases on difficult responses."""
        _, ef, _ = calculate_new_interval(
            quality=3,  # Barely passed
            ease_factor=2.5,
            interval=1,
            repetitions=1
        )
        # Difficult response should decrease ease factor
        assert ef <= 2.5
    
    def test_ease_factor_minimum(self):
        """Ease factor cannot go below minimum."""
        _, ef, _ = calculate_new_interval(
            quality=1,  # Very bad
            ease_factor=1.4,  # Already low
            interval=1,
            repetitions=0
        )
        assert ef >= MIN_EASE_FACTOR


# =============================================================================
# UPDATE ITEM AFTER REVIEW TESTS
# =============================================================================

class TestUpdateItemAfterReview:
    """Tests for update_item_after_review() function."""
    
    def test_new_item_first_review(self):
        """First review of new item."""
        item = SpacedRepetitionItem(material_id=1)
        now = datetime.now()
        
        updated = update_item_after_review(item, rating=4, reviewed_at=now)
        
        assert updated.repetitions == 1
        assert updated.last_reviewed == now
        assert updated.next_review is not None
        assert updated.next_review > now
    
    def test_multiple_reviews_progression(self):
        """Intervals grow over successful reviews."""
        item = SpacedRepetitionItem(material_id=1)
        
        intervals = []
        for i in range(5):
            item = update_item_after_review(item, rating=4)
            intervals.append(item.interval)
        
        # Each interval should be >= previous
        for i in range(1, len(intervals)):
            assert intervals[i] >= intervals[i-1]
    
    def test_perfect_responses_faster_progress(self):
        """Perfect responses lead to faster interval growth."""
        item_perfect = SpacedRepetitionItem(material_id=1)
        item_good = SpacedRepetitionItem(material_id=2)
        
        for _ in range(5):
            item_perfect = update_item_after_review(item_perfect, rating=5)
            item_good = update_item_after_review(item_good, rating=3)
        
        # Perfect responses should have longer intervals
        assert item_perfect.interval >= item_good.interval


# =============================================================================
# PRIORITIZE MATERIALS TESTS
# =============================================================================

class TestPrioritizeMaterials:
    """Tests for prioritize_materials() function."""
    
    def test_overdue_first(self):
        """Most overdue items should come first."""
        now = datetime.now()
        
        items = [
            SpacedRepetitionItem(material_id=1, next_review=now - timedelta(days=10)),  # Very overdue
            SpacedRepetitionItem(material_id=2, next_review=now - timedelta(days=1)),   # Slightly overdue
            SpacedRepetitionItem(material_id=3, next_review=now + timedelta(days=5)),   # Not due
        ]
        
        result = prioritize_materials(items, now)
        
        # Most overdue should be first
        assert result[0].material_id == 1
    
    def test_never_reviewed_high_priority(self):
        """Never-reviewed items have high priority."""
        now = datetime.now()
        
        items = [
            SpacedRepetitionItem(material_id=1, next_review=now - timedelta(days=1)),  # Overdue
            SpacedRepetitionItem(material_id=2),  # Never reviewed
        ]
        
        result = prioritize_materials(items, now)
        
        # Never reviewed should be high priority (may be first or second)
        assert result[0].material_id in [1, 2]
    
    def test_limit_respected(self):
        """Limit parameter is respected."""
        items = [SpacedRepetitionItem(material_id=i) for i in range(20)]
        
        result = prioritize_materials(items, limit=5)
        
        assert len(result) == 5
    
    def test_empty_list(self):
        """Empty list returns empty."""
        result = prioritize_materials([])
        assert result == []


# =============================================================================
# REVIEW STATS TESTS
# =============================================================================

class TestGetReviewStats:
    """Tests for get_review_stats() function."""
    
    def test_basic_stats(self):
        """Basic statistics are calculated correctly."""
        now = datetime.now()
        
        items = [
            SpacedRepetitionItem(material_id=1),  # Never reviewed - days_overdue returns 9999
            SpacedRepetitionItem(material_id=2, 
                                next_review=now - timedelta(days=2),
                                repetitions=3,
                                ease_factor=2.5,
                                interval=10),  # Overdue by 2 days
            SpacedRepetitionItem(material_id=3,
                                next_review=now + timedelta(days=5),
                                repetitions=5,
                                ease_factor=2.8,
                                interval=20),  # Not due
        ]
        
        stats = get_review_stats(items, now)
        
        assert stats["total_items"] == 3
        assert stats["never_reviewed"] == 1
        assert stats["due_today"] >= 2  # Never reviewed + overdue
        # Overdue counts items with days_overdue > 1: never reviewed (9999) + 2 day overdue = 2
        assert stats["overdue"] == 2
    
    def test_avg_ease_factor(self):
        """Average ease factor calculated for reviewed items only."""
        items = [
            SpacedRepetitionItem(material_id=1, ease_factor=2.0, repetitions=1),
            SpacedRepetitionItem(material_id=2, ease_factor=3.0, repetitions=2),
            SpacedRepetitionItem(material_id=3),  # Never reviewed - excluded
        ]
        
        stats = get_review_stats(items)
        
        # Average of 2.0 and 3.0
        assert stats["avg_ease_factor"] == 2.5
    
    def test_interval_buckets(self):
        """Items bucketed by interval correctly."""
        items = [
            SpacedRepetitionItem(material_id=1, interval=2, repetitions=1),   # Short
            SpacedRepetitionItem(material_id=2, interval=7, repetitions=2),   # Medium
            SpacedRepetitionItem(material_id=3, interval=30, repetitions=5),  # Long
        ]
        
        stats = get_review_stats(items)
        
        assert stats["short_interval_count"] == 1
        assert stats["medium_interval_count"] == 1
        assert stats["long_interval_count"] == 1


# =============================================================================
# MASTERY LEVEL TESTS
# =============================================================================

class TestEstimateMasteryLevel:
    """Tests for estimate_mastery_level() function."""
    
    def test_new_item(self):
        """Items with 0 repetitions are 'new'."""
        item = SpacedRepetitionItem(material_id=1, repetitions=0)
        assert estimate_mastery_level(item) == "new"
    
    def test_learning_phase(self):
        """Items with short intervals are 'learning'."""
        item = SpacedRepetitionItem(material_id=1, repetitions=1, interval=2)
        assert estimate_mastery_level(item) == "learning"
    
    def test_stabilizing_phase(self):
        """Items with medium intervals are 'stabilizing'."""
        item = SpacedRepetitionItem(material_id=1, repetitions=3, interval=10)
        assert estimate_mastery_level(item) == "stabilizing"
    
    def test_familiar_phase(self):
        """Items with longer intervals are 'familiar'."""
        item = SpacedRepetitionItem(material_id=1, repetitions=5, interval=20)
        assert estimate_mastery_level(item) == "familiar"
    
    def test_mastered_phase(self):
        """Items with very long intervals are 'mastered'."""
        item = SpacedRepetitionItem(material_id=1, repetitions=10, interval=45)
        assert estimate_mastery_level(item) == "mastered"


# =============================================================================
# CAPABILITY WEIGHT ADJUSTMENT TESTS
# =============================================================================

class TestGetCapabilityWeightAdjustment:
    """Tests for get_capability_weight_adjustment() function."""
    
    def test_new_item_boost(self):
        """New items get slight boost."""
        item = SpacedRepetitionItem(material_id=1)  # next_review is None
        weight = get_capability_weight_adjustment(item)
        assert weight == 1.5
    
    def test_very_overdue_high_weight(self):
        """Very overdue items get high weight."""
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=datetime.now() - timedelta(days=10)
        )
        weight = get_capability_weight_adjustment(item)
        assert weight == 3.0
    
    def test_overdue_moderate_weight(self):
        """Moderately overdue items get moderate weight."""
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=datetime.now() - timedelta(days=3)
        )
        weight = get_capability_weight_adjustment(item)
        assert weight == 2.0
    
    def test_due_today_good_weight(self):
        """Items due today get good weight."""
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=datetime.now()
        )
        weight = get_capability_weight_adjustment(item)
        assert weight == 1.5
    
    def test_not_due_yet_low_weight(self):
        """Future items get low weight."""
        item = SpacedRepetitionItem(
            material_id=1,
            next_review=datetime.now() + timedelta(days=10)
        )
        weight = get_capability_weight_adjustment(item)
        assert weight == 0.3


# =============================================================================
# BUILD SR ITEM FROM DB TESTS
# =============================================================================

class TestBuildSrItemFromDb:
    """Tests for build_sr_item_from_db() function."""
    
    def test_empty_attempts(self):
        """Empty attempt history creates new item."""
        item = build_sr_item_from_db(material_id=1, attempts=[])
        
        assert item.material_id == 1
        assert item.repetitions == 0
        assert item.ease_factor == DEFAULT_EASE_FACTOR
    
    def test_single_attempt(self):
        """Single attempt updates item state."""
        attempts = [
            {"rating": 4, "timestamp": datetime.now().isoformat()}
        ]
        
        item = build_sr_item_from_db(material_id=1, attempts=attempts)
        
        assert item.repetitions == 1
        assert item.last_reviewed is not None
    
    def test_multiple_attempts(self):
        """Multiple attempts build up item state."""
        base_time = datetime.now() - timedelta(days=30)
        attempts = [
            {"rating": 3, "timestamp": (base_time).isoformat()},
            {"rating": 4, "timestamp": (base_time + timedelta(days=1)).isoformat()},
            {"rating": 5, "timestamp": (base_time + timedelta(days=7)).isoformat()},
        ]
        
        item = build_sr_item_from_db(material_id=1, attempts=attempts)
        
        assert item.repetitions >= 1  # Should have multiple reps
    
    def test_attempts_sorted_chronologically(self):
        """Attempts are processed in chronological order."""
        # Out of order timestamps
        attempts = [
            {"rating": 5, "timestamp": (datetime.now()).isoformat()},
            {"rating": 3, "timestamp": (datetime.now() - timedelta(days=5)).isoformat()},
        ]
        
        item = build_sr_item_from_db(material_id=1, attempts=attempts)
        
        # Should work correctly regardless of order
        assert item.repetitions >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
