"""
GUARDIAN OS
Intervention Engine

Purpose:
    Compare simulated intervention scenarios, apply safety
    constraints, score candidate interventions, and produce
    an auditable recommendation.

Core flow:

    Station State
          ↓
    Risk Assessment
          ↓
    Simulation Engine
          ↓
    Candidate Scoring
          ↓
    Safety Validation
          ↓
    Intervention Decision
          ↓
    Execution Layer

Important:
    - This engine does NOT mutate station state.
    - This engine does NOT execute interventions.
    - Numeric calculations are deterministic.
    - Decision weights are prototype policy parameters.
    - Simulation data is synthetic.
"""


from dataclasses import dataclass
from typing import List


# ============================================================
# GUARDIAN OS IMPORTS
# ============================================================

from services.risk_engine.station_models import (
    StationState,
    calculate_utilization,
)

from services.risk_engine.risk_engine import (
    calculate_risk,
)

from services.event_ingestion.event_models import (
    EventSeverity,
    EventType,
    EventImpact,
    OperationalEvent,
    StationReference,
)

from services.simulation_engine.simulation_engine import (
    ScenarioResult,
    simulate_all,
)


# ============================================================
# PROTOTYPE DECISION POLICY
# ============================================================

# Relative importance of risk reduction.
RISK_WEIGHT = 0.55

# Relative importance of utilization improvement.
UTILIZATION_WEIGHT = 0.25

# Relative importance of operational recovery.
RECOVERY_WEIGHT = 0.20

# Maximum normalized operational cost penalty.
MAX_OPERATIONAL_COST = 20.0


# ============================================================
# SAFETY BOUNDARIES
# ============================================================

MAX_ACCEPTABLE_PROJECTED_UTILIZATION = 110.0

MAX_ACCEPTABLE_PROJECTED_RISK = 90.0


# ============================================================
# INTERVENTION DECISION
# ============================================================

@dataclass
class InterventionDecision:
    """
    Final recommendation produced by the
    Guardian Intervention Engine.
    """

    station_id: str

    selected_strategy: str

    baseline_risk: float
    projected_risk: float

    baseline_utilization: float
    projected_utilization: float

    risk_reduction: float
    utilization_reduction: float

    routes_moved: int
    capacity_recovered: float

    decision_score: float

    decision_status: str

    rationale: str

    safety_checks_passed: bool


# ============================================================
# BASELINE EVENT
# ============================================================

def build_capacity_shock_event(
    state: StationState,
) -> OperationalEvent:
    """
    Build the synthetic capacity-shock event used by the
    current Guardian simulation.
    """

    return OperationalEvent(
        event_id="EVT-0001",

        event_type=EventType.STATION_CAPACITY_SHOCK,

        timestamp="2026-09-18T10:30:00Z",

        source="GUARDIAN_SIMULATOR",

        station=StationReference(
            station_id=state.station_id,
            city=state.city,
            region=state.region,
        ),

        impact=EventImpact(
            severity=EventSeverity.HIGH,

            capacity_change_percent=-20.0,

            description=(
                "Synthetic station capacity disruption"
            ),
        ),

        metadata={
            "simulation": True,
        },
    )


# ============================================================
# BASELINE RISK
# ============================================================

def calculate_baseline_risk(
    state: StationState,
) -> float:
    """
    Calculate baseline risk through the canonical
    Guardian Risk Engine.
    """

    event = build_capacity_shock_event(
        state
    )

    assessment = calculate_risk(
        state,
        event,
    )

    return round(
        assessment.risk_score,
        2,
    )


# ============================================================
# RISK REDUCTION
# ============================================================

def calculate_risk_reduction(
    baseline_risk: float,
    projected_risk: float,
) -> float:
    """
    Calculate percentage risk reduction.
    """

    if baseline_risk <= 0:
        return 0.0

    reduction = (
        (
            baseline_risk
            - projected_risk
        )
        / baseline_risk
    ) * 100.0

    return max(
        0.0,
        reduction,
    )


# ============================================================
# UTILIZATION REDUCTION
# ============================================================

