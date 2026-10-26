#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL): 写源码后扫描调试残留（多语言）。

对齐 代码质量（错误闭环/勿留调试）。覆盖模式：
- PHP：var_dump / print_r / var_export / die() / exit()
- JS/TS：console.log / console.debug
- Java/Kotlin：System.out|err.print[ln|f]() / printStackTrace()
- Laravel/Symfony：dd() / dump()
仅对文本源文件生效（含 .java/.kt/.gradle/.xml/.sql 等），跳过 tests 目录（测试辅助允许）。
非阻断：命中经 PostToolUse JSON 契约回显 AI，exit 0；提示语为「请确认是否应保留」——CLI 工具的正常 stdout 输出可能命中。
"""
import sys
import os
import re

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

TEXT_EXT = {
    ".php", ".html", ".htm", ".js", ".css", ".py", ".json", ".md", ".txt",
    # Java 生态 / 其他通用源码
    ".java", ".kt", ".gradle", ".jsp", ".xml", ".sql", ".vue", ".ts", ".tsx",
}
DEBUG = re.compile(
    # PHP
    r"(?:var_dump|print_r|var_export|\bdie\b|(?<!\.)\bexit\b)\s*\("
    # JS / TS
    r"|console\s*\.\s*(?:log|debug)\s*\("
    # Java / Kotlin
    r"|System\s*\.\s*(?:out|err)\s*\.\s*print(?:ln|f)?\s*\("
    r"|printStackTrace\s*\(\s*\)"
    # Laravel / Symfony
    r"|\bdd\s*\("
    r"|\bdump\s*\("
)


def main():
    data, _err = LC.read_stdin_payload()
    if not isinstance(data, dict):
        return 0

    tool_input = LC.tool_input_of(data)
    path = (
        tool_input.get("filePath")
        or tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )
    if not path:
        return 0
    path = os.path.abspath(path)
    if os.path.splitext(path)[1].lower() not in TEXT_EXT:
        return 0
    # 跳过测试目录，避免误报测试辅助代码
    if any(s.lower() in ("tests", "test") for s in path.split(os.sep)):
        return 0
    if not os.path.isfile(path):
        return 0

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return 0

    hits = []
    for m in DEBUG.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        hits.append((line, m.group(0).strip()))
    if hits:
        lines = ["[DEBUG-WARN] 发现调试残留，请确认是否应保留（代码质量）："]
        lines += ["  行 %d: %s" % (n, tok) for n, tok in hits]
        LC.emit_context(lines)  # PostToolUse 送达契约：stdout 只出 JSON（裸 print 不回传 Agent）
    return 0


if __name__ == "__main__":
    sys.exit(main())
