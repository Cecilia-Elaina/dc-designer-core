# Phase 9: Real Plugin Usage Verification (Dogfood)

## 1. Goals

Phase 9 is the final verification layer for dc-designer-core. It answers one question: **does the plugin actually work for real teacher scenarios, end to end, without faking results?**

Phase 9 achieves this by:

1. **Running real MCP tool calls** through the same entry points a teacher (or Claude acting on behalf of a teacher) would use.
2. **Verifying blocking behavior** -- K12 designs without clause-level source documents must be prevented from reaching final status.
3. **Verifying source classification** -- Teacher-uploaded documents must not be treated as official authority sources.
4. **Verifying the review-revise-export chain** -- a full design-to-export pipeline completes without silent failures.
5. **Checking exported artifacts** -- generated .docx, .xlsx, .json, and .md files exist, have non-zero size, and follow the export contract.
6. **Detecting fake readiness** -- the system must never report `can_export_final: true` or `draft_status: "final_ready"` when blocking conditions exist.

---

## 2. Why Phase 9 Is Verification, Not New Capability

Phases 1-8 built the system:

| Phase | What It Built |
|-------|---------------|
| 1-3 | Core engines (goal, skill graph, objective, assessment) |
| 4-5 | Alignment checker, standards knowledge base, context strategy |
| 6 | Document exporter (Word, Excel, JSON, Markdown) |
| 7 | Agent session orchestrator (dc-design / dc-review / dc-revise modes) |
| 8 | MCP plugin layer (server.py, tool discovery, call_tool dispatch) |

Phase 9 builds **nothing new**. It is an acceptance test that exercises the complete system from the outside, using only the 4 public MCP tools as its entry points. If Phase 9 passes, the plugin is ready for real teachers. If it fails, the failure points back to a specific phase that needs fixing.

---

## 3. Teacher Scenarios

Phase 9 exercises four distinct teacher workflows, each representing a real use case:

### Scenario A: K12 Design Without Sources

**Input**: `examples/phase9/k12_design_insufficient_sources.json`

A K12 teacher designs a lesson on "recognizing algorithms" for 7th-grade information technology. They provide learner context (prior knowledge, common difficulties, media, devices, motivation) but supply no official curriculum standard or textbook source documents.

**Expected behavior**: The plugin must complete the design but block final export. `can_export_final` must be `false`, `final_blocking_reasons` must be non-empty, and `draft_status` must not be `"final_ready"`.

### Scenario B: K12 Design With Teacher Sources

**Input**: `examples/phase9/k12_design_with_teacher_sources.json`

Same teacher scenario, but the teacher uploads two documents: a textbook scan and a group lesson-planning record. These are teacher-private sources, not official curriculum standards.

**Expected behavior**: The design completes. Teacher-uploaded sources are classified with `source_category: "teacher_private"` and must not receive `source_level: "A1"`. The system may still block final export if the sources are insufficient for goal-basis claims, but the key invariant is that teacher sources are never treated as official authority.

### Scenario C: Review Existing Design

**Input**: `examples/phase9/review_existing_design.json`

An existing design project (from Phase 8 exports) is submitted for review. The review is read-only and must produce actionable findings.

**Expected behavior**: The review produces a non-empty `findings` array. Each finding has all required fields: `finding_id`, `type`, `severity`, `description`, `evidence`, `suggested_fix`, `affected_modules`, `related_quality_gate`.

### Scenario D: Revise From Teacher Feedback

**Input**: `examples/phase9/revise_from_teacher_feedback.json`

The existing design is revised based on teacher reflection feedback. Two issues are identified: one high-severity (vague objective verbs) and one medium-severity (unclear assessment rubric).

**Expected behavior**: The revise session produces a `revision_log` or `revision_record`, and includes `pre_revision_alignment` and `post_revision_alignment` data showing the impact of changes.

---

## 4. MCP Tool Call Chain

The dogfood script (`scripts/run_phase9_dogfood.py`) executes the full pipeline:

```
Step 1: dc_design_session (K12 insufficient sources)
   |
   +-- produces project JSON on disk
   |
Step 2: dc_review_session (reads project from Step 1)
   |
   +-- produces review findings
   |
Step 3: dc_revise_session (reads project from Step 1, applies teacher feedback)
   |
   +-- produces revised project
   |
Step 4: dc_export_package (reads project from Step 1)
   |
   +-- produces .docx, .xlsx, .json, .md files
```

Each step uses the same `server.call_tool()` entry point that a real MCP client would use. The script chains steps by passing the `project_json` path from Step 1 into Steps 2-4.

---

## 5. Success, Warning, and Failure Criteria

### Success

A step is successful when:
- `status` is `"completed"` or `"completed_with_warnings"` (for design/review/revise)
- `export_status` is `"success"` (for export)
- All output files exist on disk with non-zero size
- The response JSON is valid and contains all required contract fields

### Warning

A step produces warnings when:
- The design completes but cannot reach final status (K12 without sufficient sources)
- The review finds alignment issues
- The revision has unresolved items
- The export completes but some files could not be generated

Warnings are expected for K12 scenarios. The presence of warnings is not a failure -- it is correct behavior when the system correctly identifies insufficient input.

### Failure

A step fails when:
- An exception is raised during execution
- The response JSON is invalid or missing required fields
- `status` is `"error"`
- An output file does not exist when it should
- An output file has zero size

The dogfood summary tracks `failed_steps` and reports `run_status: "completed_with_errors"` if any step fails.

### Summary Invariants

