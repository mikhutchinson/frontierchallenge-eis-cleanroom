# Scorer-Blind Clean-Room Policy

This workspace solves `task_116_eis_equivalent_circuit_analysis` using only:

1. the public `apodex/FrontierChallenge` agent-visible instruction and inputs;
2. public scientific literature and software documentation; and
3. independently executed calculations in this workspace.

## Prohibited material

- `apodex/FrontierChallenge-reference`
- grader or verifier source, archives, fixtures, rubrics, expected values, reference outputs
- evaluator-side files from any FrontierChallenge checkout
- any answer derived from those materials

The public dataset explicitly states that it contains no graders, rubrics, fixtures, or reference outputs. Input and instruction hashes are recorded in `AGENT_VISIBLE_FILE_HASHES.json`.
