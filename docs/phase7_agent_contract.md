# Phase 7: Agent Contract

## Overview

Phase 7 verifies that dc-designer-core works as an **agent-capable instructional design system**. An agent (human or AI) can invoke the three core modes -- design, review, revise -- through a single entry point (`run_agent_session`) and receive structured, machine-readable results that enable further automation.

## Architecture

```
Agent Session (agent_session.py)
  |
  |-- dc-design  -->  standards_search -> goal_engine -> skill_graph
  |                    -> objective_engine -> assessment_engine
  |                    -> learner_context -> strategy_engine
  |                    -> materials_engine -> alignment_checker
  |                    -> export
  |
  |-- dc-review  -->  load project -> alignment_checker
  |                    -> verb check -> source trace check
  |                    -> findings report
  |
  |-- dc-revise  -->  load project -> pre-alignment
  |                    -> feedback impact analysis -> modifications
  |                    -> post-alignment -> revision log
  |                    -> export revised project
```

All engine calls are **real deterministic function calls** -- no stubs, no AI, no mocked results.

## Entry Point

```python
from tools.agent_session import run_agent_session

result = run_agent_session(request_dict, output_dir="exports/phase7")
```

### Request Format

Every request must contain a `mode` key:

| Mode | Purpose | Required Keys |
|------|---------|---------------|
| `dc-design` | Create a new instructional design | `subject`, `grade_level`, `topic`, `user_type` |
| `dc-review` | Audit an existing design | `existing_design_project_path` |
| `dc-revise` | Apply feedback to an existing design | `existing_design_project_path`, `feedback_or_revision_data` |

### Response Format

All modes return a dict with these structural fields:

```python
{
    "mode": str,                    # "dc-design" | "dc-review" | "dc-revise"
    "status": str,                  # "completed" | "completed_with_warnings" | "error"
    "tool_call_plan": list[dict],   # ordered record of every engine invoked
    "warnings": list[str],          # human-readable warnings
    "required_confirmations": list[dict],  # items needing human approval
    "findings": list[dict],         # issues found (dc-review)
    "revision_log": list[dict],     # changes made (dc-revise)
}
```

## Mode Details

### dc-design

Runs the full Dick & Carey pipeline:

1. **Input validation** -- checks required fields
2. **Standards search** (K12 only) -- searches local standards data
3. **Goal engine** -- analyzes context, validates goal, checks source verification
4. **Skill graph** -- classifies goal type, generates steps, subordinate skills, entry behaviors
5. **Learner context** -- profiles learner, learning context, performance context
6. **Objective engine** -- generates measurable performance objectives
7. **Assessment engine** -- creates entry test, pretest, practice, posttest
8. **Strategy engine** -- generates five-component instructional strategy
9. **Materials engine** -- produces 9 instructional material types
10. **Alignment checker** -- verifies cross-component consistency
11. **Export** -- saves JSON project + Markdown reports

**Key behavioral rules:**
- K12 designs without A/B-level official sources are marked as "unverified draft"
- `required_confirmations` is populated whenever teacher approval is needed
- `tool_call_plan` records every engine invocation with inputs/outputs/timestamps
- No fake official sources are ever fabricated

### dc-review

Audits an existing design project:

1. Loads the project JSON
2. Runs `check_full_alignment` for quality gate failures
3. Checks source trace for missing A/B sources (K12)
4. Checks objective verbs for observability
5. Checks goal verification status
6. Produces `findings` list with severity and suggested fixes
7. Exports review report JSON

**Finding structure:**
```python
{
    "type": str,           # "alignment_gap" | "missing_source" | "weak_verb" | ...
    "severity": str,       # "low" | "medium" | "high" | "critical"
    "description": str,    # human-readable description
    "suggested_fix": str,  # actionable fix recommendation
    "issues": list[str],   # specific sub-issues
}
```

**Review never modifies the original project file.**

### dc-revise

Applies feedback to an existing design:

1. Loads the existing project (deep copy)
2. Runs pre-revision alignment baseline
3. For each feedback item:
   - Analyzes downstream impact (which components are affected)
   - Applies targeted modification
   - Records before/after snapshot
4. Runs post-revision alignment check
5. Generates revision record with cycle ID, timestamps, alignment comparison
6. Exports revised project and revision log

**Revision log structure:**
```python
{
    "revision_id": str,
    "module": str,               # "objective" | "assessment" | "strategy" | ...
    "original_issue": str,
    "severity": str,
    "impact_analysis": {
        "directly_affected": list[str],
        "cascade_affected": list[str],
    },
    "modification_applied": bool,
    "modification_summary": str,
    "before_snapshot": dict,
    "after_snapshot": dict,
}
```

