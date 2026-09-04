# DC Designer v3 Design System

Status: approved for implementation
Date: 2026-09-04
Scope: China K-12, nine selected subjects, primary through regular senior secondary

This document is the project-level design system for the v3 multi-subject
upgrade. It is a design source of truth, not an implementation checklist. Code,
knowledge-base activation, public claims, and release work must follow the
approved decisions recorded in design/DECISIONS.md.

## 1. Product Position

DC Designer is a cross-agent, local-first instructional systems design plugin.
It uses the Dick-Carey model to help a teacher move from a real teaching need to
an evidence-linked, classroom-ready design package.

The v3 promise is:

> One workflow, nine subject adapters, official source traceability, and the
> teacher in control of every important decision.

DC Designer does not replace teacher judgment, invent student results, or turn a
course standard candidate into a confirmed requirement without teacher review.

## 2. Scope And Naming

### In scope

- Primary, junior secondary, and regular senior secondary education in mainland
  China.
- Chinese, mathematics, English, physics, chemistry, biology, history,
  geography, and politics.
- National curriculum plans and standards as the baseline source set.
- Optional local curriculum documents, textbook versions, and school materials
  selected by the teacher.
- Design, review, and revision using the same structured project contract.

### Stage-aware subject names

The internal subject IDs remain stable. The visible name follows the official
stage terminology:

| Subject ID | Primary | Junior secondary | Senior secondary |
| --- | --- | --- | --- |
| `chinese` | Chinese | Chinese | Chinese |
| `mathematics` | Mathematics | Mathematics | Mathematics |
| `english` | English when offered | English | English |
| `physics` | unavailable by default | Physics | Physics |
| `chemistry` | unavailable by default | Chemistry | Chemistry |
| `biology` | unavailable by default | Biology | Biology |
| `history` | unavailable by default | History | History |
| `geography` | unavailable by default | Geography | Geography |
| `politics` | Moral education and rule of law when selected | Moral education and rule of law | Ideological and political education |

The UI may accept `政治` as a search alias, but it must show the stage-specific
official label before a source or goal is selected. Whether a subject is offered
in a particular grade or region remains a teacher-confirmed input.

The public product claim should be **China K-12 nine-subject coverage**, not
"all K-12 subjects". The official compulsory-education plan also includes
subjects outside this v3 scope, so the broader claim would be misleading.

## 3. Design Principles

1. **System before prose**: every output must retain the relationships between
   need, analysis, objective, evidence, strategy, material, implementation, and
   revision.
2. **One core, subject adapters**: the Dick-Carey flow is shared; subject rules
   change the evidence and decision logic rather than duplicating the workflow.
3. **Sources are versioned objects**: a source is never just pasted text. It has
   authority, version, applicability, location, hash, and confirmation state.
4. **Teacher confirmation is a gate**: AI suggestions and clause candidates are
   useful working material, not final standards.
5. **Local by default**: teacher documents, class context, and historical
   projects stay in the local workspace and are not public package content.
6. **Portable by design**: a shared project contract and prompt fallback are the
   compatibility baseline; host-specific commands are adapters.
7. **Evidence over decoration**: subject differences must be visible in the
   quality of objectives, assessments, and materials, not only in labels or
   colors.

## 4. Product Architecture

```text
Agent adapters
  Codex / Claude Code / Gemini CLI / MCP / file-reading agents
        |
Portable project and prompt contract
        |
K12 workflow core
  intake -> source selection -> Dick-Carey modules -> confirmation gates
        |
Subject pack registry
  nine subject packs with stage rules and evidence rules
        |
Source and provenance registry
  official snapshots -> local staged updates -> teacher-confirmed sources
        |
Output adapters
  Markdown / Word / JSON / Excel / Draw.io / PNG / review and revision records
```

The current v2 `data/standards/` registry, source provenance rules, local
workspace policy, and cross-agent contract are inherited. v3 adds subject and
stage dimensions; it does not create a second source system.

## 5. Knowledge Base Design

### Source tiers

| Tier | Source | Allowed use |
| --- | --- | --- |
| A1 | Ministry or government official document | Candidate basis for goals and constraints, after teacher confirmation |
| A2 | Local official curriculum implementation document | Local applicability and implementation constraints |
| B1 | Teacher-selected textbook or public teaching material | Content organization and examples, not a national requirement |
| C1 | Teacher private material and anonymous class context | Local design decisions, private workspace only |
| AI | AI inference or suggestion | Candidate only, never the sole formal basis |

The initial national source set is anchored to the Ministry of Education notice
for the 2022 compulsory-education curriculum plan and standards, and the notice
for the regular senior-secondary curriculum plan and standards, 2017 edition,
2020 revision:

