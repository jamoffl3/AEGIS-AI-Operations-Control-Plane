"""
AEGIS — REST API

FastAPI application exposing the AEGIS application service
through HTTP endpoints.

Human-gated control flow:

    Client
      ↓
    FastAPI
      ↓
    GuardianAPIService
      ↓
    ASSESS
      ↓
    HUMAN REVIEW
      ↓
    APPROVE
      ↓
    EXECUTE
      ↓
    MEASURE
      ↓
    EXPLAIN
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.api.api_models import (
    EventRequest,
    StationRequest,
)

from services.api.api_service import (
    GuardianAPIService,
)


# ======================================================================
# APPLICATION
# ======================================================================

app = FastAPI(
    title="AEGIS API",
    description=(
        "Proactive Last-Mile Risk & Workload Intelligence "
        "API for AEGIS."
    ),
    version="0.2.0",
)


# ======================================================================
# CORS
# ======================================================================

# Permissive CORS for the deployed prototype.
# This can be restricted to the final frontend origin later.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# SERVICE
# ======================================================================

guardian_api = GuardianAPIService()


# ======================================================================
# REQUEST SCHEMAS
# ======================================================================


class EventPayload(BaseModel):
    """
    HTTP request model for an operational event.
    """

    event_id: str = Field(
        ...,
        description="Unique operational event ID.",
    )

    event_type: str = Field(
        ...,
        description="AEGIS event type.",
    )

    station_id: str = Field(
        ...,
        description="Affected station ID.",
    )

    city: str = Field(
        ...,
        description="Station city.",
    )

    region: str = Field(
        ...,
        description="Station region.",
    )

    severity: str = Field(
        ...,
        description="Event severity.",
    )

    description: str = Field(
        ...,
        description="Human-readable event description.",
    )

    capacity_change_percent: float = Field(
        default=0.0,
        description="Capacity impact percentage.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata.",
    )


class StationPayload(BaseModel):
    """
    HTTP request model for current station state.
    """

    station_id: str = Field(
        ...,
        description="Station identifier.",
    )

    city: str = Field(
        ...,
        description="Station city.",
    )

    region: str = Field(
        ...,
        description="Station region.",
    )

    capacity: float = Field(
        ...,
        gt=0,
        description="Effective station capacity.",
    )

    current_load: float = Field(
        ...,
        ge=0,
        description="Current station load.",
    )

    active_routes: int = Field(
        ...,
        ge=0,
        description="Number of active routes.",
    )


class ProcessEventRequest(BaseModel):
    """
    Complete request for one AEGIS event assessment.
    """

    event: EventPayload
    station: StationPayload


class ApproveAssessmentRequest(BaseModel):
    """
    Explicit human approval request.

    The presence of this request represents the approval action
    from the human reviewer.
    """

    approved: bool = Field(
        ...,
        description=(
            "Explicit human approval. "
            "Must be true to execute."
        ),
    )


# ======================================================================
# HEALTH
# ======================================================================


@app.get(
    "/api/v1/health",
)
def health_check() -> dict[str, Any]:
    """
    Health endpoint.

    Used by the frontend, deployment platform, or load balancer
    to verify that the API process is available.
    """

    return {
        "status": "healthy",
        "service": "aegis-api",
        "version": "0.2.0",
    }


# ======================================================================
# ROOT
# ======================================================================


@app.get(
    "/",
)
def root() -> dict[str, Any]:
    """
    API root endpoint.
    """

    return {
        "service": "AEGIS",
        "description": (
            "Proactive Last-Mile Risk & Workload Intelligence"
        ),
        "status": "online",
        "api_version": "v1",
        "control_loop": [
            "SENSE",
            "UNDERSTAND",
            "SIMULATE",
            "DECIDE",
            "HUMAN REVIEW",
            "ACT",
            "MEASURE",
            "EXPLAIN",
        ],
    }


# ======================================================================
# ASSESS EVENT
# ======================================================================


@app.post(
    "/api/v1/events/assess",
)
def assess_event(
    request: ProcessEventRequest,
) -> dict[str, Any]:
    """
    Assess an operational event without executing an intervention.

    Flow:

        Event
          ↓
        Risk
          ↓
        Simulation
          ↓
        Intervention Decision
          ↓
        HUMAN REVIEW

    Execution does NOT occur here.
    """

    try:
        event_request = EventRequest(
            event_id=request.event.event_id,
            event_type=request.event.event_type,
            station_id=request.event.station_id,
            city=request.event.city,
            region=request.event.region,
            severity=request.event.severity,
            description=request.event.description,
            capacity_change_percent=(
                request.event.capacity_change_percent
            ),
            metadata=request.event.metadata,
        )

        station_request = StationRequest(
            station_id=request.station.station_id,
            city=request.station.city,
            region=request.station.region,
            capacity=request.station.capacity,
            current_load=request.station.current_load,
            active_routes=request.station.active_routes,
        )

        assessment = guardian_api.assess_event(
            event_request,
            station_request,
        )

        return {
            "success": True,
            "data": assessment,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "AEGIS assessment failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc


# ======================================================================
# GET ASSESSMENT
# ======================================================================


@app.get(
    "/api/v1/assessments/{assessment_id}",
)
def get_assessment(
    assessment_id: str,
) -> dict[str, Any]:
    """
    Retrieve the current state of an AEGIS assessment.

    This endpoint does not execute anything.
    """

    try:
        assessment = guardian_api.get_assessment(
            assessment_id
        )

        return {
            "success": True,
            "data": assessment,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "AEGIS assessment lookup failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc


# ======================================================================
# APPROVE + EXECUTE
# ======================================================================


@app.post(
    "/api/v1/assessments/{assessment_id}/approve",
)
def approve_assessment(
    assessment_id: str,
    request: ApproveAssessmentRequest,
) -> dict[str, Any]:
    """
    Explicitly approve or reject a pending intervention.

    Execution occurs ONLY when:

        approved == True
    """

    if not request.approved:
        return {
            "success": True,
            "data": {
                "assessment_id": assessment_id,
                "status": "REJECTED",
                "execution": {
                    "executed": False,
                    "status": "NOT_EXECUTED",
                },
                "message": (
                    "Human reviewer rejected the "
                    "intervention. No execution occurred."
                ),
            },
        }

    try:
        result = guardian_api.approve_and_execute(
            assessment_id
        )

        return {
            "success": True,
            "data": {
                "assessment_id": assessment_id,
                "status": "APPROVED_AND_EXECUTED",
                "human_review": {
                    "required": True,
                    "approved": True,
                },
                "execution": {
                    "executed": True,
                    "status": (
                        result.execution.status
                    ),
                    "execution_id": (
                        result.execution.execution_id
                    ),
                },
                "result": (
                    _guardian_response_to_dict(
                        result
                    )
                ),
            },
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "AEGIS approval/execution failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc


# ======================================================================
# LEGACY COMPLETE PROCESS EVENT
# ======================================================================


@app.post(
    "/api/v1/events/process",
)
def process_event(
    request: ProcessEventRequest,
) -> dict[str, Any]:
    """
    Legacy complete control-loop endpoint.

    This endpoint remains available for compatibility.

    New frontend integrations should use:

        POST /api/v1/events/assess

    followed by:

        POST /api/v1/assessments/{assessment_id}/approve
    """

    try:
        event_request = EventRequest(
            event_id=request.event.event_id,
            event_type=request.event.event_type,
            station_id=request.event.station_id,
            city=request.event.city,
            region=request.event.region,
            severity=request.event.severity,
            description=request.event.description,
            capacity_change_percent=(
                request.event.capacity_change_percent
            ),
            metadata=request.event.metadata,
        )

        station_request = StationRequest(
            station_id=request.station.station_id,
            city=request.station.city,
            region=request.station.region,
            capacity=request.station.capacity,
            current_load=request.station.current_load,
            active_routes=request.station.active_routes,
        )

        result = guardian_api.process_event(
            event_request,
            station_request,
        )

        return {
            "success": True,
            "data": _guardian_response_to_dict(
                result
            ),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "AEGIS control-plane processing failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc


# ======================================================================
# RESPONSE SERIALIZATION
# ======================================================================


def _guardian_response_to_dict(
    response: Any,
) -> dict[str, Any]:
    """
    Convert GuardianResponse dataclasses into a JSON-safe
    dictionary.

    This function intentionally lives at the HTTP boundary.
    """

    return {
        # --------------------------------------------------------------
        # EVENT
        # --------------------------------------------------------------

        "event": response.event,

        # --------------------------------------------------------------
        # STATION
        # --------------------------------------------------------------

        "station": response.station,

        # --------------------------------------------------------------
        # RISK
        # --------------------------------------------------------------

        "risk": {
            "station_id": response.risk.station_id,
            "risk_score": response.risk.risk_score,
            "risk_level": response.risk.risk_level,
            "utilization": response.risk.utilization,
            "capacity_overload": (
                response.risk.capacity_overload
            ),
            "drivers": response.risk.drivers,
        },

        # --------------------------------------------------------------
        # INTERVENTION
        # --------------------------------------------------------------

        "intervention": {
            "selected_strategy": (
                response.intervention.selected_strategy
            ),
            "decision_score": (
                response.intervention.decision_score
            ),
            "baseline_risk": (
                response.intervention.baseline_risk
            ),
            "projected_risk": (
                response.intervention.projected_risk
            ),
            "baseline_utilization": (
                response.intervention.baseline_utilization
            ),
            "projected_utilization": (
                response.intervention.projected_utilization
            ),
            "risk_reduction": (
                response.intervention.risk_reduction
            ),
            "utilization_reduction": (
                response.intervention.utilization_reduction
            ),
            "routes_moved": (
                response.intervention.routes_moved
            ),
            "capacity_recovered": (
                response.intervention.capacity_recovered
            ),
            "decision_status": (
                response.intervention.decision_status
            ),
            "safety_checks_passed": (
                response.intervention.safety_checks_passed
            ),
            "rationale": (
                response.intervention.rationale
            ),
            "scenarios": [
                {
                    "strategy": scenario.strategy,
                    "projected_capacity": (
                        scenario.projected_capacity
                    ),
                    "projected_load": (
                        scenario.projected_load
                    ),
                    "projected_routes": (
                        scenario.projected_routes
                    ),
                    "projected_utilization": (
                        scenario.projected_utilization
                    ),
                    "projected_risk": (
                        scenario.projected_risk
                    ),
                    "risk_reduction": (
                        scenario.risk_reduction
                    ),
                    "utilization_improvement": (
                        scenario.utilization_improvement
                    ),
                    "decision_score": (
                        scenario.decision_score
                    ),
                    "safety_passed": (
                        scenario.safety_passed
                    ),
                }
                for scenario
                in response.intervention.scenarios
            ],
        },

        # --------------------------------------------------------------
        # EXECUTION
        # --------------------------------------------------------------

        "execution": {
            "execution_id": (
                response.execution.execution_id
            ),
            "station_id": (
                response.execution.station_id
            ),
            "strategy": (
                response.execution.strategy
            ),
            "status": (
                response.execution.status
            ),
            "previous_capacity": (
                response.execution.previous_capacity
            ),
            "new_capacity": (
                response.execution.new_capacity
            ),
            "previous_load": (
                response.execution.previous_load
            ),
            "new_load": (
                response.execution.new_load
            ),
            "previous_routes": (
                response.execution.previous_routes
            ),
            "new_routes": (
                response.execution.new_routes
            ),
            "previous_utilization": (
                response.execution.previous_utilization
            ),
            "new_utilization": (
                response.execution.new_utilization
            ),
        },

        # --------------------------------------------------------------
        # OUTCOME
        # --------------------------------------------------------------

        "outcome": {
            "execution_id": (
                response.outcome.execution_id
            ),
            "station_id": (
                response.outcome.station_id
            ),
            "strategy": (
                response.outcome.strategy
            ),
            "baseline_risk": (
                response.outcome.baseline_risk
            ),
            "post_intervention_risk": (
                response.outcome.post_intervention_risk
            ),
            "risk_reduction": (
                response.outcome.risk_reduction
            ),
            "baseline_utilization": (
                response.outcome.baseline_utilization
            ),
            "post_intervention_utilization": (
                response.outcome.post_intervention_utilization
            ),
            "utilization_improvement": (
                response.outcome.utilization_improvement
            ),
            "baseline_capacity": (
                response.outcome.baseline_capacity
            ),
            "post_intervention_capacity": (
                response.outcome.post_intervention_capacity
            ),
            "baseline_load": (
                response.outcome.baseline_load
            ),
            "post_intervention_load": (
                response.outcome.post_intervention_load
            ),
            "baseline_routes": (
                response.outcome.baseline_routes
            ),
            "post_intervention_routes": (
                response.outcome.post_intervention_routes
            ),
            "routes_moved": (
                response.outcome.routes_moved
            ),
            "effectiveness_score": (
                response.outcome.effectiveness_score
            ),
            "outcome_status": (
                response.outcome.outcome_status
            ),
            "measurement_notes": (
                response.outcome.measurement_notes
            ),
        },

        # --------------------------------------------------------------
        # AI INTELLIGENCE
        # --------------------------------------------------------------

        "intelligence": {
            "summary": (
                response.intelligence.summary
            ),
            "recommended_action": (
                response.intelligence.recommended_action
            ),
            "reasoning": (
                response.intelligence.reasoning
            ),
            "expected_effect": (
                response.intelligence.expected_effect
            ),
            "constraints": (
                response.intelligence.constraints
            ),
            "requires_human_review": (
                response.intelligence.requires_human_review
            ),
            "generated_by": (
                response.intelligence.generated_by
            ),
            "grounded_in_deterministic_data": (
                response.intelligence
                .grounded_in_deterministic_data
            ),
        },

        # --------------------------------------------------------------
        # CONTROL LOOP
        # --------------------------------------------------------------

        "control_loop": response.control_loop,
    }


# ======================================================================
# LOCAL DEVELOPMENT ENTRY POINT
# ======================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )