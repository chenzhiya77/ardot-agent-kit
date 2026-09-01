---
name: ardot-design-core
description: "Foundational workflow and hard rules shared by ALL Ardot canvas design tasks (UI screens, slides, posters, design systems, design-to-code). This skill carries the canvas schema, editing principles, the standard step-by-step workflow, visual style guide, and composite effects. It is loaded alongside a domain-specific Ardot skill (ardot-ui-design / ardot-slides / ardot-poster / ardot-design-to-code). It does NOT cover any single deliverable type on its own — always pair it with the matching domain skill. Not for PowerPoint .pptx file output (that is the pptx skill)."
---

# Ardot Design Core

Foundational workflow and hard rules for completing design tasks on the Ardot canvas via the ardot MCP server. **This skill is the shared base** — load it together with one domain skill (UI design / slides / poster / design-to-code). All canvas manipulation MUST go through ardot MCP tools.

> This skill owns **how** to work the canvas (workflow, schema, rules, effects). The paired domain skill owns **what** the deliverable should look like (domain guidelines). When the two seem to overlap, follow the domain skill for visual/layout decisions and this skill for tool usage and the step sequence.

## Reference Files

Load on demand based on task type:

| File | When to load |
|------|--------------|
| `{SKILL_ROOT}/references/ardot-schema.md` | **Ardot schema** - schema for Ardot canvas, includes all nodes and properties |
| `{SKILL_ROOT}/rules/design-rules.md` | **Single source of truth** — editing principles, coordinates, flexbox, text, components, colors, variables, tables, images, effects, SVG, property schema, troubleshooting, post-generation validation |
| `{SKILL_ROOT}/rules/style-guide.md` | Visual style guide — typography, color, layout, surface treatment, variance levels, forbidden AI patterns, bento grid |
| `{SKILL_ROOT}/rules/effects-guide.md` | Composite visual effects: glassmorphism, neon glow, metallic, glow border, iridescent, neumorphism — loaded automatically in Step 7 |
| `{SKILL_ROOT}/workflows/ardot-workflow.md` | End-to-end workflow examples (create, modify, global style update, tokens, form) and detailed operation syntax |
| `{SKILL_ROOT}/tool-usage/batch-edit.md` | `batch_edit` tool usage guide — load anytime `batch_edit` is used (applies to every Ardot task) |
| `{SKILL_ROOT}/tool-usage/apply-variables.md` | `apply_variables` tool usage guide — load anytime `apply_variables` is used (applies to every Ardot task) |
| `{SKILL_ROOT}/tool-usage/search-style-guide.md` | `search_style_guide` tool usage guide — load before Step 4 (English-only keywords, per-domain selection protocol) |
| `{SKILL_ROOT}/tool-usage/build-style-guide.md` | `build_style_guide` tool usage guide — load before Step 5 (selection rules, returned-system authority, post-build adjustment) |

> Domain-specific guidelines (web-app / landing-page / mobile-app / table / slides / poster / code / tailwind) and specialized workflows (slides, design-to-code, style extraction) live in the paired domain skill that goes with this one — load them from that skill's `{SKILL_ROOT}`.

## Preparation: (IMPORTANT: Establish the Design File Context)

Before any canvas operation, know **which** Ardot design file you are working on.
See **Standard Workflow → Step 0** below.

> 🔧 **KIT NOTE.** Upstream assumed a host would inject an `<ardot_file_directive>` and
> that `create_design` / `open_design` always exist. **Neither holds out here** on the
> default Ardot-client channel. Step 0 below replaces that logic.

## Mandatory Rules

> ⚠️ **SUB-AGENTS (relaxed for external agents).** Upstream banned delegation outright.
> Out here delegation is permitted, but Ardot tool calls are stateful and share one canvas
> session — splitting writes across parallel sub-agents risks interleaved edits and corrupted
> node IDs. You *may* delegate read-only work (design analysis, asset inventory).
> **Keep every `batch_edit` in the main conversation.**

