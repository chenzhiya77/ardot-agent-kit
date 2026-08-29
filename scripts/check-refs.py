#!/usr/bin/env python3
"""
技能包静态自检：引用解析、工具名有效性、frontmatter、README 数字声明。

为什么要有它：之前 `slides-workflow.md` 里 5 处 `../ardot-design-core/...`
全部指向不存在的目录（子目录里的文件要上两级），肉眼读完全看不出来 ——
这类断链只能靠「把路径真正解析一遍」发现。

用法:
    python scripts/check-refs.py            # 用内置工具快照，离线可用
    python scripts/check-refs.py --live     # 实测本机 MCP（50501 / 50551），以实测为准
    python scripts/check-refs.py -q         # 只报问题，不报通过项

退出码: 0 = 全过，1 = 有问题。可直接挂 git pre-commit。
"""

import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

# 2026-08-29 实测：通路 A(50501, 21) ∪ 通路 B(50551, 20) = 24 个工具
TOOL_SNAPSHOT = {
    "apply_variables", "batch_edit", "batch_read", "build_style_guide",
    "capture_layout", "capture_screenshot", "create_design", "create_new_page",
    "export_nodes", "export_variables", "fetch_component_lib", "fetch_editor_state",
    "fetch_file_info", "fetch_guidelines", "fetch_variables", "get_available_fonts",
    "html_to_ardot", "locate_available_space", "open_design", "register_assets",
    "save_tokens", "scan_exportable_resources", "search_style_guide", "upload_images",
}

# 已知不是工具名、但长得像工具名的东西（每次新增都要写清理由，免得以后重新排查）
ALLOWED_NON_TOOLS = {
    # 在「对上游内容的修正」表格里描述 bug 用的旧名
    "get_editor_state", "set_variables",
    # 上游存在但未对外暴露，文档里明确写了「别调用」
    "scan_all_unique_properties", "substitute_all_matching_properties",
    # 节点类型 / 布局模式，不是工具
    "icon_font", "hug_contents", "fill_container", "fixed_size",
}

# 行尾豁免标记：文档里的**示例**路径 / 示例工具名不是真实引用，加上它跳过该行。
# 例：| 技能根的 SKILL.md | `../` 上一级 | `../ardot-design-core/rules/design-rules.md` | <!-- skip-ref-check -->
SKIP_MARKER = "<!-- skip-ref-check -->"

# 明显是路径或参数名，不是工具名
NOT_TOOL_RE = re.compile(r"(\.(md|json|sh)|_(dir|id|name|url|depth|only|size|type))$|^(get|set)_[a-z]+_(state|variables)$")


def live_tools():
    """实测本机两条 MCP 通路，返回工具名并集。拿不到就返回 None。"""
    found = set()
    for port in (50501, 50551):
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
        except Exception:
            continue
    return found or None


def skill_root(md_file):
    """{SKILL_ROOT} = 含 SKILL.md 的那层（技能自己的根），不是 md 文件所在目录。"""
    d = os.path.dirname(md_file)
    while d.startswith(SKILLS):
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(md_file)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="实测本机 MCP 取工具清单")
    ap.add_argument("-q", "--quiet", action="store_true", help="只报问题")
    args = ap.parse_args()

    tools = live_tools() if args.live else None
    source = "实测" if tools else "内置快照"
    if not tools:
        tools = TOOL_SNAPSHOT

    problems, oks = [], []

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

    print("=" * 70)
    print(f"技能包自检   工具清单来源: {source}（{len(tools)} 个）")
    print("=" * 70)
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
