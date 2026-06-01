# Reference: Self-Evolution and Subagent Fleet Orchestration

> **Loaded by:** SKILL.md when the user asks to evolve, audit, improve, research, implement, deploy, or monitor the X Distribution System pipeline.
> **Purpose:** Turn pipeline improvement into a controlled loop: audit -> research -> approval -> implementation -> validation -> monitoring.
> **Outputs:** `data/evolution_state.json`, `data/evolution_backlog.json`, timestamped logs in `logs/agent_runs/`.

---

## Table of Contents

1. Operating Rules
2. Mode A: 7-Agent Pipeline Evolution Audit
3. Mode B: 10-Agent Outcome Research Fleet
4. Mode C: 10-20 Agent Approved Implementation Fleet
5. Mode D: Self-Monitoring and Evolution Loop
6. Approval Gates
7. Persistence Schemas
8. Output Formats
9. Failure Handling

---

## 1. Operating Rules

### Core Principle

The system may research and recommend improvements automatically, but it must not edit, persist audit state, deploy, delete, rename, or restructure user files without explicit approval of the plan and write scope.

### Subagent Availability

If the runtime supports subagents:
- Run research and audit agents in parallel.
- Assign each agent a clear role, input bundle, and expected output.
- For implementation agents, assign disjoint write ownership before launch.

If subagents are unavailable:
- Emulate the fleet with sequential role passes.
- Label each pass with the same agent name.
- Preserve the same output format so the rest of the pipeline still works.

### No Recursive Autonomy

One evolution cycle means:
1. Gather evidence.
2. Produce a plan.
3. Ask for approval.
4. Implement approved changes.
5. Validate.
6. Log results.

The system may recommend another cycle, but it must return to the user before launching it.

### Dry-Run Default

If the user asks to audit, research, review, plan, or show improvements "before changing anything," run in dry-run mode:
- Do not write `data/evolution_state.json`.
- Do not write `data/evolution_backlog.json`.
- Do not append logs.
- Present the exact state/backlog/log entries that would be written.
- Ask whether to persist them.

If the user explicitly says "save this audit," "persist the backlog," "update evolution state," or approves persistence, then write only the approved state/backlog/log files.

---

## 2. Mode A: 7-Agent Pipeline Evolution Audit

### Trigger Examples

- "evolve pipeline"
- "self evolve"
- "audit this skill"
- "improve the whole pipeline"
- "make this system better"

### Input Bundle

Before launching agents, collect:
- `SKILL.md`
- `commands/*.toml`
- `config/*.json`
- `data/*.json`
- `evals/evals.json`
- Relevant `references/*.md`
- Recent logs from `logs/agent_runs/` and `logs/fact_checks/` if present

### Agent Fleet

Run these 7 agents in parallel when possible.

| Agent | Purpose | Required Output |
|---|---|---|
| 1. Architecture Mapper | Map pipeline stages, dependencies, and state transitions. | Current architecture, bottlenecks, missing links. |
| 2. Data Contract Auditor | Compare schemas, actual data files, command assumptions, and reference docs. | Contract mismatches, missing fields, migration needs. |
| 3. Command Routing Auditor | Inspect trigger phrases, command TOML, workflow routing, and edge cases. | Ambiguous routes, contradictions, unreachable modes. |
| 4. Research and Verification Auditor | Review news, source, fact-check, and credibility procedures. | Verification gaps, source-quality risks, evidence rules. |
| 5. Scoring and Eval Auditor | Review grading formulas, thresholds, eval coverage, and measurable outcomes. | Calibration risks, missing tests, proposed evals. |
| 6. Automation Engineer | Identify where scripts, validation, logs, or deterministic tooling are needed. | Implementation opportunities, script candidates, run checks. |
| 7. Safety and Governance Auditor | Check approval gates, destructive actions, privacy, posting risk, and autonomy limits. | Safety issues, approval requirements, policy-safe alternatives. |

### Standard Agent Prompt

Use this prompt shape for each auditor:

```text
You are [AGENT NAME].

Audit the X Distribution System pipeline from your specialty only.
Use the provided files as source of truth.
Return:
1. Findings ranked by severity.
2. Evidence with file paths and line references when available.
3. Concrete fixes.
4. Risks if not fixed.
5. What should be tested after the fix.

Do not edit files. Do not solve other agents' scopes.
```

### Synthesis Scoring

After all 7 agents return, score each improvement:

