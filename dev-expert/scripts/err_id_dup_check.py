#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错误册编号唯一性断言（机械层防重）。

补「集合比对」类检查的盲区：按编号**集合**比对时，索引内同一编号出现多行仍报
「双向一致」（基数对不上却全绿）。本断言四项：

  ① 索引内重复编号（同一 ERR 号出现 >1 行）
  ② 索引行数与单条文件数基数不一致（重复编号的直接征兆）
  ③ 索引声明路径与实际路径不符
  ④ 内容判重：两两五维加权相似度（≥0.75 同构须合并 / 0.45–0.74 相关仅提示）

只读、不写盘；退出码 1 表示存在问题，0 表示通过。
用法：python err_id_dup_check.py
"""
import collections
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks'))
import ledger_common as LC  # noqa: E402

ROW_RE = re.compile(r'^(\d{4}/\d{2})/(ERR-(\d+))', re.M)
FILE_RE = re.compile(r'^ERR-(\d+)\.md$')

# 五维权重 + 阈值：≥0.75 同构须合并 / 0.45–0.74 相关（仅提示）/ <0.45 独立
W_DIM = (("Pattern-Key", 0.30), ("keywords", 0.25), ("标题", 0.20),
         ("触发信号", 0.15), ("根因", 0.10))
MERGE_AT, RELATED_AT = 0.75, 0.45


def _norm(s):
    return re.sub(r'\s+', ' ', s or '').strip().lower()


def _jacc(a, b):
    A = set(x for x in re.split(r'[/，。；、\s]+', _norm(a)) if x)
    B = set(x for x in re.split(r'[/，。；、\s]+', _norm(b)) if x)
    return (len(A & B) / len(A | B)) if (A and B) else 0.0


def _field(text, key):
    """front-matter 优先，正文行内式回退（两种实现均取自 ledger_common，口径同源）。"""
    return LC.fm_value(text, key) or LC.value(text, key) or ''


def _title(text):
    m = re.search(r'^#{1,2}\s*\[?ERR-\d+\]?[：:]?\s*(.+)$', text, re.M)
    return m.group(1) if m else ''


def content_sim(t1, t2):
    tot = 0.0
    for key, w in W_DIM:
        v1 = _title(t1) if key == '标题' else _field(t1, key)
        v2 = _title(t2) if key == '标题' else _field(t2, key)
        tot += w * _jacc(v1, v2)
    return tot


def rd(p):
    with io.open(p, encoding='utf-8', errors='ignore') as f:
        return f.read()


def main():
    root = LC.memory_root()
    if not root:
        sys.stderr.write('[ERR-DUP-CHECK] 记忆根不可用（设 AI_MEMORY_DIR 或在含 .ai-memory/ 的目录运行）\n')
        sys.exit(3)  # 环境/自身错误＝3（禁与「校验 FAIL＝1」混淆）
    errd = os.path.join(root, 'errors')
    # 索引路径经 LC 单源解析（复数索引/索引落根布局均可定位）
    idx_path = LC.err_index_path() or os.path.join(root, 'error_index.md')

    fails = 0

    def rep(ok, name, detail):
        nonlocal fails
        if not ok:
            fails += 1
        print('[%s] %s  %s' % ('PASS' if ok else 'FAIL', name, detail))

    if not os.path.isfile(idx_path):
        rep(False, 'index exists', 'missing: %s' % idx_path)
        print('[ERR-DUP-CHECK] fail=%d' % fails)
        sys.exit(1)

    text = rd(idx_path)
    rows = ROW_RE.findall(text)
    counts = collections.Counter(r[1] for r in rows)
    dup = sorted([(k, v) for k, v in counts.items() if v > 1])
    rep(not dup, 'no duplicate id', 'dup=%s' % dup if dup
        else '%d rows / %d unique ids' % (len(rows), len(counts)))

    files = {}
    if os.path.isdir(errd):
        for dp, _dn, fn in os.walk(errd):
            for f in fn:
                m = FILE_RE.match(f)
                if m:
                    files[m.group(1)] = os.path.join(dp, f)
    rep(len(rows) == len(files), 'index rows == err files',
        'index %d vs files %d' % (len(rows), len(files))
        if len(rows) != len(files) else '%d == %d' % (len(rows), len(files)))

    bad = []
    for ym, name, _num in rows:
        if name in files:
            real = os.path.relpath(files[name], errd).replace(os.sep, '/')
            if real != '%s/%s.md' % (ym, name):
                bad.append((name, '%s/%s' % (ym, name), real))
    rep(not bad, 'index path == real path', 'bad=%s' % bad[:3] if bad
        else '%d paths ok' % len(rows))

    # ④ 内容判重：两两五维加权相似度（只读）
    texts = {}
    for num, p in files.items():
        try:
            texts[num] = rd(p)
        except Exception:
            continue
    keys = sorted(texts, key=int)
    merge, related = [], []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            s = content_sim(texts[keys[i]], texts[keys[j]])
            if s >= MERGE_AT:
                merge.append(('ERR-%s' % keys[i], 'ERR-%s' % keys[j], round(s, 2)))
            elif s >= RELATED_AT:
                related.append(('ERR-%s' % keys[i], 'ERR-%s' % keys[j], round(s, 2)))
    rep(not merge, 'content duplicate (merge)', 'merge=%s' % merge[:3] if merge
        else 'no pair >= %.2f (related pairs=%d)' % (MERGE_AT, len(related)))

    print('[ERR-DUP-CHECK] %s (fail %d)'
          % ('all passed' if not fails else 'problems found', fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
