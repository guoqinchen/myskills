#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL): 写源码后扫描 SELECT * 裸查询。

对齐 性能禁则（禁止 SELECT *，须显式列名）。仅对文本源文件生效。
非阻断：命中经 PostToolUse JSON 契约（hookSpecificOutput.additionalContext）回显 AI，exit 0。SELECT 与 * 跨行(\\s+)亦可识别；count(*) 不含 'select *' 不误报。
"""
import sys
import os
import re

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

TEXT_EXT = {".php", ".html", ".htm", ".js", ".css", ".py", ".sql", ".inc"}
SELECT_STAR = re.compile(r"select\s+\*", re.IGNORECASE)


def find_select_star_lines(text):
    """逐行扫描，跳过 PHP/JS/CSS 注释（//、#、/* */），返回命中行号。

    块注释剥离经 `LC.strip_block_comments` 单源（字符串内的 `/*` 不算注释开起，
    闭合同行的后续代码保留进扫描）。
    真实 SQL 多位于字符串字面量所在代码行，仍会被捕获；仅排除注释行，
    以降低说明性注释里出现 select * 的误报。
    """
    hits = []
    for i, line in LC.strip_block_comments(text):
        s = line.strip()
        if s.startswith("//") or s.startswith("#"):
            continue
        if SELECT_STAR.search(line):
            hits.append(i)
    return hits


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
    if not os.path.isfile(path):
        return 0

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return 0

    hits = find_select_star_lines(text)
    if hits:
        lines = ["[SQL-WARN] 发现 SELECT * 裸查询，请改为显式列名（性能禁则）："]
        lines += ["  行 %d" % n for n in hits]
        LC.emit_context(lines)  # PostToolUse 送达契约：stdout 只出 JSON（裸 print 不回传 Agent）
    return 0


if __name__ == "__main__":
    sys.exit(main())