def calculate_utilization_reduction(
    baseline_utilization: float,
    projected_utilization: float,
) -> float:
    """
    Calculate utilization improvement in percentage points.
    """

    return max(
        0.0,
        baseline_utilization
        - projected_utilization,
    )


# ============================================================
# NORMALIZED UTILIZATION SCORE
# ============================================================

def calculate_utilization_score(
    baseline_utilization: float,
    projected_utilization: float,
) -> float:
    """
    Convert utilization improvement into a normalized
    0–100 score.

    A 30 percentage-point improvement is treated as
    a full-score improvement for this prototype.

    This normalization prevents percentage-point values
    from dominating the other decision components.
    """

    improvement = calculate_utilization_reduction(
        baseline_utilization,
        projected_utilization,
    )

    return min(
        100.0,
        (improvement / 30.0) * 100.0,
    )


# ============================================================
# RECOVERY SCORE
# ============================================================

def calculate_recovery_score(
    scenario: ScenarioResult,
) -> float:
    """
    Calculate normalized operational recovery.

    This is a prototype metric, not a real-world
    operational valuation.
    """

    utilization_recovery = max(
        0.0,
        100.0
        - scenario.projected_utilization,
    )

    risk_recovery = max(
        0.0,
        100.0
        - scenario.projected_risk,
    )

    recovery_score = (
        utilization_recovery * 0.5
        + risk_recovery * 0.5
    )

    return min(
        100.0,
        max(
            0.0,
            recovery_score,
        ),
    )


# ============================================================
# NORMALIZED OPERATIONAL COST
# ============================================================

def calculate_operational_cost(
    baseline_state: StationState,
    scenario: ScenarioResult,
) -> float:
    """
    Calculate a normalized operational movement penalty.

    IMPORTANT:

    We do NOT multiply raw capacity units by a cost factor.

    Capacity and route counts have different units, so they
    are normalized against the station baseline first.

    The resulting penalty is bounded between 0 and
    MAX_OPERATIONAL_COST.
    """

    # --------------------------------------------------------
    # Route movement ratio
    # --------------------------------------------------------

    if baseline_state.active_routes > 0:

        route_movement_ratio = (
            scenario.routes_moved
            / baseline_state.active_routes
        )

    else:

        route_movement_ratio = 0.0

    # --------------------------------------------------------
    # Capacity movement ratio
    # --------------------------------------------------------

    if baseline_state.capacity > 0:

        capacity_movement_ratio = (
            scenario.capacity_recovered
            / baseline_state.capacity
        )

    else:

        capacity_movement_ratio = 0.0

    # --------------------------------------------------------
    # Weighted normalized movement
    # --------------------------------------------------------

    normalized_cost = (
        route_movement_ratio * 0.50
        + capacity_movement_ratio * 0.50
    )

    return round(
        min(
            MAX_OPERATIONAL_COST,
            normalized_cost
            * MAX_OPERATIONAL_COST,
        ),
        2,
    )


# ============================================================
# DECISION SCORE
# ============================================================

def calculate_decision_score(
    baseline_state: StationState,
    baseline_risk: float,
    baseline_utilization: float,
    scenario: ScenarioResult,
) -> float:
    """
    Calculate the prototype intervention score.

    Score components:

        1. Risk reduction
        2. Utilization improvement
        3. Recovery
        4. Operational movement penalty

    Higher score indicates a stronger candidate under the
    documented prototype policy.

    This is not an objectively optimal real-world policy.
    """

    # --------------------------------------------------------
    # Risk reduction
    # --------------------------------------------------------

    risk_reduction = calculate_risk_reduction(
        baseline_risk,
        scenario.projected_risk,
    )

    # --------------------------------------------------------
    # Utilization improvement
    # --------------------------------------------------------

    utilization_score = calculate_utilization_score(
        baseline_utilization,
        scenario.projected_utilization,
    )

    # --------------------------------------------------------
    # Recovery
    # --------------------------------------------------------

    recovery_score = calculate_recovery_score(
        scenario
    )

    # --------------------------------------------------------
    # Operational cost
    # --------------------------------------------------------

    operational_cost = calculate_operational_cost(
        baseline_state,
        scenario,
    )

    # --------------------------------------------------------
    # Weighted score
    # --------------------------------------------------------

    score = (
        risk_reduction
        * RISK_WEIGHT

        + utilization_score
        * UTILIZATION_WEIGHT

        + recovery_score
        * RECOVERY_WEIGHT

        - operational_cost
    )

    return round(
        max(
            0.0,
            score,
        ),
        2,
    )