> ⛔ **HARD RULE — OUTPUT LANGUAGE.** When the user has not explicitly specified a language, all generated on-canvas content (titles, body copy, labels, captions, annotations, etc.) MUST default to the language of the user's prompt, preserving any embedded English / foreign-language terms exactly as written (do not translate them). When the user explicitly specifies a target language (e.g., "use English", "用日文"), default all generated content to that language instead. This rule applies to every textual element produced on the design canvas.
>
> 🔔 **MANDATORY PRE-GENERATION ANNOUNCEMENT — NON-NEGOTIABLE.** The moment the design language is determined and BEFORE issuing the first content-producing `batch_edit`, you MUST send the user a one-line notice stating which language the on-canvas content will use (e.g., `本次设计稿内容将使用中文生成` / `Generating the design content in English`). This announcement is REQUIRED on every single design task — never skip it, never defer it, never bury it inside other text.

## Standard Workflow

### Step 0: Establish the Design File Context

> 🔧 **PORT NOTE.** Upstream relied on `create_design` / `open_design` plus a host-injected
> `<ardot_file_directive>`. **The default Ardot-client channel (A) has neither.**
> (`create_design` / `open_design` exist only on the WorkBuddy channel (B).)
> So out here you establish file context from **the link the user gives you**, not by tool call.
> Full channel comparison: `../PORT-NOTES.md`.

**Decision logic — in order:**

1. **The user gave a file URL or ID** (e.g. `https://ardot.tencent.com/file/719793184410961`
   or bare `719793184410961`) → treat it as the **intended** target and **verify it**:
   call `fetch_file_info`, compare the returned file ID / URL against the link,
   - **Match** → proceed to Step 1.
   - **Mismatch** → **stop and say so.** On channel A the link does *not* select a file;
     every tool acts on whatever is open in the Ardot client. Ask the user to open that
     file in the client, then re-verify. Never silently operate on the wrong file.
   **Do not call any open/create tool** to "apply" the link — none exists on channel A.
2. **No link, and this turn you already worked on a file** → skip Step 0.
3. **No link, read-only task** (generate code from a design, review layout, export assets)
   → **ask the user for the file link before doing anything.** There is no way to discover
   or list files. Running `open-canvas` may reveal the currently active file.
4. **No link, and the user wants a brand-new file** → the Ardot-client channel cannot create
   one. Either (a) ask the user to create it in the Ardot client / web app and paste the link,
   or (b) if the WorkBuddy channel (B) is connected, use its `create_design`.

> ⛔ **HARD RULE — never invent a file-creation tool.** On channel A there is no
> `create_design`, `open_design`, or `save_tokens`. Calling them fails. If a new file is
> needed, ask the human.

> ✅ **Always verify before drawing.** Call `fetch_file_info` / `fetch_editor_state` first
> and check the result against what the user asked for:
> - `NO_ADAPTER` → no design file is open in the Ardot client. Ask the user to open one.
> - **File ID differs from the user's link** → you are pointed at a different file.
>   Stop and tell the user; on channel A you cannot switch targets by passing an ID.

> 🎯 **Targeting a file: `fileUrl` on channel A, `fileId` on channel B.** The two channels
> use different parameter names — do not guess.
>
> | | 参数名 | 覆盖工具 | 只开 1 个文件时 | 开多个且未指定 |
> |---|---|---|---|---|
> | **A** | `fileUrl` | **19 / 22**（除 `build_style_guide` `search_style_guide` `fetch_guidelines`，这 3 个与文件无关） | 可省略，自动命中 | 按工具描述会返回可选文件列表让你挑 |
> | **B** | `fileId` | 16 / 20（`open_design` 两者都收） | — | 实测直接报 `ROUTE_KEY_REQUIRED` |
>
> **A 的 `fileUrl` 要点**（2026-08-29 实测）：
> - host 部分被忽略，三种写法都接受：`https://ardot.tencent.com/file/<id>`、
>   `cocraft://localhost/file/<id>`、裸 `<id>`。所以**用户粘贴的网页版链接可以直接传**。
> - 它只在**客户端里已经打开的文件之间做选择**——**不能**打开没打开的文件。
>   传一个未打开的 ID 会得到 `NO_ADAPTER`，此时只能让用户在客户端里打开。
> - ⚠️ 未验证项：当前 A 只开了 1 个文件（`/api/v1/health` → `adapters: 1`），所以「开多个时
>   返回列表让你挑」只是工具描述的承诺，尚未实测。若真遇到，按工具返回的文件列表挑。
>
> **B 更严格**：当前开着 2 个文件时，不传 `fileId` 直接报
> `ROUTE_KEY_REQUIRED: Unable to resolve route key in strict mode`。开多个文件时**每次调用都要传**。

