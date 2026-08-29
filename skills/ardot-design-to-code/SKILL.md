---
name: ardot-design-to-code
description: "Use this skill for Ardot canvas tasks that convert a design into frontend code, or extract a design system / style guide from a website. Covers: design-to-code, design → HTML/CSS/JS, export as webpage, pixel-perfect reproduction, generate an Application from a design, slide transitions, responsive scaling; and website → design-guide / design-token extraction. Trigger phrases: convert design to code, design to HTML, export as webpage, pixel-perfect reproduction, design to App, generate Application, create design system from website, extract design tokens, 设计稿转代码, 转为前端代码, 生成HTML, 导出为网页, 一比一还原, 复刻设计稿, 设计稿出码, 设计稿转应用, 转应用, 网站风格转设计稿, 提取设计风格, 生成设计指南, 提取设计 token. Pairs with ardot-design-core (load it alongside)."
---

# Ardot Design-to-Code & Style Extraction

Domain workflows for **design → frontend code** conversion and **website → style-guide** extraction on the Ardot canvas.

> **The general workflow and hard rules live in `ardot-design-core`**, which goes with this skill. Follow `ardot-design-core` for the step sequence, schema, editing rules, effects, and screenshot verification. This skill carries the **specialized conversion/extraction workflows and implementation guidelines**.

## Specialized Workflows (follow strictly — do NOT improvise the procedure)

- **Design → frontend code** → `{SKILL_ROOT}/workflows/design-to-code-workflow.md` — design → HTML/CSS/JS, generate Application, to code, slide transitions, responsive scaling.
- **Website → style guide extraction** → `{SKILL_ROOT}/workflows/extract-style-guide-from-web.md` — pull a design guide / tokens from an existing website.
- **HTML → 设计稿（逆向）** → 见下方「逆向能力」。

---

## 逆向能力（仅通路 A：Ardot 客户端）

出码是把设计稿转成代码。反过来——**把现成网页变成可编辑的设计稿**——
通路 A 上也能做，且这三个工具是 A 独有的（`extract-style-guide-from-web.md` 未覆盖）：

| 工具 | 作用 |
|---|---|
| `register_assets` | 拿一对临时上传/下载 URL，供其它工具使用 |
| `html_to_ardot` | 把一个**已上传的远程 HTML 页面**转成当前页面上的可编辑图层 |
| `export_variables` | 把设计变量导出为可直接消费的代码 token（W3C Design Tokens 等格式） |

### 网页 → 设计稿（三步）

```
1. register_assets          → 拿到 uploadUrl / downloadUrl
2. 把 HTML 上传到 uploadUrl（curl -T / PUT）
3. html_to_ardot(downloadUrl) → 网页变成可编辑图层
```

适用场景：把竞品页面、参考站、自己的旧页面"扒"进 Ardot 改。
比从零重画快得多，且结构（布局、层级）是真实的。

⚠️ 转换结果需要人工/截图校验——自动转换的图层命名、分组、样式绑定通常不理想。

### 设计变量 → 代码 token

出码时若设计稿用了变量（tokens），别去手抄数值，
**优先 `export_variables`** 直接拿到结构化 token（含 W3C Design Tokens 格式）。
比 `fetch_variables` 更适合消费——它给的是能直接喂给样式系统的格式。

## Implementation Guidelines (load alongside a design-type guideline when generating code)

- `{SKILL_ROOT}/references/guidelines-code.md` — design-to-code implementation rules.
- `{SKILL_ROOT}/references/guidelines-tailwind.md` — Tailwind v4 implementation (load alongside `guidelines-code.md`).

> Files referenced by these workflows that live in the core skill are read from the **ardot-design-core** skill root — relative to this skill's own directory it lives at `../ardot-design-core/` (the sibling skill inside the same plugin). This includes `design-rules.md` etc. and the shared **tool-usage guides** (`tool-usage/batch-edit.md`, `tool-usage/apply-variables.md`), which now live in `ardot-design-core` because `batch_edit` / `apply_variables` are used by every Ardot task.