# ============================================================
# SAFETY VALIDATION
# ============================================================

def validate_scenario(
    scenario: ScenarioResult,
) -> tuple[bool, List[str]]:
    """
    Validate whether a simulated intervention satisfies
    Guardian's prototype safety boundaries.
    """

    failures: List[str] = []

    # --------------------------------------------------------
    # Utilization boundary
    # --------------------------------------------------------

    if (
        scenario.projected_utilization
        > MAX_ACCEPTABLE_PROJECTED_UTILIZATION
    ):

        failures.append(
            "Projected utilization exceeds safety boundary."
        )

    # --------------------------------------------------------
    # Risk boundary
    # --------------------------------------------------------

    if (
        scenario.projected_risk
        > MAX_ACCEPTABLE_PROJECTED_RISK
    ):

        failures.append(
            "Projected risk exceeds safety boundary."
        )

    # --------------------------------------------------------
    # Capacity validation
    # --------------------------------------------------------

    if (
        scenario.projected_capacity
        <= 0
    ):

        failures.append(
            "Projected capacity must remain positive."
        )

    # --------------------------------------------------------
    # Load validation
    # --------------------------------------------------------

    if (
        scenario.projected_load
        < 0
    ):

        failures.append(
            "Projected load cannot be negative."
        )

    # --------------------------------------------------------
    # Route validation
    # --------------------------------------------------------

    if (
        scenario.projected_routes
        < 0
    ):

        failures.append(
            "Projected routes cannot be negative."
        )

    return (
        len(failures) == 0,
        failures,
    )


# ============================================================
# RATIONALE
# ============================================================

def generate_rationale(
    baseline_risk: float,
    baseline_utilization: float,
    selected: ScenarioResult,
    decision_score: float,
) -> str:
    """
    Generate a deterministic explanation of the decision.

    Bedrock can later turn this structured explanation
    into richer natural-language operational intelligence.
    """

    risk_reduction = calculate_risk_reduction(
        baseline_risk,
        selected.projected_risk,
    )

    utilization_reduction = (
        calculate_utilization_reduction(
            baseline_utilization,
            selected.projected_utilization,
        )
    )

    return (
        f"{selected.strategy} was selected under the "
        f"Guardian prototype intervention policy. "

        f"Projected risk changes from "
        f"{baseline_risk:.2f} to "
        f"{selected.projected_risk:.2f}, "

        f"representing a "
        f"{risk_reduction:.2f}% reduction. "

        f"Projected utilization changes from "
        f"{baseline_utilization:.2f}% to "
        f"{selected.projected_utilization:.2f}%, "

        f"an improvement of "
        f"{utilization_reduction:.2f} "
        f"percentage points. "

        f"The strategy moves "
        f"{selected.routes_moved} routes "

        f"and recovers "
        f"{selected.capacity_recovered:.2f} "
        f"units of capacity. "

        f"Prototype decision score: "
        f"{decision_score:.2f}."
    )


# ============================================================
# SELECT INTERVENTION
# ============================================================

