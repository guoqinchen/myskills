#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook (GLOBAL): 写入前检测「数据外发」组合（外发调用 + 敏感来源同现）。

背景：PostToolUse 的 stdout 不回传 Agent，只有 PreToolUse 的 exit 2 会把拒绝理由
回传给 Agent；「把敏感数据发出去」必须在写入前拦住，故本检查挂在 PreToolUse。

判定：**组合模式**——命中「外发调用」的行（含其前若干行窗口）同时出现「敏感来源」
才判定，不按裸函数名命中，把误报压到最低。

覆盖扩展名：.php / .py / .js / .jsx / .ts / .tsx / .java / .go / .sh / .bash

**判定边界（有意收窄）**：只判「服务端外发调用」＋「明确敏感来源」（超全局 /
`request.*` / `req.*` / 环境凭证）。浏览器侧 `fetch`/`axios`/`XMLHttpRequest` 与
裸变量名 `token`/`password` 不纳入——前者目标域静态不可判、后者在正常鉴权代码高频
出现，一并拦会使 `hook-allow` 逃生阀常态化；这部分交 `code-review`/`threat-modeling`。

豁免 / 逃生阀：
  1. 目标扩展名不在覆盖集 → 放行；2. 内容含 hook-allow 标记 → 放行；
  3. 任何异常 → 放行（失败放行，绝不误阻断）。

退出码：命中 → 2（拒绝并把理由回传 Agent）；否则 0。

注：敏感词与外发函数名一律拼接构造，源码中不出现完整字面量（防杀软启发式误删，
    也防本 hook 被再次写入时自拦）。
"""
import sys
import os
import re

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

EXTS = (".php", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".sh", ".bash")
ALLOW_MARK = "hook-allow"
WINDOW = 3

# --- 外发调用（拼接构造，避免完整字面量；只收服务端外发） ---
_SEND = re.compile(
    "curl" + "_exec|curl" + "_multi|fsock" + "open|"
    "requests?\\.(?:get|post|put|patch)|url" + "lib\\.request|http\\.client|"
    "urlopen\\s*\\(|"
    "Http" + "Client|URL" + "Connection|Rest" + "Template|Ok" + "Http|"
    "http\\.(?:Get|Post|Head|NewRequest)\\s*\\(|mail\\s*\\(",
    re.IGNORECASE,
)

# --- 敏感来源：用户输入 或 环境凭证（须与外发同现才命中） ---
# 裸变量名（token/password/session_id）有意不收：正常鉴权代码高频出现，误拦会迫使
# 逃生阀常态化；前端 fetch/axios 同理不纳入本钩子（交 code-review/threat-modeling）。
_SENS = re.compile(
    "\\$_(?:GET|POST|REQUEST|COOKIE|FILES)\\b|"
    "request\\.(?:form|args|json|data|values|get_json)\\b|"
    "req\\.(?:body|query|params|cookies)\\b|"
    "process\\.env\\.[A-Za-z_]*(?:TOKEN|SECRET|KEY|PASSWORD|PASSWD|CRED)[A-Za-z_]*|"
    "os\\.environ(?:\\[[^\\]]*(?:TOKEN|SECRET|KEY|PASSWORD|PASSWD|CRED)[^\\]]*\\]"
    "|\\.get\\(\\s*['\"][^'\"]*(?:TOKEN|SECRET|KEY|PASSWORD|PASSWD|CRED))|"
    "getenv\\(\\s*['\"][^'\"]*(?:TOKEN|SECRET|KEY|PASSWORD|PASSWD|CRED)",
    re.IGNORECASE,
)

_COMMENT_PREFIX = ("#", "//", "*", "/*", "--")


def new_text_of(tool_input):
    """取本次写入的新增文本（replace 用 new_str，write 用 content 全文）。"""
    for key in ("new_str", "new_string", "content", "text"):
        v = tool_input.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def scan(text):
    """返回 [(行号, 行摘要)]；命中＝外发行（或其前 WINDOW 行窗口）含敏感来源。"""
    hits = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith(_COMMENT_PREFIX):
            continue
        if not _SEND.search(line):
            continue
        ctx = "\n".join(lines[max(0, i - WINDOW): i + 1])
        if _SENS.search(ctx):
            hits.append((i + 1, s[:120]))
    return hits


def main():
    LC.fix_stdio()
    data, _err = LC.read_stdin_payload()
    if not isinstance(data, dict):
        return 0

    ti = LC.tool_input_of(data)
    path = ti.get("filePath") or ti.get("file_path") or ti.get("path") or ""
    if not path or os.path.splitext(str(path))[1].lower() not in EXTS:
        return 0

    text = new_text_of(ti)
    if not text or ALLOW_MARK in text:
        return 0

    try:
        hits = scan(text)
    except Exception:
        return 0

    if hits:
        print("[EGRESS-BLOCK] 疑似敏感数据外发（写入前拦截）：")
        for ln, src in hits[:5]:
            print("  - L%d: %s" % (ln, src))
        print("  处置：改为服务端代理 / 先脱敏再外发；确认为误报时在内容中加入 hook-allow 标记")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
