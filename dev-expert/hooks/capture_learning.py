#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨工具「学习捕获」hook 草案（PostToolUse / UserPromptSubmit 通用）。

借鉴 elf-improving-agent 的 activator.sh + error-detector.sh 设计理念，
改写为 Python 以兼容 Windows 与所有 Agent 工具（CodeBuddy / Trae / Cursor /
Claude Code / Codex / OpenClaw），不依赖单一平台的 bash 运行时。

设计原则（与 dev-expert 现有 28 个防护 hook 一致）：
- 跨工具兼容：stdin 事件字段名多源容错（tool_input/filePath/file_path/path、
  tool_response/tool_output/output/result、prompt/query/user_input）。
- 非阻塞：默认 exit 0（仅回显提醒文本，交 Agent 判断）；--strict 时命中 exit 1（强提醒）。
- 不自动写文件：遵循 elf「提醒而非写入」+ error-ledger「不经确认不写入」禁忌，
  仅输出「建议记录」提醒，由 Agent 决定是否落盘到 .ai-memory/。
- 去重提示：扫描 error_index.md 判定 Recurrence，复现时提示更新 Recurrence-Count。

触发信号：
- 错误信号（工具/命令输出含关键词）：elf 16 个 + dev-expert 语境扩展。
- 纠错信号（用户输入含句式）：中英文清单，仅在 --mode correction 或事件含用户输入时检测。

退出码：
  0 = 无信号 / 仅提醒（非阻塞默认）
  1 = 命中信号且 --strict（强提醒，仍不阻断已完成的写入/执行）
"""
import sys
import os
import re
import argparse

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

try:  # 控制台 GBK 兼容（提示文本与工具输出片段可能含中文/符号）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ---- 错误关键词（命令/工具输出扫描）----
ERROR_PATTERNS = [
    "error:", "Error:", "ERROR:", "failed", "FAILED",
    "command not found", "No such file", "Permission denied",
    "fatal:", "Exception", "Traceback", "npm ERR!",
    "ModuleNotFoundError", "SyntaxError", "TypeError",
    "exit code", "non-zero",
    # dev-expert 语境扩展
    "Parse error", "Fatal error", "PHP Fatal", "PHP Warning",
    "断言失败", "assert", "测试失败", "未通过", "GATE-CHECK 不足",
]

# ---- 用户纠错句式（用户输入扫描）----
CORRECTION_PATTERNS = [
    "不对", "错了", "搞混", "实际上", "应该是", "你理解", "你误会",
    "纠正", "混淆", "你之前",
    "no, that", "actually", "you're wrong", "that's outdated", "not right",
    "i said",
]


def read_event():
    """容错读取 hook 事件 JSON；任何解析失败返回空 dict（静默 exit 0）。"""
    payload, _err = LC.read_stdin_payload()
    return payload if isinstance(payload, dict) else {}


def pick(data, *keys, default=""):
    """从多源字段名中取第一个非空字符串。"""
    for k in keys:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return default


def get_output(data):
    return pick(data, "tool_response", "tool_output", "output", "result", "stdout", default="")


def get_prompt(data):
    return pick(data, "prompt", "query", "user_input", "input", default="")


def get_tool_name(data):
    return pick(data, "tool_name", "toolName", "name", default="")


def scan_error(text):
    """返回命中的首个错误关键词，或 None。"""
    for p in ERROR_PATTERNS:
        if p in text:
            return p
    return None


def scan_correction(text):
    """返回命中的首个纠错句式，或 None。"""
    low = text.lower()
    for p in CORRECTION_PATTERNS:
        if p.lower() in low:
            return p
    return None


def find_recurrence(index_path, keyword):
    """扫描 error_index.md，返回含该关键词的已有 ERR-ID 列表（去重提示用）。"""
    if not index_path or not os.path.isfile(index_path):
        return []
    try:
        with open(index_path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return []
    hits = []
    for line in content.splitlines():
        if "|" not in line:
            continue
        if keyword.lower() in line.lower():
            m = re.search(r"ERR-\d+", line)
            if m and m.group(0) not in hits:
                hits.append(m.group(0))
    return hits


def main():
    parser = argparse.ArgumentParser(description="跨工具学习捕获 hook（草案）")
    parser.add_argument(
        "--mode", choices=["auto", "correction"], default="auto",
        help="auto=扫描输出+输入; correction=仅扫描用户输入纠错",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="命中信号时 exit 1（强提醒，仍不阻断）",
    )
    parser.add_argument(
        "--index", default="",
        help="error_index.md 路径（默认经 ledger_common.err_index_path() 解析）",
    )
    args = parser.parse_args()

    data = read_event()
    if not data:
        return 0

    tool_name = get_tool_name(data)
    output = get_output(data)
    prompt = get_prompt(data)

    signal_kind = None
    signal_word = None
    snippet = ""

    if args.mode == "correction":
        c = scan_correction(prompt)
        if c:
            signal_kind, signal_word, snippet = "correction", c, prompt[:200]
    else:
        e = scan_error(output)
        if e:
            signal_kind, signal_word, snippet = "error", e, output[:200]
        else:
            c = scan_correction(prompt)
            if c:
                signal_kind, signal_word, snippet = "correction", c, prompt[:200]

    if not signal_kind:
        return 0

    # 去重 / Recurrence 提示：索引定位经 LC 单源（禁硬编码 PROJECT_ROOT/.ai-memory 单候选）
    index_path = args.index or LC.err_index_path() or ''
    index_located = bool(index_path and os.path.isfile(index_path))
    hits = find_recurrence(index_path, signal_word) if index_located else []

    lines = ["[LEARN-CAPTURE] 检测到可提炼信号（建议记录到 error-ledger）",
             "  类型: %s | 关键词: %s" % (signal_kind, signal_word),
             "  工具: %s" % (tool_name or "unknown"),
             "  片段: %s" % snippet.replace("\n", " ").strip()]
    if hits:
        lines.append("  复现提示: 已记录 %s，建议更新其 Recurrence-Count" % ", ".join(hits))
    elif not index_located:
        # 禁把「索引没找到」呈现成「没有历史记录」——那会诱导建重复条目
        lines.append("  复现提示: 反册索引未定位（LC 解析未命中），去重提示不可用；"
                     "设 AI_MEMORY_DIR 或在含 .ai-memory/ 的目录运行后重试")
    else:
        lines.append("  复现提示: 未见历史记录，建议新建 ERR-XXX 并附 Recurrence-Count: 1")
    lines.append("  动作: 落 errors/<年>/<月>/ERR-XXX.md 单条，再重跑索引生成器（禁手工追写索引行）")
    LC.emit_context(lines)

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
