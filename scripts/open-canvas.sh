#!/usr/bin/env bash
# 在浏览器里打开 Ardot 设计文件 —— 补上「外部 agent 没有实时画布」这一环。
# 因为 Ardot 支持多人实时协作，浏览器里的画布会随 agent 的编辑实时刷新。
#
# 用法:
#   open-canvas.sh                # 不传参数：询问 MCP 当前活跃文件，再打开
#   open-canvas.sh 719793184410961
#   open-canvas.sh https://ardot.tencent.com/file/719793184410961

set -uo pipefail

PORT="$("$(dirname "$0")/detect-ardot.sh" -q)" || {
  echo "错误：未检测到运行中的 Ardot MCP server（请先启动 WorkBuddy）" >&2
  exit 1
}

FILE_ID="${1:-}"

if [ -z "$FILE_ID" ]; then
  # 向 MCP 询问当前活跃文件
  RESP=$(curl -s -m 8 -X POST "http://127.0.0.1:${PORT}/api/v1/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"fetch_file_info","arguments":{}}}')
  FILE_ID=$(printf '%s' "$RESP" | sed 's/^data: //' \
    | grep -o 'https://ardot.tencent.com/file/[0-9]*' | head -1)
  if [ -n "$FILE_ID" ]; then
    FILE_ID="${FILE_ID##*/}"
  fi
fi

# 只保留纯数字 ID（用户可能贴了完整 URL）
FILE_ID="${FILE_ID##*/}"

if [ -z "$FILE_ID" ]; then
  echo "无法确定文件 ID。请显式传入：" >&2
  echo "  $0 719793184410961" >&2
  exit 1
fi

URL="https://ardot.tencent.com/file/${FILE_ID}"
echo "打开画布: $URL"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) start "" "$URL" ;;
  Darwin*)              open "$URL" ;;
  *)                    xdg-open "$URL" 2>/dev/null || echo "请手动打开: $URL" ;;
esac
