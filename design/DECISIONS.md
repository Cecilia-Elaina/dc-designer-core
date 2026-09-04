# Design Decisions

Status: approved for v3 implementation

This file records decisions that affect product scope, data, public claims and
implementation boundaries. The user confirmed the v3 direction before the
knowledge-base implementation started.

## D-001: v3 scope is nine selected K-12 subjects

- Status: approved
- Decision: Cover Chinese, mathematics, English, physics, chemistry, biology,
  history, geography and politics across primary, junior secondary and regular
  senior secondary where the subject is available.
- Reason: This matches the requested product scope while excluding vocational and
  higher education.
- Consequence: Public language says nine-subject coverage rather than all K-12
  subjects.
- Risk: Users may interpret politics differently by stage; use stage-aware
  official names.

## D-002: national sources are the v3 baseline

- Status: approved
- Decision: Start with Ministry of Education curriculum plans and standards, then
  add local official documents and textbook mappings as optional extensions.
- Reason: National and regional rules must not be mixed into one unlabelled
  knowledge base.
- Consequence: Every source is versioned, scoped, linked and
  confirmation-aware.

## D-003: one workflow core, nine subject adapters

- Status: approved
- Decision: Keep the Dick-Carey workflow, project state, provenance, privacy and
  export contracts in the core. Put terminology, evidence, misconceptions,
  assessment, strategy and safety rules in subject packs.
- Reason: Avoid nine divergent plugins and preserve cross-subject consistency.
- Consequence: A new subject must satisfy the same adapter contract before it is
  advertised.

## D-004: politics uses stage-aware naming

- Status: approved
- Decision: Use 道德与法治 for compulsory education and 思想政治 for regular
  senior secondary; keep politics as the stable internal ID and search alias.
- Reason: The user-facing label follows the applicable official curriculum
  terminology.

## D-005: source updates remain staged

- Status: inherited and approved for v3
- Decision: Online official-document retrieval creates a pending local
  candidate; it never silently changes active evidence or historical projects.
- Reason: Version drift and applicability errors are more damaging than a
  slower update path.

## D-006: teacher data stays local

- Status: inherited and approved for v3
- Decision: Teacher documents, class context and anonymous learner information
  remain in the private workspace and are excluded from public packaging.
- Reason: Privacy, copyright and reproducibility boundaries.

## D-007: compatibility means shared capability, not identical host UI

- Status: inherited and approved for v3
- Decision: Provide a portable prompt, project contract, MCP path and native
  adapters where supported. Do not promise the same installation command or
  command namespace on every agent host.
- Reason: Agent plugin systems differ even when the workflow is shared.

## D-008: v3 requires a major affected validation pass

- Status: approved
- Decision: Before v3 release, validate schemas, source provenance, all nine
  representative subject cases, host adapters, privacy and output integrity.
- Reason: This changes core knowledge and contracts, unlike a local website style
  edit.

## Implementation note

The first implementation slice is complete: official source acquisition,
18 stage-specific standard records, the nine-subject adapter registry,
stage-aware retrieval and focused regression checks. Full plugin behavior,
public copy and release validation remain later implementation gates.