The `phase9_dogfood_summary.json` must satisfy:
- `public_tools_called` lists all 4 tools
- `can_export_final` is `false` for K12 without sources
- `required_confirmations_count` is greater than 0 for K12 without sources
- `final_blocking_reasons_count` is greater than 0 for K12 without sources
- `generated_files` is a non-empty list of filenames

---

## 6. K12 Source Insufficiency Behavior

When a K12 teacher starts a design without clause-level source documents (official curriculum standards or textbook references), the system must enforce the following:

1. **Design still completes** -- the engine runs all steps (goal, skill graph, objectives, assessment, strategy, materials) and produces a full project JSON.

2. **Final export is blocked** -- `can_export_final` is set to `false`. The system generates `final_blocking_reasons` explaining why (e.g., "no clause-level source document for goal basis").

3. **Required confirmations listed** -- the system lists `required_confirmations` that a human must address before the design can be finalized.

4. **Draft status reflects reality** -- `draft_status` must be `"draft_pending_confirmation"` or `"blocked"`, never `"final_ready"`.

5. **Export still works** -- the `dc_export_package` tool still generates files, but they represent a draft, not a final product. This allows teachers to review and iterate.

This behavior prevents the dangerous scenario where an AI system produces a "final" curriculum design without verified alignment to official standards.

---

## 7. Teacher Source vs. Official Source Distinction

The system distinguishes between two source categories:

### Official Authority Sources (`source_category: "official_authority"`)

- Curriculum standards documents (e.g., 课程标准)
- Official textbook content from approved publishers
- Government-issued teaching guidelines
- These receive source levels like `A1` (strong official basis)

### Teacher Private Sources (`source_category: "teacher_private"`)

- Teacher-uploaded textbook scans
- Group lesson-planning records
- School-level supplementary materials
- Teacher-created worksheets or rubrics

**Key rules for teacher sources**:

1. Teacher sources must **never** receive `source_level: "A1"`. They may receive `B1`, `C1`, or other levels based on their relevance and credibility, but they cannot serve as the official authority basis for curriculum alignment.

2. Teacher sources are recorded with appropriate `copyright_scope` and `use_scope` reflecting their non-official status.

3. When teacher sources are the only sources available for a goal-basis claim, the system must still block final export and list the source insufficiency as a blocking reason.

4. The `source_trace.goal_basis.sources` array must accurately reflect whether the basis came from an official or teacher-private source.

---

## 8. Acceptance Artifact Checklist

After running the dogfood pipeline, the following artifacts must exist in `exports/phase9/`:

| Artifact | Description | Required |
|----------|-------------|----------|
| `phase9_design_result.json` | Full output from dc_design_session | Yes |
| `phase9_review_result.json` | Full output from dc_review_session | Yes |
| `phase9_revise_result.json` | Full output from dc_revise_session | Yes |
| `phase9_export_result.json` | Full output from dc_export_package | Yes |
| `phase9_dogfood_summary.json` | Aggregated summary of all steps | Yes |
| Project JSON file | The generated project on disk | Yes |
| Exported .docx files | dc_report, lesson_plan, student_worksheet, ai_process_record | Yes |
| Exported .xlsx file | alignment_matrix | Yes |
| Export index JSON | export_index.json pointing to all exported files | Yes |

The `phase9_dogfood_summary.json` must contain:

```json
{
  "run_status": "completed | completed_with_errors",
  "public_tools_called": ["dc_design_session", "dc_review_session", "dc_revise_session", "dc_export_package"],
  "design_status": "...",
  "review_status": "...",
  "revise_status": "...",
  "export_status": "...",
  "can_export_final": false,
  "required_confirmations_count": "> 0",
  "final_blocking_reasons_count": "> 0",
  "generated_files": ["..."],
  "warnings": [],
  "failed_steps": []
}
```

---

## 9. Test Commands

### Run the dogfood pipeline

```bash
cd <plugin-directory>
python scripts/run_phase9_dogfood.py
```

### Run Phase 9 tests

```bash
cd <plugin-directory>
python -m pytest tests/test_phase9_dogfood.py -v
```

### Run all phases' tests

```bash
cd <plugin-directory>
python -m pytest tests/ -v
```

### Check specific test classes

```bash
# Verify blocking behavior
python -m pytest tests/test_phase9_dogfood.py::TestK12InsufficientSourcesBlocksFinal -v

# Verify source classification
python -m pytest tests/test_phase9_dogfood.py::TestTeacherSourceNotMarkedOfficial -v

# Verify export contract
python -m pytest tests/test_phase9_dogfood.py::TestExportResultContract -v

# Verify review findings
python -m pytest tests/test_phase9_dogfood.py::TestReviewOutputsActionableFindings -v
```

### Verify dogfood summary manually

```bash
# After running dogfood, inspect the summary
python -c "import json; print(json.dumps(json.load(open('exports/phase9/phase9_dogfood_summary.json')), indent=2, ensure_ascii=False))"
```

---

## 10. File Locations

| File | Purpose |
|------|---------|
| `examples/phase9/k12_design_insufficient_sources.json` | Design input: K12 teacher, no official sources |
| `examples/phase9/k12_design_with_teacher_sources.json` | Design input: K12 teacher, teacher-uploaded sources |
| `examples/phase9/review_existing_design.json` | Review input: existing design project |
| `examples/phase9/revise_from_teacher_feedback.json` | Revise input: teacher reflection feedback |
| `scripts/run_phase9_dogfood.py` | Dogfood pipeline script (runs all 4 tools end to end) |
| `tests/test_phase9_dogfood.py` | 8 test classes, 18 test methods verifying Phase 9 invariants |
| `docs/phase9_dogfood_acceptance.md` | This document |