> 🔀 **Channel B (WorkBuddy) addendum — applies only when you are on channel B**
> (MCP registered as `ardot-local`, `http://127.0.0.1:50551/api/v1/mcp`). Channel B *does*
> expose `create_design` / `open_design`, so two upstream hard rules come back into force
> that channel A never needed. Do not skip them — they are what prevents duplicate files:
>
> ⛔ **At most ONE `create_design` / `open_design` per task.** The instant the call is issued,
> the file is considered created/opened. **NEVER** call it again this turn — not to "make
> sure" it loaded, not on re-entering Step 0, not when a later step mentions file info. The
> only way to confirm the file or get its id is `fetch_file_info`.
>
> ⛔ **Async load gate.** The file loads asynchronously. After that single call, **wait** for
> the ready context update before any other MCP call — waiting means waiting, not re-issuing
> the call. Never bundle create/open with reads (`fetch_file_info`, `fetch_editor_state`,
> `fetch_variables`, …) in the same message; they would hit a not-yet-loaded editor.
>
> ⏱ **`fetch_file_info` timing on channel B.** `open_design` → call it right after the file
> is ready (before Step 1 reads). `create_design` → **defer** it to the Step 6 parallel
> batch; Steps 1–5 are local reasoning / file reads that naturally cover the async load
> window, so by Step 6 the file is ready.

> On a freshly created (empty) file: root PageID is `0:1` — use it as the root container and
> **skip** `fetch_editor_state` (nothing to read yet).

### Step 1: Read Existing State (parallel, conditional)

Read whatever state is relevant to the task. **Issue all independent reads in a single message as parallel tool calls** — do not serialize them.

| Scenario | What to call | Notes |
|---|---|---|
| Freshly created empty file | **nothing** | Empty canvas — root is `0:1`, no variables yet. Skip Step 1, go straight to Step 2. |
| Opened existing file / file already loaded | `fetch_editor_state({includeSchema: false})` + `fetch_variables` | Parallel in one message. |
| Task must match existing paint / font / effect values (restyle, design-to-code, style audit) | **plus** `fetch_styles` — omit `styleIds` to list all, or narrow with `styleTypes: ["FILL"]` | Same message, parallel. Shared styles are a **separate store from variables** — `fetch_variables` does not cover them. An empty file returns `styles: []` with an `issue` note; that is a normal empty result, not a failure. |
| Pure modification (file already loaded, target known) | The above **plus** any of `batch_read` / `capture_layout` / `capture_screenshot` as needed | All parallel in one message. |

### Step 2: Creative vs. Compositional

- **Creative** (new screen, page, dashboard, restyle) → proceed to Step 3
- **Compositional** ("add a button", "supplement a module", "move this") → skip to Step 6 and load `design-rules.md`. Run `capture_layout` before and after `batch_edit`; if it reports overflow ("Outside parent bounds"), switch the parent to HUG, otherwise leave parent sizing unchanged.

### Step 3: Load Design Guidelines

Load the **domain guideline(s)** from the paired domain skill that goes with this core skill (UI design / slides / poster / design-to-code). Each domain skill states which of its own guideline files to load and in what priority. `guidelines-code.md` / `guidelines-tailwind.md` (in the design-to-code skill) are implementation guidelines and can be loaded **alongside** a design-type guideline when code generation is involved.

> 🔧 **PORT NOTE — 优先用官方活版本（仅通路 A）。**
> 本地那 8 份 `guidelines-*.md` 是从 WorkBuddy 安装包里拷出来的**快照**，可能过时。
> 在通路 A（Ardot 客户端）上，改用 `fetch_guidelines(topic)` 直接取官方最新版：
>
> | topic | 本地快照 |
> |---|---|
> | `table` `landing-page` `web-app` `mobile-app` `slides` `code` `tailwind` | 同名 `guidelines-<topic>.md` |
> | `posters` | `guidelines-poster.md`（文件名单数） |
>
> 做法：**先调 `fetch_guidelines`**；若工具不存在（连的是 B/C）或调用报错，
> 再回退读本地快照。两条路都别跳过——规范是硬约束，不是参考。

### Step 4: Search Style Guide

**Before calling, load `{SKILL_ROOT}/tool-usage/search-style-guide.md`** — it covers the English-only keyword requirement and the per-domain selection protocol.

