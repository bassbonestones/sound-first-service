"""Response schemas for admin user endpoints."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ============ Progression Response ============

class InstrumentData(BaseModel):
    id: int
    instrument_name: str
    is_primary: bool
    clef: Optional[str]
    resonant_note: Optional[str]
    range_low: Optional[str]
    range_high: Optional[str]
    day0_completed: bool
    day0_stage: int


class CapabilityData(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    domain: Optional[str]
    introduced_at: Optional[str]
    mastered_at: Optional[str]
    evidence_count: int
    is_global: bool
    instrument_id: Optional[int]


class RecentPromotion(BaseModel):
    capability_name: str
    promoted_at: Optional[str]


class CapabilitiesSection(BaseModel):
    mastered: List[CapabilityData]
    introduced: List[CapabilityData]
    recent_promotions: List[RecentPromotion]


class SoftGateData(BaseModel):
    dimension_name: str
    comfortable_value: float
    max_demonstrated_value: float
    frontier_success_ema: float
    frontier_attempt_count_since_last_promo: int


class JourneyData(BaseModel):
    stage: str
    capabilities_mastered: int
    materials_completed: int


class UserBasicInfo(BaseModel):
    id: int
    email: Optional[str]
    instrument: Optional[str]
    resonant_note: Optional[str]
    range_low: Optional[str]
    range_high: Optional[str]
    day0_completed: bool
    day0_stage: int


class UserProgressionResponse(BaseModel):
    user: UserBasicInfo
    instruments: List[InstrumentData]
    capabilities: CapabilitiesSection
    soft_gates: List[SoftGateData]
    journey: JourneyData


# ============ Session Candidates Response ============

class EligibleMaterial(BaseModel):
    id: int
    title: str
    eligibility_reason: str


class IneligibleMaterial(BaseModel):
    id: int
    title: str
    ineligibility_reason: str


class SessionCandidatesResponse(BaseModel):
    user_id: int
    eligible_materials: List[EligibleMaterial]
    eligible_count: int
    ineligible_sample: List[IneligibleMaterial]
    total_materials: int


# ============ Diagnostic Session Response ============

class TargetCapability(BaseModel):
    name: str
    weight: float


class SoftEnvelopeFilter(BaseModel):
    dimension: str
    comfort: float
    max_allowed: float
    frontier_buffer: float


class CandidateRanking(BaseModel):
    title: str
    score: float
    reason: str


class SelectionReason(BaseModel):
    material: str
    reason: str


class DiagnosticData(BaseModel):
    target_capabilities: List[TargetCapability]
    hard_gates: List[str]
    soft_envelope_filters: List[SoftEnvelopeFilter]
    candidates_considered: int
    candidate_ranking: List[CandidateRanking]
    selection_reasons: List[SelectionReason]


class DiagnosticMiniSession(BaseModel):
    material_id: int
    material_title: str
    focus_card_id: Optional[int]
    focus_card_name: str
    goal_type: str
    target_key: Optional[str]


class GeneratedSession(BaseModel):
    session_id: int
    user_id: int
    planned_duration_minutes: int
    mini_sessions: List[DiagnosticMiniSession]


class DiagnosticSessionResponse(BaseModel):
    session: Optional[GeneratedSession]
    diagnostics: DiagnosticData
    error: Optional[str] = None


# ============ Last Session Diagnostics Response ============

class LastSessionMiniSession(BaseModel):
    material_id: int
    material_title: str
    target_key: Optional[str]
    focus_card_id: Optional[int]
    focus_card_name: str
    goal_type: Optional[str]
    is_completed: bool


class LastSessionData(BaseModel):
    session_id: int
    user_id: int
    started_at: Optional[str]
    ended_at: Optional[str]
    practice_mode: Optional[str]
    mini_sessions: List[LastSessionMiniSession]


class LastSessionDiagnostics(BaseModel):
    message: str
    mini_session_count: Optional[int] = None


class LastSessionDiagnosticsResponse(BaseModel):
    session: Optional[LastSessionData]
    diagnostics: LastSessionDiagnostics


# ============ User Info Update Response ============

class UserInfoUpdateResponse(BaseModel):
    success: bool
    changes: List[str]


# ============ Available Capabilities Response ============

class AvailableCapability(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    domain: Optional[str]
    is_global: bool
    user_has: bool
    mastered: bool
    evidence_count: int


class AvailableCapabilitiesResponse(BaseModel):
    capabilities: List[AvailableCapability]


# ============ Capability Mutation Responses ============

class CapabilityAddResponse(BaseModel):
    success: bool
    message: str


class CapabilityRemoveResponse(BaseModel):
    success: bool
    message: str


class CapabilityToggleMasteryResponse(BaseModel):
    success: bool
    action: str


# ============ Soft Gates Responses ============

class AllSoftGateData(BaseModel):
    dimension_name: str
    frontier_buffer: float
    min_attempts: int
    success_required_count: int
    comfortable_value: float
    max_demonstrated_value: float
    frontier_success_ema: float
    frontier_attempt_count_since_last_promo: int
    has_state: bool


class AllSoftGatesResponse(BaseModel):
    soft_gates: List[AllSoftGateData]


class SoftGateUpdateResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    changes: Optional[List[str]] = None


# ============ User Reset Response ============

class UserResetResponse(BaseModel):
    success: bool
    message: str
    deleted_counts: Dict[str, int]


# ============ Grant Day0 Capabilities Response ============

class GrantDay0Response(BaseModel):
    success: bool
    granted: List[str]
    all_day0_capabilities: List[str]
    message: str
