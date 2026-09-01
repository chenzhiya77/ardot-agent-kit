#!/usr/bin/env python3
"""
技能包静态自检：引用解析、工具名有效性、frontmatter、README 数字声明、全仓数字口径。

为什么要有它：之前 `slides-workflow.md` 里 5 处 `../ardot-design-core/...`
全部指向不存在的目录（子目录里的文件要上两级），肉眼读完全看不出来 ——
这类断链只能靠「把路径真正解析一遍」发现。

用法:
    python scripts/check-refs.py            # 用内置工具快照，离线可用
    python scripts/check-refs.py --live     # 实测本机 MCP 核对快照是否过期（可只开一条通路）
    python scripts/check-refs.py -q         # 只报问题，不报通过项

--live 判工具名用的是「实测 ∪ 内置快照」，不是「仅实测」：打不通的通路不等于它没有
工具 —— 只开 A 时 B 独有的 create_design / open_design / save_tokens 会整批从实测里
消失，按「仅实测」判就把文档里对它们的正当引用全报成虚构工具名。只有一条通路在线时
差集只出信息行；两条都在线而快照与实测对不上，才是真问题。

退出码: 0 = 全过，1 = 有问题。可直接挂 git pre-commit。
"""

import argparse
import json
import os
import re
import sys
import urllib.request

# ⚠️ 中文 Windows 控制台默认代码页是 GBK，而输出里有 ✓/✗（U+2713/U+2717）——
# 编码不了的字符会让最后一句 print 抛 UnicodeEncodeError，于是「全部通过」
# 反而以非 0 退出，挂 pre-commit 时方向整个是反的。脚本自带输出编码，
# 不依赖调用者设 PYTHONIOENCODING。
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

# 2026-09-01 实测：通路 A(50501, 22) ∪ 通路 B(50551, 20) = 25 个工具
# （A 较 08-29 新增 fetch_styles；B 侧当日未运行，20 沿用 08-29 实测）
TOOL_SNAPSHOT = {
    "apply_variables", "batch_edit", "batch_read", "build_style_guide",
    "capture_layout", "capture_screenshot", "create_design", "create_new_page",
    "export_nodes", "export_variables", "fetch_component_lib", "fetch_editor_state",
    "fetch_file_info", "fetch_guidelines", "fetch_styles", "fetch_variables",
    "get_available_fonts", "html_to_ardot", "locate_available_space", "open_design",
    "register_assets", "save_tokens", "scan_exportable_resources",
    "search_style_guide", "upload_images",
}

# 已知不是工具名、但长得像工具名的东西（每次新增都要写清理由，免得以后重新排查）
ALLOWED_NON_TOOLS = {
    # 在「对上游内容的修正」表格里描述 bug 用的旧名
    "get_editor_state", "set_variables",
    # 上游存在但未对外暴露，文档里明确写了「别调用」
    "scan_all_unique_properties", "substitute_all_matching_properties",
    # 未暴露：fetch_styles 的描述里引用它做推荐调用顺序，但 tools/list 里没有
    "search_styles",
    # 宿主侧的 MCP 元工具（Qoder 桌面端惰性加载下所有 MCP 调用都走它），不是 Ardot 的工具
    "mcp_call",
    # 节点类型 / 布局模式，不是工具
    "icon_font", "hug_contents", "fill_container", "fixed_size",
}

# 行尾豁免标记：此行是**被引用的例子或历史叙述**，不是当前声明 —— 五类检查一起豁免
# （路径引用、示例工具名、以及第 5 项的数字口径，如引用官方旧文档的那句）。
# 例：| 技能根的 SKILL.md | `../` 上一级 | `../ardot-design-core/rules/…` | <!-- skip-ref-check -->
SKIP_MARKER = "<!-- skip-ref-check -->"

# 数字口径的唯一真值（2026-09-01 实测：A 由 tools/list 现测；B 沿用 08-29 实测）。
# 改这些数字时，把下面第 5 项检查扫出来的每一处一起改掉，别留下半新半旧。
CANON = {
    "totals": {"20", "22", "25"},    # 通路 A / 通路 B / 并集
    "ratios": {"19/22", "16/20"},    # A 接受 fileUrl 的工具数 / B 接受 fileId 的工具数
    "union": "25",                   # 并集
    "shared": "17",                  # 两通路共有
}

