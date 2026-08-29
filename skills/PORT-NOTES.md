# PORT-NOTES — Ardot 画布技能（ardot-agent-kit）

给 agent 看的第一份文件。说明有三条 MCP 通路、各自的工具集、以及跟在 WorkBuddy 里用有什么不同。

> ⚠️ **工具数以实测为准，不以文档为准。** 官方文档写「18 个工具」已过时：
> 2026-08-29 实测 Ardot 客户端本地 MCP 返回 **21 个**。下面所有数字均为 `tools/list` 实测。

---

## 目录布局与路径（先读这段，否则找不到文件）

装上之后技能在插件里是**嵌套**的，不是平铺的：

```
~/.claude/skills/ardot-design/          ← 插件根
└── skills/
    ├── PORT-NOTES.md                   ← 本文件
    ├── ardot-design-core/              ← 通用规则（所有任务都要用）
    │   ├── rules/design-rules.md
    │   ├── rules/style-guide.md
    │   ├── rules/effects-guide.md
    │   ├── references/ardot-schema.md
    │   ├── tool-usage/batch-edit.md
    │   └── workflows/ardot-workflow.md
    ├── ardot-ui-design/                ← 领域技能（四选一）
    ├── ardot-slides/
    ├── ardot-poster/
    └── ardot-design-to-code/
```

**跨技能引用的路径写法 —— 按你所在文件的深度决定上几级：**

| 出发的文件 | 写法 | 例 |
|---|---|---|
| 技能根的 `SKILL.md`（`skills/ardot-X/SKILL.md`） | `../` 上一级 | `../ardot-design-core/rules/design-rules.md` | <!-- skip-ref-check -->
| 子目录里的文件（`skills/ardot-X/workflows/*.md`、`references/*.md`） | `../../` 上两级 | `../../ardot-design-core/rules/design-rules.md` | <!-- skip-ref-check -->

> 上表两行只是**示例**，故标了 `<!-- skip-ref-check -->`，
> `scripts/check-refs.py` 会跳过带这个标记的行。

```
skills/
├── ardot-design-core/          ← 目标
└── ardot-slides/               ← 技能根（SKILL.md 在这）→ 用 ../
    └── workflows/              ← 深一层（slides-workflow.md 在这）→ 用 ../../
```

> ⚠️ 上游原版写的是 `<ardot-design-core>/rules/design-rules.md` 这种**占位符**，
> 由宿主注入绝对路径，与文件深度无关。改成相对路径后就必须数清楚层级——
> 这是移植引入的坑，`slides-workflow.md` 曾因为统一写成 `../` 而全部指向不存在的目录。

`{SKILL_ROOT}` 指**当前技能自己的目录**（即 SKILL.md 所在的那一层），
**不是**当前 md 文件所在目录。Claude Code 里的等价写法是 `${CLAUDE_SKILL_DIR}`，两者同义。
所以它不用数层级——`{SKILL_ROOT}/references/xxx.md` 从技能内任何深度的文件里写都一样。 <!-- skip-ref-check -->

> 工作目录不影响这些路径 —— 它们都相对于技能自己的位置，不是相对于你的项目。

---

## 三条通路

| | A · Ardot 客户端本地 | B · WorkBuddy 内置 | C · 云端 |
|---|---|---|---|
| 端点 | `http://127.0.0.1:50501/api/v1/mcp` | `http://127.0.0.1:50551/api/v1/mcp` | `https://ardot.tencent.com/mcp` |
| MCP 服务名 | `ardot-desktop` | `ardot-local` | `ardot-remote` |
| 工具数 | **21** | **20** | 未实测（文档称 18） |
| 指定目标文件 | **`fileUrl`**（18/21 工具） | **`fileId`**（16/20 工具） | 未实测 |
| 依赖 | Ardot 客户端运行 | **WorkBuddy 运行** | 无 |
| 限速 | 无 | 无 | 600 次/天、20 次/分钟 |
| 官方承诺 | ✅ | ❌ 内部实现 | ✅ |

**默认用 A**（独立、官方承诺、工具最多）。需要 `create_design` 从零起稿时切 B。

> ⚠️ **两条通路指定文件的参数名不一样，别猜。** 完整规则见
> `ardot-design-core/SKILL.md` → Step 0。一句话版：
> **A 用 `fileUrl` 且只能在「客户端已打开的文件」之间挑；B 用 `fileId`，开多个时漏传会直接报
> `ROUTE_KEY_REQUIRED`。** 两个都打不开没打开的文件。

---

## 工具集差异（实测）

