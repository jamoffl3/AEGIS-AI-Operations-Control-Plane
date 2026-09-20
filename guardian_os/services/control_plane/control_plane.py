"""
AEGIS — Control Plane

Central orchestration layer for:

SENSE → UNDERSTAND → SIMULATE → DECIDE
→ HUMAN REVIEW → ACT → MEASURE → EXPLAIN

The control plane coordinates the existing deterministic engines.

It does not duplicate their calculations.

Local persistence is provided through LocalStateStore so that
assessment state can survive application restarts.

Cloud migration path:

    LocalStateStore
          ↓
    DynamoDBStateStore
"""


from __future__ import annotations


# ============================================================
# STANDARD LIBRARY
# ============================================================

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4


# ============================================================
# EVENT INGESTION
# ============================================================

from services.event_ingestion.event_models import (
    OperationalEvent,
    event_from_dict,
)

from services.event_ingestion.event_processor import (
    load_json,
)


# ============================================================
# RISK ENGINE
# ============================================================

from services.risk_engine.station_models import (
    StationState,
    determine_station_status,
)

from services.risk_engine.risk_engine import (
    calculate_risk,
)


# ============================================================
# INTERVENTION ENGINE
# ============================================================

from services.intervention_engine.intervention_engine import (
    evaluate_interventions,
)


# ============================================================
# EXECUTION ENGINE
# ============================================================

from services.execution_engine.execution_engine import (
    execute_intervention,
)


# ============================================================
# OUTCOME ENGINE
# ============================================================

from services.outcome_engine.outcome_engine import (
    measure_outcome,
)


# ============================================================
# AI INTELLIGENCE
# ============================================================

from services.ai_intelligence.intelligence_models import (
    RiskDriver,
    ScenarioSummary,
    OperationalContext,
)

from services.ai_intelligence.intelligence_service import (
    IntelligenceService,
    create_intelligence_service,
)


# ============================================================
# STATE STORE
# ============================================================

from services.state_store import (
    LocalStateStore,
)


# ============================================================
# CONTROL PLANE RESULT
# ============================================================


@dataclass
class ControlPlaneResult:
    """
    Complete result produced by an AEGIS control-plane cycle.
    """

    event: OperationalEvent
    initial_state: StationState
    risk_assessment: Any
    intervention_decision: Any
    execution_result: Any
    outcome_measurement: Any
    operational_context: OperationalContext
    intelligence_result: Any


# ============================================================
# AEGIS CONTROL PLANE
# ============================================================


