# AEGIS — Proactive Last-Mile Risk & Workload Intelligence

> **AI Operations Control Plane for Proactive Last-Mile Network Resilience**

AEGIS is a proactive operational control plane designed to help last-mile delivery networks respond to disruptions before their effects propagate across the network.

Instead of stopping at detection or visualization, AEGIS closes the operational loop:

**SENSE → UNDERSTAND → SIMULATE → DECIDE → HUMAN REVIEW → ACT → MEASURE → EXPLAIN**

The system detects an operational disruption, assesses its impact, simulates multiple intervention strategies, recommends an action, waits for human approval, executes the approved intervention, and measures the resulting outcome.


## 🚨 The Problem

In a last-mile delivery network, detecting a disruption is only the beginning.

A sudden capacity reduction, workload spike, route disruption, or station overload can propagate across:

- Station utilization
- Delivery workload
- Route availability
- Associate capacity
- Downstream operational risk

The difficult operational question is:

> **What should the network do next, before the disruption propagates?**

Traditional monitoring systems can show that something is wrong.

AEGIS is designed to answer:

> **What can we do about it, what happens if we do it, and did it actually work?**



## 🧠 How AEGIS Works

                    ┌─────────────────────┐
                    │  OPERATIONAL EVENT  │
                    └──────────┬──────────┘
                               ↓
                         ┌───────────┐
                         │   SENSE   │
                         └─────┬─────┘
                               ↓
                      ┌────────────────┐
                      │   UNDERSTAND   │
                      └───────┬────────┘
                              ↓
                       ┌─────────────┐
                       │  SIMULATE   │
                       └──────┬──────┘
                              ↓
                        ┌──────────┐
                        │  DECIDE  │
                        └────┬─────┘
                             ↓
                  ┌─────────────────────┐
                  │  HUMAN REVIEW GATE  │
                  └──────────┬──────────┘
                             ↓
                         ┌───────┐
                         │  ACT  │
                         └───┬───┘
                             ↓
                       ┌──────────┐
                       │ MEASURE  │
                       └────┬─────┘
                            ↓
                       ┌──────────┐
                       │ EXPLAIN  │
                       └──────────┘
⚙️ **Core Capabilities**
1. Event Detection & Assessment
AEGIS ingests an operational disruption and evaluates its immediate impact.
The current prototype evaluates:
- Station capacity
- Current workload
- Active routes
- Utilization
- Operational risk
2. Risk Intelligence
The risk engine converts operational conditions into a normalized risk assessment.
Example:
Station: CHN-017
Location: Chennai, Tamil Nadu

Capacity:        8,000
Current Load:    8,200
Utilization:     102.5%
Risk Score:      72.77 / 100
Risk Level:      HIGH
3. Intervention Simulation
Rather than immediately executing an action, AEGIS evaluates multiple possible interventions.
Example scenarios:
Intervention	Capacity	Load	Routes	Risk	Utilization
HYBRID_RESPONSE	8,800	7,380	346	39.26	83.86%
ROUTE_REBALANCE	—	—	—	44.44	87.12%
CAPACITY_SHIFT	—	—	—	50.43	89.13%


The prototype evaluates intervention scenarios using operational constraints and decision scoring.
4. Decision Engine
AEGIS compares simulated intervention strategies and generates a recommended action.
The recommendation is not automatically executed.
The system creates an explicit human approval gate.
5. Human-in-the-Loop Control
Operational actions require human approval.
**AI Recommendation
       ↓
Human Review
       ↓
Approve / Reject
       ↓
Approved Action
       ↓
Execution**
This design provides an explicit control boundary between AI-generated recommendations and operational execution.
6. Intervention Execution
Once approved, AEGIS executes the selected intervention against the operational state.
Example:
Capacity
8,000 → 8,800

Load
8,200 → 7,380

Active Routes
384 → 346
7. Outcome Measurement
AEGIS does not stop after execution.
It measures the resulting operational state and compares it with the predicted outcome.
Example:
Risk
72.77 → 43.86

Risk Reduction
39.73%

Utilization
102.50% → 83.86%

Outcome
IMPROVED
📊 Prediction → Reality
One of the key concepts demonstrated by AEGIS is the distinction between:
Predicted outcome vs Measured outcome
Example:
Metric	Predicted	Actual	Deviation
Risk	39.26	43.86	+4.60
Utilization	83.86%	83.86%	0.00%


The prototype uses this comparison to make intervention outcomes observable rather than assuming that a simulated intervention automatically produced the expected result.
Prediction deviation is an operational comparison metric in this prototype; it is not presented as validated ML accuracy.

☁️ **AWS Architecture**
AEGIS is designed as an AWS-integrated serverless control plane.
              ┌──────────────────┐
              │   AEGIS FRONTEND │
              └────────┬─────────┘
                       │ HTTPS
                       ▼
              ┌──────────────────┐
              │  API GATEWAY     │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │  AWS LAMBDA      │
              │  CONTROL PLANE   │
              └────────┬─────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     ┌─────────┐ ┌────────────┐ ┌──────────────┐
     │DynamoDB │ │EventBridge │ │Step Functions│
     │  STATE  │ │   EVENTS   │ │   WORKFLOW   │
     └────┬────┘ └─────┬──────┘ └──────┬───────┘
          │             │               │
          └─────────────┼───────────────┘
                        ▼
                 ┌────────────┐
                 │     S3     │
                 │ ARTIFACTS  │
                 └─────┬──────┘
                       ▼
                 ┌────────────┐
                 │  BEDROCK   │
                 │     AI     │
                 └────────────┘
               
