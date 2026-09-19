# Challenge 4: Production Workflow

Time: ~20 minutes

## Objectives

By the end of this challenge, you will have:

- ✅ A production-style trip risk workflow
- ✅ A multi-agent orchestration pattern for rides
- ✅ Knowledge of how to connect the agents into a real operational flow
- ✅ A clear understanding of how to monitor, evaluate, and improve the system over time

## Scenario

The individual agents from Challenge 1 are useful, but in real production they need to work together as a single workflow.

For a ride-hailing platform, the safest workflow is:

1. Evaluate the trip before it proceeds
2. Monitor the live trip while it is active
3. Escalate any safety concern to operations
4. Investigate incidents with a support or dispute workflow
5. Produce a final operational summary for the platform team

## Workflow design

The production workflow is:

```text
ensure_agents_deployed()
    |
    v
run_trip_risk_scan()          <-- Safety Risk Agent checks all rides
    |
    v
for each trip with risk > threshold
run_incident_response()       <-- Incident Response Agent investigates risky trips
    |
    v
print_ride_health_report()    <-- Final report for operations team
```

## Files in this folder

- `deploy.py` — orchestrates the multi-agent workflow
- `evaluation_dataset.json` — sample dataset for evaluation and benchmarking
- `README.md` — challenge instructions

## Run the workflow

From the solution root:

```bash
cd challenge-4-deploy
python deploy.py
```

The script will:

- ensure the safety and incident agents exist,
- evaluate a batch of trip scenarios,
- trigger incident analysis for higher-risk rides,
- and print a final ride health report.

## Why this matters

This is the step that turns a prototype into a production-friendly system. The agents are no longer just isolated experiments — they form a workflow that can be monitored, evaluated, and reused by a business process.

## Success criteria

- [ ] The workflow runs end-to-end without errors
- [ ] The safety agent evaluates rides and identifies risk levels
- [ ] The incident response agent investigates high-risk trips
- [ ] The final output is a structured operational summary for the business team
