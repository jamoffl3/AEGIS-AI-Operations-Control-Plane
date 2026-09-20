"""
GUARDIAN OS — API Models

API-facing contracts for the Guardian OS control plane.

These models provide a stable boundary between the backend
control plane and future clients such as:

- Web frontend
- REST API
- AWS API Gateway
- Lambda
- External integrations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EventRequest:
    """
    Request submitted to Guardian OS for processing.
    """

    event_id: str
    event_type: str
    station_id: str
    city: str
    region: str
    severity: str
    description: str
    capacity_change_percent: float = 0.0
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class StationRequest:
    """
    Current operational state supplied to Guardian OS.
    """

    station_id: str
    city: str
    region: str
    capacity: float
    current_load: float
    active_routes: int


@dataclass(frozen=True)
class RiskResponse:
    """
    API representation of a risk assessment.
    """

    station_id: str
    risk_score: float
    risk_level: str
    utilization: float
    capacity_overload: float
    drivers: list[str]


@dataclass(frozen=True)
class ScenarioResponse:
    """
    API representation of one simulated intervention.
    """

    strategy: str
    projected_capacity: float
    projected_load: float
    projected_routes: int
    projected_utilization: float
    projected_risk: float
    risk_reduction: float
    utilization_improvement: float
    decision_score: float
    safety_passed: bool


@dataclass(frozen=True)
class InterventionResponse:
    """
    API representation of the selected intervention.
    """

    selected_strategy: str
    decision_score: float
    baseline_risk: float
    projected_risk: float
    baseline_utilization: float
    projected_utilization: float
    risk_reduction: float
    utilization_reduction: float
    routes_moved: int
    capacity_recovered: float
    decision_status: str
    safety_checks_passed: bool
    rationale: str
    scenarios: list[ScenarioResponse]


@dataclass(frozen=True)
class ExecutionResponse:
    """
    API representation of intervention execution.
    """

    execution_id: str
    station_id: str
    strategy: str
    status: str

    previous_capacity: float
    new_capacity: float

    previous_load: float
    new_load: float

    previous_routes: int
    new_routes: int

    previous_utilization: float
    new_utilization: float


@dataclass(frozen=True)
class OutcomeResponse:
    """
    API representation of measured intervention outcome.
    """

    execution_id: str
    station_id: str
    strategy: str

    baseline_risk: float
    post_intervention_risk: float
    risk_reduction: float

    baseline_utilization: float
    post_intervention_utilization: float
    utilization_improvement: float

    baseline_capacity: float
    post_intervention_capacity: float

    baseline_load: float
    post_intervention_load: float

    baseline_routes: int
    post_intervention_routes: int
    routes_moved: int

    effectiveness_score: float
    outcome_status: str

    measurement_notes: str


@dataclass(frozen=True)
class IntelligenceResponse:
    """
    API representation of AI-generated intelligence.
    """

    summary: str
    recommended_action: str
    reasoning: str
    expected_effect: str
    constraints: list[str]
    requires_human_review: bool
    generated_by: str
    grounded_in_deterministic_data: bool


@dataclass(frozen=True)
class GuardianResponse:
    """
    Complete API response from one Guardian OS control cycle.
    """

    event: dict[str, Any]
    station: dict[str, Any]

    risk: RiskResponse
    intervention: InterventionResponse
    execution: ExecutionResponse
    outcome: OutcomeResponse
    intelligence: IntelligenceResponse

    control_loop: list[str]