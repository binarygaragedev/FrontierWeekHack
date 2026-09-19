"""
Challenge 1: Build Agents — SDK Track
Ride-hailing safety agents for a multi-agent platform.

Usage:
    python agents.py

Creates a risk assessment agent and an incident response agent.
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
        Use evaluate_trip_risk for each trip before making a decision.
        Your job is to classify risk as NORMAL, WARNING, or CRITICAL.
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
        Use fetch_trip_context when investigating a trip involving passenger complaints, route anomalies,
        or driver safety concerns. Provide a structured summary with:
        1. Incident summary
        2. Safety and policy concerns
        3. Recommended support action
        4. Escalation recommendation (support, operation review, or no action)
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


def main():
    if not PROJECT_CONNECTION_STRING:
        print("❌ PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    print("=== Ride Safety Risk Agent ===")
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

    print("\n=== Ride Incident Response Agent ===")
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
    # support_agent.cleanup()


if __name__ == "__main__":
    main()
