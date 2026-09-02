# Contributing to DC Designer

Thank you for helping improve DC Designer. The project is intentionally focused on China mainland K–12 Information Technology education and the Dick–Carey instructional systems design model, with host adapters for Codex, Claude Code, Gemini CLI, MCP, and portable project-file workflows.

## Before changing code

- Read the project scope and quality rules in `AGENTS.md` and `canon/`.
- Keep official sources, teacher-private materials,教材 or school materials, and AI inferences clearly separated.
- Do not add real student identity data, individual grades, private teacher documents, or copied restricted textbook content.

## Change scope

Keep the validation proportional to the changed surface:

- Site-only HTML, CSS, or static asset changes: use the local site preview and focused resource, navigation, and syntax checks.
- Core plugin, schemas, source rules, export logic, or shared configuration changes: run the relevant focused tests and the broader checks required by the affected contract.
- Host adapter or public packaging changes: run `python scripts/compatibility_check.py` and the affected site or release metadata checks; do not claim that this verifies every third-party host.
- Release work: follow `docs/release_checklist.md` and record external validation separately from local evidence.

Do not add generated exports, caches, screenshots containing private data, or conversation and agent handoff records to a pull request unless the change explicitly requires a public fixture or asset.

## Pull requests

Describe the user-visible behavior, the files changed, and the checks performed. For a visual change, include a before/after screenshot or a local preview URL when appropriate. Keep product copy and version boundaries aligned across `README.md`, all native host manifests, `manifest.json`, `prompts/`, and `site/`.
