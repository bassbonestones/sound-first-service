"""
Composite Scoring — Aggregation and Legacy Compatibility

Contains AllDomainResults, analyze_all_domains, and backward-compatible aliases.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .models import DomainResult, DomainScores
from .interval_scorer import analyze_interval_domain
from .rhythm_scorer import analyze_rhythm_domain
from .tonal_scorer import analyze_tonal_domain
from .tempo_scorer import analyze_tempo_domain
from .range_scorer import analyze_range_domain
from .throughput_scorer import analyze_throughput_domain
from .pattern_scorer import analyze_pattern_domain


@dataclass
class AllDomainResults:
    """Container for results from all domains."""
    interval: Optional[DomainResult] = None
    rhythm: Optional[DomainResult] = None
    tonal: Optional[DomainResult] = None
    tempo: Optional[DomainResult] = None
    range: Optional[DomainResult] = None
    throughput: Optional[DomainResult] = None
    pattern: Optional[DomainResult] = None
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert all domain results to dictionary."""
        result = {}
        if self.interval:
            result['interval'] = self.interval.to_dict()
        if self.rhythm:
            result['rhythm'] = self.rhythm.to_dict()
        if self.tonal:
            result['tonal'] = self.tonal.to_dict()
        if self.tempo:
            result['tempo'] = self.tempo.to_dict()
        if self.range:
            result['range'] = self.range.to_dict()
        if self.throughput:
            result['throughput'] = self.throughput.to_dict()
        if self.pattern:
            result['pattern'] = self.pattern.to_dict()
        return result


def analyze_all_domains(profiles: Dict[str, Dict[str, Any]]) -> AllDomainResults:
    """
    Analyze all domains from their profiles.
    
    Args:
        profiles: Dict mapping domain name to profile dict
            e.g., {"interval": {...}, "rhythm": {...}, ...}
    
    Returns:
        AllDomainResults with results for each domain present in profiles
    """
    results = AllDomainResults()
    
    if 'interval' in profiles:
        results.interval = analyze_interval_domain(profiles['interval'])
    if 'rhythm' in profiles:
        results.rhythm = analyze_rhythm_domain(profiles['rhythm'])
    if 'tonal' in profiles:
        results.tonal = analyze_tonal_domain(profiles['tonal'])
    if 'tempo' in profiles:
        results.tempo = analyze_tempo_domain(profiles['tempo'])
    if 'range' in profiles:
        results.range = analyze_range_domain(profiles['range'])
    if 'throughput' in profiles:
        results.throughput = analyze_throughput_domain(profiles['throughput'])
    if 'pattern' in profiles:
        results.pattern = analyze_pattern_domain(profiles['pattern'])
    
    return results


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

def interval_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_interval_domain(profile).scores


def rhythm_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_rhythm_domain(profile).scores


def tonal_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_tonal_domain(profile).scores


def tempo_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_tempo_domain(profile).scores


def range_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_range_domain(profile).scores


def throughput_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_throughput_domain(profile).scores


def pattern_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_pattern_domain(profile).scores