```
共有 17 个：
  apply_variables  batch_edit  batch_read  build_style_guide  capture_layout
  capture_screenshot  create_new_page  export_nodes  fetch_component_lib
  fetch_editor_state  fetch_file_info  fetch_variables  get_available_fonts
  locate_available_space  scan_exportable_resources  search_style_guide
  upload_images

仅 A（Ardot 客户端）4 个：
  export_variables     导出变量（W3C Design Tokens 等格式）
  fetch_guidelines     官方规范，8 主题（见下）
  html_to_ardot        HTML → 设计稿（配合 register_assets）
  register_assets      注册素材，换取临时上传/下载 URL

仅 B（WorkBuddy）3 个：
  create_design        新建设计文件
  open_design          按 URL 或 ID 打开已有文件
  save_tokens          保存 token

并集 24 个
```

> ⚠️ **A 独有的 4 个里，只有 `fetch_guidelines` 接进了工作流**
> （见 `ardot-design-core/SKILL.md` → Step 3）。
> `export_variables` / `html_to_ardot` / `register_assets` **仍只写在这份文档里**，
> 没有任何工作流调用——需要时你自己判断何时用。

### fetch_guidelines：8 个 topic 与本地文件一一对应

`fetch_guidelines(topic)` 可取 8 个值，与本地快照文件对应：

| topic | 本地快照 |
|---|---|
| `table` | `guidelines-table.md` |
| `landing-page` | `guidelines-landing-page.md` |
| `web-app` | `guidelines-web-app.md` |
| `mobile-app` | `guidelines-mobile-app.md` |
| `slides` | `guidelines-slides.md` |
| `posters` | `guidelines-poster.md`（文件名是单数） |
| `code` | `guidelines-code.md` |
| `tailwind` | `guidelines-tailwind.md` |

**在通道 A 上，优先调 `fetch_guidelines` 拿官方最新版**，本地那 8 份是从 WorkBuddy
安装包里拷出来的**当日快照**，可能过时。调不到（连的是 B/C、或报错）时再回退本地文件。

**结论**：两条路互补。要「从零起稿」只能用 B；要「HTML 转设计稿 / 读官方规范 / 导出变量」只能用 A。

---

## 怎么选

- **有现成稿子，要出码 / 改稿 / 导出** → A
- **从零开始画** → B（A 没有 `create_design`，建不了文件）
- **WorkBuddy 没开，又要从零画** → 先在 ardot.tencent.com 网页端手动新建，再用 A 接链接
- **没有本机客户端（远程环境）** → C

A 和 B 已同时注册到 Claude Code，可共存。

### ⚠️ 两个 server 同时连时的选择规则

同时连接时工具名会带前缀（`mcp__ardot-desktop__batch_edit` / `mcp__ardot-local__batch_edit`），
同名工具出现两次，**必须按用途选，不要随便挑一个**：

| 你要做什么 | 用哪个 |
|---|---|
| 读稿、出码、改稿、导出、HTML 转设计稿 | **`ardot-desktop`** |
| 读官方规范 `fetch_guidelines` | **`ardot-desktop`**（B 没有） |
| 从零新建文件 `create_design` | **`ardot-local`**（A 没有，唯一选择） |
| 按 ID 打开已有文件 `open_design` | **`ardot-local`**（A 没有） |

如果只打算操作已有稿子，**建议只启用 `ardot-desktop`**，避免工具列表里出现一堆重名项干扰判断。
需要新建文件时再把 `ardot-local` 打开。

---

## 与 WorkBuddy 内使用的三点差异

1. **没有内嵌画布面板。** 补法：跑 `open-canvas [fileId]`（插件已把它加进 PATH；
   若直接运行源码则用 `scripts/open-canvas.sh`）在浏览器打开。
   Ardot 支持多人实时协作，浏览器视图会随编辑实时刷新，当作你的"眼睛"。
2. **框选节点对话式改局部 —— 可用，但取决于你在哪框选。**
   - ✅ **在 Ardot 客户端里框选**：调 `fetch_editor_state`，返回的 `selection`
     会带节点 ID 和名称（2026-08-29 实测：`[{"id":"2:12","name":"Hero 主指标卡"}]`）。
     直接用它，别再让用户描述位置。
   - ❌ **在浏览器里框选**：浏览器标签页不是 MCP server 的适配器，
     选中事件传不回 agent。此时才需要 `batch_read` 按名字/ID 找。
3. **截图目录改为系统临时目录**（上游硬编码 `.workbuddy/screenshots`，会污染外部项目）。

> 🔑 **权限提示**：出码、审查、导出这类任务**只需要读**，`view-only` 权限就够。
> 可以放心把稿子以只读方式分享给协作者去做前端，不用担心他们改坏设计。