# 明显是路径或参数名，不是工具名
NOT_TOOL_RE = re.compile(r"(\.(md|json|sh)|_(dir|id|name|url|depth|only|size|type))$|^(get|set)_[a-z]+_(state|variables)$")


LIVE_PORTS = {50501: "通路 A · Ardot 客户端", 50551: "通路 B · WorkBuddy"}


def live_tools():
    """实测本机 MCP 通路，返回 (工具名并集, 成功应答的端口列表)。全不通 → (None, [])。

    端口名单列出来，是为了让调用方区分「这条通路没有这个工具」和
    「这条通路根本没应答」—— 后者不能拿来给文档定罪。
    """
    found = set()
    online = []
    for port in sorted(LIVE_PORTS):
        url = f"http://127.0.0.1:{port}/api/v1/mcp"
        sid = {}

        def post(payload, notify=False):
            req = urllib.request.Request(url, json.dumps(payload).encode(), method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json, text/event-stream")
            if sid.get("v"):
                req.add_header("Mcp-Session-Id", sid["v"])
            with urllib.request.urlopen(req, timeout=8) as r:
                body = r.read().decode()
                if r.headers.get("Mcp-Session-Id"):
                    sid["v"] = r.headers.get("Mcp-Session-Id")
                if notify:
                    return None
                if body.lstrip().startswith("{"):
                    try:
                        return json.loads(body)
                    except Exception:
                        pass
                for line in body.splitlines():
                    if line.startswith("data: "):
                        try:
                            return json.loads(line[6:])
                        except Exception:
                            pass
                return None

        try:
            post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "check-refs", "version": "1"}}})
            post({"jsonrpc": "2.0", "method": "notifications/initialized"}, notify=True)
            out = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            if out and "result" in out:
                found |= {t["name"] for t in out["result"]["tools"]}
                online.append(port)
        except Exception:
            continue
    return (found or None), online


def skill_root(md_file):
    """{SKILL_ROOT} = 含 SKILL.md 的那层（技能自己的根），不是 md 文件所在目录。"""
    d = os.path.dirname(md_file)
    while d.startswith(SKILLS):
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(md_file)


# 数字口径检查的范围：整个仓库的文本文件。
# 目录黑名单里 .workbuddy 是 WorkBuddy 侧的历史记忆转储，不随插件分发，
# 里面全是当时的旧数字，扫它只会自娱自乐。
CLAIM_SKIP_DIRS = {".git", ".workbuddy", "node_modules", "__pycache__"}
CLAIM_SKIP_EXTS = {".zip", ".png", ".jpg", ".ico", ".woff", ".woff2", ".pyc"}


