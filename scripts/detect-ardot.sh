#!/usr/bin/env bash
# 探测本机 Ardot MCP server 的端口。
# 用法:  detect-ardot.sh [-q]
#        正常输出 "<port>"，失败输出空并返回 1。加 -q 静默（不打印说明到 stderr）。
#
# 两条本地通路（都在 127.0.0.1，但不是同一个程序）：
#   50501 = Ardot 客户端     （通路 A，21 工具，默认推荐）
#   50551 = WorkBuddy 内置   （通路 B，20 工具，独有 create_design）
# 先试 A，A 没起再试 B，都没有才在邻近区间扫一遍。

set -uo pipefail
QUIET=0
[ "${1:-}" = "-q" ] && QUIET=1

log() { [ "$QUIET" -eq 1 ] || printf '%s\n' "$*" >&2; }

PRIMARY_PORT=50501
FALLBACK_PORT=50551
SCAN_START=50500
SCAN_END=50570

probe() {
  local port="$1"
  local h
  h=$(curl -s -m 2 "http://127.0.0.1:${port}/api/v1/health" 2>/dev/null)
  [ -z "$h" ] && return 1
  # 两条通路的 health 格式不同，不能只认 status：
  #   A(50501): {"version":"0.0.0",...,"connections":{...}}   ← 无 status 字段
  #   B(50551): {"status":"ok",...}                           ← 有 status
  printf '%s' "$h" | grep -q '"connections"\|"status"'
}

if probe "$PRIMARY_PORT"; then
  echo "$PRIMARY_PORT"
  exit 0
fi

if probe "$FALLBACK_PORT"; then
  log "通路 A（${PRIMARY_PORT}）无响应，改用通路 B（${FALLBACK_PORT}）"
  echo "$FALLBACK_PORT"
  exit 0
fi

log "两个默认端口都无响应，扫描 ${SCAN_START}-${SCAN_END} ..."
for ((p = SCAN_START; p <= SCAN_END; p++)); do
  if probe "$p"; then
    log "在 ${p} 找到服务（端口被占用时客户端会换端口）"
    echo "$p"
    exit 0
  fi
done

log "未找到运行中的 Ardot MCP server。"
log "请先启动 Ardot 客户端并打开设计文件（端口 ${PRIMARY_PORT}），"
log "或启动 WorkBuddy（端口 ${FALLBACK_PORT}），然后重试。"
exit 1