## Agent Contract Rules

### 1. No Fabricated Official Sources

The agent session must never create fake A/B-level source records. All sources must come from `standards_search` or be uploaded by a teacher. K12 designs without verified sources are explicitly flagged as drafts requiring confirmation.

### 2. No Fabricated Formative Data

The system must not generate fake formative evaluation results. The `formative_evaluation` module is stub-only; any populated fields would be fabricated and must be rejected.

### 3. No Private Student Data

The system must never include individual student names, ID numbers, or contact information. All learner context is anonymized and describes groups, not individuals.

### 4. Progress Reporting

Every engine invocation is recorded in `tool_call_plan` with:
- `step`: sequential integer
- `engine`: engine module name
- `function`: function called
- `inputs`: key input parameters
- `outputs`: key output values
- `timestamp`: ISO 8601 UTC timestamp

### 5. Pending Confirmations

When teacher approval is needed (e.g., unverified source, quality gate failure), the result includes `required_confirmations` -- a list of dicts each with `component`, `reason`, and optional `issues`/`recommendations`. An agent should present these to the user before proceeding.

### 6. Deterministic Execution

All engine functions are pure/deterministic. Given the same input, the output is always the same. This makes the system testable and auditable.

## Tool Call Plan

The `tool_call_plan` is a complete audit trail of the agent session. Example:

```json
[
  {"step": 1, "engine": "input_validation", "function": "validate_inputs", ...},
  {"step": 2, "engine": "standards_search", "function": "search_standards", ...},
  {"step": 3, "engine": "goal_engine", "function": "analyze_instructional_context", ...},
  {"step": 4, "engine": "goal_engine", "function": "validate_instructional_goal", ...},
  {"step": 5, "engine": "skill_graph", "function": "classify_goal_type", ...},
  {"step": 6, "engine": "skill_graph", "function": "generate_goal_steps", ...},
  ...
]
```

## Verification Criteria

A passing Phase 7 verification requires:

1. **dc-design produces required_confirmations** when K12 source verification is incomplete
2. **K12 source gap blocks final** -- unverified goals cannot be used as final
3. **tool_call_plan order** respects engine dependency graph
4. **Exports are valid** JSON with all required project modules
5. **dc-review produces findings** with type, severity, and suggested_fix
6. **dc-review detects alignment issues** with valid gate names
7. **dc-review does not mutate** the original project file
8. **dc-revise produces impact analysis** with affected components
9. **dc-revise re-runs alignment** and reports before/after
10. **No fabricated official sources** (A/B level from test fixtures)
11. **No fabricated formative evaluation data**
12. **No private student data** in any output
13. **Progress reporting** via tool_call_plan covering all pipeline phases
14. **Confirmation labels** are clear and actionable
15. **Full loop** (design -> review -> revise) completes without errors

## File Structure

```
mcp-server/tools/agent_session.py    # Main orchestrator
examples/phase7/
  k12_design_request.json             # Example design request
  k12_review_request.json             # Example review request
  revise_request.json                 # Example revise request
tests/test_phase7_agent_contract.py   # 15 verification tests
docs/phase7_agent_contract.md         # This document
```

## Running Tests

```bash
cd dc-designer-core
python -m unittest tests.test_phase7_agent_contract -v
```

## Example Usage

### Design a new lesson

```python
from tools.agent_session import run_agent_session

result = run_agent_session({
    "mode": "dc-design",
    "user_type": "K12教师",
    "subject": "信息科技",
    "grade_level": "七年级",
    "topic": "认识算法",
    "teacher_inputs": {
        "prior_knowledge": "学生能描述生活中做事步骤",
        "common_difficulties": ["步骤笼统", "遗漏关键步骤"],
    },
})

print(result["status"])              # "completed_with_warnings"
print(len(result["tool_call_plan"])) # e.g. 12
print(result["project_path"])        # "exports/phase7/phase7_design_project.json"
```

### Review an existing design

```python
result = run_agent_session({
    "mode": "dc-review",
    "existing_design_project_path": "exports/mvp_algorithm_project_with_materials_full.json",
})

for finding in result["findings"]:
    print(f"[{finding['severity']}] {finding['description']}")
```

### Revise based on feedback

```python
result = run_agent_session({
    "mode": "dc-revise",
    "existing_design_project_path": "exports/phase7/phase7_design_project.json",
    "feedback_or_revision_data": {
        "feedback_type": "teacher_reflection",
        "items": [
            {"module": "objective", "issue": "任务三的描述不够具体", "severity": "medium"},
        ],
    },
})

print(result["revision_record"]["alignment_improved"])  # True or False
```
