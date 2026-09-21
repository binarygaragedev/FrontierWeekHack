"""
Challenge 2: Monitor with Application Insights — SDK Track
Enable GenAI tracing and verify traces appear in App Insights.

Usage:
    python monitor.py
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

MISSING_DEPENDENCIES = []
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None
    MISSING_DEPENDENCIES.append("python-dotenv")


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


env_path = _find_repo_root() / ".env"
if load_dotenv:
    load_dotenv(env_path)

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
APPINSIGHTS_CONN_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
FORCE_WAIT_SECONDS = int(os.getenv("MONITOR_FORCE_WAIT_SECONDS", "45"))


def wait_for_exit() -> None:
    """Keep the console open so users can read output before exit."""
    fallback_wait_used = False

    if os.name == "nt":
        # Use a native keypress wait on Windows. This does not require stdin.
        try:
            import msvcrt

            print("\nPress any key to exit...")
            msvcrt.getch()
            return
        except Exception:
            fallback_wait_used = True

    try:
        input("\nPress Enter to exit...")
    except EOFError:
        # Some launch modes do not provide stdin. On Windows, force a pause.
        if os.name == "nt":
            exit_code = os.system("cmd /c pause")
            if exit_code != 0:
                fallback_wait_used = True
        else:
            fallback_wait_used = True

    if fallback_wait_used:
        print(
            f"\nInteractive pause is unavailable in this launch mode. "
            f"Keeping output visible for {FORCE_WAIT_SECONDS} seconds..."
        )
        time.sleep(FORCE_WAIT_SECONDS)


def ensure_console_launch() -> None:
    """If launched via pythonw (no console), relaunch in cmd so output is visible."""
    if os.name != "nt":
        return

    if os.environ.get("MONITOR_CONSOLE_RELAUNCHED") == "1":
        return

    if sys.executable.lower().endswith("pythonw.exe"):
        script_path = Path(__file__).resolve()
        repo_root = _find_repo_root()
        venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
        python_cmd = f'"{venv_python}"' if venv_python.exists() else "py"
        relaunch_cmd = (
            f'set MONITOR_CONSOLE_RELAUNCHED=1 && '
            f'cd /d "{script_path.parent}" && '
            f'{python_cmd} "{script_path.name}"'
        )
        subprocess.Popen(["cmd", "/k", relaunch_cmd])
        sys.exit(0)


def setup_tracing():
    print("=== Setting up tracing ===")
    print("✅ AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING is enabled")

    from azure.ai.projects.telemetry import AIProjectInstrumentor
    AIProjectInstrumentor().instrument()
    print("✅ AIProjectInstrumentor configured")

    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(
        connection_string=APPINSIGHTS_CONN_STRING,
        enable_live_metrics=True,
    )
    print("✅ Azure Monitor exporter connected")


def fetch_live_trip_signals(trip_id: str) -> str:
    """Returns in-trip telemetry events and route context for live risk consolidation."""
    live_trip_data = {
        "RIDE-103": {
            "trip_id": "RIDE-103",
            "lifecycle_phase": "in_trip",
            "telemetry_agent_payload": {
                "source": "telemetry_agent",
                "events": [
                    {
                        "event_type": "hard_brake",
                        "event_severity": "high",
                        "risk_points": 3,
                        "evidence": {"speed_kph": 78, "decel_mps2": -5.1, "rpm": 4200},
                    },
                    {
                        "event_type": "speeding",
                        "event_severity": "high",
                        "risk_points": 3,
                        "evidence": {"speed_kph": 102, "zone_limit_kph": 70},
                    },
                    {
                        "event_type": "rapid_acceleration",
                        "event_severity": "medium",
                        "risk_points": 2,
                        "evidence": {"accel_mps2": 3.7},
                    },
                ],
            },
            "route_context": {
                "route_risk_level": "high",
                "route_deviation_pct": 18,
                "idle_time_sec": 135,
                "driver_response_time_sec": 42,
            },
            "policy_thresholds": {
                "high_severity_event_count_for_critical": 2,
                "route_deviation_pct_warning": 12,
            },
        }
    }

    trip = live_trip_data.get(trip_id)
    if not trip:
        return json.dumps({"error": f"Trip '{trip_id}' not found"})
    return json.dumps(trip)


def run_traced_agent_call():
    print("\n=== Running traced agent call ===")

    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
    from azure.identity import DefaultAzureCredential
    from openai.types.responses.response_input_param import FunctionCallOutput

    live_signal_tool = FunctionTool(
        name="fetch_live_trip_signals",
        description=(
            "Fetch in-trip telemetry event payload and route context. "
            "Telemetry payload is event-level only and does not represent final live risk state."
        ),
        parameters={
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "Trip ID to assess"}
            },
            "required": ["trip_id"],
            "additionalProperties": False,
        },
        strict=False,
    )

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    openai_client = client.get_openai_client()

    agent = client.agents.create_version(
        agent_name="ride-intrip-monitoring-tracing-agent",
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT_NAME,
            instructions=(
                "You are an In-Trip Monitoring decision agent for a ride-hailing platform. "
                "Assume the trip has already started (lifecycle_phase=in_trip). "
                "Always call fetch_live_trip_signals first. "
                "Telemetry events are input signals only. You own the final_live_risk_state decision. "
                "If telemetry and route context conflict, apply policy thresholds and set review_required when uncertain. "
                "Return strict JSON with keys: trip_id, lifecycle_phase, state_owner, final_live_risk_state, "
                "decision_reason, escalation_action."
            ),
            tools=[live_signal_tool],
        ),
    )

    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        input=(
            "Analyze in-trip safety and produce the final live risk state for trip RIDE-103. "
            "Remember: telemetry is event-level signal source, and In-Trip Monitoring is final state owner."
        ),
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    while True:
        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls:
            break

        input_list = []
        for item in function_calls:
            if item.name == "fetch_live_trip_signals":
                args = json.loads(item.arguments)
                result = fetch_live_trip_signals(args["trip_id"])
            else:
                result = json.dumps({"error": f"Unknown tool '{item.name}'"})

            input_list.append(
                FunctionCallOutput(
                    type="function_call_output",
                    call_id=item.call_id,
                    output=result,
                )
            )

        response = openai_client.responses.create(
            input=input_list,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )

    print(f"✅ Agent responded: {response.output_text[:180]}...")

    openai_client.conversations.delete(conversation_id=conversation.id)
    client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
    client.close()


def verify_traces():
    print("\n=== Verifying traces in App Insights ===")

    if not APPINSIGHTS_CONN_STRING:
        print("⚠️  APPLICATIONINSIGHTS_CONNECTION_STRING not set — skipping verification")
        print("   You can still check traces manually in the Azure Portal")
        return

    print("⏳ Waiting for traces to propagate (30 seconds)...")
    time.sleep(30)

    print("✅ Traces should now be visible in Application Insights")
    print("   Go to: Azure Portal → Application Insights → Search")
    print("   Filter by: Last 30 minutes")


def main():
    try:
        ensure_console_launch()

        if MISSING_DEPENDENCIES:
            print("❌ Missing Python dependencies:")
            for dep in MISSING_DEPENDENCIES:
                print(f"   - {dep}")
            print("\nInstall dependencies and try again:")
            print("   python -m pip install -r requirements.txt")
            return

        if os.getenv("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING") != "true":
            print("❌ AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING is not set to 'true' in .env")
            print("   Add: AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true")
            return

        if not PROJECT_CONNECTION_STRING:
            print("❌ PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
            return

        setup_tracing()
        run_traced_agent_call()
        verify_traces()

        print("\n🎉 Monitoring is active! Check App Insights for the ride safety trace.")
    except Exception as exc:
        print(f"\n❌ monitor.py failed: {exc}")
    finally:
        wait_for_exit()


if __name__ == "__main__":
    main()
