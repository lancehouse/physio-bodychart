"""Clinical logic layer - pure functions, no UI imports, no persistence."""

from typing import List, Dict, Tuple, Optional
from pathlib import Path
from .models import Session, OutcomeMeasureResult


def get_bodychart_command(session_path: Path) -> list:
    """
    Generate command line to launch GTK body chart with this session.

    Args:
        session_path: Path to session JSON file

    Returns:
        List ready for subprocess.Popen() or similar
    """
    return ["physio-bodychart", "--session", str(session_path)]


def generate_report_paragraph(section: str, session_data: Session) -> str:
    """
    Generate Jinja2 template for given section with session data substitutions.

    Args:
        section: Section name (e.g. "consent", "subjective", "pain_classification")
        session_data: Completed session model

    Returns:
        Generated paragraph text with placeholders replaced
    """
    # TODO: Wire up Jinja2 templates from core/*.md files
    return ""


def query_patterns(region: str, symptom_zones: List[str], active_overlay: Optional[str]) -> List[Tuple[str, float]]:
    """
    Query clinical patterns matching body chart findings.

    Args:
        region: Body region (e.g. "lumbar")
        symptom_zones: List of symptom locations/types from body chart
        active_overlay: Active overlay type (dermatome, peripheral, somatic)

    Returns:
        List of (pattern_id, confidence_score) tuples, ranked by score
    """
    # TODO: Query clinical_kb.db BodyChartTrigger table
    return []


def query_tests(pattern_ids: List[str], priority_filter: Optional[str] = None) -> List[Dict]:
    """
    Get special tests for given patterns, ordered by priority.

    Args:
        pattern_ids: List of pattern IDs
        priority_filter: Filter by "essential" or "supporting"

    Returns:
        List of special test dicts with metadata
    """
    # TODO: Query clinical_kb.db SpecialTest + PatternTest
    return []


def score_pattern(pattern_id: str, features_present: List[str]) -> float:
    """
    Score confidence in a pattern based on present features.

    Args:
        pattern_id: Pattern ID
        features_present: List of feature IDs confirmed present

    Returns:
        Confidence score 0.0–1.0
    """
    # TODO: Lookup PatternFeature weights and calculate
    return 0.0


def suggest_icd11_pathway(duration: Optional[str], mechanism: Optional[str],
                         pain_type: Optional[str]) -> Tuple[str, str]:
    """
    Suggest most likely ICD-11 pathway based on clinical data.

    Args:
        duration: Symptom duration
        mechanism: Pain mechanism/cause
        pain_type: Dominant pain type from classification

    Returns:
        Tuple of (pathway_code, reasoning_text)
    """
    # TODO: Implement ICD-11 pathway logic per core/06
    return ("", "")


def suggest_barriers(outcome_scores: Dict[str, float], pain_type: str) -> List[str]:
    """
    Suggest likely treatment barriers based on outcome measures and pain type.

    Args:
        outcome_scores: Dict of measure_name → score
        pain_type: Dominant pain type

    Returns:
        List of barrier IDs to suggest ticking
    """
    # TODO: Implement barrier suggestion logic
    return []


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """Calculate BMI (display only, not editable)."""
    if height_cm <= 0:
        return 0.0
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)


def tally_inflammatory_score(features_checked: Dict[str, bool]) -> int:
    """
    Tally inflammatory pain features (0–4).

    Returns:
        Count of checked inflammatory features
    """
    return sum(1 for v in features_checked.values() if v)


def tally_pain_type_features(features_checked: Dict[str, bool]) -> Dict[str, int]:
    """
    Tally pain type feature counts (subjective + examination separate).

    Returns:
        Dict of pain_type → count
    """
    return {}


def interpret_outcome_score(measure_name: str, score: float) -> str:
    """
    Return interpretation label for an outcome measure score.

    Args:
        measure_name: Measure name (e.g. "PSFS", "BPI", "CSI")
        score: Raw score

    Returns:
        Interpretation label (e.g. "Mild", "Moderate", "High risk")
    """
    # TODO: Implement per core/05 thresholds
    return ""
