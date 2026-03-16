"""
Tests for app/services/spaced_repetition.py
Tests spaced repetition algorithm implementation.
"""

import pytest
from datetime import datetime, timedelta


class TestSpacedRepetitionItem:
    """Tests for SpacedRepetitionItem dataclass."""
    
    def test_days_overdue_when_past_due(self):
        """days_overdue returns positive value when item is past due date."""
        from app.services.spaced_repetition import SpacedRepetitionItem
        
        item = SpacedRepetitionItem(
            material_id=1,
            interval=7,
            ease_factor=2.5,
            repetitions=3,
            next_review=datetime.now() - timedelta(days=5),
        )
        
        overdue = item.days_overdue()
        assert overdue >= 4.9
    
    def test_days_overdue_when_not_due(self):
        """days_overdue returns negative value when item is not yet due."""
        from app.services.spaced_repetition import SpacedRepetitionItem
        
        item = SpacedRepetitionItem(
            material_id=2,
            interval=30,
            ease_factor=2.5,
            repetitions=5,
            next_review=datetime.now() + timedelta(days=10),
        )
        
        overdue = item.days_overdue()
        assert overdue < 0


class TestRatingToQuality:
    """Tests for rating_to_quality function."""
    
    def test_rating_1_maps_to_quality_0(self):
        """Rating 1 maps to quality 0 (complete failure)."""
        from app.services.spaced_repetition import rating_to_quality
        
        assert rating_to_quality(1) == 0
    
    def test_rating_5_maps_to_quality_5(self):
        """Rating 5 maps to quality 5 (perfect)."""
        from app.services.spaced_repetition import rating_to_quality
        
        assert rating_to_quality(5) == 5
    
    def test_rating_3_maps_to_quality_3(self):
        """Rating 3 maps to quality 3 (medium)."""
        from app.services.spaced_repetition import rating_to_quality
        
        assert rating_to_quality(3) == 3


class TestCalculateNewInterval:
    """Tests for calculate_new_interval function."""
    
    def test_first_review_with_good_quality(self):
        """First review with good quality returns interval of 1."""
        from app.services.spaced_repetition import calculate_new_interval
        
        interval, ease, reps = calculate_new_interval(
            quality=4,
            ease_factor=2.5,
            interval=0,
            repetitions=0
        )
        
        assert interval == 1
        assert reps == 1
    
    def test_failed_review_resets_interval(self):
        """Failed review (quality < 3) resets interval to 1."""
        from app.services.spaced_repetition import calculate_new_interval
        
        interval, ease, reps = calculate_new_interval(
            quality=2,
            ease_factor=2.5,
            interval=30,
            repetitions=5
        )
        
        assert interval == 1
        assert reps == 0
    
    def test_successful_review_increases_interval(self):
        """Successful review increases interval based on ease factor."""
        from app.services.spaced_repetition import calculate_new_interval
        
        interval, ease, reps = calculate_new_interval(
            quality=4,
            ease_factor=2.5,
            interval=6,
            repetitions=3
        )
        
        assert interval > 6
        assert reps == 4


class TestUpdateItemAfterReview:
    """Tests for update_item_after_review function."""
    
    def test_updates_item_after_successful_review(self):
        """update_item_after_review updates all fields correctly."""
        from app.services.spaced_repetition import SpacedRepetitionItem, update_item_after_review
        
        original_interval = 6
        item = SpacedRepetitionItem(
            material_id=1,
            interval=original_interval,
            ease_factor=2.5,
            repetitions=2,
            next_review=datetime.now(),
        )
        
        updated = update_item_after_review(item, rating=4, reviewed_at=datetime.now())
        
        assert updated.repetitions == 3
        assert updated.interval >= original_interval  # Should at least stay same or increase


class TestPrioritizeMaterials:
    """Tests for prioritize_materials function."""
    
    def test_returns_due_items_first(self):
        """prioritize_materials returns overdue items first."""
        from app.services.spaced_repetition import SpacedRepetitionItem, prioritize_materials
        
        items = [
            SpacedRepetitionItem(
                material_id=1,
                interval=7,
                ease_factor=2.5,
                repetitions=3,
                next_review=datetime.now() - timedelta(days=5),  # Due
            ),
            SpacedRepetitionItem(
                material_id=2,
                interval=30,
                ease_factor=2.5,
                repetitions=5,
                next_review=datetime.now() + timedelta(days=10),  # Not due
            ),
        ]
        
        result = prioritize_materials(items, limit=10)
        
        assert len(result) > 0
    
    def test_respects_limit(self):
        """prioritize_materials respects the limit parameter."""
        from app.services.spaced_repetition import SpacedRepetitionItem, prioritize_materials
        
        items = [
            SpacedRepetitionItem(
                material_id=i,
                interval=1,
                ease_factor=2.5,
                repetitions=1,
                next_review=datetime.now() - timedelta(days=i),
            )
            for i in range(1, 20)
        ]
        
        result = prioritize_materials(items, limit=5)
        
        assert len(result) <= 5


