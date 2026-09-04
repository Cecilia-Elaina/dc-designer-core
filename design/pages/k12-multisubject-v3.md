# Page Delta: K-12 Multi-Subject v3

Parent design system: `/DESIGN.md`
Status: approved for implementation
Surface: public product site and the first-run design entry

This delta adds the v3 multi-subject story to the existing DC Designer visual
language. It does not replace the confirmed editorial report-style site.

## Intended User Outcome

A K-12 teacher should understand the supported scope, choose a stage and subject,
see which official source layer will be used, and copy a portable start request
without learning the internal model or a host-specific installation command.

## Page Structure

### 1. Scope signal

Keep the existing hero language and report preview. Add one concise scope line:

```text
中国 K-12 九学科 · 从课标到课堂的 Dick-Carey 教学系统设计
```

Do not claim universal coverage of every K-12 course.

### 2. Subject and stage entry

Use one unframed work area with two grouped selectors:

- 学段: 小学 / 初中 / 普通高中
- 学科: 语文 / 数学 / 英语 / 物理 / 化学 / 生物学 / 历史 / 地理 /
  道德与法治 or 思想政治

The subject list must update after stage selection. Unavailable combinations are
not shown as active options. A teacher may still type a topic directly; the
system then asks for the missing stage or subject before selecting sources.

### 3. Source boundary

Show a compact source row directly beside the context entry:

```text
国家课标基线 · 版本 · 适用学段 · 查看来源
```

The source row must expose version and confirmation status. A candidate source
must be visibly different from a teacher-confirmed source. The page may link to
the official document, but must not display a long copied document excerpt as a
marketing surface.

### 4. Design modes

Retain the existing two modes:

- 课标约束快速设计
- 完整协同设计

Explain the difference through task outcome and time commitment, not model or
provider terminology. The mode choice should remain a work-tool decision, not a
large promotional card grid.

### 5. Deliverable preview

Reuse the existing report and diagram imagery. Add a small subject-aware caption
showing that the same project can produce:

```text
报告 · 评价量表 · 课标证据链 · 学科图 · 可编辑项目文件
```

The imagery must remain real project output. Do not create fake subject examples
until a representative artifact exists for that subject.

### 6. Copy action

The primary action remains “复制给任意智能体”. The copied prompt should include
the selected stage, subject, and topic when known, then ask the host to detect
available project-file, MCP, or native-plugin access. It must not silently claim
that installation is complete.

## Interaction Rules

- Stage selection filters subjects before source selection.
- Changing stage or subject clears incompatible source selections and explains
  what needs reconfirmation.
- Opening a source goes to the official link or the local source record; it never
  converts a candidate into a confirmed source.
- Every final design entry point preserves the existing sticky-header anchor
  offset through `--site-header-height`.
- Mobile layout stacks stage, subject, source, and mode in that order; no control
  may depend on color alone.
- The page has one primary action and one secondary action. Additional host
  instructions remain in the compatibility documentation.

## Content Rules

- Say “九学科” in public scope language.
- Say “道德与法治” or “思想政治” according to the selected stage.
- Say “官方来源候选” until the teacher confirms the source.
- Say “待实施” or “待验证” when no real classroom evidence exists.
- Do not say “自动完成所有教学设计” or “保证教学效果”.
- Do not expose provider names, hidden model details, or internal session IDs in
  the teacher-facing primary flow.

## Responsive And Accessibility Notes

- Preserve the existing desktop editorial composition and dark evidence section.
- On narrow screens, keep subject names and source status readable without
  horizontal clipping.
- Use native labels, keyboard-focus states, and text equivalents for every source
  status and subject state.
- Keep navigation anchors aligned with the actual header height after section
  changes; this is a release-blocking visual regression for the site.

## Implementation Handoff Boundary

Implementation follows the approved parent design system and decisions in
`design/DECISIONS.md`. The data contract, stage-aware subject registry and
representative end-to-end flow are implemented together with the remaining
subject adapters.
