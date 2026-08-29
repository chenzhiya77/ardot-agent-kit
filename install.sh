#!/usr/bin/env bash
# Ardot Agent Kit —— 一键安装
#
# 做三件事：
#   1. 探测本机的 Ardot MCP server（先 127.0.0.1:50501 Ardot 客户端，再 50551 WorkBuddy）
#   2. 把它注册到 Claude Code
#   3. 安装 6 个画布设计技能包
#
# 用法: ./install.sh [--skills-only]
#   --skills-only  跳过 MCP 注册，只装技能（两个客户端都没开时用）
#
# 注：若用 Claude Code 插件方式安装（拷到 ~/.claude/skills/ardot-design/），
#     MCP 由插件的 .mcp.json 自动注册，本脚本可只用于非插件场景。
#
# 注：本脚本是「非插件」退路。走插件方式时不要用它在 ~/.claude/skills/ 下平铺安装，
#     否则会和插件里的 6 个技能重名；直接 cp 到 ~/.claude/skills/ardot-design/ 即可。

set -uo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$KIT_DIR/skills"

# 服务名按实际探测到的通路决定（在下面探测之后赋值）。
# 命名必须与 skills/PORT-NOTES.md 一致，否则 agent 会按错的工具集行动：
#   50501 = 通路 A → ardot-desktop（21 工具，无 create_design）
#   50551 = 通路 B → ardot-local  （20 工具，有 create_design）
SERVER_NAME=""
CHANNEL=""
CHANNEL_LABEL=""
CHANNEL_DEPENDENCY=""

SKILLS_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --skills-only) SKILLS_ONLY=1 ;;
    *) echo "未知参数: $arg"; exit 1 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
step() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
err()  { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; }

# ---------------------------------------------------------------- 1. 探测端口
PORT=""
if [ "$SKILLS_ONLY" -eq 0 ]; then
  step "探测 Ardot MCP server"
  if command -v curl >/dev/null 2>&1; then
    PORT="$("$KIT_DIR/scripts/detect-ardot.sh" -q)" || PORT=""
  else
    warn "未找到 curl，跳过探测（必须手动指定端口）"
  fi

  if [ -n "$PORT" ]; then
    ok "找到服务: http://127.0.0.1:${PORT}/api/v1/mcp"
  else
    warn "未检测到运行中的 Ardot MCP server"
    warn "→ 需要先启动 Ardot 客户端（端口 50501）或 WorkBuddy（端口 50551）"
    warn "  并打开一个设计文件，MCP server 才会随之可用"
    warn "→ 现在只装技能。装完后重跑本脚本完成 MCP 注册；"
    warn "  或改用云端模式（ardot-remote，工具数未实测）：见 README「三条 MCP 通路」"
    SKILLS_ONLY=1
  fi
fi

# 未探测到时默认按通路 A（Ardot 客户端 50501）
MCP_URL="http://127.0.0.1:${PORT:-50501}/api/v1/mcp"

# 按端口确定通路、服务名与依赖的宿主进程
case "${PORT:-50501}" in
  50551)
    CHANNEL="B"; CHANNEL_LABEL="WorkBuddy 内置"
    SERVER_NAME="ardot-local"
    CHANNEL_DEPENDENCY="WorkBuddy"
    ;;
  *)
    CHANNEL="A"; CHANNEL_LABEL="Ardot 客户端"
    SERVER_NAME="ardot-desktop"
    CHANNEL_DEPENDENCY="Ardot 客户端"
    ;;
esac

if [ -n "$PORT" ]; then
  ok "通路 ${CHANNEL}（${CHANNEL_LABEL}）→ 注册为 ${SERVER_NAME}"
fi

# ------------------------------------------------------------ 2. 注册 MCP
if [ "$SKILLS_ONLY" -eq 0 ]; then
  step "注册 MCP 到 agent"

  if command -v claude >/dev/null 2>&1; then
    claude mcp remove "$SERVER_NAME" --scope user >/dev/null 2>&1
    if claude mcp add "$SERVER_NAME" --transport http "$MCP_URL" --scope user >/dev/null 2>&1; then
      ok "Claude Code ← ${SERVER_NAME} (${MCP_URL})"
    else
      err "Claude Code 注册失败，请手动执行："
      err "  claude mcp add ${SERVER_NAME} --transport http ${MCP_URL} --scope user"
    fi
  else
    warn "未找到 claude 命令，跳过 MCP 注册"
  fi
fi

# -------------------------------------------------------------- 3. 装技能
step "安装技能包"
[ -d "$SKILLS_SRC" ] || { err "找不到 skills/ 目录"; exit 1; }

installed=0
DEST="$HOME/.claude/skills"
mkdir -p "$DEST"
for d in "$SKILLS_SRC"/ardot-*; do
  [ -d "$d" ] || continue
  rm -rf "$DEST/$(basename "$d")"
  cp -r "$d" "$DEST/" && installed=$((installed + 1))
done
cp -f "$SKILLS_SRC/PORT-NOTES.md" "$DEST/" 2>/dev/null
ok "Claude Code → ${DEST}（${installed} 个技能包）"
warn "若同时用插件方式安装（~/.claude/skills/ardot-design/），这里会与插件内的技能重名——"
warn "二选一即可；插件方式是首选。"

# ------------------------------------------------------------------- 收尾
step "完成"
say "  技能包: ${installed} 个 / $(find "$SKILLS_SRC"/ardot-* -type f | wc -l | tr -d ' ') 个文件（另有 PORT-NOTES.md）"
if [ "$SKILLS_ONLY" -eq 0 ]; then
  say "  MCP:    ${MCP_URL}（通路 ${CHANNEL} · ${CHANNEL_LABEL}，注册为 ${SERVER_NAME}）"
  if [ "$CHANNEL" = "A" ]; then
    say "  工具:   21 个 —— 含 fetch_guidelines / html_to_ardot / export_variables / register_assets"
    warn "无 create_design / open_design：只能操作客户端里已打开的那一个文件。"
    warn "要从零起稿，请在 Ardot 客户端/网页端先建好文件再粘贴链接；"
    warn "或加连通路 B（WorkBuddy 50551）用其 create_design，见 README「三条 MCP 通路」。"
  else
    say "  工具:   20 个 —— 含 create_design / open_design / save_tokens"
    warn "无 fetch_guidelines / html_to_ardot：官方规范读取与 HTML 转稿需走通路 A。"
  fi
else
  warn "MCP 未注册 —— 当前不能用画布。"
  warn "启动 Ardot 客户端（50501，推荐）或 WorkBuddy（50551），打开一个设计文件后重跑：$0"
fi
say ""
say "验证：新开一个 Claude Code 会话，说"
say "  「用 ardot 画一个健身 App 的数据看板」"
say "打开画布看效果："
say "  ${KIT_DIR}/scripts/open-canvas.sh"
say ""
warn "前提：本模式依赖${CHANNEL_DEPENDENCY}保持运行；退出后外部 agent 会断连。"
warn "详见 ${SKILLS_SRC}/PORT-NOTES.md"