def select_intervention(
    state: StationState,
    scenarios: List[ScenarioResult],
) -> InterventionDecision:
    """
    Select the highest-scoring scenario that passes
    all safety constraints.
    """

    if not scenarios:

        raise ValueError(
            "At least one simulation scenario is required."
        )

    # --------------------------------------------------------
    # Baseline metrics
    # --------------------------------------------------------

    baseline_utilization = calculate_utilization(
        state
    )

    baseline_risk = calculate_baseline_risk(
        state
    )

    # --------------------------------------------------------
    # Candidate scenarios
    # --------------------------------------------------------

    candidates = []

    for scenario in scenarios:

        safety_passed, failures = (
            validate_scenario(
                scenario
            )
        )

        if not safety_passed:
            continue

        score = calculate_decision_score(
            state,
            baseline_risk,
            baseline_utilization,
            scenario,
        )

        candidates.append(
            (
                score,
                scenario,
            )
        )

    # --------------------------------------------------------
    # No safe intervention
    # --------------------------------------------------------

    if not candidates:

        return InterventionDecision(

            station_id=state.station_id,

            selected_strategy=(
                "NO_AUTOMATIC_INTERVENTION"
            ),

            baseline_risk=round(
                baseline_risk,
                2,
            ),

            projected_risk=round(
                baseline_risk,
                2,
            ),

            baseline_utilization=round(
                baseline_utilization,
                2,
            ),

            projected_utilization=round(
                baseline_utilization,
                2,
            ),

            risk_reduction=0.0,

            utilization_reduction=0.0,

            routes_moved=0,

            capacity_recovered=0.0,

            decision_score=0.0,

            decision_status="ESCALATE",

            rationale=(
                "No simulated intervention passed "
                "the Guardian safety boundaries. "
                "Automatic intervention was not selected."
            ),

            safety_checks_passed=False,
        )

    # --------------------------------------------------------
    # Highest scoring safe candidate
    # --------------------------------------------------------

    selected_score, selected = max(
        candidates,
        key=lambda item: item[0],
    )

    # --------------------------------------------------------
    # Outcome metrics
    # --------------------------------------------------------

    risk_reduction = calculate_risk_reduction(
        baseline_risk,
        selected.projected_risk,
    )

    utilization_reduction = (
        calculate_utilization_reduction(
            baseline_utilization,
            selected.projected_utilization,
        )
    )

    # --------------------------------------------------------
    # Rationale
    # --------------------------------------------------------

    rationale = generate_rationale(
        baseline_risk,
        baseline_utilization,
        selected,
        selected_score,
    )

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    return InterventionDecision(

        station_id=state.station_id,

        selected_strategy=selected.strategy,

        baseline_risk=round(
            baseline_risk,
            2,
        ),

        projected_risk=round(
            selected.projected_risk,
            2,
        ),

        baseline_utilization=round(
            baseline_utilization,
            2,
        ),

        projected_utilization=round(
            selected.projected_utilization,
            2,
        ),

        risk_reduction=round(
            risk_reduction,
            2,
        ),

        utilization_reduction=round(
            utilization_reduction,
            2,
        ),

        routes_moved=selected.routes_moved,

        capacity_recovered=round(
            selected.capacity_recovered,
            2,
        ),

        decision_score=selected_score,

        decision_status="RECOMMEND",

        rationale=rationale,

        safety_checks_passed=True,
    )


# ============================================================
# COMPLETE DECISION PIPELINE
# ============================================================

def evaluate_interventions(
    state: StationState,
) -> InterventionDecision:
    """
    Execute the complete:

        SIMULATE → DECIDE

    pipeline.
    """

    scenarios = simulate_all(
        state
    )

    return select_intervention(
        state,
        scenarios,
    )


# ============================================================
# SERIALIZATION
# ============================================================

