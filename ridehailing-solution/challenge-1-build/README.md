# Challenge 1: Build Agents

Time: ~30 minutes

## Objectives

By the end of this challenge, you will have:

- ✅ A ride safety risk assessment agent
- ✅ An incident response and support agent
- ✅ Both agents evaluated against real trip scenarios for ride-hailing safety

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

### Agent 2: Ride Incident Response Agent

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
3. create the Incident Response Agent,
4. investigate high-risk trips,
5. print the results to the terminal.

## Why this matters

This challenge demonstrates how a single general-purpose AI agent would be too broad for a ride-hailing environment. In production, the platform needs:

- a safety agent focused on risk scoring,
- an operations/support agent focused on investigation and resolution,
- and clear traceability for both.

This is the foundation of a production-ready multi-agent safety workflow.

## Success criteria

- [ ] The safety risk agent is created successfully
- [ ] It identifies normal, warning, and critical trip scenarios
- [ ] The incident response agent is created successfully
- [ ] It provides operationally useful suggestions for risky rides
- [ ] The logic is grounded in trip data and not just general model assumptions
