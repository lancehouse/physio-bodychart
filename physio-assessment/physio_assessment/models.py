"""Data models (Pydantic) - pure state, no UI imports, no clinical logic."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session completion status."""
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class Patient(BaseModel):
    """Patient demographic data."""
    model_config = ConfigDict(extra='ignore')

    id: str
    preferred_name: str
    date_of_birth: Optional[str] = None
    created_at: str
    updated_at: str


class Session(BaseModel):
    """Assessment session - contains all form field values, calculations, and generated report."""
    model_config = ConfigDict(extra='ignore')

    id: str
    patient_id: str
    schema_version: int
    date: str
    region: List[str]
    status: SessionStatus = SessionStatus.IN_PROGRESS
    field_data: Dict[str, Any] = {}
    checkboxes: Dict[str, bool] = {}
    tables: Dict[str, List[Dict[str, Any]]] = {}
    barriers_selected: List[str] = []
    barriers_priority_order: List[str] = []
    pain_type_dominant: Optional[str] = None
    pain_type_contributing: List[str] = []
    icd11_pathway: Optional[str] = None
    icd11_subtype: Optional[str] = None
    icd11_severity: Optional[str] = None
    report_text: str = ""
    report_confirmed: bool = False
    created_at: str
    updated_at: str


class OutcomeMeasureResult(BaseModel):
    """Outcome measure score and interpretation."""
    model_config = ConfigDict(extra='ignore')

    id: str
    session_id: str
    measure_name: str
    score: float
    subscores: Optional[Dict[str, float]] = None
    interpretation: Optional[str] = None
    administered_at: str


class SpecialTestResult(BaseModel):
    """Special test result for a region."""
    model_config = ConfigDict(extra='ignore')

    id: str
    session_id: str
    test_id: str
    result: str
    notes: Optional[str] = None
    recorded_at: str
