#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL, 非阻断): 写码前自动提示双册命中 + 命中自动记账。

- 反样本册 `error_index.md` → [ERR-RECALL]；正样本册 `success_index.md` → [SUC-RECALL]。
  对本次写操作的「文件名（不含目录）+ 内容」做轻量匹配（只取文件名：完整路径里的泛词
  会让整个目录下的任意写操作常驻误报）。
- 单一召回通道（铁律）：两册由本 hook 一并承担、同一去重口径、**每册独立预算
  MAX_HITS=3**；禁为正册另建第二个提醒类 hook。
- **命中记账（闭环机械化，Plan/49）**：召回判定成立即把该条 front-matter 的
  `hit_count` +1、`last_hit_at` 刷新；仅泛用短词（boundary 通道）命中时
  `low_quality_hit_count` +1（低质命中嫌疑，供人工精修评审，不触发自动降级）。
  记账先于展示预算截断——挂在展示面上会漏计去重命中与超预算命中，使
  「连续 N 个月召回 0 次 ⇒ 死触发词」判据永久失真。记账失败按**条目号**留痕
  （只记数量无法定位是哪条失败，痕迹不可定位比无痕迹更危险）。
- 始终 exit 0（非阻断）；记忆维护类写（记忆根下）直接跳过，避免自噪声。
- 任一册缺失即静默跳过该册（无记忆体系的项目不产生噪声）。