- [Compulsory education curriculum plan and standards, 2022 edition](https://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html)
- [Regular senior-secondary curriculum plan and subject standards, 2017 edition, 2020 revision](https://www.moe.gov.cn/srcsite/A26/s8001/202006/t20200603_462199.html)

The acquisition process must be official-domain first, version-pinned, and
reviewable. A newly fetched document enters a pending local update area. It does
not alter the active evidence snapshot until the source record and applicability
are reviewed.

### Required source record

```text
source_id
authority
title
publication_date
effective_date
version
stage
grade_levels
subject
source_url
retrieved_at
content_sha256 or metadata_snapshot_status
chapter_or_page
clause_id
excerpt
normalized_summary
applicable_modules
copyright_scope
verification_status
```

Commercial textbook full text, private student information, and unverified
downloaded documents must not enter the public plugin package. Public exports
should contain links, citations, short permitted excerpts, and structured
summaries rather than uncontrolled document copies.

## 6. Subject Adapter Contract

Every subject pack must provide the same contract:

```text
subject_id
stage_rules
official_source_ids
core_competency_terms
concept_and_skill_patterns
observable_verbs
common_misconceptions
assessment_evidence_patterns
strategy_patterns
material_patterns
formative_feedback_patterns
safety_or_ethics_rules
terminology_aliases
validation_rules
```

The adapter may recommend content and checks, but the workflow core owns project
state, confirmation gates, provenance, privacy, and export contracts.

Minimum subject-specific evidence rules:

- Language subjects: comprehension, expression, text or conversation evidence,
  and revision quality.
- Mathematics: reasoning, representation, modeling, calculation, and problem
  solving evidence.
- Physics, chemistry, and biology: observation or experiment evidence, variables,
  explanation, and safety constraints where relevant.
- History: chronology, source evidence, contextualization, and historical
  interpretation.
- Geography: spatial representation, map or data evidence, and human-environment
  reasoning.
- Moral education and ideological-political education: concept understanding,
  situation analysis, reasoned judgment, and teacher-confirmed value boundaries.

## 7. Teacher Workflow

The main interaction remains a short natural-language request. The system then
confirms only the decisions that affect the current design:

1. Stage, grade, subject, topic, textbook version, and lesson time.
2. Learner characteristics, known difficulties, equipment, and classroom
   constraints.
3. National source version and optional local source scope.
4. Fast standards-constrained design or full collaborative design.
5. Teacher confirmation of purpose, objectives, evidence, and any local rules.

The shared Dick-Carey sequence remains:

```text
need -> instructional analysis -> learner and environment -> performance objectives
-> assessment -> strategy -> materials -> formative evaluation -> revision
```

Each important conclusion carries a provenance label such as `OFFICIAL_STANDARD`,
`LOCAL_OFFICIAL`, `TEXTBOOK`, `TEACHER_INPUT`, `LEARNER_DATA`, `AI_SUGGESTION`,
or `AI_INFERENCE`.

## 8. Cross-Agent Contract

The portable baseline consists of:

- One shared project JSON schema and source schema.
- One shared design, review, and revise behavior contract.
- One generic startup prompt for agents without a native plugin system.
- Optional native manifests for Codex, Claude Code, Gemini CLI, and MCP hosts.
- The same privacy, provenance, confirmation, and output rules on every host.

"Supports all agents" means any host that can read the project files, execute
the local scripts, or call the MCP server can use the core workflow. It does not
promise identical installation commands or identical plugin menus on every host.

## 9. Output Contract

One structured project must generate linked deliverables:

- Full teaching systems design report.
- Teacher guide and student learning sheet.
- Objective-assessment-strategy alignment matrix.
- Source and evidence record with citations and confirmation status.
- Subject-specific assessment rubric.
- Dick-Carey workflow diagram.
- Skill hierarchy or concept map where useful.
- Subject-specific process, experiment, argument, or decision diagram where
  useful.
- JSON and Markdown project records for review and revision.

The output status must remain `draft`, `completed_with_warnings`, or
`final_ready` according to the existing quality gates. No real student outcome,
score, or formative result may be inferred from an unverified description.

## 10. Visual And Interaction System

The existing DC Designer website is the confirmed visual reference. v3 should
extend its editorial report language rather than introduce a new visual theme:

- Warm paper background, ink typography, restrained rules, and the existing dark
  evidence section remain the visual foundation.
- Use the existing display/body font pair and spacing tokens in `site/styles.css`.
- New subject and stage controls should read as quiet work tools, not marketing
  cards or decorative dashboards.
- Source status, stage, and subject must be scannable through text and structure;
  color cannot be the only signal.
- Keep the existing navigation anchor offset tied to
  `--site-header-height` whenever section heights change.
- The public page should show one clear path: choose context -> inspect sources
  -> design -> confirm -> export.

The page-specific layout and interaction delta is recorded in
`design/pages/k12-multisubject-v3.md`.

## 11. Privacy, Copyright, And Public Packaging

- Keep `.dc-designer/` and teacher knowledge-base content local.
- Do not store student names, IDs, contact information, or identifiable grades.
- Do not publish teacher conversations, agent handoffs, private reports, caches,
  generated test outputs, or temporary screenshots.
- Ship only the minimum source, schemas, adapters, manifests, prompts, templates,
  and public documentation needed for a fresh user to run the project.
- Preserve source links, versions, hashes, and copyright scope for official and
  third-party material.

## 12. Release Plan And Gates

### v3.0.0

- Multi-subject project and source schemas.
- Nine stage-aware subject packs.
- National source registry and provenance fields.
- Shared prompt and native host adapter updates.
- Subject-aware reports, rubrics, diagrams, and review rules.

### v3.1.0

- Regional curriculum implementation packs.
- Textbook-version mappings selected by the teacher.
- More detailed local policy update workflow.

Before v3 release, the affected validation must cover schema compatibility,
source provenance, each subject's representative design case, stage naming,
privacy and copyright checks, all supported host adapters, and output integrity.
This is a major core change and therefore needs broader validation than a static
introduction-page edit.

## 13. Approval Boundary

This design is approved for implementation. The confirmed public v3 positioning is:

> **中国 K-12 九学科教学系统设计插件**

with national standards as the baseline and regional documents as optional
extensions. The v3 implementation includes the stage-aware source and
subject-pack contract, MCP and portable-script routing, subject-aware project
generation, review/revision/export paths, and public host documentation.
Release validation remains a separate gate.
