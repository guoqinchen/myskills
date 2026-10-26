#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL): 写 .php 后做 PHP 8.x 兼容性静态扫描（对齐 PHP 8 兼容）。

仅做纯模式匹配（不依赖 php -l，因本环境 php -l 退出码不可信），命中即 warning 回显 AI，
非阻断（exit 0）。涵盖：短标签、裸数组键、each()/create_function()/get_magic_quotes_gpc()。
"""
import sys
import os
import re

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

# <? 后非 php/=/xml 视为短标签（<?php / <?= / <?xml 合法；大小写不敏感，<?PHP 非短标签）
# `=` 后不加 \b：`<?= $x ?>` 的 `=` 后是空格或 `$`，无词边界，加 \b 会把短回显标签误判为短标签
SHORT_TAG = re.compile(r'<\?(?!php\b|xml\b|=)', re.IGNORECASE)
# $arr[key] 裸键（key 为字母开头、非 $ 变量、非引号、非纯数字）
BARE_KEY = re.compile(r'\$\w+\[([A-Za-z_][A-Za-z0-9_]*)\]')
BAD_FUNCS = [
    (re.compile(r'\beach\s*\('), 'each()'),
    (re.compile(r'\bcreate_function\s*\('), 'create_function()'),
    (re.compile(r'\bget_magic_quotes_gpc\s*\('), 'get_magic_quotes_gpc()'),
]


def scan(text):
    hits = []
    if SHORT_TAG.search(text):
        hits.append("短标签 <?（非 <?php/<?=/<?xml），须改 <?php")
    mk = BARE_KEY.search(text)
    if mk:
        key = mk.group(1)
        # 跳过全大写常量（如 $arr[MY_CONST]）及语言常量 true/false/null，
        # 避免误伤合法常量用法；PHP 8 兼容针对的是裸字符串键（小写/混合大小写）
        if key.isupper() or key.lower() in ("true", "false", "null"):
            pass
        else:
            hits.append("裸数组键 $arr[%s] 未加引号，须 $arr['%s']（PHP 8 兼容）" % (key, key))
    for rx, name in BAD_FUNCS:
        if rx.search(text):
            hits.append("已废弃函数 %s（PHP8 已移除），须替换（PHP 8 兼容）" % name)
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
    if os.path.splitext(path)[1].lower() != ".php":
        return 0
    if not os.path.isfile(path):
        return 0

    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return 0

    hits = scan(text)
    if hits:
        LC.emit_context(["[PHP8-COMPAT-WARN] 发现 PHP8 兼容隐患："]
                        + ["  - " + h for h in hits])
    return 0


if __name__ == "__main__":
    sys.exit(main())