def claim_files():
    """产出全仓参与数字口径检查的文本文件路径。取不到 UTF-8 内容的（二进制等）跳过。"""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in CLAIM_SKIP_DIRS)
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1] in CLAIM_SKIP_EXTS:
                continue
            full = os.path.join(dirpath, fn)
            try:
                text = open(full, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            yield full, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="实测本机 MCP，与内置快照取并集判工具名（用来核对快照是否过期）")
    ap.add_argument("-q", "--quiet", action="store_true", help="只报问题")
    args = ap.parse_args()

    live, online = live_tools() if args.live else (None, [])
    problems, oks, notes = [], [], []

    if live:
        # 判工具名的合法集 = 实测 ∪ 快照。没应答的通路不等于它没有工具 ——
        # 只按实测判，B 离线时文档里对 create_design 等三个工具的正当引用会整批
        # 变成「虚构工具名」（2026-09-02 实测：35 条假问题、exit 1）。
        tools = live | TOOL_SNAPSHOT
        offline = [p for p in sorted(LIVE_PORTS) if p not in online]
        source = f"实测 ∪ 内置快照（实测 {len(live)}，并集 {len(tools)}）"
        if len(online) < len(LIVE_PORTS):
            notes.append(
                f"--live 只连上 {len(online)} 条通路："
                + "、".join(LIVE_PORTS[p] for p in online)
                + "；未应答 " + "、".join(f"{p}（{LIVE_PORTS[p]}）" for p in offline)
                + " —— 它的独有工具用快照兜住，不判成问题")
        added = sorted(live - TOOL_SNAPSHOT)
        if added:
            problems.append(
                f"实测有 {len(added)} 个快照里没有的工具: {', '.join(added)}\n"
                f"    客户端新增了工具 —— 更新 TOOL_SNAPSHOT 与 CANON，"
                f"全仓口径检查会把连带要改的数字全列出来")
        gone = sorted(TOOL_SNAPSHOT - live)
        if gone:
            if offline:
                notes.append(
                    f"实测没见到 {len(gone)} 个快照里的工具: {', '.join(gone)}"
                    f" —— 未应答的通路上有它们属正常，故本轮不判问题")
            else:
                problems.append(
                    f"两条通路都应答，但快照里 {len(gone)} 个工具实测不存在: "
                    f"{', '.join(gone)}\n"
                    f"    已被移除或改名 —— 以 --live 实测清单校正 TOOL_SNAPSHOT 与 CANON")
    else:
        tools = TOOL_SNAPSHOT
        source = f"内置快照（{len(tools)} 个）"
        if args.live:
            notes.append("--live 一条通路都没连上（MCP 未运行？），本轮工具名改用内置快照判")

    for dirpath, _, filenames in os.walk(SKILLS):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            text = open(full, encoding="utf-8").read()
            sroot = skill_root(full)

            # 逐行处理，这样行尾的豁免标记才能生效
            lines = text.splitlines()
            for lineno, line in enumerate(lines, 1):
                skip = SKIP_MARKER in line

                # 1. 路径引用
                for m in re.finditer(r"`(\{SKILL_ROOT\}/[^`\s]+|\.\./[^`\s]+)`", line):
                    ref = m.group(1)
                    if ref.endswith("/"):      # 纯目录片段（如说明文字里的 `../`）跳过
                        continue
                    if skip:
                        continue
                    if ref.startswith("{SKILL_ROOT}/"):
                        target = os.path.join(sroot, ref[len("{SKILL_ROOT}/"):])
                    else:
                        target = os.path.normpath(os.path.join(dirpath, ref))
                    where = f"{rel}:{lineno}"
                    if os.path.exists(target):
                        oks.append(f"引用 {where} → {ref}")
                    else:
                        problems.append(
                            f"引用断链 {where}\n    写法: {ref}\n"
                            f"    解析为: {os.path.relpath(target, ROOT)}（不存在）")

                # 2. 工具名
                for m in re.finditer(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`", line):
                    name = m.group(1)
                    if name in tools or name in ALLOWED_NON_TOOLS or NOT_TOOL_RE.search(name):
                        continue
                    if skip:
                        continue
                    problems.append(
                        f"疑似工具名不在清单里 {rel}:{lineno} → `{name}`\n"
                        f"    若确认不是工具名，加进 scripts/check-refs.py 的 ALLOWED_NON_TOOLS")

    # 3. frontmatter
    for d in sorted(os.listdir(SKILLS)):
        p = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isfile(p):
            continue
        t = open(p, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
        if not m:
            problems.append(f"frontmatter 缺失: {d}")
            continue
        fm = m.group(1)
        if "name:" not in fm:
            problems.append(f"frontmatter 缺 name: {d}")
        if "description:" not in fm:
            problems.append(f"frontmatter 缺 description: {d}")
        leftover = [x for x in ("disable-model-invocation", "allowed-tools") if x in fm]
        if leftover:
            problems.append(f"frontmatter 残留宿主标志 {leftover}: {d}（外部 agent 会加载不了这个技能）")
        else:
            oks.append(f"frontmatter {d}")

    # 4. README 数字声明
    rd_path = os.path.join(ROOT, "README.md")
    if os.path.isfile(rd_path):
        rd = open(rd_path, encoding="utf-8").read()
        n_skill = sum(len(f) for d in os.listdir(SKILLS) if d.startswith("ardot-")
                      for _, _, f in os.walk(os.path.join(SKILLS, d)))
        n_core = sum(len(f) for _, _, f in os.walk(os.path.join(SKILLS, "ardot-design-core")))
        hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8"))
        n_hooks = len(hooks["hooks"])

        expected = [
            (f"{n_skill} 文件", f"README 应写「6 个包 {n_skill} 文件」"),
            (f"Hooks ({n_hooks})", f"README 应写「Hooks ({n_hooks})」"),
            (f"({n_core})", f"目录树里 core 应写 ({n_core})"),
        ]
        for token, hint in expected:
            if token in rd:
                oks.append(f"README 数字 {token}")
            else:
                problems.append(f"README 数字对不上: 缺「{token}」—— {hint}")

    # 5. 全仓数字口径
    #    为什么单独一项：客户端 08-29→09-01 从 21 升到 22，一次升级就把 6 处数字
    #    打成过期，而旧版只 walk skills/ 查路径与工具名、数字仅在 README 里比 ——
    #    于是「41 项全过」和「6 处过期数字」同时成立。盲区正是 bin/、scripts/、
    #    install.sh、docs 里的图，以及技能正文里「N / M 个工具」这种比例句。
    if str(len(TOOL_SNAPSHOT)) != CANON["union"]:
        problems.append(
            f"自检脚本自身不一致：union 口径 {CANON['union']} "
            f"但 TOOL_SNAPSHOT 实际 {len(TOOL_SNAPSHOT)} 个 —— 改了快照忘了改口径")
    else:
        oks.append(f"口径真值表与工具快照自洽（{len(TOOL_SNAPSHOT)}）")

    claim_rules = [
        # 总数类只认两位以上数字，免得「这 3 个工具」那种指量词被当成声明
        (re.compile(r"(\d{2,3})\s*个?\s*工具(?!列表|集)"), "total"),
        (re.compile(r"工具[:：]\s*(\d{2,3})\s*个"), "total"),
        (re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*个?\s*工具"), "ratio"),
        (re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})(?![^\n]*工具)"), "ratio"),
        (re.compile(r"并集\s*(\d{2,3})"), "union"),
        (re.compile(r"共有\s*(\d{2,3})"), "shared"),
    ]
    seen_claims = set()
    for full, text in claim_files():
        rel = os.path.relpath(full, ROOT)
        for lineno, line in enumerate(text.splitlines(), 1):
            # 裸比例只在讲目标文件或讲工具数量的句子里判，别处的 N/M 不是数字声明
            if SKIP_MARKER in line or not re.search(r"fileUrl|fileId|工具", line):
                continue
            for rule_re, kind in claim_rules:
                for m in rule_re.finditer(line):
                    if kind == "total":
                        value, phrase = m.group(1), m.group(0)
                        good = value in CANON["totals"]
                        hint = "应是 A=22 / B=20 / 并集=25 之一（改值请同步 CANON）"
                    elif kind == "ratio":
                        a, b = m.group(1), m.group(2)
                        value, phrase = f"{a}/{b}", m.group(0)
                        good = value in CANON["ratios"]
                        hint = "应是 A 的 19/22 或 B 的 16/20"
                    elif kind == "union":
                        value, phrase = m.group(1), m.group(0)
                        good = value == CANON["union"]
                        hint = f"并集应是 {CANON['union']}"
                    else:
                        value, phrase = m.group(1), m.group(0)
                        good = value == CANON["shared"]
                        hint = f"两通路共有应是 {CANON['shared']}"
                    key = (rel, lineno, value, kind)
                    if key in seen_claims:
                        continue
                    seen_claims.add(key)
                    if good:
                        oks.append(f"口径 {rel}:{lineno} → {phrase.strip()}")
                    else:
                        problems.append(
                            f"数字口径过期 {rel}:{lineno}\n"
                            f"    写法: {m.group(0).strip()}\n    {hint}")

    print("=" * 70)
    print(f"技能包自检   工具清单来源: {source}")
    print("=" * 70)
    for n in notes:
        print(f"\n提示: {n}")
    if not args.quiet:
        print(f"\n通过 {len(oks)} 项")
    if problems:
        print(f"\n发现 {len(problems)} 个问题：\n")
        for p in problems:
            print("  ✗ " + p + "\n")
        return 1
    print("\n全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