class GuardianControlPlane:
    """
    Main AEGIS orchestration service.

    The control plane separates:

        ASSESS
            ↓
        HUMAN REVIEW
            ↓
        EXECUTE
            ↓
        MEASURE
            ↓
        EXPLAIN

    This prevents an intervention recommendation from being
    executed without an explicit approval step.

    Local assessment persistence is handled through LocalStateStore.
    """


    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        intelligence_service: IntelligenceService | None = None,
        state_store: LocalStateStore | None = None,
    ) -> None:

        self.intelligence_service = (
            intelligence_service
            or create_intelligence_service(
                mock_mode=True,
            )
        )

        self.state_store = (
            state_store
            or LocalStateStore()
        )


    # ========================================================
    # ASSESS
    # ========================================================

    def assess(
        self,
        event: OperationalEvent,
        initial_state: StationState,
    ) -> tuple[
        OperationalEvent,
        StationState,
        Any,
        Any,
    ]:
        """
        Run the deterministic AEGIS assessment pipeline.

        Flow:

            SENSE
              ↓
            UNDERSTAND
              ↓
            SIMULATE
              ↓
            DECIDE
              ↓
            HUMAN REVIEW

        IMPORTANT:

        This method does NOT execute an intervention.

        The resulting assessment bundle is persisted locally so
        that the approval stage can recover it after a restart.
        """


        # ----------------------------------------------------
        # 1. SENSE
        # ----------------------------------------------------

        if not isinstance(
            event,
            OperationalEvent,
        ):
            raise TypeError(
                "Control Plane expects an OperationalEvent instance."
            )


        if not isinstance(
            initial_state,
            StationState,
        ):
            raise TypeError(
                "Control Plane expects a StationState instance."
            )


        processed_event = event


        # ----------------------------------------------------
        # 2. UNDERSTAND
        # ----------------------------------------------------

        state = self._normalize_station_status(
            initial_state
        )


        risk_assessment = calculate_risk(
            state,
            processed_event,
        )


        # ----------------------------------------------------
        # 3. SIMULATE
        # 4. DECIDE
        # ----------------------------------------------------

        intervention_decision = evaluate_interventions(
            state,
        )


        # ----------------------------------------------------
        # PERSIST ASSESSMENT
        # ----------------------------------------------------

        assessment_id = self._generate_assessment_id()


        assessment_record = {
            "assessment_id": assessment_id,
            "status": "AWAITING_HUMAN_APPROVAL",
            "event": processed_event,
            "state": state,
            "risk_assessment": risk_assessment,
            "intervention_decision": intervention_decision,
        }


        self.state_store.put(
            assessment_id,
            assessment_record,
        )


        # ----------------------------------------------------
        # HUMAN REVIEW GATE
        # ----------------------------------------------------

        return (
            processed_event,
            state,
            risk_assessment,
            intervention_decision,
        )


    # ========================================================
    # ASSESSMENT PERSISTENCE
    # ========================================================

    def create_assessment(
        self,
        event: OperationalEvent,
        initial_state: StationState,
    ) -> dict[str, Any]:
        """
        Create and persist a human-review assessment.

        This method is intended for API/UI workflows where the
        assessment needs a stable identifier.

        The deterministic assessment itself is still performed
        by assess().
        """

        (
            processed_event,
            state,
            risk_assessment,
            intervention_decision,
        ) = self.assess(
            event,
            initial_state,
        )


        records = self.state_store.all()


        matching_records = [
            record
            for record in records.values()
            if (
                isinstance(record, dict)
                and record.get("event") == processed_event
                and record.get("status")
                == "AWAITING_HUMAN_APPROVAL"
            )
        ]


        if matching_records:
            record = matching_records[-1]

        else:
            assessment_id = self._generate_assessment_id()

            record = {
                "assessment_id": assessment_id,
                "status": "AWAITING_HUMAN_APPROVAL",
                "event": processed_event,
                "state": state,
                "risk_assessment": risk_assessment,
                "intervention_decision": intervention_decision,
            }

            self.state_store.put(
                assessment_id,
                record,
            )


        return record


    def get_assessment(
        self,
        assessment_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a persisted assessment.
        """

        record = self.state_store.get(
            assessment_id
        )

        if record is None:
            return None

        if not isinstance(
            record,
            dict,
        ):
            return None

        return record


    def reject_assessment(
        self,
        assessment_id: str,
    ) -> bool:
        """
        Reject and remove a pending assessment.

        No intervention is executed.
        """

        record = self.state_store.get(
            assessment_id
        )

        if record is None:
            return False


        if record.get("status") != "AWAITING_HUMAN_APPROVAL":
            return False


        self.state_store.delete(
            assessment_id
        )

        return True


    # ========================================================
    # APPROVE + EXECUTE
    # ========================================================

    def approve_assessment(
        self,
        assessment_id: str,
    ) -> ControlPlaneResult:
        """
        Retrieve a persisted assessment and execute it after
        explicit human approval.
        """

        record = self.state_store.get(
            assessment_id
        )


        if record is None:
            raise ValueError(
                f"Assessment '{assessment_id}' was not found."
            )


        if record.get("status") != "AWAITING_HUMAN_APPROVAL":
            raise ValueError(
                f"Assessment '{assessment_id}' is not awaiting approval."
            )


        event = record["event"]
        state = record["state"]
        risk_assessment = record["risk_assessment"]
        intervention_decision = record["intervention_decision"]


        result = self.approve_and_execute(
            event,
            state,
            risk_assessment,
            intervention_decision,
        )


        self.state_store.delete(
            assessment_id
        )


        return result


    # ========================================================
    # APPROVE + EXECUTE
    # ========================================================

    def approve_and_execute(
        self,
        event: OperationalEvent,
        state: StationState,
        risk_assessment: Any,
        intervention_decision: Any,
    ) -> ControlPlaneResult:
        """
        Execute a previously assessed intervention after
        explicit human approval.

        Flow:

            APPROVED
              ↓
            ACT
              ↓
            MEASURE
              ↓
            EXPLAIN
        """


        if not isinstance(
            event,
            OperationalEvent,
        ):
            raise TypeError(
                "Control Plane expects an OperationalEvent instance."
            )


        if not isinstance(
            state,
            StationState,
        ):
            raise TypeError(
                "Control Plane expects a StationState instance."
            )


        if intervention_decision is None:
            raise ValueError(
                "An intervention decision is required before execution."
            )


        # ----------------------------------------------------
        # 5. ACT
        # ----------------------------------------------------

        execution_id = self._generate_execution_id()


        execution_result = execute_intervention(
            state,
            intervention_decision,
            execution_id,
        )


        # ----------------------------------------------------
        # 6. MEASURE
        # ----------------------------------------------------

        post_state = self._build_post_state(
            state,
            execution_result,
        )


        outcome_measurement = measure_outcome(
            state,
            post_state,
            execution_result,
        )


        # ----------------------------------------------------
        # 7. EXPLAIN
        # ----------------------------------------------------

        operational_context = self._build_ai_context(
            event=event,
            state=state,
            risk_assessment=risk_assessment,
            intervention_decision=intervention_decision,
            execution_result=execution_result,
            outcome_measurement=outcome_measurement,
        )


        intelligence_result = (
            self.intelligence_service.analyze(
                operational_context
            )
        )


        return ControlPlaneResult(
            event=event,
            initial_state=state,
            risk_assessment=risk_assessment,
            intervention_decision=intervention_decision,
            execution_result=execution_result,
            outcome_measurement=outcome_measurement,
            operational_context=operational_context,
            intelligence_result=intelligence_result,
        )


    # ========================================================
    # LEGACY / COMPLETE CONTROL LOOP
    # ========================================================

    def process(
        self,
        event: OperationalEvent,
        initial_state: StationState,
    ) -> ControlPlaneResult:
        """
        Run the complete AEGIS loop.

        This method is retained for backward compatibility with
        existing local tests and API code.

        It represents an explicitly authorized execution path.

        New UI/API flows should use:

            assess()
                ↓
            human approval
                ↓
            approve_and_execute()
        """


        (
            processed_event,
            state,
            risk_assessment,
            intervention_decision,
        ) = self.assess(
            event,
            initial_state,
        )


        return self.approve_and_execute(
            processed_event,
            state,
            risk_assessment,
            intervention_decision,
        )


    # ========================================================
    # EXECUTION ID
    # ========================================================

    @staticmethod
    def _generate_execution_id() -> str:
        """Generate a unique execution identifier."""

        return (
            f"EXEC-CP-"
            f"{uuid4().hex[:8].upper()}"
        )


    @staticmethod
    def _generate_assessment_id() -> str:
        """Generate a unique human-review assessment identifier."""

        return (
            f"ASSESS-"
            f"{uuid4().hex[:10].upper()}"
        )


    # ========================================================
    # STATION STATUS
    # ========================================================

    @staticmethod
    def _normalize_station_status(
        state: StationState,
    ) -> StationState:
        """Ensure StationState.status reflects actual utilization."""

        calculated_status = determine_station_status(
            state
        )


        return StationState(
            station_id=state.station_id,
            city=state.city,
            region=state.region,
            capacity=state.capacity,
            current_load=state.current_load,
            active_routes=state.active_routes,
            status=calculated_status,
        )


    # ========================================================
    # POST STATE
    # ========================================================

    @staticmethod
    def _build_post_state(
        previous_state: StationState,
        execution_result: Any,
    ) -> StationState:
        """Reconstruct station state after intervention execution."""

        transition = execution_result.state_transition


        return StationState(
            station_id=execution_result.station_id,
            city=previous_state.city,
            region=previous_state.region,
            capacity=transition.new_capacity,
            current_load=transition.new_load,
            active_routes=transition.new_routes,
            status=transition.new_status,
        )


    # ========================================================
    # STATUS NORMALIZATION
    # ========================================================

    @staticmethod
    def _status_to_string(
        status: Any,
    ) -> str:
        """Normalize either an Enum status or an existing string."""

        if hasattr(
            status,
            "value",
        ):
            return str(status.value)


        return str(status)


    # ========================================================
    # AI CONTEXT
    # ========================================================

    @staticmethod
    def _build_ai_context(
        *,
        event: OperationalEvent,
        state: StationState,
        risk_assessment: Any,
        intervention_decision: Any,
        execution_result: Any,
        outcome_measurement: Any,
    ) -> OperationalContext:
        """
        Convert deterministic engine outputs into
        OperationalContext.

        This is the boundary between deterministic AEGIS
        engines and the AI intelligence subsystem.
        """


        # ----------------------------------------------------
        # RISK DRIVERS
        # ----------------------------------------------------

        risk_drivers: list[RiskDriver] = []


        for driver in risk_assessment.drivers:

            risk_drivers.append(
                RiskDriver(
                    name=str(driver),
                    value=0.0,
                    contribution=0.0,
                    description=str(driver),
                )
            )


        # ----------------------------------------------------
        # SCENARIO SUMMARIES
        # ----------------------------------------------------

        scenarios: list[ScenarioSummary] = []


        all_scenarios = getattr(
            intervention_decision,
            "all_scenarios",
            [],
        )


        for scenario in all_scenarios:

            risk_reduction = (
                risk_assessment.risk_score
                - scenario.projected_risk
            )


            utilization_improvement = (
                risk_assessment.utilization
                - scenario.projected_utilization
            )


            decision_score = getattr(
                scenario,
                "decision_score",
                0.0,
            )


            safety_passed = (
                scenario.projected_utilization <= 110.0
                and scenario.projected_risk <= 90.0
            )


            scenarios.append(
                ScenarioSummary(
                    strategy=scenario.strategy,
                    projected_risk=scenario.projected_risk,
                    projected_utilization=(
                        scenario.projected_utilization
                    ),
                    projected_capacity=(
                        scenario.projected_capacity
                    ),
                    projected_load=(
                        scenario.projected_load
                    ),
                    projected_routes=(
                        scenario.projected_routes
                    ),
                    risk_reduction=risk_reduction,
                    utilization_improvement=(
                        utilization_improvement
                    ),
                    decision_score=decision_score,
                    safety_passed=safety_passed,
                )
            )


        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        execution_status = (
            GuardianControlPlane._status_to_string(
                execution_result.status
            )
        )


        outcome_status = (
            GuardianControlPlane._status_to_string(
                outcome_measurement.outcome_status
            )
        )


        # ----------------------------------------------------
        # OPERATIONAL CONTEXT
        # ----------------------------------------------------

        return OperationalContext(
            station_id=state.station_id,
            city=state.city,
            region=state.region,

            event_type=event.event_type.value,
            event_severity=event.impact.severity.value,
            event_description=event.impact.description,

            capacity=state.capacity,
            current_load=state.current_load,
            active_routes=state.active_routes,

            utilization=risk_assessment.utilization,
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level,

            risk_drivers=risk_drivers,
            scenarios=scenarios,

            selected_strategy=(
                intervention_decision.selected_strategy
            ),

            decision_score=(
                intervention_decision.decision_score
            ),

            execution_status=execution_status,

            outcome_status=outcome_status,

            outcome_effectiveness=(
                outcome_measurement.effectiveness_score
            ),

            metadata={
                "simulation": True,
                "data_source": "synthetic",
                "control_plane": "AEGIS",
                "human_approval_required": True,
            },
        )


# ============================================================
# FACTORY
# ============================================================


def create_control_plane() -> GuardianControlPlane:
    """Create a local AEGIS control plane."""

    intelligence_service = (
        create_intelligence_service(
            mock_mode=True,
        )
    )


    state_store = LocalStateStore()


    return GuardianControlPlane(
        intelligence_service=intelligence_service,
        state_store=state_store,
    )


# ============================================================
# TEST EVENT
# ============================================================


def load_test_event() -> OperationalEvent:
    """Load the first synthetic event from simulator/events.json."""

    project_root = (
        Path(__file__).resolve().parents[2]
    )


    events_file = (
        project_root
        / "simulator"
        / "events.json"
    )


    events = load_json(
        events_file
    )


    if not events:
        raise ValueError(
            "No events found in simulator/events.json."
        )


    return event_from_dict(
        events[0]
    )


# ============================================================
# TEST STATION
# ============================================================


def build_test_station() -> StationState:
    """Build the synthetic CHN-017 station used by local tests."""

    return StationState(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        capacity=8000,
        current_load=8200,
        active_routes=384,
    )


# ============================================================
# ASSESSMENT DISPLAY
# ============================================================


def print_assessment(
    event: OperationalEvent,
    state: StationState,
    risk_assessment: Any,
    intervention_decision: Any,
) -> None:
    """Print the human-review stage."""

    print()
    print("=" * 70)
    print("AEGIS — HUMAN REVIEW GATE")
    print("=" * 70)

    print("\nEVENT")
    print("-" * 70)

    print(
        f"Event ID: {event.event_id}"
    )

    print(
        f"Type: {event.event_type.value}"
    )

    print(
        f"Severity: {event.impact.severity.value}"
    )

    print(
        f"Station: {event.station.station_id}"
    )

    print("\nRISK ASSESSMENT")
    print("-" * 70)

    print(
        f"Risk: "
        f"{risk_assessment.risk_score:.2f}/100"
    )

    print(
        f"Risk Level: "
        f"{risk_assessment.risk_level}"
    )

    print(
        f"Utilization: "
        f"{risk_assessment.utilization:.2f}%"
    )

    print("\nINTERVENTION RECOMMENDATION")
    print("-" * 70)

    print(
        f"Strategy: "
        f"{intervention_decision.selected_strategy}"
    )

    print(
        f"Decision Score: "
        f"{intervention_decision.decision_score:.2f}"
    )

    print(
        "Safety Checks: "
        + (
            "PASSED"
            if intervention_decision.safety_checks_passed
            else "FAILED"
        )
    )

    print(
        f"\nProjected Risk: "
        f"{intervention_decision.baseline_risk:.2f}"
        f" → "
        f"{intervention_decision.projected_risk:.2f}"
    )

    print(
        f"Projected Utilization: "
        f"{intervention_decision.baseline_utilization:.2f}%"
        f" → "
        f"{intervention_decision.projected_utilization:.2f}%"
    )

    print(
        f"\nRationale:\n"
        f"{intervention_decision.rationale}"
    )

    print()
    print("STATUS: AWAITING HUMAN APPROVAL")
    print("NO INTERVENTION HAS BEEN EXECUTED.")
    print("=" * 70)


# ============================================================
# COMPLETE LOCAL TEST
# ============================================================


if __name__ == "__main__":

    event = load_test_event()

    station = build_test_station()

    control_plane = create_control_plane()


    # --------------------------------------------------------
    # ASSESS ONLY
    # --------------------------------------------------------

    (
        processed_event,
        state,
        risk_assessment,
        intervention_decision,
    ) = control_plane.assess(
        event,
        station,
    )


    print_assessment(
        processed_event,
        state,
        risk_assessment,
        intervention_decision,
    )


    # --------------------------------------------------------
    # EXPLICIT APPROVAL
    #
    # This simulates the human pressing:
    #
    # APPROVE & EXECUTE
    # --------------------------------------------------------

    APPROVED = True


    if APPROVED:

        print()
        print("HUMAN APPROVAL RECEIVED")
        print("Proceeding to execution...")


        result = control_plane.approve_and_execute(
            processed_event,
            state,
            risk_assessment,
            intervention_decision,
        )


        print("\nEXECUTION")
        print("-" * 70)

        print(
            f"Execution ID: "
            f"{result.execution_result.execution_id}"
        )

        print(
            "Status: "
            + GuardianControlPlane._status_to_string(
                result.execution_result.status
            )
        )


        transition = (
            result.execution_result.state_transition
        )


        print(
            f"Capacity: "
            f"{transition.previous_capacity:.2f}"
            f" → "
            f"{transition.new_capacity:.2f}"
        )


        print(
            f"Load: "
            f"{transition.previous_load:.2f}"
            f" → "
            f"{transition.new_load:.2f}"
        )


        print(
            f"Routes: "
            f"{transition.previous_routes}"
            f" → "
            f"{transition.new_routes}"
        )


        print(
            f"Utilization: "
            f"{transition.previous_utilization:.2f}%"
            f" → "
            f"{transition.new_utilization:.2f}%"
        )


        print("\nOUTCOME")
        print("-" * 70)


        print(
            f"Risk: "
            f"{result.outcome_measurement.baseline_risk:.2f}"
            f" → "
            f"{result.outcome_measurement.post_intervention_risk:.2f}"
        )


        print(
            f"Risk Reduction: "
            f"{result.outcome_measurement.risk_reduction:.2f}%"
        )


        print(
            f"Utilization Improvement: "
            f"{result.outcome_measurement.utilization_improvement:.2f}"
            f" percentage points"
        )


        print(
            f"Effectiveness: "
            f"{result.outcome_measurement.effectiveness_score:.2f}/100"
        )


        print(
            "Outcome Status: "
            + GuardianControlPlane._status_to_string(
                result.outcome_measurement.outcome_status
            )
        )


        print("\nAI INTELLIGENCE")
        print("-" * 70)


        intelligence = result.intelligence_result


        print(
            f"Generated By: "
            f"{intelligence.generated_by}"
        )


        print(
            "Grounded In Deterministic Data: "
            f"{intelligence.grounded_in_deterministic_data}"
        )


        print(
            "Human Review Required: "
            f"{intelligence.recommendation.requires_human_review}"
        )


        print("\nCONTROL LOOP")
        print("-" * 70)


        print(
            "SENSE → UNDERSTAND → SIMULATE → DECIDE "
            "→ HUMAN REVIEW → ACT → MEASURE → EXPLAIN"
        )


    else:

        print()
        print("INTERVENTION REJECTED")
        print("NO STATE CHANGE WAS EXECUTED.")