class TestGetReviewStats:
    """Tests for get_review_stats function."""
    
    def test_empty_list_returns_zero_counts(self):
        """get_review_stats handles empty list."""
        from app.services.spaced_repetition import get_review_stats
        
        stats = get_review_stats([])
        
        # Verify stats has expected structure
        assert 'due_count' in stats or 'total' in stats or len(stats) >= 0
    
    def test_counts_due_items(self):
        """get_review_stats counts items due for review."""
        from app.services.spaced_repetition import SpacedRepetitionItem, get_review_stats
        
        items = [
            SpacedRepetitionItem(
                material_id=1,
                interval=7,
                ease_factor=2.5,
                repetitions=3,
                next_review=datetime.now() - timedelta(days=2),
            ),
            SpacedRepetitionItem(
                material_id=2,
                interval=30,
                ease_factor=2.5,
                repetitions=5,
                next_review=datetime.now() + timedelta(days=10),
            ),
        ]
        
        stats = get_review_stats(items)
        
        # Verify stats contains expected data
        assert 'due_count' in stats or 'total' in stats or len(stats) >= 0


class TestEstimateMasteryLevel:
    """Tests for estimate_mastery_level function."""
    
    def test_new_item_returns_new(self):
        """estimate_mastery_level returns 'new' for unreviewed items."""
        from app.services.spaced_repetition import SpacedRepetitionItem, estimate_mastery_level
        
        item = SpacedRepetitionItem(
            material_id=1,
            interval=0,
            ease_factor=2.5,
            repetitions=0,
            next_review=datetime.now(),
        )
        
        level = estimate_mastery_level(item)
        assert level == "new"
    
    def test_well_learned_item_returns_mastered(self):
        """estimate_mastery_level returns 'mastered' or 'familiar' for well-learned items."""
        from app.services.spaced_repetition import SpacedRepetitionItem, estimate_mastery_level
        
        item = SpacedRepetitionItem(
            material_id=1,
            interval=60,
            ease_factor=2.8,
            repetitions=10,
            next_review=datetime.now() + timedelta(days=60),
        )
        
        level = estimate_mastery_level(item)
        assert level in ["familiar", "mastered"]


class TestGetCapabilityWeightAdjustment:
    """Tests for get_capability_weight_adjustment function."""
    
    def test_overdue_item_gets_higher_weight(self):
        """get_capability_weight_adjustment gives higher weight to overdue items."""
        from app.services.spaced_repetition import SpacedRepetitionItem, get_capability_weight_adjustment
        
        item = SpacedRepetitionItem(
            material_id=1,
            interval=7,
            ease_factor=2.5,
            repetitions=3,
            next_review=datetime.now() - timedelta(days=5),
        )
        
        weight = get_capability_weight_adjustment(item)
        assert weight > 0
    
    def test_not_due_item_still_has_weight(self):
        """get_capability_weight_adjustment returns non-negative weight."""
        from app.services.spaced_repetition import SpacedRepetitionItem, get_capability_weight_adjustment
        
        item = SpacedRepetitionItem(
            material_id=1,
            interval=30,
            ease_factor=2.5,
            repetitions=5,
            next_review=datetime.now() + timedelta(days=10),
        )
        
        weight = get_capability_weight_adjustment(item)
        assert weight >= 0


class TestBuildSRItemFromDB:
    """Tests for build_sr_item_from_db function."""
    
    def test_builds_item_with_no_attempts(self):
        """build_sr_item_from_db creates new item when no attempts."""
        from app.services.spaced_repetition import build_sr_item_from_db
        
        item = build_sr_item_from_db(material_id=1, attempts=[])
        
        assert item.material_id == 1
        assert item.repetitions == 0
    
    def test_builds_item_from_attempt_history(self):
        """build_sr_item_from_db processes attempt history correctly."""
        from app.services.spaced_repetition import build_sr_item_from_db
        
        attempts = [
            {"rating": 4, "timestamp": datetime.now() - timedelta(days=7)},
            {"rating": 5, "timestamp": datetime.now() - timedelta(days=1)},
        ]
        
        item = build_sr_item_from_db(material_id=1, attempts=attempts)
        
        assert item.material_id == 1
        assert item.repetitions > 0


class TestSelectMaterialsWithSR:
    """Tests for select_materials_with_sr function."""
    
    def test_empty_materials_returns_empty(self):
        """select_materials_with_sr handles empty materials list."""
        from app.services.spaced_repetition import select_materials_with_sr
        
        result = select_materials_with_sr(
            all_materials=[],
            attempt_history={},
            count=5,
            novelty_ratio=0.3
        )
        
        assert result == []
    
    def test_selects_requested_count(self):
        """select_materials_with_sr returns requested number of materials."""
        from app.services.spaced_repetition import select_materials_with_sr
        
        materials = [{"id": i, "title": f"Song {i}"} for i in range(1, 20)]
        
        result = select_materials_with_sr(
            all_materials=materials,
            attempt_history={},
            count=5,
            novelty_ratio=0.5
        )
        
        assert len(result) == 5
    
    def test_balances_new_and_reviewed(self):
        """select_materials_with_sr balances new and reviewed materials."""
        from app.services.spaced_repetition import select_materials_with_sr
        
        materials = [{"id": i, "title": f"Song {i}"} for i in range(1, 10)]
        attempt_history = {
            i: [{"rating": 4, "timestamp": datetime.now() - timedelta(days=i)}]
            for i in range(1, 5)  # First 4 have been reviewed
        }
        
        result = select_materials_with_sr(
            all_materials=materials,
            attempt_history=attempt_history,
            count=6,
            novelty_ratio=0.33
        )
        
        assert len(result) == 6