**AWS Components**
AWS Service	Role in AEGIS
Amazon API Gateway	HTTPS API entry point
AWS Lambda	Serverless control-plane backend
Amazon DynamoDB	Operational assessment/state persistence
Amazon EventBridge	Event-driven integration
AWS Step Functions	Workflow orchestration
Amazon S3	Data/artifact storage
Amazon Bedrock	AI intelligence / explanation layer
AWS Amplify	Frontend hosting


The architecture intentionally uses AWS services where they contribute to the product workflow rather than adding infrastructure solely for demonstration.
🖥️ Frontend
The AEGIS command center provides an operational view of:
- Network health
- Active disruptions
- Risk assessment
- Intervention scenarios
- Human approval
- Execution status
- Prediction vs actual outcome
- AWS/control-plane status
The interface is designed around an operations-control workflow rather than a conventional analytics dashboard.
🔐 **Human-Gated** **Execution**
AEGIS separates:
AI decision support
from
Operational execution
The system can:
1. Detect a disruption
2. Assess risk
3. Generate intervention scenarios
4. Recommend a strategy
5. Present the recommendation to a human
6. Wait for approval
7. Execute the approved intervention
8. Measure the outcome
This prevents the prototype from treating AI-generated recommendations as automatically authorized operational actions.
🧪 **Demonstration** **Scenario**
The primary demonstration scenario uses a simulated station capacity shock.
Station: CHN-017
Location: Chennai, Tamil Nadu

Initial Capacity: 10,000
Disrupted Capacity: 8,000
Current Load: 8,200
Utilization: 102.5%
Initial Risk: 72.77 / 100
AEGIS evaluates multiple intervention strategies.
The selected prototype scenario:
HYBRID_RESPONSE
After execution:
Capacity:      8,000 → 8,800
Load:          8,200 → 7,380
Routes:        384 → 346
Utilization:   102.5% → 83.86%
Measured Risk: 72.77 → 43.86
Result:
OUTCOME: IMPROVED

📦**Synthetic** **Data** **&** **Prototype** **Scope**
The network-scale values used in the demonstration are synthetic/simulated.
The prototype environment represents a simulated network containing:
400 cities
1,000 stations
50,000 routes
75,000 associates
2,500,000 orders
These values are used to demonstrate the architecture and operational decision workflow.
They do not represent Amazon's internal operational data.
AEGIS is an independent prototype and does not claim access to Amazon proprietary systems, datasets, or internal operational policies.
🏗️ **Project** **Structure**
AEGIS-AI-Operations-Control-Plane/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── assets/
│
├── services/
│   ├── api/
│   ├── ai_intelligence/
│   ├── control_plane/
│   ├── event_ingestion/
│   ├── execution_engine/
│   ├── intervention_engine/
│   ├── outcome_engine/
│   ├── risk_engine/
│   ├── simulation_engine/
│   └── state_store/
│
├── infrastructure/
├── simulator/
├── data/
├── docs/
├── tests/
├── README.md
└── .gitignore

🔄 **Operational** **Control** **Loop**
The central AEGIS loop can be summarized as:
EVENT
  ↓
RISK ASSESSMENT
  ↓
INTERVENTION SIMULATION
  ↓
DECISION
  ↓
HUMAN APPROVAL
  ↓
EXECUTION
  ↓
MEASURED OUTCOME
  ↓
PREDICTION vs REALITY
  ↓
EXPLANATION
This transforms the system from a passive monitoring interface into a prototype operational decision loop.

🛠️ **Technology** **Stack**
Backend
- Python
- FastAPI
- Pydantic
- Mangum
- Serverless AWS architecture
Frontend
- HTML
- CSS
- JavaScript
AWS
- Amazon API Gateway
- AWS Lambda
- Amazon DynamoDB
- Amazon EventBridge
- AWS Step Functions
- Amazon S3
- Amazon Bedrock
- AWS Amplify
**Local** **Development**
The system can also be executed locally for development and demonstration without requiring the deployed AWS environment.
🚀 Local Development
Backend
Start the FastAPI application using the project's Python environment.
The API exposes:
GET  /api/v1/health
POST /api/v1/events/assess
GET  /api/v1/assessments/{assessment_id}
POST /api/v1/assessments/{assessment_id}/approve
Interactive API documentation is available at:
/docs
when running the FastAPI application locally.
🌐 Deployment
The prototype includes an AWS serverless deployment architecture consisting of:
Frontend
   ↓
AWS Amplify
   ↓
API Gateway
   ↓
Lambda
   ↓
AWS operational services
The frontend can be hosted using AWS Amplify while the backend control plane runs through API Gateway and Lambda.
🎯 **Why** **AEGIS**?
AEGIS focuses on a specific operational problem:
When a disruption occurs, how can a delivery network move from detection to an explainable, constrained, human-approved intervention — and then verify whether that intervention actually worked?

The prototype demonstrates that workflow end-to-end.
It is intentionally focused on one operational loop rather than attempting to solve every aspect of last-mile logistics.
⚠️ **Prototype** **Disclaimer**
AEGIS is a prototype.
Operational models, risk scores, intervention effects, effectiveness metrics, network values, and outcomes shown in the demonstration are simulated or prototype-generated unless explicitly stated otherwise.
The system should not be used to make real-world logistics or safety-critical decisions without appropriate validation, governance, authorization, and integration with verified operational systems.
🏆 **Hackathon**
Amazon First Commit / Bharat Builds
AEGIS demonstrates an AWS-integrated AI operations control plane focused on proactive disruption response, human-in-the-loop decision making, intervention simulation, and closed-loop outcome measurement.
👥 **Team**
Built for the Amazon First Commit / Bharat Builds hackathon.
📜 License
This repository is currently provided as a hackathon prototype.