```text
priority_score =
  impact (0-5)
  + confidence (0-3)
  + unblock_value (0-3)
  - implementation_risk (0-3)
  - complexity (0-2)
```

Priority labels:
- 8+ = P0/P1, do next.
- 5-7 = P2, schedule.
- 2-4 = P3, backlog.
- Below 2 = watch only.

In dry-run mode, present the ranked backlog as proposed JSON. Save it to `data/evolution_backlog.json` only if the user approves persistence.

---

## 3. Mode B: 10-Agent Outcome Research Fleet

### Trigger Examples

- "this is what I want, this is how I want it"
- "research how to achieve this outcome"
- "plan this feature"
- "find the best way to build this"

### User Brief Extraction

Extract the user's request into:

```json
{
  "desired_outcome": "what the user wants",
  "style_or_constraints": "how the user wants it",
  "target_files_or_modules": [],
  "success_criteria": [],
  "known_risks": [],
  "approval_needed_before_implementation": true
}
```

If any field is missing, make a reasonable assumption and mark it as an assumption. Ask only if the missing field would make implementation risky.

### Research Fleet

Spawn 10 research agents in parallel when possible.

| Agent | Research Scope |
|---|---|
| 1. Outcome Analyst | Clarify the requested outcome, non-goals, and success criteria. |
| 2. Existing-System Integrator | Find where the outcome fits in the current skill, commands, schemas, and references. |
| 3. Architecture Options Researcher | Propose 2-3 viable designs with tradeoffs. |
| 4. Runtime Feasibility Researcher | Check whether required tools, subagents, filesystem, web, MCP, or scripts are available. |
| 5. Data and Schema Planner | Define state files, migrations, IDs, logs, and retention rules. |
| 6. Prompt and Agent Designer | Draft specialized agent roles, prompts, input bundles, and output contracts. |
| 7. Eval and Validation Strategist | Define deterministic checks, smoke tests, forward tests, and pass/fail criteria. |
| 8. Safety and Approval Reviewer | Identify risky actions, user approval gates, and safe fallbacks. |
| 9. Implementation Planner | Break work into phases and disjoint write scopes. |
| 10. Operator Workflow Designer | Design how the user invokes, reviews, approves, and monitors the feature. |

### Research Output

Synthesize results into:

1. Recommended design.
2. Alternatives rejected and why.
3. Implementation phases.
4. Files to edit/create.
5. Validation plan.
6. Approval request for implementation.

Do not implement until the user approves.

---

## 4. Mode C: 10-20 Agent Approved Implementation Fleet

### Trigger Examples

- "approved, implement it"
- "deploy approved changes"
- "execute the implementation"
- "build the approved plan"

### Approval Gate

Before implementation, confirm:
- The exact approved plan.
- The files/directories that may be edited.
- Whether new scripts/data/log directories may be created.
- Whether tests/validators may be run.

### Fleet Size Selection

Use 10 agents for compact changes.
Use 11-15 agents for multi-file skill changes.
Use 16-20 agents only for large changes with clearly separable write scopes.

Never spawn more agents than there are meaningful independent work packages.

### Implementation Agent Roles

Use these roles as a base set and add specialists only when needed:

| Agent | Ownership |
|---|---|
| 1. Lead Integrator | Final synthesis, conflict resolution, validation summary. |
| 2. SKILL.md Editor | Routing, hard rules, mode descriptions. |
| 3. Command Spec Editor | `commands/*.toml` files only. |
| 4. Reference Writer | `references/*.md` files only. |
| 5. Schema/Data Editor | `config/*.json` and `data/*.json` only. |
| 6. Eval Builder | `evals/evals.json` and eval fixtures only. |
| 7. Script Builder | `scripts/*` validators or automation helpers only. |
| 8. Logging/Observability Builder | Log schemas, run summaries, monitoring outputs. |
| 9. Safety Reviewer | Approval gates, destructive-action prevention, privacy checks. |
| 10. Validation Runner | Parse checks, smoke tests, line-reference verification. |

Optional roles:
- Migration Builder
- Documentation Consistency Checker
- Performance/Cost Reviewer
- Tool Integration Specialist
- Backward Compatibility Reviewer
- Prompt Quality Reviewer
- Test Data Builder
- Final QA Reviewer

### Worker Prompt Requirements

Every implementation agent must receive:

```text
You are not alone in the codebase. Other agents may be editing different files.
Do not revert or overwrite unrelated changes.
Own only these files/modules: [WRITE SCOPE].
Adjust your work to accommodate other changes.
Return a concise summary and a list of changed files.
```