记忆根/索引解析/触发词判据全部经 `ledger_common` 单源（禁在本文件另写第二份解析）。
退出码：本 hook 注册在 PostToolUse（Pre 侧无送达通道），始终 0。
"""
import datetime
import io
import json
import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

try:  # 控制台 GBK 兼容（提示文本含中文与符号）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

MAX_HITS = 3
_BOM = '﻿'
_BOOK_DIR = {'err': 'errors', 'suc': 'success'}


def _skip_path(path):
    """记忆维护类写（记忆根下）跳过，避免自噪声（记账/改索引不触发召回）。"""
    norm = os.path.abspath(path).replace('\\', '/').lower()
    if '.ai-memory' in norm:
        return True
    root = LC.memory_root()
    if root:
        r = os.path.abspath(root).replace('\\', '/').lower()
        if norm.startswith(r + '/') or norm == r:
            return True
    return False


def _entry_path(book, entry_id):
    """索引行 entry_id（可带 `年/月/` 前缀）→ 单条文件路径；找不到时走目录遍历兜底。"""
    root = LC.memory_root()
    if not root:
        return None
    base = entry_id.split('/')[-1]
    cand = os.path.join(root, _BOOK_DIR[book], entry_id + '.md')
    if os.path.isfile(cand):
        return cand
    d = os.path.join(root, _BOOK_DIR[book])
    if os.path.isdir(d):
        for dp, _dn, fn in os.walk(d):
            if base + '.md' in fn:
                return os.path.join(dp, base + '.md')
    return None


def _bump(book, entry_id, weak=False):
    """消费记账：单条 front-matter `hit_count` +1、`last_hit_at` 刷新，
    `low_quality_hit_count`（weak=True 时）+1。

    - 只改 front-matter 区：行级原位替换，缺失则追加在 front-matter 末行；
    - 保留原行尾风格（\\r\\n / \\n），正文一字不动；
    - 原子写（临时文件 + os.replace）并回读校验（行首锚定计数——`low_quality_hit_count:`
      含子串 `hit_count:`，用 count() 会自增成 2）；
    - 失败返回 (False, 原因)——原因必须可定位（ERR-229：只记「失败 N 条」不可定位）。
    """
    path = _entry_path(book, entry_id)
    if not path:
        return False, 'entry-not-found'
    try:
        with io.open(path, encoding='utf-8', newline='') as fh:
            text = fh.read()
        lines = text.splitlines(keepends=True)
        # 定位 front-matter 区块（首行 --- 至下一个 --- ）
        if not lines or lines[0].lstrip(_BOM).strip() != '---':
            return False, 'no-front-matter'
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end = i
                break
        if end is None:
            return False, 'fm-unclosed'
        hit_i = last_i = low_i = -1
        cnt = low_cnt = 0
        for i in range(1, end):
            ln = lines[i]
            if ln.startswith('hit_count:'):
                hit_i = i
                m = re.match(r'^\d+', ln.split(':', 1)[1].strip())
                cnt = int(m.group(0)) if m else 0
            elif ln.startswith('last_hit_at:'):
                last_i = i
            elif ln.startswith('low_quality_hit_count:'):
                low_i = i
                m = re.match(r'^\d+', ln.split(':', 1)[1].strip())
                low_cnt = int(m.group(0)) if m else 0
        now = datetime.datetime.now().isoformat(timespec='seconds')
        new_keys = []
        if hit_i >= 0:
            lines[hit_i] = 'hit_count: %d%s' % (cnt + 1, _eol(lines[hit_i]))
        else:
            new_keys.append('hit_count: %d' % (cnt + 1))
        if last_i >= 0:
            lines[last_i] = 'last_hit_at: %s%s' % (now, _eol(lines[last_i]))
        else:
            new_keys.append('last_hit_at: %s' % now)
        if weak:
            if low_i >= 0:
                lines[low_i] = 'low_quality_hit_count: %d%s' % (low_cnt + 1, _eol(lines[low_i]))
            else:
                new_keys.append('low_quality_hit_count: %d' % (low_cnt + 1))
        for k in reversed(new_keys):
            lines.insert(end, k + _eol(lines[end - 1]))
        out = ''.join(lines)
        tmp = path + '.tmp'
        with io.open(tmp, 'w', encoding='utf-8', newline='') as fh:
            fh.write(out)
        os.replace(tmp, path)
        with io.open(path, encoding='utf-8', newline='') as fh:
            verify = fh.read()
        return (len(re.findall(r'(?m)^hit_count:', verify)) == 1
                and len(re.findall(r'(?m)^last_hit_at:', verify)) == 1
                and len(re.findall(r'(?m)^low_quality_hit_count:', verify)) <= 1), 'verified'
    except Exception as exc:
        return False, repr(exc)[:80]


def _eol(line):
    """取该行原有行尾；无行尾（文件末行）返回空串。"""
    m = re.search(r'(\r\n|\n|\r)$', line)
    return m.group(1) if m else ''


def emit(lines, event="PostToolUse"):
    """JSON 契约输出：`hookSpecificOutput.additionalContext` 在 PostToolUse 可达 Agent
    （平台以 <system-reminder> 注入）。`systemMessage` 供 IDE UI。
    **只输出这一个 JSON**，不与裸 print 混排。"""
    msg = "\n".join(lines)
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": msg},
    }, ensure_ascii=False))


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
    if not path or _skip_path(path):
        return 0

    content = tool_input.get("content") or tool_input.get("new_str") or ""
    # 只把文件名（含扩展名）纳入匹配，不拼完整路径：路径里的泛词会让该目录下
    # 任意写操作常驻误报。
    hay = (os.path.basename(path).lower() + "\n" + content).lower()

    # 双册召回：同一去重口径、每册独立预算（单一召回通道，禁拆分）
    buckets = (("err", LC.err_index_path(), []),
               ("suc", LC.success_index_path(), []))
    for _kind, index_path, hits in buckets:
        if not index_path or not os.path.isfile(index_path):
            continue
        for row_id, keyword, desc in LC.load_triggers(index_path):
            strong, boundary = LC.tokenize(keyword)
            matched, weak = None, False
            for tok in strong:
                if tok in hay:
                    matched = tok
                    break
            if matched is None:
                for tok in boundary:
                    if re.search(r"(?<![0-9a-z_])" + re.escape(tok) + r"(?![0-9a-z_])", hay):
                        matched = tok
                        weak = True     # 仅泛用短词命中＝低质命中嫌疑
                        break
            if matched is not None:
                hits.append((matched, row_id, desc or keyword, weak))

    # 记账：召回判定成立即记，先于展示预算截截（口径见模块文档字符串）
    failed = []
    for kind, _ip, hits in buckets:
        for matched, row_id, _desc, weak in hits:
            ok, why = _bump(kind, row_id, weak=weak)
            if not ok:
                failed.append('%s(%s)' % (row_id, why))

    lines = []
    if buckets[0][2]:
        lines += ["[ERR-RECALL] 操作可能命中踩坑册触发词「%s」（%s：%s）。" % (t, e, d)
                  for t, e, d, _w in buckets[0][2][:MAX_HITS]]
        lines.append("建议 read_file 对应单条复核（踩坑记忆 #2 动手前必查，禁全量读 errors/）。")
    if buckets[1][2]:
        lines += ["[SUC-RECALL] 操作可能命中正样本册触发词「%s」（%s：%s）。" % (t, e, d)
                  for t, e, d, _w in buckets[1][2][:MAX_HITS]]
        lines.append("建议 read_file 对应单条复核，并按「命中即复核」验证：实际套用 ⇒ "
                     "Recurrence-Count+1；失效 ⇒ 改 utility 并留痕（禁全量读 success/）。")
    if failed:
        lines.append(
            "[ERR-RECALL-NOTE] 本次召回记账失败 %d 条（%s；hit_count 未递增）。"
            % (len(failed), ",".join(failed[:5])))
    if lines:
        emit(lines)
    return 0  # 非阻断


if __name__ == "__main__":
    sys.exit(main())
