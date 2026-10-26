#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL, 非阻断): 新建/追加踩坑册条目前查重，防近重复。

补 errors_recall_guard 显式跳过记忆区写留下的去重缝：
recall guard 在写 ERR 单条/索引行时 self-exclude，故新建坑那一刻无人提醒"可能已有"。

- 仅当写目标为 `errors/ERR-*.md` 单条 或 `error_index.md` 时介入；其余写直接 exit 0。
- 从本次写内容抽取候选触发词，与现有活跃索引逐条比对：整词/短语级共享 >=1 或
  中文 bigram 共享 >=3 即判疑似重复（bigram 单独计权，防「弹窗/编辑」类高频二字误报）。
- 含空格的 ASCII 短语（ERROR 1046 等）按折叠空白后的原文做子串匹配，不走分词交集。
- 始终 exit 0（非阻断）：仅提醒，由 Agent 先核对再建（用户确认）。

记忆根目录解析与索引解析经 `ledger_common` 单源（`memory_root`/`err_index_path`/
`load_triggers`：`AI_MEMORY_DIR` → `PROJECT_ROOT/.ai-memory` → cwd/脚本位置上溯；
`ledger_target` 判别写目标）。查重分词（whole/bigram）与召回匹配判据有意不同，见
`tokenize` 文档字符串。
"""
import sys
import os
import re
import json
import argparse

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

STRONG_MIN = 1  # 整词/短语级共享达此数即判疑似重复
WEAK_MIN = 3    # 仅中文 bigram 共享时须达此数（防「弹窗/编辑」类高频二字误报）

MAX_HITS = 3


def tokenize(keyword):
    """查重侧分词（whole/bigram 交集判据）——与召回匹配判据**有意不同**：

    召回＝写入内容 vs 触发词的子串/词边界匹配（`ledger_common.tokenize`）；
    查重＝两条触发词之间的整词/短语共享与中文 bigram 共享（本函数）。
    两个判据服务不同决策，禁互相套用；索引解析（`LC.load_triggers`）已收敛单源。
    """
    whole, bigram = [], []
    for t in re.split(r"[/\，、,；;]+", keyword):
        t = t.strip().lower()
        if not t:
            continue
        if t.isascii():
            if len(t) < 6:
                continue
            whole.append(t)
        else:
            if len(t) == 1:
                continue
            whole.append(t)            # 整词（缓存击穿）
            # 仅对纯中文整词补 bigram；混入数字/字母的混合词不切，避免 ASCII 噪声 bigram。
            if len(t) >= 3 and re.fullmatch(r"[\u4e00-\u9fff]+", t):
                for i in range(len(t) - 1):
                    bigram.append(t[i:i + 2])
    return whole, bigram


def content_tokens(text):
    """候选侧分词，返回 (cand_whole, cand_bigram, norm_text)。

    - 先按空白切词再对每词走 tokenize，保证正文里 'ehref whhref 后台404'
      被拆成独立词。
    - norm_text：空白折叠为单空格的小写原文，供**含空格**的 ASCII 触发词
      （ERROR 1046 / CREATE TABLE …）做子串匹配。
    """
    cand_whole, cand_bigram = set(), set()
    for word in re.split(r"\s+", text or ""):
        w, b = tokenize(word)
        cand_whole.update(w)
        cand_bigram.update(b)
    norm_text = re.sub(r"\s+", " ", text or "").lower()
    return cand_whole, cand_bigram, norm_text


def read_event():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="ignore")
    except Exception:
        raw = ""
    raw = raw.lstrip("\ufeff")
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description="踩坑册新建条目查重守卫")
    parser.add_argument("--event-file", default="", help="测试用：从文件读 hook 事件 JSON")
    args = parser.parse_args()

    if args.event_file:
        try:
            with open(args.event_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return 0
    else:
        data = read_event()
    if not data:
        return 0

    tool_input = LC.tool_input_of(data)
    path = (tool_input.get("filePath") or tool_input.get("file_path")
            or tool_input.get("path") or "")
    if not path:
        return 0
    # 路径判别经 ledger_common（技能自有约定；err 单条/err 索引均介入）
    if LC.ledger_target(path) not in ('err', 'err_index'):
        return 0

    index_path = LC.err_index_path()
    if not index_path or not os.path.isfile(index_path):
        return 0

    # 排除自身编号，避免更新现有条目时自匹配。
    low = os.path.abspath(path).replace("\\", "/").lower()
    self_id = None
    m = re.search(r"err-(\d+)\.md$", low)
    if m:
        self_id = "ERR-" + m.group(1)
    content = (tool_input.get("content") or tool_input.get("new_str") or "")
    cm = re.search(r"ERR-(\d+)", content, re.IGNORECASE)
    if cm and not self_id:
        self_id = "ERR-" + cm.group(1)

    cand_whole, cand_bigram, norm_text = content_tokens(content)
    if not cand_whole and not cand_bigram:
        return 0

    triggers = LC.load_triggers(index_path)
    if not triggers:
        return 0

    hits = []
    for err_id, keyword, desc in triggers:
        # 索引 err_id 可能带 年/月/ 前缀（如 2026/08/ERR-007），与自排除的
        # ERR-XXX 对齐后再比，否则编辑旧坑会自匹配误报。
        if err_id.split("/")[-1] == self_id:
            continue
        kw_whole, kw_bigram = tokenize(keyword)
        strong = set()
        for t in kw_whole:
            if " " in t:
                if t in norm_text:
                    strong.add(t)
            elif t in cand_whole:
                strong.add(t)
        weak = cand_bigram & set(kw_bigram)
        # 强（整词/短语）命中 1 个即疑似重复；仅 bigram 命中则需 >=3 个。
        if len(strong) >= STRONG_MIN or len(weak) >= WEAK_MIN:
            hits.append((len(strong), len(weak), err_id, desc or keyword, strong, weak))
    if not hits:
        return 0

    hits.sort(key=lambda x: (x[0], x[1]), reverse=True)
    lines = ["[ERR-DUP] 新建/追加踩坑条目与现有条目高度相似，先核对是否重复（踩坑记忆 #4）："]
    lines += ["  疑似重复 %s（强匹配：%s；弱匹配：%s）：%s"
              % (eid, "/".join(sorted(st)) or "无", "/".join(sorted(wk)) or "无", desc)
              for _ns, _nw, eid, desc, st, wk in hits[:MAX_HITS]]
    lines.append("  若确为新坑，请在描述中明确差异点后再建；若重复，更新既有 ERR 的 Recurrence-Count。")
    LC.emit_context(lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