def decision_to_dict(
    decision: InterventionDecision,
) -> dict:
    """
    Convert the intervention decision into a serializable
    dictionary for APIs, DynamoDB, S3, EventBridge,
    and audit logs.
    """

    return {

        "station_id": decision.station_id,

        "selected_strategy": (
            decision.selected_strategy
        ),

        "baseline_risk": (
            decision.baseline_risk
        ),

        "projected_risk": (
            decision.projected_risk
        ),

        "baseline_utilization": (
            decision.baseline_utilization
        ),

        "projected_utilization": (
            decision.projected_utilization
        ),

        "risk_reduction": (
            decision.risk_reduction
        ),

        "utilization_reduction": (
            decision.utilization_reduction
        ),

        "routes_moved": (
            decision.routes_moved
        ),

        "capacity_recovered": (
            decision.capacity_recovered
        ),

        "decision_score": (
            decision.decision_score
        ),

        "decision_status": (
            decision.decision_status
        ),

        "rationale": (
            decision.rationale
        ),

        "safety_checks_passed": (
            decision.safety_checks_passed
        ),
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("GUARDIAN OS — INTERVENTION ENGINE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Synthetic station
    # --------------------------------------------------------

    station = StationState(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        capacity=8000,
        current_load=8200,
        active_routes=384,
    )

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------

    baseline_utilization = calculate_utilization(
        station
    )

    baseline_risk = calculate_baseline_risk(
        station
    )

    print("\nBASELINE")
    print("-" * 70)

    print(
        f"Station: "
        f"{station.station_id}"
    )

    print(
        f"Capacity: "
        f"{station.capacity}"
    )

    print(
        f"Load: "
        f"{station.current_load}"
    )

    print(
        f"Routes: "
        f"{station.active_routes}"
    )

    print(
        f"Utilization: "
        f"{baseline_utilization:.2f}%"
    )

    print(
        f"Risk: "
        f"{baseline_risk:.2f}/100"
    )

    # --------------------------------------------------------
    # Simulation
    # --------------------------------------------------------

    scenarios = simulate_all(
        station
    )

    print("\nSCENARIO EVALUATION")
    print("-" * 70)

    for scenario in scenarios:

        score = calculate_decision_score(
            station,
            baseline_risk,
            baseline_utilization,
            scenario,
        )

        safety_passed, failures = (
            validate_scenario(
                scenario
            )
        )

        print(
            f"\nStrategy: "
            f"{scenario.strategy}"
        )

        print(
            f"Projected Capacity: "
            f"{scenario.projected_capacity}"
        )

        print(
            f"Projected Load: "
            f"{scenario.projected_load}"
        )

        print(
            f"Projected Routes: "
            f"{scenario.projected_routes}"
        )

        print(
            f"Projected Risk: "
            f"{scenario.projected_risk:.2f}/100"
        )

        print(
            f"Projected Utilization: "
            f"{scenario.projected_utilization:.2f}%"
        )

        print(
            f"Decision Score: "
            f"{score:.2f}"
        )

        print(
            f"Safety Check: "
            f"{'PASS' if safety_passed else 'FAIL'}"
        )

        if failures:

            print(
                "Safety Failures:"
            )

            for failure in failures:

                print(
                    f"  - {failure}"
                )

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    decision = select_intervention(
        station,
        scenarios,
    )

    print("\nFINAL DECISION")
    print("-" * 70)

    print(
        f"Selected Strategy: "
        f"{decision.selected_strategy}"
    )

    print(
        f"Decision Status: "
        f"{decision.decision_status}"
    )

    print(
        f"Decision Score: "
        f"{decision.decision_score:.2f}"
    )

    print(
        f"Risk: "
        f"{decision.baseline_risk:.2f}"
        f" → "
        f"{decision.projected_risk:.2f}"
    )

    print(
        f"Utilization: "
        f"{decision.baseline_utilization:.2f}%"
        f" → "
        f"{decision.projected_utilization:.2f}%"
    )

    print(
        f"Risk Reduction: "
        f"{decision.risk_reduction:.2f}%"
    )

    print(
        f"Utilization Improvement: "
        f"{decision.utilization_reduction:.2f} "
        f"percentage points"
    )

    print(
        f"Routes Moved: "
        f"{decision.routes_moved}"
    )

    print(
        f"Capacity Recovered: "
        f"{decision.capacity_recovered:.2f}"
    )

    print(
        f"Safety Checks: "
        f"{'PASSED' if decision.safety_checks_passed else 'FAILED'}"
    )

    print(
        f"\nRationale:\n"
        f"{decision.rationale}"
    )

    print("\n" + "=" * 70)
    print("INTERVENTION ENGINE TEST COMPLETE")
    print("=" * 70)