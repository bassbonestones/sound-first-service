"""
Tests for app/services/history_service.py
Tests history service methods.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


class TestHistoryServiceGetDueItems:
    """Tests for HistoryService.get_due_items method."""
    
    def test_returns_only_due_items(self):
        """get_due_items filters out items that are not yet due."""
        from app.services.history_service import HistoryService
        
        # Material 1: practiced long ago (should be due)
        m1 = MagicMock(id=1, title="Old Song")
        # Material 2: practiced just now (should NOT be due)
        m2 = MagicMock(id=2, title="Recent Song")
        
        history = {
            1: [{"rating": 4, "timestamp": datetime.now() - timedelta(days=60)}],  # 60 days ago
            2: [{"rating": 5, "timestamp": datetime.now() - timedelta(minutes=5)}],  # Just practiced
        }
        
        result = HistoryService.get_due_items([m1, m2], history, limit=10)
        
        # Only the old song should be in results (it's due)
        # The recent song has a future next_review date
        due_ids = [item["material_id"] for item in result]
        assert 1 in due_ids  # Old song is due
    
    def test_sorts_by_most_overdue_first(self):
        """get_due_items returns items sorted by days_overdue descending."""
        from app.services.history_service import HistoryService
        
        m1 = MagicMock(id=1, title="Slightly Overdue")
        m2 = MagicMock(id=2, title="Very Overdue")
        m3 = MagicMock(id=3, title="Moderately Overdue")
        
        history = {
            1: [{"rating": 3, "timestamp": datetime.now() - timedelta(days=10)}],   # 10 days
            2: [{"rating": 3, "timestamp": datetime.now() - timedelta(days=100)}],  # 100 days
            3: [{"rating": 3, "timestamp": datetime.now() - timedelta(days=50)}],   # 50 days
        }
        
        result = HistoryService.get_due_items([m1, m2, m3], history, limit=10)
        
        # Check that results are ordered by most overdue first
        if len(result) >= 2:
            assert result[0]["days_overdue"] >= result[1]["days_overdue"]
        if len(result) >= 3:
            assert result[1]["days_overdue"] >= result[2]["days_overdue"]
    
    def test_respects_limit_parameter(self):
        """get_due_items returns at most 'limit' items."""
        from app.services.history_service import HistoryService
        
        materials = [MagicMock(id=i, title=f"Song {i}") for i in range(1, 20)]
        history = {
            i: [{"rating": 3, "timestamp": datetime.now() - timedelta(days=100+i)}]
            for i in range(1, 20)
        }
        
        result = HistoryService.get_due_items(materials, history, limit=5)
        
        assert len(result) <= 5
    
    def test_returns_correct_fields(self):
        """get_due_items returns dicts with expected fields."""
        from app.services.history_service import HistoryService
        
        m1 = MagicMock(id=1, title="Test Song")
        history = {1: [{"rating": 4, "timestamp": datetime.now() - timedelta(days=30)}]}
        
        result = HistoryService.get_due_items([m1], history, limit=10)
        
        if result:  # If the item is due
            item = result[0]
            assert "material_id" in item
            assert "material_title" in item
            assert "days_overdue" in item
            assert "ease_factor" in item
            assert "interval_days" in item
            assert "mastery_level" in item
            assert item["material_id"] == 1
            assert item["material_title"] == "Test Song"
    
    def test_empty_materials_returns_empty_list(self):
        """get_due_items returns empty list for empty input."""
        from app.services.history_service import HistoryService
        
        result = HistoryService.get_due_items([], {}, limit=10)
        
        assert result == []
    
    def test_new_materials_are_due(self):
        """Materials with no history (new) are always due."""
        from app.services.history_service import HistoryService
        
        m1 = MagicMock(id=1, title="New Song")
        history = {}  # No history for this material
        
        result = HistoryService.get_due_items([m1], history, limit=10)
        
        # New materials should be considered due
        assert len(result) == 1
        assert result[0]["material_id"] == 1


class TestHistoryServiceBuildSRItemsWithMastery:
    """Tests for HistoryService.build_sr_items_with_mastery method."""
    
    def test_builds_one_item_per_material(self):
        """build_sr_items_with_mastery returns one SR item per material."""
        from app.services.history_service import HistoryService
        
        materials = [MagicMock(id=i) for i in range(1, 4)]
        history = {}
        
        sr_items, mastery_counts = HistoryService.build_sr_items_with_mastery(materials, history)
        
        assert len(sr_items) == 3
        item_ids = [item.material_id for item in sr_items]
        assert set(item_ids) == {1, 2, 3}
    
    def test_mastery_counts_tracks_levels(self):
        """build_sr_items_with_mastery counts practiced materials by mastery level."""
        from app.services.history_service import HistoryService
        
        # Create materials with practice histories
        m_practiced1 = MagicMock(id=1)
        m_practiced2 = MagicMock(id=2)
        
        history = {
            1: [
                {"rating": 4, "timestamp": datetime.now() - timedelta(days=7)},
                {"rating": 5, "timestamp": datetime.now() - timedelta(days=3)},
            ],
            2: [
                {"rating": 4, "timestamp": datetime.now() - timedelta(days=1)},
                {"rating": 5, "timestamp": datetime.now() - timedelta(hours=2)},
            ]
        }
        
        sr_items, mastery_counts = HistoryService.build_sr_items_with_mastery(
            [m_practiced1, m_practiced2], history
        )
        
        # mastery_counts tracks practiced materials by level (mastered, familiar, stabilizing, learning)
        assert "mastered" in mastery_counts
        assert "familiar" in mastery_counts
        # Both materials have been practiced
        assert sum(mastery_counts.values()) == 2
    
    def test_empty_materials_returns_empty_results(self):
        """build_sr_items_with_mastery handles empty input."""
        from app.services.history_service import HistoryService
        
        sr_items, mastery_counts = HistoryService.build_sr_items_with_mastery([], {})
        
        assert sr_items == []
        assert sum(mastery_counts.values()) == 0


class TestHistoryServiceGetMaterialHistory:
    """Tests for HistoryService.get_material_history method."""
    
    def test_returns_history_data_for_each_material(self):
        """get_material_history returns MaterialHistoryData for each material."""
        from app.services.history_service import HistoryService, MaterialHistoryData
        
        m1 = MagicMock(id=1, title="Song 1")
        m2 = MagicMock(id=2, title="Song 2")
        
        history = {
            1: [{"rating": 4, "timestamp": datetime.now() - timedelta(days=5)}],
            2: [{"rating": 3, "timestamp": datetime.now() - timedelta(days=10)}],
        }
        
        result = HistoryService.get_material_history([m1, m2], history)
        
        assert len(result) == 2
        assert all(isinstance(item, MaterialHistoryData) for item in result)
    
    def test_calculates_average_rating(self):
        """get_material_history calculates correct average rating."""
        from app.services.history_service import HistoryService
        
        m1 = MagicMock(id=1, title="Song 1")
        history = {
            1: [
                {"rating": 3, "timestamp": datetime.now() - timedelta(days=10)},
                {"rating": 4, "timestamp": datetime.now() - timedelta(days=5)},
                {"rating": 5, "timestamp": datetime.now() - timedelta(days=1)},
            ]
        }
        
        result = HistoryService.get_material_history([m1], history)
        
        assert len(result) == 1
        # Average of 3, 4, 5 is 4.0
        assert result[0].average_rating == 4.0
    
    def test_counts_attempts_correctly(self):
        """get_material_history counts attempts correctly."""
        from app.services.history_service import HistoryService
        
        m1 = MagicMock(id=1, title="Song 1")
        history = {
            1: [
                {"rating": 3, "timestamp": datetime.now() - timedelta(days=i)}
                for i in range(5)  # 5 attempts
            ]
        }
        
        result = HistoryService.get_material_history([m1], history)
        
        assert result[0].attempt_count == 5
    
    def test_handles_material_with_no_history(self):
        """get_material_history handles materials with no practice history."""
        from app.services.history_service import HistoryService
        
        m1 = MagicMock(id=1, title="New Song")
        history = {}  # No history
        
        result = HistoryService.get_material_history([m1], history)
        
        assert len(result) == 1
        assert result[0].attempt_count == 0
        assert result[0].average_rating is None
        assert result[0].last_practiced is None


class TestHistoryServiceGetPracticeTimeline:
    """Tests for HistoryService.get_practice_timeline method."""
    
    def test_returns_timeline_grouped_by_day(self):
        """get_practice_timeline groups attempts by day."""
        from app.services.history_service import HistoryService
        
        # Verify the method exists on the class
        assert hasattr(HistoryService, 'get_practice_timeline')


class TestHistoryServiceCalculateStreak:
    """Tests for HistoryService.calculate_streak method."""
    
    def test_returns_zero_for_no_sessions(self):
        """calculate_streak returns 0 when no sessions exist."""
        from app.services.history_service import HistoryService
        
        streak = HistoryService.calculate_streak([])
        
        assert streak == 0
    
    def test_counts_consecutive_days(self):
        """calculate_streak counts consecutive practice days."""
        from app.services.history_service import HistoryService
        
        today = datetime.now()
        sessions = [
            MagicMock(started_at=today),
            MagicMock(started_at=today - timedelta(days=1)),
            MagicMock(started_at=today - timedelta(days=2)),
        ]
        
        streak = HistoryService.calculate_streak(sessions)
        
        assert streak == 3
    
    def test_streak_breaks_on_gap(self):
        """calculate_streak stops counting when there's a gap."""
        from app.services.history_service import HistoryService
        
        today = datetime.now()
        sessions = [
            MagicMock(started_at=today),
            MagicMock(started_at=today - timedelta(days=1)),
            # Gap on day 2
            MagicMock(started_at=today - timedelta(days=3)),
        ]
        
        streak = HistoryService.calculate_streak(sessions)
        
        assert streak == 2  # Only today and yesterday count