---

## 对上游内容的修正（与内置版不一致的地方）

这一节记的是**主动修掉的上游 bug**，不是移植适配。将来同步 WorkBuddy 新版时不要覆盖回去。

| 位置 | 上游原文 | 修正为 | 为什么 |
|---|---|---|---|
| `ardot-design-core/rules/design-rules.md` → Working with Design Variables | `get_editor_state` / `set_variables` | **`fetch_editor_state`** / **`apply_variables`** | 上游写的这两个工具名在 A、B 两条通路上**都不存在**（2026-08-29 `tools/list` 实测）。它正好在 token 绑定路径上，不修必然报 unknown tool |
| `ardot-design-core/workflows/ardot-workflow.md` → Example C | `scan_all_unique_properties` / `substitute_all_matching_properties` | `batch_read` 盘点 + `apply_variables` / `batch_edit` 分批 Update | 见下方「未暴露的工具」 |

---

## 未暴露的工具（别调用）

`scan_all_unique_properties`、`substitute_all_matching_properties`

⚠️ **当前版本未对外暴露，调用了会失败。** 它们并非虚构——WorkBuddy 内部注册表有 28 条、
只暴露 20 条，这两个就在未暴露的 10 条里。

（`ardot-workflow.md` 的 Example C **原版曾引用它们**，现已替换为
`batch_read` 盘点 + `batch_edit` 分批 Update / `apply_variables`。若你读的是 WorkBuddy
原版技能，会看到旧写法——那是上游的遗留，按本文件为准。）**别调用。**

全局样式变更的替代做法：`batch_read` 盘点 → `batch_edit` 分批 Update（每批 ≤25 op）；
主题级改动优先 `apply_variables` 改 token，绑定的节点会自动更新。

---

## 通道 A 的附加说明

- Ardot 客户端自带**图形化 MCP 配置入口**（首页右上角），可一键给各 agent 启用，
  比本 kit 的脚本更官方。本 kit 的 `install.sh` 只是把它自动化。
- 客户端必须**打开着设计文件**才有适配器：`/api/v1/health` 里 `adapters` 为 0 时，
  画布类工具会报 `NO_ADAPTER`。
- 健康检查返回形如 `{"version":"0.0.0",...,"connections":{"mcpServers":N,"adapters":M}}`
  —— 注意 A 没有 `status` 字段，B 才有。`adapters` = **当前打开着的设计文件数**
  （2026-08-29 实测 A=1、B=2）。它决定要不要显式传文件参数。
- **`fileUrl` 的 host 被忽略**，以下写法实测等价（都是只读 `fetch_file_info`）：
  ```
  https://ardot.tencent.com/file/<id>     ← 用户粘贴的网页版链接，可直接原样传
  cocraft://localhost/file/<id>           ← 客户端内部返回用的 scheme
  <id>                                    ← 裸 ID 也收
  ```
- **`fileUrl` 打不开没打开的文件**：传一个未打开的 ID 得到
  `NO_ADAPTER: Target adapter not connected`（不是「列出可选文件」）。
  它只在 `adapters` 里已存在的文件之间做选择。

> ⚠️ **待验证**：A 的 `adapters` 当前只有 1，所以「开多个文件时工具会返回可选列表让你挑」
> 只是参数描述里的承诺，**尚未实测**。下次客户端里开了 2 个以上文件时补测：
> `fetch_file_info` 不传参数，看是返回列表还是报错。

## 排障

| 现象 | 原因 / 处理 |
|---|---|
| 连接被拒 | 对应客户端没运行，或端口变了。跑 `scripts/detect-ardot.sh`（先探 50501，再探 50551，都没有才扫描 50500–50570） |
| `NO_ADAPTER` | 两种可能：① 客户端没打开任何设计文件（`adapters: 0`）——打开一个再试；② 你传了 `fileUrl`/`fileId`，但那个文件**没在客户端里打开**——`fileUrl` 只能在已打开的文件间选择，打不开新文件 |
| `ROUTE_KEY_REQUIRED: Unable to resolve route key in strict mode` | 通路 B 上开着多个文件却没传 `fileId`。**每次调用都带上 `fileId`** |
| `create_design` 报 unknown tool | 你连的是 A 或 C，切到 B |
| `html_to_ardot` 报 unknown tool | 你连的是 B 或 C，切到 A |
| 工具数不对 | 连错端口。A=21，B=20 |

```bash
curl http://127.0.0.1:50501/api/v1/health    # A
curl http://127.0.0.1:50551/api/v1/health    # B（含 "status":"ok"）
```
