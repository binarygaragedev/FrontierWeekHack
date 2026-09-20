# Challenge 1: Build Agents

## Objectives

By the end of this challenge, the following will be completed:

- ✅ A ride safety risk assessment agent
- ✅ A vehicle telemetry and dangerous driving agent
- ✅ A driver operations and in-trip monitoring agent
- ✅ An incident response and support agent
- ✅ A clear contract for how pre-trip and in-trip risk decisions are separated
- ✅ All four agents evaluated against real trip scenarios for ride-hailing safety

## Scenario

This solution is designed for a ride-hailing platform similar to Uber, where the business must simultaneously protect:

- passengers,
- drivers,
- operations staff,
- and the trust of the overall platform.

The main risk factors include:

- long working hours for drivers,
- low driver ratings,
- repeated complaints or incidents,
- high-risk pickup or route conditions,
- route deviation and idle time anomalies,
- delayed driver response during a trip.

The system must identify unsafe situations early and direct them to the correct response workflow.

## Timing and Ownership Model

To keep the workflow operationally credible, risk decisions are split by trip phase:

- Pre-trip phase: the Ride Safety Risk Agent owns the approval state (`approve`, `review_required`, `reject`).
- In-trip phase: live agents process telemetry and route behavior only after trip start.
- Final live risk state owner: the In-Trip Monitoring Agent owns the final consolidated in-trip risk state.

Telemetry findings alone do not directly set the final in-trip state. Telemetry emits event-level risk signals, and In-Trip Monitoring resolves them with route context and policy rules.

## Live-Agent Contracts (for downstream steps)

This step implements all four core agents, including explicit contracts for live monitoring:

Telemetry Agent output payload:

```json
{
	"trip_id": "RIDE-103",
	"event_time_utc": "2026-09-20T18:42:11Z",
	"lifecycle_phase": "in_trip",
	"source": "telemetry_agent",
	"event_type": "harsh_brake",
	"event_severity": "high",
	"risk_points": 3,
	"evidence": {
		"speed_kph": 78,
		"decel_mps2": -5.1,
		"rpm": 4200
	},
	"recommended_action": "raise_live_alert"
}
```

In-Trip Monitoring Agent output payload:

```json
{
	"trip_id": "RIDE-103",
	"event_time_utc": "2026-09-20T18:42:14Z",
	"lifecycle_phase": "in_trip",
	"source": "in_trip_monitoring_agent",
	"final_live_risk_state": "critical",
	"state_owner": "in_trip_monitoring_agent",
	"telemetry_summary": {
		"high_severity_events": 2,
		"latest_event_type": "harsh_brake"
	},
	"route_context": {
		"deviation_pct": 18,
		"idle_seconds": 135
	},
	"decision_reason": "Repeated high-severity telemetry events with route deviation in high-risk zone",
	"escalation_action": "operations_intervention_required"
}
```

Conflict-resolution rule:

- If telemetry and route-context conclusions disagree, In-Trip Monitoring applies policy priority and emits the authoritative `final_live_risk_state`.
- If confidence is low or signals are contradictory, the state is set to `review_required` and escalated to operations.

## Agents and tools

This challenge mirrors the structure used in the factory scenario, but applies it to ride-hailing safety and incident handling.

### Agent 1: Ride Safety Risk Agent

This agent examines each ride and uses the `evaluate_trip_risk` tool to determine whether the trip is:

- normal,
- warning,
- or critical.

It considers:

- driver shift length,
- recent incidents,
- driver rating,
- route risk,
- rider complaint history,
- response time,
- route deviation,
- idle time,
- and other trip quality indicators.

### Agent 2: Vehicle Telemetry and Dangerous Driving Agent

This agent focuses on vehicle telemetry and dangerous-driving event detection during the trip. It uses `evaluate_telemetry_events()` and returns event-level payloads such as:

- speeding,
- route-deviation anomalies,
- extended idle anomalies,
- slow driver response events.

It does not own the final live risk state.

### Agent 3: Driver Operations and In-Trip Monitoring Agent

This agent owns the final in-trip decision. It uses `consolidate_in_trip_risk()` to combine telemetry and route context and outputs:

- `state_owner`,
- `final_live_risk_state`,
- conflict flag,
- and escalation action.

### Agent 4: Ride Incident Response Agent

This agent focuses on customer support and operational follow-up. It uses `fetch_trip_context()` to investigate a trip in more detail and recommends:

- whether the case is safe to continue,
- whether a human operations review is needed,
- whether compensation or support resolution is appropriate,
- and what follow-up action the platform should take.

## Files in this folder

- `agents.py` — creates and tests the agents
- `trip_data.json` — sample trip scenarios with normalized risk conditions
- `README.md` — challenge instructions

## Run the script

From the `ridehailing-solution` root, run:

```bash
cd challenge-1-build
python agents.py
```

The script will:

1. create the Safety Risk Agent,
2. evaluate all sample trips,
3. create the Vehicle Telemetry Agent,
4. generate event-level telemetry payloads for each trip,
5. create the In-Trip Monitoring Agent,
6. consolidate authoritative live risk states,
7. create the Incident Response Agent,
8. investigate higher-risk trips,
9. print all results to the terminal.

## Why this matters

This challenge demonstrates how a single general-purpose AI agent would be too broad for a ride-hailing environment. In production, the platform needs:

- a safety agent focused on risk scoring,
- a telemetry agent focused on live event detection,
- an in-trip monitoring agent focused on authoritative live risk-state decisions,
- an operations/support agent focused on investigation and resolution,
- and clear traceability for both.

This is the foundation of a production-ready multi-agent safety workflow.

## Success criteria

- [ ] The safety risk agent is created successfully
- [ ] It identifies normal, warning, and critical trip scenarios
- [ ] The telemetry agent is created successfully
- [ ] It emits event-level telemetry payloads for in-trip analysis
- [ ] The in-trip monitoring agent is created successfully
- [ ] It owns final live risk state and escalation outputs
- [ ] The incident response agent is created successfully
- [ ] It provides operationally useful suggestions for risky rides
- [ ] The logic is grounded in trip data and not just general model assumptions
