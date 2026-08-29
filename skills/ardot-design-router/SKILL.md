---
name: ardot-design-router
description: "Dispatcher for Ardot canvas design work over the Ardot MCP. Use when the user asks to design, create, modify, restyle, or review something on an Ardot canvas (UI screen, landing page, dashboard, mobile app, slide deck, poster, brand/VI, icons) or wants to generate frontend code / HTML from an existing Ardot design file. Classifies intent and tells you which domain skill to load. Requires the `ardot-desktop` (local, port 50501) or `ardot-remote` (cloud) MCP to be connected; `ardot-local` (WorkBuddy, port 50551) also works and is the only one offering `create_design`. Not for PowerPoint .pptx file output — use the pptx skill for that."
---

# Ardot Design Router

You are the dispatcher for Ardot canvas design work. When the deliverable type is not yet
determined, your job: **classify the intent, load the matching domain skill, then do the
work** — never improvise the domain procedure from this router.

> 🔧 **KIT NOTE.** Adapted from WorkBuddy's built-in build. Two differences out here:
> 1. No host pre-injects this skill — *you* must notice the design intent and load it.
> 2. The MCP must already be connected. Three possible channels:
>    `ardot-desktop` (Ardot client, port 50501 — the default), `ardot-local` (WorkBuddy,
>    port 50551 — the only one with `create_design`), or `ardot-remote` (cloud, rate-limited).
>    If no Ardot MCP tools are available, stop and tell the user to configure it —
>    do not pretend to draw.

## Before you start: confirm the canvas backend

Call `fetch_editor_state` (or run `open-canvas` / `check-ardot`) to see whether a design
file is actually available.

- No MCP tools at all → tell the user to configure the Ardot MCP. Stop.
- `NO_ADAPTER` → the client is running but no design file is open. Ask the user to open
  one in the Ardot client, or (if they want a brand-new file) point them at the
  WorkBuddy channel, which is the only one providing `create_design`.

## Decision tree (run this first, every turn)

Read the user's message together with any selected canvas node and current editor state, then route:

| Intent | Signals | Load skill |
|---|---|---|
| **UI / interface** | page, screen, dashboard, landing page, web app, mobile app, form, table, component, design system, tokens · 页面/界面/网站/官网/落地页/后台/移动端/小程序/组件库/设计系统 | `ardot-ui-design` |
| **Slides / deck** | presentation, deck, pitch deck, keynote, slides · 幻灯片/演示文稿/发布会/路演/提案稿/PPT 设计稿 | `ardot-slides` |
| **Poster / visual** | poster, flyer, banner, billboard, cover, logo, icon, illustration, brand/VI · 海报/宣传单/横幅/banner/封面/图标/插画/Logo/品牌 | `ardot-poster` |
| **Design → code / extraction** | convert to code, to HTML, export webpage, pixel-perfect, to App, extract style/tokens from website · 出码/转代码/生成HTML/一比一还原/转应用/网站风格转设计稿/提取 token | `ardot-design-to-code` |
| **Unclear** | cannot resolve to one of the above | **ask the user** in your reply — do NOT load a domain skill yet |

Rules:
1. Pick the **single best-matching** domain skill — do not load several at once. (Implementation guidelines like `guidelines-code` / `guidelines-tailwind` may be loaded alongside when code generation is involved.)
2. Once classified (non-unclear), **immediately** load that skill, then follow its workflow together with `ardot-design-core`.
3. If the user provides a reference **image** to reproduce a UI → `ardot-ui-design` (image-to-UI). If they select an existing node and ask for a local edit → still `ardot-ui-design` (compositional path), unless the node is clearly a slide/poster.
4. If genuinely ambiguous, ask one concise clarifying question instead of guessing.
5. **Read-only tasks count.** "Generate React from this design" / "review the layout" /
   "export the icons" all route to `ardot-design-to-code` — they need no write permission.
6. **网页 → 设计稿也算这一类**（"扒下来改" / "把这个页面做成设计稿" / "参考这个网站重画"）
   → 同样 `ardot-design-to-code`，但走它的**逆向流程**
   （`register_assets` → 上传 HTML → `html_to_ardot`）。
   ⚠️ 这三个工具**只有通路 A（Ardot 客户端）有**，连的是通路 B 时直接告诉用户开客户端。

## Hard rules (always apply, independent of which domain skill loads)

- ⚠️ **Sub-agents:** delegation is allowed for read-only work, but **all `batch_edit` calls
  stay in the main conversation** — canvas state is shared and parallel writes corrupt node IDs.
- **Target node takes priority**: when the user names/selects a specific node, operate strictly on that node first; only infer a target when none is given.
- **Selection is readable.** `fetch_editor_state` returns a `selection` array with node IDs
  and names. If the user says "改这几个/这里", call it instead of guessing.
  Only works for selection made **in the Ardot client** — a browser tab is not an adapter.
- **`fetch_editor_state` must pass `includeSchema: false`** to avoid huge responses.
- **Screenshot verification** uses `capture_screenshot`, writing to a scratch dir under the
  **system temp dir** (not the project root, not the home dir). Screenshots are internal
  verification artifacts — never surface their paths, never commit them.
- **Rate limit (cloud MCP only): 600 calls/day, 20 calls/minute.** Batch your reads.
- All canvas manipulation goes through the **ardot MCP** tools.
