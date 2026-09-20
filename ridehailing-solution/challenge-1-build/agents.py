"""
Challenge 1: Build Agents — SDK Track
Ride-hailing safety agents for a multi-agent platform.

Usage:
    python agents.py

Creates and runs all four core agents:
1) Safety Risk and Trip Assessment Agent
2) Vehicle Telemetry and Dangerous Driving Agent
3) Driver Operations and In-Trip Monitoring Agent
4) Incident Response and Customer Support Agent
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput


# Resolve repo root by finding .env in parent directories.
def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _find_repo_root()
env_path = REPO_ROOT / ".env"
load_dotenv(env_path)

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
TRIP_DATA_PATH = Path(__file__).resolve().parent / "trip_data.json"


def _load_trip_batch() -> list[dict]:
    with open(TRIP_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("trips", [])


def _find_trip(trip_id: str) -> dict | None:
    for trip in _load_trip_batch():
        if trip.get("trip_id") == trip_id:
            return trip
    return None


def evaluate_trip_risk(trip_id: str) -> str:
    """
    Reads trip data and evaluates if the trip is within safe operational thresholds.
    Returns a JSON string with the risk analysis.
    """
    with open(TRIP_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    trip = None
    for item in data["trips"]:
        if item["trip_id"] == trip_id:
            trip = item
            break

    if not trip:
        return json.dumps({"error": f"Trip '{trip_id}' not found"})

    driver = trip["driver"]
    rider = trip["rider"]
    route = trip["route"]
    signals = trip["trip_signals"]
    thresholds = trip["thresholds"]

    concerns = []
    risk_score = 0

    if driver["shift_hours"] > thresholds["shift_hours"]:
        concerns.append({
            "type": "driver_fatigue",
            "detail": f"Driver has worked {driver['shift_hours']} hours, above the safe threshold of {thresholds['shift_hours']} hours."
        })
        risk_score += 2

    if driver["rating"] < thresholds["driver_rating"]:
        concerns.append({
            "type": "low_driver_rating",
            "detail": f"Driver rating {driver['rating']} is below the minimum threshold {thresholds['driver_rating']}."
        })
        risk_score += 2

    if driver["recent_incidents"] > 0:
        concerns.append({
            "type": "recent_incident_history",
            "detail": f"Driver has {driver['recent_incidents']} recent incident(s) in the last review window."
        })
        risk_score += 2

    if not driver["rest_compliance"]:
        concerns.append({
            "type": "rest_policy_violation",
            "detail": "Driver rest compliance is not satisfied." 
        })
        risk_score += 3

    if rider["prior_complaints"] > 0:
        concerns.append({
            "type": "rider_complaint_history",
            "detail": f"Rider has {rider['prior_complaints']} previous complaint(s)."
        })
        risk_score += 1

    if route["risk_level"] == "high":
        concerns.append({
            "type": "route_risk",
            "detail": "Route is classified as high risk."
        })
        risk_score += 3
    elif route["risk_level"] == "medium":
        concerns.append({
            "type": "route_risk",
            "detail": "Route is classified as medium risk."
        })
        risk_score += 1

    if signals["driver_response_time_sec"] > thresholds["response_time_sec"]:
        concerns.append({
            "type": "slow_driver_response",
            "detail": f"Driver response time is {signals['driver_response_time_sec']}s, above the limit of {thresholds['response_time_sec']}s."
        })
        risk_score += 2

    if signals["idle_time_sec"] > thresholds["idle_time_sec"]:
        concerns.append({
            "type": "extended_idle_time",
            "detail": f"Idle time is {signals['idle_time_sec']}s, above the threshold of {thresholds['idle_time_sec']}s."
        })
        risk_score += 1

    if signals["route_deviation"] > thresholds["route_deviation_pct"]:
        concerns.append({
            "type": "route_deviation",
            "detail": f"Route deviation is {signals['route_deviation']}%, above the maximum allowed {thresholds['route_deviation_pct']}%."
        })
        risk_score += 3

    if risk_score >= 7:
        final_status = "critical"
    elif risk_score >= 4:
        final_status = "warning"
    else:
        final_status = "normal"

    return json.dumps({
        "trip_id": trip["trip_id"],
        "status": trip["status"],
        "risk_score": risk_score,
        "risk_status": final_status,
        "concerns": concerns,
        "driver": driver,
        "rider": rider,
        "route": route,
        "signals": signals,
    }, indent=2)


def fetch_trip_context(trip_id: str) -> str:
    """Returns the full trip context for support or escalations."""
    with open(TRIP_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for trip in data["trips"]:
        if trip["trip_id"] == trip_id:
            return json.dumps(trip, indent=2)

    return json.dumps({"error": f"Trip '{trip_id}' not found"})


def evaluate_telemetry_events(trip_id: str) -> str:
    """Generates event-level telemetry anomalies for an in-trip phase payload."""
    trip = _find_trip(trip_id)
    if not trip:
        return json.dumps({"error": f"Trip '{trip_id}' not found"})

    signals = trip["trip_signals"]
    thresholds = trip["thresholds"]
    events = []

    if signals["speed_kmh"] >= 70:
        events.append(
            {
                "event_type": "speeding",
                "event_severity": "high",
                "risk_points": 3,
                "evidence": {"speed_kmh": signals["speed_kmh"], "speed_limit_kmh": 60},
            }
        )
    elif signals["speed_kmh"] >= 62:
        events.append(
            {
                "event_type": "speeding",
                "event_severity": "medium",
                "risk_points": 2,
                "evidence": {"speed_kmh": signals["speed_kmh"], "speed_limit_kmh": 60},
            }
        )

    if signals["route_deviation"] > thresholds["route_deviation_pct"]:
        events.append(
            {
                "event_type": "route_deviation_anomaly",
                "event_severity": "high",
                "risk_points": 3,
                "evidence": {
                    "route_deviation_pct": signals["route_deviation"],
                    "max_allowed_pct": thresholds["route_deviation_pct"],
                },
            }
        )

    if signals["idle_time_sec"] > thresholds["idle_time_sec"]:
        events.append(
            {
                "event_type": "extended_idle",
                "event_severity": "medium",
                "risk_points": 2,
                "evidence": {
                    "idle_time_sec": signals["idle_time_sec"],
                    "max_allowed_sec": thresholds["idle_time_sec"],
                },
            }
        )

    if signals["driver_response_time_sec"] > thresholds["response_time_sec"]:
        events.append(
            {
                "event_type": "slow_driver_response",
                "event_severity": "medium",
                "risk_points": 2,
                "evidence": {
                    "response_time_sec": signals["driver_response_time_sec"],
                    "max_allowed_sec": thresholds["response_time_sec"],
                },
            }
        )

    high_severity_count = len([e for e in events if e["event_severity"] == "high"])
    recommended_action = "raise_live_alert" if high_severity_count > 0 else "continue_monitoring"

    payload = {
        "trip_id": trip_id,
        "event_time_utc": trip.get("timestamp") or "2026-09-20T18:42:11Z",
        "lifecycle_phase": "in_trip",
        "source": "telemetry_agent",
        "events": events,
        "high_severity_events": high_severity_count,
        "recommended_action": recommended_action,
    }
    return json.dumps(payload, indent=2)


def consolidate_in_trip_risk(trip_id: str) -> str:
    """Builds authoritative in-trip risk state by combining telemetry and route context."""
    trip = _find_trip(trip_id)
    if not trip:
        return json.dumps({"error": f"Trip '{trip_id}' not found"})

    telemetry_payload = json.loads(evaluate_telemetry_events(trip_id))
    if telemetry_payload.get("error"):
        return json.dumps(telemetry_payload)

    route = trip["route"]
    signals = trip["trip_signals"]
    thresholds = trip["thresholds"]

    telemetry_points = sum(event["risk_points"] for event in telemetry_payload["events"])
    route_context_points = 0
    if route["risk_level"] == "high":
        route_context_points += 2
    elif route["risk_level"] == "medium":
        route_context_points += 1

    if signals["route_deviation"] > thresholds["route_deviation_pct"]:
        route_context_points += 2
    if signals["idle_time_sec"] > thresholds["idle_time_sec"]:
        route_context_points += 1

    telemetry_suggests_high = telemetry_points >= 5
    route_suggests_high = route_context_points >= 3
    conflict_exists = telemetry_suggests_high != route_suggests_high

    if conflict_exists and abs(telemetry_points - route_context_points) <= 2:
        final_live_risk_state = "review_required"
        escalation_action = "operations_review_required"
        decision_reason = "Telemetry and route context are conflicting with low certainty."
    elif telemetry_points + route_context_points >= 8:
        final_live_risk_state = "critical"
        escalation_action = "operations_intervention_required"
        decision_reason = "High-severity telemetry events combined with risky route context."
    elif telemetry_points + route_context_points >= 4:
        final_live_risk_state = "warning"
        escalation_action = "enhanced_monitoring"
        decision_reason = "Elevated live risk signals detected."
    else:
        final_live_risk_state = "normal"
        escalation_action = "no_action"
        decision_reason = "Live telemetry and route context are within acceptable limits."

    payload = {
        "trip_id": trip_id,
        "event_time_utc": telemetry_payload["event_time_utc"],
        "lifecycle_phase": "in_trip",
        "source": "in_trip_monitoring_agent",
        "state_owner": "in_trip_monitoring_agent",
        "final_live_risk_state": final_live_risk_state,
        "telemetry_summary": {
            "high_severity_events": telemetry_payload["high_severity_events"],
            "event_count": len(telemetry_payload["events"]),
            "telemetry_points": telemetry_points,
        },
        "route_context": {
            "risk_level": route["risk_level"],
            "deviation_pct": signals["route_deviation"],
            "idle_seconds": signals["idle_time_sec"],
            "context_points": route_context_points,
        },
        "conflict_detected": conflict_exists,
        "decision_reason": decision_reason,
        "escalation_action": escalation_action,
    }
    return json.dumps(payload, indent=2)


CHECK_RISK_TOOL = FunctionTool(
    name="evaluate_trip_risk",
    description="Assess a ride for safety and operational risk using trip, driver, rider, and route data.",
    parameters={
        "type": "object",
        "properties": {
            "trip_id": {
                "type": "string",
                "description": "The trip identifier, for example 'RIDE-103'",
            }
        },
        "required": ["trip_id"],
        "additionalProperties": False,
    },
    strict=False,
)

CHECK_SUPPORT_CONTEXT_TOOL = FunctionTool(
    name="fetch_trip_context",
    description="Retrieves the complete trip data for a customer support or incident investigation workflow.",
    parameters={
        "type": "object",
        "properties": {
            "trip_id": {
                "type": "string",
                "description": "The trip identifier to inspect",
            }
        },
        "required": ["trip_id"],
        "additionalProperties": False,
    },
    strict=False,
)

CHECK_TELEMETRY_TOOL = FunctionTool(
    name="evaluate_telemetry_events",
    description="Generate event-level telemetry anomaly payload for a live in-trip ride.",
    parameters={
        "type": "object",
        "properties": {
            "trip_id": {
                "type": "string",
                "description": "The trip identifier to evaluate live telemetry for",
            }
        },
        "required": ["trip_id"],
        "additionalProperties": False,
    },
    strict=False,
)

CHECK_IN_TRIP_STATE_TOOL = FunctionTool(
    name="consolidate_in_trip_risk",
    description=(
        "Combine telemetry signals and route context into final in-trip risk state. "
        "This tool returns the authoritative live risk state payload."
    ),
    parameters={
        "type": "object",
        "properties": {
            "trip_id": {
                "type": "string",
                "description": "The trip identifier to consolidate in-trip risk for",
            }
        },
        "required": ["trip_id"],
        "additionalProperties": False,
    },
    strict=False,
)


class SafetyRiskAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are a safety risk assessment expert for a ride-hailing platform.
        Your scope is PRE-TRIP approval only.
        Use evaluate_trip_risk for each trip before making a decision.
        Your job is to classify risk as NORMAL, WARNING, or CRITICAL.
        You are the owner of the pre-trip risk decision.
        Do not use in-trip telemetry events as justification for trip approval decisions.
        Explain the key issues, risks, and recommended operational action.
        If the risk is CRITICAL, recommend escalation to a human operations reviewer.
        Be concise and structured.
        """

        self.agent = self.client.agents.create_version(
            agent_name="ride-safety-risk-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
                tools=[CHECK_RISK_TOOL],
            ),
        )

        return self.agent

    def run(self, input_text: str) -> str:
        conversation = self.openai.conversations.create()

        response = self.openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )

        while True:
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            input_list = []
            for item in function_calls:
                if item.name == "evaluate_trip_risk":
                    args = json.loads(item.arguments)
                    result = evaluate_trip_risk(args["trip_id"])
                else:
                    result = json.dumps({"error": f"Unknown tool '{item.name}'"})

                input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=result,
                    )
                )

            response = self.openai.responses.create(
                input=input_list,
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
            )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return response.output_text

    def cleanup(self):
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version,
            )
        if self.client:
            self.client.close()


class IncidentResponseAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are an incident response and customer support expert for a ride-hailing platform.
        Your scope is POST-ALERT investigation and support response.
        Use fetch_trip_context when investigating a trip involving passenger complaints, route anomalies,
        or driver safety concerns. Provide a structured summary with:
        1. Incident summary
        2. Safety and policy concerns
        3. Recommended support action
        4. Escalation recommendation (support, operation review, or no action)
        Do not override the pre-trip risk decision; explain downstream handling actions instead.
        Keep the response operational and evidence-based.
        """

        self.agent = self.client.agents.create_version(
            agent_name="ride-incident-response-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
                tools=[CHECK_SUPPORT_CONTEXT_TOOL],
            ),
        )

        return self.agent

    def run(self, input_text: str) -> str:
        conversation = self.openai.conversations.create()

        response = self.openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )

        while True:
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            input_list = []
            for item in function_calls:
                if item.name == "fetch_trip_context":
                    args = json.loads(item.arguments)
                    result = fetch_trip_context(args["trip_id"])
                else:
                    result = json.dumps({"error": f"Unknown tool '{item.name}'"})

                input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=result,
                    )
                )

            response = self.openai.responses.create(
                input=input_list,
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
            )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return response.output_text

    def cleanup(self):
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version,
            )
        if self.client:
            self.client.close()


class VehicleTelemetryAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are the Vehicle Telemetry and Dangerous Driving Agent.
        Your scope is IN-TRIP event detection only.
        Always call evaluate_telemetry_events for each requested trip.
        Output telemetry findings as structured event-level signals.
        Do not set final live risk state; that is owned by the In-Trip Monitoring Agent.
        Keep the output concise and operational.
        """

        self.agent = self.client.agents.create_version(
            agent_name="ride-telemetry-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
                tools=[CHECK_TELEMETRY_TOOL],
            ),
        )

        return self.agent

    def run(self, input_text: str) -> str:
        conversation = self.openai.conversations.create()

        response = self.openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )

        while True:
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            input_list = []
            for item in function_calls:
                if item.name == "evaluate_telemetry_events":
                    args = json.loads(item.arguments)
                    result = evaluate_telemetry_events(args["trip_id"])
                else:
                    result = json.dumps({"error": f"Unknown tool '{item.name}'"})

                input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=result,
                    )
                )

            response = self.openai.responses.create(
                input=input_list,
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
            )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return response.output_text

    def cleanup(self):
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version,
            )
        if self.client:
            self.client.close()


class InTripMonitoringAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are the Driver Operations and In-Trip Monitoring Agent.
        Your scope is live in-trip risk consolidation and intervention decisioning.
        Always call consolidate_in_trip_risk for each requested trip.
        You are the authoritative owner of final_live_risk_state.
        If telemetry and route context conflict, keep review_required when confidence is low.
        Return clear intervention and escalation guidance.
        """

        self.agent = self.client.agents.create_version(
            agent_name="ride-intrip-monitoring-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
                tools=[CHECK_IN_TRIP_STATE_TOOL],
            ),
        )

        return self.agent

    def run(self, input_text: str) -> str:
        conversation = self.openai.conversations.create()

        response = self.openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )

        while True:
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            input_list = []
            for item in function_calls:
                if item.name == "consolidate_in_trip_risk":
                    args = json.loads(item.arguments)
                    result = consolidate_in_trip_risk(args["trip_id"])
                else:
                    result = json.dumps({"error": f"Unknown tool '{item.name}'"})

                input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=result,
                    )
                )

            response = self.openai.responses.create(
                input=input_list,
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
            )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return response.output_text

    def cleanup(self):
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version,
            )
        if self.client:
            self.client.close()


def main():
    if not PROJECT_CONNECTION_STRING:
        print("❌ PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    print("=== Agent 1: Ride Safety Risk Agent ===")
    print("Creating agent...")
    risk_agent = SafetyRiskAgent()
    risk_agent.create()
    print(f"✅ Created: {risk_agent.agent.name} (version {risk_agent.agent.version})")

    trip_batch = _load_trip_batch()
    trip_ids = [trip["trip_id"] for trip in trip_batch]

    risk_result = risk_agent.run(
        "You are receiving a batch of trip records that need a safety risk assessment. "
        "Use evaluate_trip_risk for each trip_id in the payload and return a concise summary.\n\n"
        f"BATCH_TRIP_IDS: {json.dumps(trip_ids)}\n"
        "BATCH_TRIP_DATA:\n"
        f"{json.dumps(trip_batch, indent=2)}"
    )
    print(risk_result)

    print("\n=== Agent 2: Vehicle Telemetry and Dangerous Driving Agent ===")
    print("Creating agent...")
    telemetry_agent = VehicleTelemetryAgent()
    telemetry_agent.create()
    print(f"✅ Created: {telemetry_agent.agent.name} (version {telemetry_agent.agent.version})")

    telemetry_result = telemetry_agent.run(
        "You are receiving active in-trip rides. "
        "For each trip_id, call evaluate_telemetry_events and return a concise telemetry event summary.\n\n"
        f"BATCH_TRIP_IDS: {json.dumps(trip_ids)}"
    )
    print(telemetry_result)

    print("\n=== Agent 3: Driver Operations and In-Trip Monitoring Agent ===")
    print("Creating agent...")
    intrip_agent = InTripMonitoringAgent()
    intrip_agent.create()
    print(f"✅ Created: {intrip_agent.agent.name} (version {intrip_agent.agent.version})")

    intrip_result = intrip_agent.run(
        "For each active trip_id, call consolidate_in_trip_risk and return final live risk states. "
        "Clearly show state_owner, final_live_risk_state, and escalation_action.\n\n"
        f"BATCH_TRIP_IDS: {json.dumps(trip_ids)}"
    )
    print(intrip_result)

    print("\n=== Agent 4: Ride Incident Response Agent ===")
    print("Creating agent...")
    support_agent = IncidentResponseAgent()
    support_agent.create()
    print(f"✅ Created: {support_agent.agent.name} (version {support_agent.agent.version})")

    critical_trips = [trip for trip in trip_batch if trip["status"] in {"warning", "critical"}]
    support_result = support_agent.run(
        "Investigate the following higher-risk trips and provide a structured response plan.\n\n"
        "TRIP_BATCH:\n"
        f"{json.dumps(critical_trips, indent=2)}"
    )
    print(support_result)

    # Cleanup — comment out to keep agents visible in the Foundry portal
    # risk_agent.cleanup()
    # telemetry_agent.cleanup()
    # intrip_agent.cleanup()
    # support_agent.cleanup()


if __name__ == "__main__":
    main()
