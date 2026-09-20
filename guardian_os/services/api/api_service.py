"""



GUARDIAN OS — API Service







Application-facing service layer.







This service converts API requests into Guardian OS domain objects,



runs the control plane, and converts domain results into



frontend/API-safe responses.







Human-gated flow:







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







The local pending-assessment store is persisted to a local pickle-backed



state file for the Build It prototype. In the deployed Ship It



architecture, this state can move to DynamoDB.



"""







from __future__ import annotations







import os
from typing import Any



from uuid import uuid4











from services.api.api_models import (



    EventRequest,



    StationRequest,



    RiskResponse,



    ScenarioResponse,



    InterventionResponse,



    ExecutionResponse,



    OutcomeResponse,



    IntelligenceResponse,



    GuardianResponse,



)











from services.control_plane.control_plane import (



    GuardianControlPlane,



    create_control_plane,



)











from services.event_ingestion.event_models import (



    EventSeverity,



    EventType,



    EventImpact,



    OperationalEvent,



    StationReference,



)











from services.risk_engine.station_models import (



    StationState,



)





from services.state_store import LocalStateStore
from services.state_store.dynamodb_state_store import DynamoDBStateStore











class GuardianAPIService:



    """



    Application service for Guardian OS.







    Responsibilities:







    1\. Validate API-level requests.



    2\. Convert requests into domain objects.



    3\. Invoke the Guardian control plane.



    4\. Hold pending assessments during human review.



    5\. Execute only after explicit approval.



    6\. Convert domain results into API responses.



    """







    def __init__(



        self,



        control_plane: GuardianControlPlane | None = None,



    ) -> None:







        self.control_plane = (



            control_plane



            or create_control_plane()



        )







        # --------------------------------------------------------------



        # LOCAL HUMAN-REVIEW STATE



        # --------------------------------------------------------------



        #



        # The Build It prototype persists human-review state to disk so



        # a newly created API service instance can recover an assessment.



        #



        # Ship It migration path:



        #



        #     LocalStateStore



        #           ↓



        #     DynamoDBStateStore



        #



        state_table_name = os.environ.get("AEGIS_STATE_TABLE")

        if state_table_name:
            self._state_store = DynamoDBStateStore(
                table_name=state_table_name
            )
        else:
            self._state_store = LocalStateStore(
                "data/aegis_state.pkl"
            )
    # ==================================================================



    # LEGACY COMPLETE CONTROL-PLANE OPERATION



    # ==================================================================







    def process_event(



        self,



        event_request: EventRequest,



        station_request: StationRequest,



    ) -> GuardianResponse:



        """



        Legacy convenience operation.







        Runs the complete control loop in one call.







        This remains available for compatibility, but the new frontend



        should use assess_event() followed by approve_and_execute().



        """







        self._validate_event_request(



            event_request



        )







        self._validate_station_request(



            station_request



        )







        event = self._build_event(



            event_request



        )







        station = self._build_station(



            station_request



        )







        result = self.control_plane.process(



            event,



            station,



        )







        return self._build_response(



            result



        )







    # ==================================================================



    # HUMAN-GATED ASSESSMENT



    # ==================================================================







    def assess_event(



        self,



        event_request: EventRequest,



        station_request: StationRequest,



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



            Decision



              ↓



            HUMAN REVIEW







        No intervention is executed here.



        """







        self._validate_event_request(



            event_request



        )







        self._validate_station_request(



            station_request



        )







        event = self._build_event(



            event_request



        )







        station = self._build_station(



            station_request



        )







        (



            processed_event,



            assessed_station,



            risk_assessment,



            intervention_decision,



        ) = self.control_plane.assess(



            event,



            station,



        )







        assessment_id = (



            f"ASSESS-{uuid4().hex[:8].upper()}"



        )







        self._state_store.put(



            assessment_id,



            {



                "event": processed_event,



                "station": assessed_station,



                "risk": risk_assessment,



                "decision": intervention_decision,



                "result": None,



            },



        )







        return {



            "assessment_id": assessment_id,



            "status": "AWAITING_HUMAN_APPROVAL",







            "execution": {



                "executed": False,



                "status": "NOT_EXECUTED",



            },







            "event": {



                "event_id": processed_event.event_id,



                "event_type": (



                    processed_event.event_type.value



                ),



                "severity": (



                    processed_event.impact.severity.value



                ),



                "station_id": (



                    processed_event.station.station_id



                ),



                "city": (



                    processed_event.station.city



                ),



                "region": (



                    processed_event.station.region



                ),



                "description": (



                    processed_event.impact.description



                ),



            },







            "station": {



                "station_id": assessed_station.station_id,



                "city": assessed_station.city,



                "region": assessed_station.region,



                "capacity": assessed_station.capacity,



                "current_load": assessed_station.current_load,



                "active_routes": assessed_station.active_routes,



            },







            "risk": {



                "risk_score": risk_assessment.risk_score,



                "risk_level": (



                    self._status_to_string(



                        risk_assessment.risk_level



                    )



                ),



                "utilization": (



                    risk_assessment.utilization



                ),



                "capacity_overload": (



                    risk_assessment.capacity_overload



                ),



                "drivers": list(



                    risk_assessment.drivers



                ),



            },







            "intervention": {



                "selected_strategy": (



                    intervention_decision.selected_strategy



                ),



                "decision_score": (



                    intervention_decision.decision_score



                ),



                "baseline_risk": (



                    intervention_decision.baseline_risk



                ),



                "projected_risk": (



                    intervention_decision.projected_risk



                ),



                "baseline_utilization": (



                    intervention_decision.baseline_utilization



                ),



                "projected_utilization": (



                    intervention_decision.projected_utilization



                ),



                "risk_reduction": (



                    intervention_decision.risk_reduction



                ),



                "utilization_reduction": (



                    intervention_decision.utilization_reduction



                ),



                "routes_moved": (



                    intervention_decision.routes_moved



                ),



                "capacity_recovered": (



                    intervention_decision.capacity_recovered



                ),



                "decision_status": (



                    intervention_decision.decision_status



                ),



                "safety_checks_passed": (



                    intervention_decision.safety_checks_passed



                ),



                "rationale": (



                    intervention_decision.rationale



                ),



            },







            "human_review": {



                "required": True,



                "approved": False,



                "message": (



                    "Intervention requires explicit "



                    "human approval before execution."



                ),



            },







            "control_loop": [



                "SENSE",



                "UNDERSTAND",



                "SIMULATE",



                "DECIDE",



                "HUMAN REVIEW",



            ],



        }







    # ==================================================================



    # HUMAN APPROVAL + EXECUTION



    # ==================================================================







    def approve_and_execute(



        self,



        assessment_id: str,



    ) -> GuardianResponse:



        """



        Approve a previously assessed intervention and execute it.







        The assessment must already exist in the pending-review store.







        Execution cannot happen through this method unless an



        assessment has first been created.



        """







        if not assessment_id:



            raise ValueError(



                "assessment_id is required."



            )







        pending = self._state_store.get(



            assessment_id



        )







        if pending is None:



            raise ValueError(



                f"Assessment not found: {assessment_id}"



            )







        # --------------------------------------------------------------



        # IDEMPOTENT APPROVAL



        # --------------------------------------------------------------



        #



        # If the same assessment was already approved, return the



        # existing result instead of executing a second time.



        #



        if pending["result"] is not None:



            return self._build_response(



                pending["result"]



            )







        event = pending["event"]



        station = pending["station"]



        risk_assessment = pending["risk"]



        intervention_decision = pending["decision"]







        # --------------------------------------------------------------



        # EXECUTE ONLY AFTER EXPLICIT APPROVAL



        # --------------------------------------------------------------







        result = (



            self.control_plane.approve_and_execute(



                event,



                station,



                risk_assessment,



                intervention_decision,



            )



        )







        # Store completed result for idempotent repeat requests.



        pending["result"] = result



        self._state_store.put(



            assessment_id,



            pending,



        )







        return self._build_response(



            result



        )







    # ==================================================================



    # PENDING ASSESSMENT LOOKUP



    # ==================================================================







    def get_assessment(



        self,



        assessment_id: str,



    ) -> dict[str, Any]:



        """



        Retrieve a pending assessment for the frontend.







        This does not execute anything.



        """







        if not assessment_id:



            raise ValueError(



                "assessment_id is required."



            )







        pending = self._state_store.get(



            assessment_id



        )







        if pending is None:



            raise ValueError(



                f"Assessment not found: {assessment_id}"



            )







        if pending["result"] is not None:



            return {



                "assessment_id": assessment_id,



                "status": "EXECUTED",



                "execution": {



                    "executed": True,



                },



            }







        return {



            "assessment_id": assessment_id,



            "status": "AWAITING_HUMAN_APPROVAL",



            "execution": {



                "executed": False,



                "status": "NOT_EXECUTED",



            },



            "intervention": {



                "selected_strategy": (



                    pending[



                        "decision"



                    ].selected_strategy



                ),



                "projected_risk": (



                    pending[



                        "decision"



                    ].projected_risk



                ),



                "projected_utilization": (



                    pending[



                        "decision"



                    ].projected_utilization



                ),



                "safety_checks_passed": (



                    pending[



                        "decision"



                    ].safety_checks_passed



                ),



            },



            "human_review": {



                "required": True,



                "approved": False,



            },



        }







    # ==================================================================



    # VALIDATION



    # ==================================================================







    @staticmethod



    def _validate_event_request(



        request: EventRequest,



    ) -> None:







        if not request.event_id:



            raise ValueError(



                "event_id is required."



            )







        if not request.event_type:



            raise ValueError(



                "event_type is required."



            )







        if not request.station_id:



            raise ValueError(



                "station_id is required."



            )







        if not request.severity:



            raise ValueError(



                "severity is required."



            )







    @staticmethod



    def _validate_station_request(



        request: StationRequest,



    ) -> None:







        if not request.station_id:



            raise ValueError(



                "station_id is required."



            )







        if request.capacity <= 0:



            raise ValueError(



                "capacity must be greater than zero."



            )







        if request.current_load < 0:



            raise ValueError(



                "current_load cannot be negative."



            )







        if request.active_routes < 0:



            raise ValueError(



                "active_routes cannot be negative."



            )







    # ==================================================================



    # DOMAIN OBJECT BUILDERS



    # ==================================================================







    @staticmethod



    def _build_event(



        request: EventRequest,



    ) -> OperationalEvent:







        try:



            event_type = EventType(



                request.event_type



            )



        except ValueError as exc:



            raise ValueError(



                f"Unsupported event_type: "



                f"{request.event_type}"



            ) from exc







        try:



            severity = EventSeverity(



                request.severity



            )



        except ValueError as exc:



            raise ValueError(



                f"Unsupported severity: "



                f"{request.severity}"



            ) from exc







        return OperationalEvent(



            event_id=request.event_id,



            event_type=event_type,



            timestamp="2026-09-18T10:30:00Z",



            source="GUARDIAN_API",



            station=StationReference(



                station_id=request.station_id,



                city=request.city,



                region=request.region,



            ),



            impact=EventImpact(



                severity=severity,



                capacity_change_percent=(



                    request.capacity_change_percent



                ),



                description=request.description,



            ),



            metadata={



                **request.metadata,



                "synthetic": True,



                "api_request": True,



            },



        )







    @staticmethod



    def _build_station(



        request: StationRequest,



    ) -> StationState:







        return StationState(



            station_id=request.station_id,



            city=request.city,



            region=request.region,



            capacity=request.capacity,



            current_load=request.current_load,



            active_routes=request.active_routes,



        )







    # ==================================================================



    # RESPONSE BUILDER



    # ==================================================================







    @staticmethod



    def _build_response(



        result: Any,



    ) -> GuardianResponse:



        """



        Convert ControlPlaneResult into a complete API response.



        """







        # ==============================================================



        # EVENT



        # ==============================================================







        event_response = {



            "event_id": result.event.event_id,



            "event_type": result.event.event_type.value,



            "severity": result.event.impact.severity.value,



            "station_id": result.event.station.station_id,



            "city": result.event.station.city,



            "region": result.event.station.region,



            "description": result.event.impact.description,



            "source": result.event.source,



        }







        # ==============================================================



        # STATION



        # ==============================================================







        station = result.initial_state







        station_response = {



            "station_id": station.station_id,



            "city": station.city,



            "region": station.region,



            "capacity": station.capacity,



            "current_load": station.current_load,



            "active_routes": station.active_routes,



        }







        # ==============================================================



        # RISK



        # ==============================================================







        risk = result.risk_assessment







        risk_response = RiskResponse(



            station_id=risk.station_id,



            risk_score=risk.risk_score,



            risk_level=risk.risk_level,



            utilization=risk.utilization,



            capacity_overload=risk.capacity_overload,



            drivers=list(risk.drivers),



        )







        # ==============================================================



        # INTERVENTION



        # ==============================================================







        decision = result.intervention_decision







        selected_scenario = getattr(



            decision,



            "selected_scenario",



            None,



        )







        scenario_responses: list[



            ScenarioResponse



        ] = []







        if selected_scenario is not None:







            safety_passed = (



                selected_scenario.projected_utilization



                <= 110.0



                and selected_scenario.projected_risk



                <= 90.0



            )







            scenario_responses.append(



                ScenarioResponse(



                    strategy=(



                        selected_scenario.strategy



                    ),



                    projected_capacity=(



                        selected_scenario.projected_capacity



                    ),



                    projected_load=(



                        selected_scenario.projected_load



                    ),



                    projected_routes=(



                        selected_scenario.projected_routes



                    ),



                    projected_utilization=(



                        selected_scenario.projected_utilization



                    ),



                    projected_risk=(



                        selected_scenario.projected_risk



                    ),



                    risk_reduction=(



                        decision.baseline_risk



                        - selected_scenario.projected_risk



                    ),



                    utilization_improvement=(



                        decision.baseline_utilization



                        - selected_scenario.projected_utilization



                    ),



                    decision_score=(



                        decision.decision_score



                    ),



                    safety_passed=safety_passed,



                )



            )







        intervention_response = (



            InterventionResponse(



                selected_strategy=(



                    decision.selected_strategy



                ),



                decision_score=(



                    decision.decision_score



                ),



                baseline_risk=(



                    decision.baseline_risk



                ),



                projected_risk=(



                    decision.projected_risk



                ),



                baseline_utilization=(



                    decision.baseline_utilization



                ),



                projected_utilization=(



                    decision.projected_utilization



                ),



                risk_reduction=(



                    decision.risk_reduction



                ),



                utilization_reduction=(



                    decision.utilization_reduction



                ),



                routes_moved=(



                    decision.routes_moved



                ),



                capacity_recovered=(



                    decision.capacity_recovered



                ),



                decision_status=(



                    decision.decision_status



                ),



                safety_checks_passed=(



                    decision.safety_checks_passed



                ),



                rationale=(



                    decision.rationale



                ),



                scenarios=scenario_responses,



            )



        )







        # ==============================================================



        # EXECUTION



        # ==============================================================







        execution = result.execution_result







        transition = (



            execution.state_transition



        )







        execution_response = ExecutionResponse(



            execution_id=(



                execution.execution_id



            ),



            station_id=(



                execution.station_id



            ),



            strategy=(



                execution.strategy



            ),



            status=(



                GuardianAPIService._status_to_string(



                    execution.status



                )



            ),







            previous_capacity=(



                transition.previous_capacity



            ),



            new_capacity=(



                transition.new_capacity



            ),







            previous_load=(



                transition.previous_load



            ),



            new_load=(



                transition.new_load



            ),







            previous_routes=(



                transition.previous_routes



            ),



            new_routes=(



                transition.new_routes



            ),







            previous_utilization=(



                transition.previous_utilization



            ),



            new_utilization=(



                transition.new_utilization



            ),



        )







        # ==============================================================



        # OUTCOME



        # ==============================================================







        outcome = (



            result.outcome_measurement



        )







        outcome_response = OutcomeResponse(



            execution_id=(



                outcome.execution_id



            ),



            station_id=(



                outcome.station_id



            ),



            strategy=(



                outcome.strategy



            ),







            baseline_risk=(



                outcome.baseline_risk



            ),



            post_intervention_risk=(



                outcome.post_intervention_risk



            ),



            risk_reduction=(



                outcome.risk_reduction



            ),







            baseline_utilization=(



                outcome.baseline_utilization



            ),



            post_intervention_utilization=(



                outcome.post_intervention_utilization



            ),



            utilization_improvement=(



                outcome.utilization_improvement



            ),







            baseline_capacity=(



                outcome.baseline_capacity



            ),



            post_intervention_capacity=(



                outcome.post_intervention_capacity



            ),







            baseline_load=(



                outcome.baseline_load



            ),



            post_intervention_load=(



                outcome.post_intervention_load



            ),







            baseline_routes=(



                outcome.baseline_routes



            ),



            post_intervention_routes=(



                outcome.post_intervention_routes



            ),



            routes_moved=(



                outcome.routes_moved



            ),







            effectiveness_score=(



                outcome.effectiveness_score



            ),



            outcome_status=(



                GuardianAPIService._status_to_string(



                    outcome.outcome_status



                )



            ),







            measurement_notes=(



                outcome.measurement_notes



            ),



        )







        # ==============================================================



        # AI INTELLIGENCE



        # ==============================================================







        intelligence = (



            result.intelligence_result



        )







        intelligence_response = (



            IntelligenceResponse(



                summary=(



                    intelligence.explanation.summary



                ),



                recommended_action=(



                    intelligence.recommendation.recommended_action



                ),



                reasoning=(



                    intelligence.recommendation.reasoning



                ),



                expected_effect=(



                    intelligence.recommendation.expected_effect



                ),



                constraints=(



                    intelligence.recommendation.constraints



                ),



                requires_human_review=(



                    intelligence.recommendation.requires_human_review



                ),



                generated_by=(



                    intelligence.generated_by



                ),



                grounded_in_deterministic_data=(



                    intelligence.grounded_in_deterministic_data



                ),



            )



        )







        # ==============================================================



        # FINAL RESPONSE



        # ==============================================================







        return GuardianResponse(



            event=event_response,



            station=station_response,



            risk=risk_response,



            intervention=intervention_response,



            execution=execution_response,



            outcome=outcome_response,



            intelligence=intelligence_response,



            control_loop=[



                "SENSE",



                "UNDERSTAND",



                "SIMULATE",



                "DECIDE",



                "HUMAN REVIEW",



                "ACT",



                "MEASURE",



                "EXPLAIN",



            ],



        )







    # ==================================================================



    # STATUS HELPER



    # ==================================================================







    @staticmethod



    def _status_to_string(



        status: Any,



    ) -> str:







        if hasattr(status, "value"):



            return str(status.value)







        return str(status)











# ======================================================================



# LOCAL API TEST DATA



# ======================================================================







def build_test_event_request() -> EventRequest:



    """Create the synthetic API event used for testing."""







    return EventRequest(



        event_id="EVT-API-0001",



        event_type="STATION_CAPACITY_SHOCK",



        station_id="CHN-017",



        city="Chennai",



        region="Tamil Nadu",



        severity="HIGH",



        description=(



            "Synthetic station capacity disruption"



        ),



        capacity_change_percent=-20.0,



        metadata={



            "simulation": True,



        },



    )











def build_test_station_request() -> StationRequest:



    """Create the synthetic station used for testing."""







    return StationRequest(



        station_id="CHN-017",



        city="Chennai",



        region="Tamil Nadu",



        capacity=8000,



        current_load=8200,



        active_routes=384,



    )











# ======================================================================



# LOCAL TEST HELPERS



# ======================================================================







def print_assessment(



    assessment: dict[str, Any],



) -> None:



    """Print the human-review assessment."""







    print("\n")



    print("=" * 70)



    print("GUARDIAN OS — API HUMAN REVIEW")



    print("=" * 70)







    print("\nASSESSMENT")



    print("-" * 70)







    print(



        f"Assessment ID: "



        f"{assessment['assessment_id']}"



    )







    print(



        f"Status: "



        f"{assessment['status']}"



    )







    print("\nRISK")



    print("-" * 70)







    print(



        f"Risk: "



        f"{assessment['risk']['risk_score']:.2f}/100"



    )







    print(



        f"Risk Level: "



        f"{assessment['risk']['risk_level']}"



    )







    print(



        f"Utilization: "



        f"{assessment['risk']['utilization']:.2f}%"



    )







    print("\nRECOMMENDATION")



    print("-" * 70)







    print(



        f"Strategy: "



        f"{assessment['intervention']['selected_strategy']}"



    )







    print(



        f"Decision Score: "



        f"{assessment['intervention']['decision_score']:.2f}"



    )







    print(



        f"Projected Risk: "



        f"{assessment['intervention']['baseline_risk']:.2f}"



        f" → "



        f"{assessment['intervention']['projected_risk']:.2f}"



    )







    print(



        f"Projected Utilization: "



        f"{assessment['intervention']['baseline_utilization']:.2f}%"



        f" → "



        f"{assessment['intervention']['projected_utilization']:.2f}%"



    )







    print(



        f"Safety Checks: "



        f"{assessment['intervention']['safety_checks_passed']}"



    )







    print("\nHUMAN REVIEW")



    print("-" * 70)







    print(



        "Approval Required: "



        f"{assessment['human_review']['required']}"



    )







    print(



        "Execution: "



        f"{assessment['execution']['status']}"



    )







    print(



        "\nNO INTERVENTION HAS BEEN EXECUTED."



    )







    print("=" * 70)











# ======================================================================



# LOCAL TEST



# ======================================================================







if __name__ == "__main__":







    print("=" * 70)



    print("GUARDIAN OS — API HUMAN-GATED SERVICE TEST")



    print("=" * 70)







    api = GuardianAPIService()







    event_request = (



        build_test_event_request()



    )







    station_request = (



        build_test_station_request()



    )







    # --------------------------------------------------------------



    # STEP 1 — ASSESS



    # --------------------------------------------------------------







    assessment = api.assess_event(



        event_request,



        station_request,



    )







    print_assessment(



        assessment



    )







    # --------------------------------------------------------------



    # IMPORTANT:



    #



    # The assessment above stops before execution.



    #



    # For this local test only, we simulate an explicit human



    # approval by calling approve_and_execute().



    # --------------------------------------------------------------







    print("\n")



    print("HUMAN APPROVAL RECEIVED")



    print("Proceeding to execution...")







    response = api.approve_and_execute(



        assessment["assessment_id"]



    )







    # --------------------------------------------------------------



    # FINAL RESULT



    # --------------------------------------------------------------







    print("\n")



    print("EXECUTION RESULT")



    print("-" * 70)







    print(



        f"Execution: "



        f"{response.execution.execution_id}"



    )







    print(



        f"Status: "



        f"{response.execution.status}"



    )







    print(



        f"Risk: "



        f"{response.outcome.baseline_risk:.2f}"



        f" → "



        f"{response.outcome.post_intervention_risk:.2f}"



    )







    print(



        f"Risk Reduction: "



        f"{response.outcome.risk_reduction:.2f}%"



    )







    print(



        f"Utilization: "



        f"{response.outcome.baseline_utilization:.2f}%"



        f" → "



        f"{response.outcome.post_intervention_utilization:.2f}%"



    )







    print(



        f"Effectiveness: "



        f"{response.outcome.effectiveness_score:.2f}/100"



    )







    print(



        f"Outcome: "



        f"{response.outcome.outcome_status}"



    )







    print("\n")



    print("=" * 70)



    print("API HUMAN-GATED TEST COMPLETE")



    print("=" * 70)