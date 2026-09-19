# Challenge 3: Evaluate

Time: ~30 minutes

## Objectives

By the end of this challenge, you will have:

- ✅ A dataset of ride-hailing safety scenarios
- ✅ A systematic evaluation of the ride safety agent
- ✅ Quality scoring using built-in evaluators
- ✅ An understanding of the difference between trace monitoring and quality evaluation

## Why evaluate?

Monitoring tells you whether the system runs. Evaluation tells you whether it makes the right decisions.

In a ride-hailing platform, a safety agent that is fast but wrong is not acceptable. It may classify a high-risk trip as safe, or escalate a low-risk trip too aggressively.

## Evaluation dataset

This challenge uses a dataset stored in `eval_portal.jsonl`.

Each row contains:

- an input ride scenario,
- the expected safety classification,
- the recommended action,
- and the expected risk category.

## Example evaluation cases

The dataset includes examples such as:

- normal ride with healthy driver and low-risk route
- warning trip with delayed response and moderate risk
- critical trip with long shift, route deviation, and rest violation
- rider complaint case requiring support intervention
- high-risk night trip with multiple concerns

## Evaluate in the Foundry portal

1. Open the Microsoft Foundry portal.
2. Navigate to your project.
3. Go to Build → Evaluations.
4. Select the ride safety agent.
5. Upload the `eval_portal.jsonl` file.
6. Choose the relevant criteria (for example, coherence and fluency).
7. Run the evaluation.

## What to look at in results

The evaluation gives you both:

- aggregate scores across the full dataset,
- and per-row analysis showing which scenarios performed poorly.

This allows the team to identify systematic issues: for example, the agent may be too lenient with late-night high-risk routes or too strict for moderate route deviations.

## Success criteria

- [ ] The evaluation dataset is uploaded successfully
- [ ] The ride safety agent is evaluated against the full test set
- [ ] You can inspect aggregate metrics and per-row results
- [ ] You have identified at least one case where the agent needs improvement
- [ ] You understand how evaluation fits into the production lifecycle
