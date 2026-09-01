# Ardot MCP Tool Usage Guide — Complete Reference

This document provides end-to-end workflow examples. For design rules, property constraints, troubleshooting, and the full **Tiered Validation / Convergence Threshold** spec, see `design-rules.md`.

> **Three reminders** before reading the examples:
> 1. **File handling (see SKILL.md Step 0 for the full rule)** — 🔧 *port note:* on the
>    default Ardot-client channel (A) there is **no** `create_design` / `open_design`, and no
>    host injects an `<ardot_file_directive>`. Establish the target file from **the link the
>    user pastes**; if none was given, ask before any MCP call. Where the examples below say
>    `create_design` / `open_design`, substitute "user supplied the file link" and continue.
> 2. **Parallelize independent reads** — when a step contains multiple calls with no mutual data dependency, issue them in a single message as parallel tool calls; do not serialize them. The examples mark these with `(parallel, single message)`.
> 3. **Validation tiers** — `[T1]`/`[T3]`/`[T4]`/`[T5]` tags mark which validation tier applies to each `batch_edit`. Do **not** run full screenshot+layout after every batch. Cap corrective iterations at 2 per section.

## Ardot MCP Tool Usage Guide

## End-to-End Workflow Examples

### Example A: Creating a New Landing Page

```
Step 0 (message 1):
  [PORTED] Confirm the target file from the user's link
           (e.g. https://ardot.tencent.com/file/719793184410961).
           NO create/open tool exists on channel A.
  fetch_file_info  ← optional; cheap way to confirm the active file + your permission.

Step 1 — read existing state (skipped only for a brand-new empty file):
  # Fresh file: empty canvas, root "0:1", no variables yet → nothing to read.
  # Opened existing file: call the following (parallel, single message):
  #   fetch_editor_state(includeSchema: false)
  #   fetch_variables

Step 2: Creative vs. Compositional → creative (new landing page) → continue to Step 3.

Step 3: Load references/guidelines-landing-page.md → learn landing page design rules
        (Local file reads — no MCP calls.)

Step 4: search_style_guide(styleKeywords: "modern minimal website", colorKeywords: "...", typographyKeywords: "...", layoutKeywords: "...")
        (Single call — styleKeywords is required, English-only; review the returned candidates, then proceed to Step 5.)

Step 5: Review search_style_guide candidates → select best fit per domain
  build_style_guide(style: "...", color: 3, typography: "...", layout: "...")   ← 平铺顶层参数,各域传 index(数字)或 name(字符串)
  → receive complete design system

Step 6 (parallel, single message):
  # [PORTED] fetch_file_info was folded in here only to cover WorkBuddy's async
  #          create/open load window. With no create/open tool on channel A,
  #          call it in Step 0 or omit it.
  locate_available_space(width: 1440, height: 3000)

Step 7: batch_edit → page frame + hero scaffold (structural)      [T1]
        → capture_layout(heroId, problemsOnly: true)              (skip screenshot)
        batch_edit → hero content + styling (visual)              [T3]
        → capture_screenshot(nodeIds: [heroId])                   (skip layout)
        batch_edit → features section scaffold + content + style  [T4, section complete]
        → capture_screenshot + capture_layout(problemsOnly: true) (once)
        batch_edit → footer + CTA sections                        [T4, section complete]
        → capture_screenshot + capture_layout(problemsOnly: true) (once)
        IF any real issues accumulated → ONE batch_edit fixing all of them
        → re-run only the tier that flagged them
        (Max 2 fix iterations per section; ignore ≤4px spacing noise.)

Step 8: capture_screenshot(full page)                            [T5, final]
```

