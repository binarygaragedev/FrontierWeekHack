"""
Challenge 4: Production Workflow — SDK Track
Multi-agent orchestration workflow for a ride-hailing platform.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


env_path = _find_repo_root() / ".env"
load_dotenv(env_path)

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
TRIP_DATA_PATH = Path(__file__).resolve().parent.parent / "challenge-1-build" / "trip_data.json"

TRIP_IDS = ["RIDE-101", "RIDE-102", "RIDE-103", "RIDE-104", "RIDE-105"]
SAFETY_AGENT_NAME = "ride-safety-risk-agent"
SUPPORT_AGENT_NAME = "ride-incident-response-agent"


def evaluate_trip_risk(trip_id: str) -> str:
    with open(TRIP_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    trip = next((item for item in data["trips"] if item["trip_id"] == trip_id), None)
    if not trip:
        return json.dumps({"error": f"Trip not found: {trip_id}"})

    driver = trip["driver"]
    rider = trip["rider"]
    route = trip["route"]
    signals = trip["trip_signals"]
    thresholds = trip["thresholds"]

    risk_score = 0
    concerns = []

    if driver["shift_hours"] > thresholds["shift_hours"]:
        concerns.append("driver fatigue")
        risk_score += 2
    if driver["rating"] < thresholds["driver_rating"]:
        concerns.append("low driver rating")
        risk_score += 2
    if driver["recent_incidents"] > 0:
        concerns.append("recent incidents")
        risk_score += 2
    if not driver["rest_compliance"]:
        concerns.append("rest compliance violation")
        risk_score += 3
    if rider["prior_complaints"] > 0:
        concerns.append("rider complaint history")
        risk_score += 1
    if route["risk_level"] == "high":
        concerns.append("high route risk")
        risk_score += 3
    elif route["risk_level"] == "medium":
        concerns.append("medium route risk")
        risk_score += 1
    if signals["driver_response_time_sec"] > thresholds["response_time_sec"]:
        concerns.append("slow response time")
        risk_score += 2
    if signals["idle_time_sec"] > thresholds["idle_time_sec"]:
        concerns.append("extended idle time")
        risk_score += 1
    if signals["route_deviation"] > thresholds["route_deviation_pct"]:
        concerns.append("route deviation")
        risk_score += 3

    if risk_score >= 7:
        risk_status = "critical"
    elif risk_score >= 4:
        risk_status = "warning"
    else:
        risk_status = "normal"

    return json.dumps({
        "trip_id": trip["trip_id"],
        "risk_status": risk_status,
        "risk_score": risk_score,
        "concerns": concerns,
        "driver": driver,
        "rider": rider,
        "route": route,
        "signals": signals,
    }, indent=2)


def ensure_agents_deployed() -> tuple:
    print("=== Step 1: Ensure Agents Are Deployed ===")

    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
    from azure.identity import DefaultAzureCredential

    risk_tool = FunctionTool(
        name="evaluate_trip_risk",
        description="Assess a trip for safety and operational risk.",
        parameters={
            "type": "object",
            "properties": {"trip_id": {"type": "string"}},
            "required": ["trip_id"],
        },
        strict=False,
    )

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    existing_names = {a.name for a in client.agents.list()}

    if SAFETY_AGENT_NAME not in existing_names:
        client.agents.create_version(
            agent_name=SAFETY_AGENT_NAME,
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=(
                    "You are a ride-hailing safety risk expert. Use evaluate_trip_risk for each trip. "
                    "Return a risk decision and recommended action. If the result is critical, trigger escalation."
                ),
                tools=[risk_tool],
            ),
        )
        print(f"  Deployed: {SAFETY_AGENT_NAME}")
    else:
        print(f"  Found existing: {SAFETY_AGENT_NAME}")

    if SUPPORT_AGENT_NAME not in existing_names:
        client.agents.create_version(
            agent_name=SUPPORT_AGENT_NAME,
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=(
                    "You are an incident response specialist for a ride-hailing platform. "
                    "Given a risky trip, produce a concise investigation summary, recommended support action, "
                    "and escalation path."
                ),
            ),
        )
        print(f"  Deployed: {SUPPORT_AGENT_NAME}")
    else:
        print(f"  Found existing: {SUPPORT_AGENT_NAME}")

    client.close()
    return SAFETY_AGENT_NAME, SUPPORT_AGENT_NAME


def run_trip_risk_scan(safety_agent_name: str) -> str:
    print("\n=== Step 2a: Trip Risk Scan ===")

    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    from openai.types.responses.response_input_param import FunctionCallOutput

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    openai_client = client.get_openai_client()
    agent_ref = {"agent_reference": {"name": safety_agent_name, "type": "agent_reference"}}

    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        input=(
            f"Assess the following trips: {', '.join(TRIP_IDS)}. "
            "Use evaluate_trip_risk for each trip and return a compact summary."
        ),
        conversation=conversation.id,
        extra_body=agent_ref,
    )

    while any(item.type == "function_call" for item in response.output):
        tool_outputs = []
        for item in response.output:
            if item.type == "function_call":
                args = json.loads(item.arguments)
                result = evaluate_trip_risk(args.get("trip_id", ""))
                tool_outputs.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=result,
                    )
                )
        response = openai_client.responses.create(
            input=tool_outputs,
            conversation=conversation.id,
            extra_body=agent_ref,
        )

    report = response.output_text
    openai_client.conversations.delete(conversation_id=conversation.id)
    client.close()
    return report


def run_incident_response(support_agent_name: str, trip_id: str) -> str:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    openai_client = client.get_openai_client()
    agent_ref = {"agent_reference": {"name": support_agent_name, "type": "agent_reference"}}

    with open(TRIP_DATA_PATH, "r", encoding="utf-8") as f:
        trips = json.load(f)["trips"]
    trip = next((item for item in trips if item["trip_id"] == trip_id), None)

    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        input=(
            f"Investigate this trip in a safety workflow. Trip context:\n{json.dumps(trip, indent=2)}\n"
            "Provide incident summary, safety concerns, and recommended response."
        ),
        conversation=conversation.id,
        extra_body=agent_ref,
    )
    result = response.output_text
    openai_client.conversations.delete(conversation_id=conversation.id)
    client.close()
    return result


def run_ride_health_workflow(safety_agent_name: str, support_agent_name: str) -> dict:
    risk_report = run_trip_risk_scan(safety_agent_name)
    print(risk_report)

    print("\n=== Step 2b: Incident Response ===")
    escalations = ["RIDE-102", "RIDE-103", "RIDE-104"]
    responses = {}

    for trip_id in escalations:
        print(f"  Investigating {trip_id}...")
        responses[trip_id] = run_incident_response(support_agent_name, trip_id)

    return {
        "risk_report": risk_report,
        "trip_ids_reviewed": escalations,
        "responses": responses,
    }


def print_ride_health_report(report: dict):
    print("\n" + "=" * 60)
    print("RIDE-HAILING SAFETY REPORT")
    print("=" * 60)
    print(f"Trips reviewed: {len(report['trip_ids_reviewed'])}")
    print(f"Trip IDs: {', '.join(report['trip_ids_reviewed'])}")

    for trip_id, response in report["responses"].items():
        print(f"\n--- {trip_id} ---")
        print(response)


def main():
    if not PROJECT_CONNECTION_STRING:
        print("❌ PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    safety_agent, support_agent = ensure_agents_deployed()
    workflow_report = run_ride_health_workflow(safety_agent, support_agent)
    print_ride_health_report(workflow_report)

    print("\n✅ Ride-hailing workflow complete.")


if __name__ == "__main__":
    main()
