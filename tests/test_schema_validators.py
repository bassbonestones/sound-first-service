"""Tests for Pydantic schema validators."""
import pytest
from pydantic import ValidationError


class TestCapabilitySchemaValidators:
    """Test validators in capability_schemas.py."""

    def test_capability_name_valid_snake_case(self):
        """Valid snake_case names should pass."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        req = CapabilityCreateRequest(
            name="valid_capability_name",
            domain="test"
        )
        assert req.name == "valid_capability_name"

    def test_capability_name_invalid_uppercase(self):
        """Names with uppercase should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(name="Invalid_Name", domain="test")
        assert "snake_case" in str(exc_info.value)

    def test_capability_name_invalid_starts_with_number(self):
        """Names starting with number should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(name="123_invalid", domain="test")
        assert "snake_case" in str(exc_info.value)

    def test_requirement_type_valid(self):
        """Valid requirement_type should pass."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        for req_type in ["required", "learnable_in_context"]:
            req = CapabilityCreateRequest(
                name="test_cap",
                domain="test",
                requirement_type=req_type
            )
            assert req.requirement_type == req_type

    def test_requirement_type_invalid(self):
        """Invalid requirement_type should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(
                name="test_cap",
                domain="test",
                requirement_type="invalid_type"
            )
        assert "requirement_type" in str(exc_info.value)

    def test_mastery_type_valid(self):
        """Valid mastery_type should pass."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        for mastery_type in ["single", "any_of_pool", "multiple"]:
            req = CapabilityCreateRequest(
                name="test_cap",
                domain="test",
                mastery_type=mastery_type
            )
            assert req.mastery_type == mastery_type

    def test_mastery_type_invalid(self):
        """Invalid mastery_type should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(
                name="test_cap",
                domain="test",
                mastery_type="invalid_type"
            )
        assert "mastery_type" in str(exc_info.value)

    def test_difficulty_tier_valid(self):
        """Valid difficulty_tier should pass."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        req = CapabilityCreateRequest(name="test_cap", domain="test", difficulty_tier=5)
        assert req.difficulty_tier == 5

    def test_difficulty_tier_invalid_zero(self):
        """difficulty_tier of 0 should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(name="test_cap", domain="test", difficulty_tier=0)
        assert "difficulty_tier" in str(exc_info.value)

    def test_evidence_threshold_valid(self):
        """Valid evidence_acceptance_threshold should pass."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        for threshold in [1, 2, 3, 4, 5]:
            req = CapabilityCreateRequest(
                name="test_cap",
                domain="test",
                evidence_acceptance_threshold=threshold
            )
            assert req.evidence_acceptance_threshold == threshold

    def test_evidence_threshold_invalid(self):
        """Invalid evidence_acceptance_threshold should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(
                name="test_cap",
                domain="test",
                evidence_acceptance_threshold=6
            )
        assert "evidence_acceptance_threshold" in str(exc_info.value)

    def test_difficulty_weight_valid(self):
        """Valid difficulty_weight should pass."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        req = CapabilityCreateRequest(name="test_cap", domain="test", difficulty_weight=5.0)
        assert req.difficulty_weight == 5.0

    def test_difficulty_weight_invalid_low(self):
        """difficulty_weight below 0.1 should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(name="test_cap", domain="test", difficulty_weight=0.05)
        assert "difficulty_weight" in str(exc_info.value)

    def test_difficulty_weight_invalid_high(self):
        """difficulty_weight above 10.0 should fail."""
        from app.schemas.capability_schemas import CapabilityCreateRequest
        
        with pytest.raises(ValidationError) as exc_info:
            CapabilityCreateRequest(name="test_cap", domain="test", difficulty_weight=15.0)
        assert "difficulty_weight" in str(exc_info.value)


class TestSessionSchemaValidators:
    """Test validators in session_schemas.py."""

    def test_onboarding_valid_note(self):
        """Valid resonant_note should pass."""
        from app.schemas.session_schemas import OnboardingIn
        
        for note in ["C4", "F#3", "Bb5", "G2"]:
            req = OnboardingIn(instrument="trombone", resonant_note=note)
            assert req.resonant_note == note

    def test_onboarding_invalid_note(self):
        """Invalid resonant_note should fail."""
        from app.schemas.session_schemas import OnboardingIn
        
        with pytest.raises(ValidationError) as exc_info:
            OnboardingIn(instrument="trombone", resonant_note="invalid")
        assert "resonant_note" in str(exc_info.value)

    def test_onboarding_range_notes_valid(self):
        """Valid range notes should pass."""
        from app.schemas.session_schemas import OnboardingIn
        
        req = OnboardingIn(
            instrument="trombone",
            resonant_note="Bb3",
            range_low="E2",
            range_high="C5"
        )
        assert req.range_low == "E2"
        assert req.range_high == "C5"

    def test_onboarding_range_notes_invalid(self):
        """Invalid range notes should fail."""
        from app.schemas.session_schemas import OnboardingIn
        
        with pytest.raises(ValidationError) as exc_info:
            OnboardingIn(
                instrument="trombone",
                resonant_note="Bb3",
                range_low="invalid"
            )
        assert "Range note" in str(exc_info.value)

    def test_practice_attempt_rating_valid(self):
        """Valid rating (1-5) should pass."""
        from app.schemas.session_schemas import PracticeAttemptIn
        import datetime
        
        for rating in [1, 2, 3, 4, 5]:
            req = PracticeAttemptIn(
                user_id=1,
                material_id=1,
                rating=rating,
                fatigue=5,
                timestamp=datetime.datetime.now()
            )
            assert req.rating == rating

    def test_practice_attempt_rating_invalid(self):
        """Invalid rating should fail."""
        from app.schemas.session_schemas import PracticeAttemptIn
        import datetime
        
        with pytest.raises(ValidationError) as exc_info:
            PracticeAttemptIn(
                user_id=1,
                material_id=1,
                rating=6,
                fatigue=5,
                timestamp=datetime.datetime.now()
            )
        assert "rating" in str(exc_info.value)

    def test_practice_attempt_fatigue_valid(self):
        """Valid fatigue (0-10) should pass."""
        from app.schemas.session_schemas import PracticeAttemptIn
        import datetime
        
        for fatigue in [0, 5, 10]:
            req = PracticeAttemptIn(
                user_id=1,
                material_id=1,
                rating=4,
                fatigue=fatigue,
                timestamp=datetime.datetime.now()
            )
            assert req.fatigue == fatigue

    def test_practice_attempt_fatigue_invalid(self):
        """Invalid fatigue should fail."""
        from app.schemas.session_schemas import PracticeAttemptIn
        import datetime
        
        with pytest.raises(ValidationError) as exc_info:
            PracticeAttemptIn(
                user_id=1,
                material_id=1,
                rating=4,
                fatigue=11,
                timestamp=datetime.datetime.now()
            )
        assert "fatigue" in str(exc_info.value)

    def test_session_duration_valid(self):
        """Valid duration should pass."""
        from app.schemas.session_schemas import SelfDirectedSessionIn
        
        req = SelfDirectedSessionIn(
            material_id=1,
            focus_card_id=1,
            goal_type="mastery",
            planned_duration_minutes=30
        )
        assert req.planned_duration_minutes == 30

    def test_session_duration_invalid_zero(self):
        """Zero duration should fail."""
        from app.schemas.session_schemas import SelfDirectedSessionIn
        
        with pytest.raises(ValidationError) as exc_info:
            SelfDirectedSessionIn(
                material_id=1,
                focus_card_id=1,
                goal_type="mastery",
                planned_duration_minutes=0
            )
        assert "planned_duration_minutes" in str(exc_info.value)

    def test_session_duration_invalid_too_long(self):
        """Duration > 180 minutes should fail."""
        from app.schemas.session_schemas import SelfDirectedSessionIn
        
        with pytest.raises(ValidationError) as exc_info:
            SelfDirectedSessionIn(
                material_id=1,
                focus_card_id=1,
                goal_type="mastery",
                planned_duration_minutes=200
            )
        assert "planned_duration_minutes" in str(exc_info.value)


class TestUserSchemaValidators:
    """Test validators in user_schemas.py."""

    def test_user_range_valid(self):
        """Valid range notes should pass."""
        from app.schemas.user_schemas import UserRangeIn
        
        req = UserRangeIn(range_low="E2", range_high="C6")
        assert req.range_low == "E2"
        assert req.range_high == "C6"

    def test_user_range_invalid(self):
        """Invalid range notes should fail."""
        from app.schemas.user_schemas import UserRangeIn
        
        with pytest.raises(ValidationError) as exc_info:
            UserRangeIn(range_low="invalid", range_high="C6")
        assert "Note must be a valid format" in str(exc_info.value)


class TestAdminSchemaValidators:
    """Test validators in admin_schemas.py."""

    def test_soft_gate_create_valid(self):
        """Valid soft gate rule should pass."""
        from app.schemas.admin_schemas import SoftGateRuleCreate
        
        rule = SoftGateRuleCreate(
            dimension_name="test_dim",
            frontier_buffer=0.5,
            promotion_step=0.1,
            min_attempts=3,
            success_required_count=2
        )
        assert rule.dimension_name == "test_dim"

    def test_soft_gate_create_invalid_negative_buffer(self):
        """Negative frontier_buffer should fail."""
        from app.schemas.admin_schemas import SoftGateRuleCreate
        
        with pytest.raises(ValidationError) as exc_info:
            SoftGateRuleCreate(
                dimension_name="test_dim",
                frontier_buffer=-0.5,
                promotion_step=0.1,
                min_attempts=3,
                success_required_count=2
            )
        assert "positive" in str(exc_info.value)

    def test_soft_gate_create_invalid_rating_threshold(self):
        """Rating threshold outside 1-5 should fail."""
        from app.schemas.admin_schemas import SoftGateRuleCreate
        
        with pytest.raises(ValidationError) as exc_info:
            SoftGateRuleCreate(
                dimension_name="test_dim",
                frontier_buffer=0.5,
                promotion_step=0.1,
                min_attempts=3,
                success_rating_threshold=6,
                success_required_count=2
            )
        assert "success_rating_threshold" in str(exc_info.value)

    def test_soft_gate_create_window_less_than_required(self):
        """Window count < required count should fail."""
        from app.schemas.admin_schemas import SoftGateRuleCreate
        
        with pytest.raises(ValidationError) as exc_info:
            SoftGateRuleCreate(
                dimension_name="test_dim",
                frontier_buffer=0.5,
                promotion_step=0.1,
                min_attempts=3,
                success_required_count=5,
                success_window_count=3  # < required
            )
        assert "window_count must be >= success_required_count" in str(exc_info.value)


class TestTeachingModuleSchemaValidators:
    """Test validators in teaching_module_schemas.py."""

    def test_lesson_config_bpm_valid(self):
        """Valid BPM should pass."""
        from app.schemas.teaching_module_schemas import LessonConfig
        
        for bpm in [60, 120, 200]:
            config = LessonConfig(bpm=bpm)
            assert config.bpm == bpm

    def test_lesson_config_bpm_invalid_low(self):
        """BPM below 20 should fail."""
        from app.schemas.teaching_module_schemas import LessonConfig
        
        with pytest.raises(ValidationError) as exc_info:
            LessonConfig(bpm=10)
        assert "bpm" in str(exc_info.value)

    def test_lesson_config_bpm_invalid_high(self):
        """BPM above 300 should fail."""
        from app.schemas.teaching_module_schemas import LessonConfig
        
        with pytest.raises(ValidationError) as exc_info:
            LessonConfig(bpm=400)
        assert "bpm" in str(exc_info.value)

    def test_lesson_mastery_accuracy_valid(self):
        """Valid accuracy (0-1) should pass."""
        from app.schemas.teaching_module_schemas import LessonMastery
        
        for accuracy in [0.0, 0.5, 1.0]:
            mastery = LessonMastery(min_accuracy=accuracy)
            assert mastery.min_accuracy == accuracy

    def test_lesson_mastery_accuracy_invalid(self):
        """Accuracy outside 0-1 should fail."""
        from app.schemas.teaching_module_schemas import LessonMastery
        
        with pytest.raises(ValidationError) as exc_info:
            LessonMastery(min_accuracy=1.5)
        assert "min_accuracy" in str(exc_info.value)

    def test_lesson_mastery_streak_invalid_zero(self):
        """Zero correct_streak should fail."""
        from app.schemas.teaching_module_schemas import LessonMastery
        
        with pytest.raises(ValidationError) as exc_info:
            LessonMastery(correct_streak=0)
        assert "correct_streak" in str(exc_info.value)

    def test_module_difficulty_tier_valid(self):
        """Valid difficulty tier should pass."""
        from app.schemas.teaching_module_schemas import ModuleBase
        
        for tier in [1, 5, 10]:
            module = ModuleBase(id="test", display_name="Test", difficulty_tier=tier)
            assert module.difficulty_tier == tier

    def test_module_difficulty_tier_invalid(self):
        """Invalid difficulty tier should fail."""
        from app.schemas.teaching_module_schemas import ModuleBase
        
        with pytest.raises(ValidationError) as exc_info:
            ModuleBase(id="test", display_name="Test", difficulty_tier=15)
        assert "difficulty_tier" in str(exc_info.value)


class TestMaterialSchemaValidators:
    """Test validators in material_schemas.py."""

    def test_material_upload_valid(self):
        """Valid material upload should pass."""
        from app.schemas.material_schemas import MaterialUpload
        
        upload = MaterialUpload(
            title="Test Material",
            musicxml_content="<xml></xml>",
            original_key_center="C",
            allowed_keys=["C", "F#", "Bb"]
        )
        assert upload.title == "Test Material"

    def test_material_upload_empty_title(self):
        """Empty title should fail."""
        from app.schemas.material_schemas import MaterialUpload
        
        with pytest.raises(ValidationError) as exc_info:
            MaterialUpload(title="  ", musicxml_content="<xml></xml>")
        assert "title" in str(exc_info.value)

    def test_material_upload_invalid_key(self):
        """Invalid key format should fail."""
        from app.schemas.material_schemas import MaterialUpload
        
        with pytest.raises(ValidationError) as exc_info:
            MaterialUpload(
                title="Test",
                musicxml_content="<xml></xml>",
                original_key_center="invalid"
            )
        assert "original_key_center" in str(exc_info.value)

    def test_material_upload_invalid_allowed_key(self):
        """Invalid allowed key should fail."""
        from app.schemas.material_schemas import MaterialUpload
        
        with pytest.raises(ValidationError) as exc_info:
            MaterialUpload(
                title="Test",
                musicxml_content="<xml></xml>",
                allowed_keys=["C", "invalid"]
            )
        assert "Invalid key format" in str(exc_info.value)

    def test_batch_ingestion_valid_metrics(self):
        """Valid metrics should pass."""
        from app.schemas.material_schemas import BatchIngestionRequest
        
        req = BatchIngestionRequest(specific_metrics=["capabilities", "soft_gates"])
        assert req.specific_metrics == ["capabilities", "soft_gates"]

    def test_batch_ingestion_invalid_metrics(self):
        """Invalid metrics should fail."""
        from app.schemas.material_schemas import BatchIngestionRequest
        
        with pytest.raises(ValidationError) as exc_info:
            BatchIngestionRequest(specific_metrics=["invalid_metric"])
        assert "Invalid metric" in str(exc_info.value)