Call **`search_style_guide`** once. **`styleKeywords` is required** and must be English-only (the catalog rejects non-ASCII) — build it from deliverable type + industry + visual style names (e.g. `"fitness app dashboard modern data-dense"`). Optionally add `colorKeywords` / `typographyKeywords` / `layoutKeywords` / `sceneKeywords` / `compositionKeywords`; each optional param falls back to `styleKeywords` when omitted, and `domain` limits the search to a single domain. Extract keywords from the user's request for each domain. Be generous — more relevant keywords lead to better search coverage. The tool's own input schema is authoritative — if a parameter is rejected, follow the schema. Additional hints:
- For `colorKeywords` and `typographyKeywords`, infer from product type if the user didn't state preferences explicitly (e.g., spa → warm/calm/serif; luxury brand → elegant/serif)
- Pass `true` as `styleKeywords` to get the full catalog if no relevant keywords can be extracted

Review the returned candidates, then proceed to Step 5.

### Step 5: Build Style Guide

**Before calling, load `{SKILL_ROOT}/tool-usage/build-style-guide.md`** — it covers the selection rules, the returned-system authority, and the post-build adjustment constraints.

Review the candidates returned by `search_style_guide` and pick the closest one per domain. Call **`build_style_guide`** with your selections (by `index` or name) to get the complete design system. If a picked candidate did not fully match, adjust specific token values on the build result rather than re-searching.

### Step 6: Locate Available Space + Inspection (parallel)

Issue these as **a single parallel batch** in one message — they have no mutual dependency:

- **`fetch_file_info`** — optional; confirms the active file and your permission on it. Cheap; include it when you have not yet verified access.
- **`locate_available_space({width, height})`** — required for new top-level screens; skip for pure modification tasks. Never overlap existing content.
- **Inspection calls** (only if modifying existing design and not already covered in Step 1): `batch_read` (find by pattern/ID, `readDepth: 3` for component structure), `capture_layout` (detect problems), `capture_screenshot` (visual verify).

Skip any sub-call that doesn't apply to the current task.

> If a follow-up read depends on this batch's result (e.g. `batch_read({readDepth: 3})` targeting a component discovered via an earlier `batch_read`), issue it as a separate message afterward. Most tasks don't need that.

### Step 7: Execute Design

**Before drawing, ALWAYS load this guide** (it contains critical parameter formats that differ from standard expectations):
- `{SKILL_ROOT}/rules/effects-guide.md` — correct formats for DROP_SHADOW (showShadowBehindNode), BACKGROUND_BLUR (blurType), gradients, neumorphism

`batch_edit` with ≤ 25 ops per call. Build order: **structure → content → style → verify**. Ops: **I()** Insert, **U()** Update, **C()** Copy, **M()** Move, **D()** Delete, **G()** Image. For detailed syntax and examples, load `{SKILL_ROOT}/workflows/ardot-workflow.md`. Load `{SKILL_ROOT}/tool-usage/batch-edit.md` whenever `batch_edit` is used and `{SKILL_ROOT}/tool-usage/apply-variables.md` whenever `apply_variables` is used.

### Step 8: Validate

Follow the **Post-Generation Validation Pattern** in `design-rules.md`. Use **tiered validation** — pick the lightest check that matches what the batch changed (T1 structural → `capture_layout` only; T2 content → skip; T3 visual → `capture_screenshot` only; T4 section-complete → both once; T5 final page → one screenshot). **Do not run full dual-verification after every batch_edit.** Enforce the convergence threshold: **max 2 fix iterations per section**, ignore ≤4px spacing noise, no subjective re-polishing once the section matches spec.

## Screenshot Verification (mandatory)

Use `capture_screenshot` with a `screenShotDir` under the **system temp dir**
(e.g. `$TMPDIR/ardot-verify/`; in Node `path.join(os.tmpdir(), "ardot-verify")`).

> 🔧 **KIT NOTE.** Upstream hard-codes `".workbuddy/screenshots"` relative to the project
> root — that would litter an unrelated repo out here. Screenshots are internal verification
> artifacts: never surface their paths, never write them into the project or home dir,
> never commit them.

> 🔧 **KIT NOTE — live canvas.** Out here you have no embedded canvas panel. After (and
> periodically during) a task, run the kit's `scripts/open-canvas.sh` to open the file in the
> browser. Ardot supports real-time multi-user collaboration, so the browser view refreshes
> as you edit — that is your "eye".