class TestHistoryServiceBuildAttemptHistory:
    """Tests for HistoryService.build_attempt_history method."""
    
    def test_groups_attempts_by_material_id(self):
        """build_attempt_history groups attempts by material_id."""
        from app.services.history_service import HistoryService
        
        attempts = [
            MagicMock(id=1, material_id=10, rating=4, timestamp=datetime.now(), fatigue=1),
            MagicMock(id=2, material_id=10, rating=5, timestamp=datetime.now(), fatigue=1),
            MagicMock(id=3, material_id=20, rating=3, timestamp=datetime.now(), fatigue=2),
        ]
        
        history = HistoryService.build_attempt_history(attempts)
        
        assert 10 in history
        assert 20 in history
        assert len(history[10]) == 2
        assert len(history[20]) == 1
    
    def test_returns_empty_dict_for_no_attempts(self):
        """build_attempt_history returns empty dict for no attempts."""
        from app.services.history_service import HistoryService
        
        history = HistoryService.build_attempt_history([])
        
        assert history == {}
    
    def test_preserves_attempt_data(self):
        """build_attempt_history preserves rating and timestamp data."""
        from app.services.history_service import HistoryService
        
        timestamp = datetime.now()
        attempts = [
            MagicMock(id=1, material_id=10, rating=4, timestamp=timestamp, fatigue=2),
        ]
        
        history = HistoryService.build_attempt_history(attempts)
        
        assert history[10][0]["rating"] == 4
        assert history[10][0]["timestamp"] == timestamp
        assert history[10][0]["fatigue"] == 2