Notes:
- [PORTED] Round-trip budget on an existing file: Step 1 parallel reads → Step 4 `search_style_guide` → Step 5 `build_style_guide` → Step 6 `locate_available_space` = **4 MCP round-trips** before the first `batch_edit`. Search and build are inherently sequential (build depends on the search selection).
- **Budget against the cloud limit: 600 calls/day, 20 calls/minute.** A full page typically needs 4 reads + N `batch_edit` calls + 2–5 validation calls.
- Do not screenshot between T2 (pure content) or consecutive T3 batches — defer to the section boundary.
- Skip the in-Step-7 fix pass entirely if the T4 checks came back clean.

### Example B: Modifying an Existing Design

> Modify tasks are **non-generation** — Step 0 of `SKILL.md` is a no-op for this example. Go straight to the reads below.

```
Step 0: Ensure design file is open → skip if editor already has a file loaded
Step 1: fetch_editor_state(includeSchema: false) → check current state and selection
Step 2: batch_read(patterns: [{name: "Header"}]) → find target elements
Step 3: capture_layout(parentId: "headerId", maxDepth: 2) → mandatory pre-flight layout check
        If any child reports "Outside parent bounds":
          → parent is too small for existing + incoming children. Switch parent to HUG: {height: "hug_contents"}.
          → Do NOT calculate or set a numeric height — let the engine size it from children.
        If no overflow → parent has enough space; keep existing sizing, no change.
Step 4: batch_edit → apply the change from Step 3 + insert modifications (≤25 ops)
Step 5: capture_layout(parentId: "headerId", maxDepth: 2) → mandatory post-flight verify
```

### Example C: Global Style Update

> 🔧 **PORT NOTE — 原版示例引用了两个当前未暴露的工具。** `scan_all_unique_properties`
> 与 `substitute_all_matching_properties` 在 WorkBuddy 内部注册表里真实存在，但**当前版本
> 未对外暴露，调用会失败**。别调。改成下面这样：

```
Step 0: [PORTED] Confirm the target file from the user's link (no open/create tool on channel A)
Step 1: fetch_editor_state(includeSchema: false) → check current state
Step 2: batch_read(parentId: "rootFrame", readDepth: 3) → inventory nodes + current styles
Step 3a (preferred): apply_variables → redefine tokens; bound nodes update themselves
Step 3b (fallback):  batch_edit → Update ops in ≤25-op batches until all nodes covered
Step 4: capture_screenshot → verify the global changes            [T3]
        (No capture_layout — style substitutions don't change structure.)
```

### Example D: Setting Up Design Tokens

```
Step 0: [PORTED] Confirm the target file from the user's link (no create/open tool on channel A);
        skip only if you already verified the file this turn
Step 1: fetch_editor_state(includeSchema: false) → check current state
Step 2: fetch_variables → inspect existing variables
Step 3: apply_variables → create or update variable sets with Light/Dark modes
Step 4: batch_read(patterns: [{reusable: true}]) → find components to bind variables to
Step 5: batch_edit → bind variable references to component properties   [T2]
        (Token binding alone doesn't change visuals or structure — skip validation.
         If a subsequent visual batch follows, validate there instead.)
```

### Example E: Creating a Registration Form

```
Step 0: [PORTED] Confirm the target file from the user's link (no open/create tool on channel A)
Step 1: fetch_editor_state(includeSchema: false) → get available components
Step 2: batch_edit → container frame + title + inputs in ONE batch   [T4 small form]
  container=I(document, {type: "frame", name: "Registration", layout: "vertical", width: 400, height: "hug_contents(600)"})
  title=I("containerId", {type: "text", name: "Title", content: "Create Account", fontSize: 28, fill: "#18191C"})
  input1=I("containerId", {type: "ref", ref: "InputComponentId"})
  U(input1+"/label", {content: "First Name"})
  ... (remaining fields, submit button, all in the same batch_edit)
Step 3: capture_screenshot + capture_layout(problemsOnly: true)      (once)
Step 4: IF issues → ONE batch_edit fixing all → re-run same tier (max 2 iterations)
```

Notes:
- Small self-contained UIs like a form should be built in **one** batch when ≤25 ops allow, then validated once — not scaffolded, content-filled, and styled in separate round-trips.