### Integration Rules

After workers finish:
1. Review changed files.
2. Resolve overlaps manually.
3. Run validation.
4. Update `data/evolution_state.json`.
5. Append an implementation log.
6. Present exactly what changed and what still needs work.

---

## 5. Mode D: Self-Monitoring and Evolution Loop

### Trigger Examples

- "monitor evolution"
- "check if the pipeline improved"
- "evolution report"
- "what should evolve next"

### Monitor Inputs

Read:
- `data/evolution_state.json`
- `data/evolution_backlog.json`
- `evals/evals.json`
- `data/performance_history.json`
- Recent logs in `logs/agent_runs/`
- Any failed validation output

### Monitor Checks

Report:
- Open backlog items by priority.
- Recently implemented changes and validation status.
- Repeated failures across logs.
- Schema drift or stale data.
- Evals missing for new behavior.
- Agent fleet bottlenecks.
- Recommended next evolution cycle.

### Evolution Decision

Use this rule:

```text
Only recommend self-evolution when there is evidence:
- repeated failure,
- new user requirement,
- measurable performance gap,
- schema mismatch,
- stale strategy,
- manual work that should be automated,
- missing eval coverage.
```

Do not evolve just because a change is possible.

---

## 6. Approval Gates

### No Approval Needed

- Read files.
- Audit.
- Research.
- Draft plans.
- Draft proposed patches.
- Produce recommendations.

### Approval Required Before Action

- Editing files.
- Persisting audit, research, monitoring, state, backlog, or log files.
- Creating new persistent scripts.
- Running generated scripts.
- Moving/renaming files.
- Updating skill behavior that changes future autonomy.
- Launching implementation fleets that will write files.

The approval request must include:
- What will change.
- Which files may be edited.
- Which state/backlog/log files may be written.
- What validation will run.
- What could go wrong.

---

## 7. Persistence Schemas

### data/evolution_state.json

```json
{
  "metadata": {
    "description": "Current self-evolution state for the X Distribution System",
    "updated_by": "evolution pipeline"
  },
  "last_updated": null,
  "cycle_count": 0,
  "current_phase": "idle",
  "last_audit": null,
  "last_research_plan": null,
  "last_approved_plan": null,
  "last_implementation": null,
  "validation_status": "not_run",
  "open_questions": []
}
```

### data/evolution_backlog.json

```json
{
  "metadata": {
    "description": "Ranked backlog of pipeline evolution opportunities",
    "priority_formula": "impact + confidence + unblock_value - implementation_risk - complexity"
  },
  "last_updated": null,
  "items": []
}
```

### Evolution Backlog Item

```json
{
  "id": "evo_YYYYMMDD_slug",
  "title": "string",
  "source": "audit | research | monitoring | user_request",
  "priority_score": 0,
  "priority": "P0 | P1 | P2 | P3",
  "impact": 0,
  "confidence": 0,
  "unblock_value": 0,
  "implementation_risk": 0,
  "complexity": 0,
  "evidence": [{"file": "path", "line": 0, "note": "string"}],
  "recommended_fix": "string",
  "status": "open | approved | in_progress | implemented | rejected | deferred",
  "validation_plan": [],
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

---

## 8. Output Formats

### Evolution Audit

```markdown
# Pipeline Evolution Audit - [Date]

| Rank | Priority | Area | Finding | Evidence | Fix |
|---|---|---|---|---|---|

## Recommended Next Plan
[Short implementation plan requiring approval]
```

### Outcome Research

```markdown
# Outcome Research Plan

## Recommended Design

## Why This Design

## Implementation Phases

## Files To Change

## Validation Plan

## Approval Needed
```

### Implementation Report

```markdown
# Implementation Report

## Changed Files

## Validation Results

## Remaining Risks

## Evolution State Updated
```

### Monitoring Report

```markdown
# Evolution Monitor

| Area | Status | Evidence | Recommended Action |
|---|---|---|---|
```

---

## 9. Failure Handling

- If a subagent fails, continue with remaining agents and log the failure.
- If more than 30% of agents fail, stop and present a partial report.
- If outputs conflict, prefer evidence-backed findings with file references.
- If implementation agents edit overlapping files, integrate manually and verify.
- If validation fails, do not mark the plan implemented.
- If state files are malformed, preserve the original and create a fresh replacement only after approval.
