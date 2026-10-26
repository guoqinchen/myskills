#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成功册索引生成器（禁二次手工维护）。

产出：`success_index.md` —— 索引（生成物，**禁手工追写**；写入侧由
`success_entry_guard.py` 拦截，生成器即唯一入口）。写入数据一旦变化即重跑本生成器，
杜绝「索引与单条脱节且无人报警」。

退出码：0 成功；1 有单条不合规（缺字段/类型越界）⇒ **不写盘**，防半迁移索引；
3 环境/自身错误（记忆根不可解析、目录缺失——与校验器错误码契约一致，禁与 1 混淆）。用法：
  python success_index_gen.py [--success-dir DIR] [--out FILE]
"""
import argparse
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks'))
import ledger_common as LC  # noqa: E402

KEYS = ('suc', 'year_month', 'type', 'keywords', 'summary')
TITLE_RE = re.compile(r'^#{1,2}\s*\[?SUC-\d+\]?[：:]?\s*(.+?)\s*$', re.M)


def read_text(p):
    with io.open(p, encoding='utf-8', errors='ignore') as fh:
        return fh.read()


def fm_values(text):
    """解析 front-matter。**必须支持 YAML 块标尺 `|-`**（多行值）——漏掉会把
    `keywords` 读成字面量 `|-`，索引第 2 段全丢而校验器仍报 PASS（假绿）。

    判据经 `LC.fm_block` 单源（禁在本文件另写一份解析——两实现对块标尺内空行的
    处理曾有分歧，续行被丢 ⇒ 索引第 2 列丢词，机械召回不可达）。
    """
    fm = LC.fm_block(text)
    if fm is None:
        return None
    return {k: v for k, v in fm.items() if v}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--success-dir', help='success/ 目录（默认按记忆根解析）')
    ap.add_argument('--out', help='索引写入路径（默认 <success-dir>/success_index.md）')
    args = ap.parse_args()

    if args.success_dir:
        sucdir = args.success_dir
        out = args.out or os.path.join(sucdir, 'success_index.md')
    else:
        root = LC.memory_root()
        if not root:
            sys.stderr.write('[SUC-GEN] 记忆根不可用（设 AI_MEMORY_DIR 或在含 .ai-memory/ 的目录运行）\n')
            return 3
        sucdir = os.path.join(root, 'success')
        # 默认输出经 LC 解析（复数索引布局/索引落根的形态可定位）；禁写死册目录
        out = args.out or LC.success_index_path() or os.path.join(sucdir, 'success_index.md')
    if not os.path.isdir(sucdir):
        print('success dir missing: %s' % sucdir)
        return 3

    files = sorted(glob.glob(os.path.join(sucdir, '**', 'SUC-*.md'), recursive=True))
    rows, bad, no_code = [], [], []
    for p in files:
        rel = os.path.relpath(p, sucdir).replace('\\', '/')
        name = os.path.basename(p)
        text = read_text(p)
        fm = fm_values(text)
        if fm is None:
            bad.append('%s (缺 front-matter)' % rel)
            continue
        miss = [k for k in KEYS if not fm.get(k)]
        if miss:
            bad.append('%s (缺/空 %s)' % (rel, '/'.join(miss)))
            continue
        t = TITLE_RE.search(text)
        title = t.group(1).strip() if t else name.replace('.md', '')
        kw = fm.get('keywords', '').replace('\n', ' ').strip()
        if not LC.code_tokens(kw):
            no_code.append('%s (keywords 无代码字面词 ⇒ 机械召回不可达)' % rel)
        # 值内半角 `|` 改写为全角 `｜`（半角是列分隔符，值内出现会使行多胞）
        kw = kw.replace('|', '｜')
        title_cell = title.replace('|', '｜')
        # 索引第 1 段不带 .md 后缀（确定性定位时补 .md 即可）
        rows.append('%s | %s | %s' % (rel[:-3] if rel.endswith('.md') else rel, kw, title_cell))

    if bad:
        print('[SUC-GEN] [FAIL] bad entries=%d（不写盘，防半迁移索引）' % len(bad))
        for x in bad:
            print('    - %s' % x)
        return 1

    body = ('# 正样本册索引（success/）\n\n'
            '> 索引＝生成物，禁手工追写；改单条后重跑 `python scripts/success_index_gen.py`。\n'
            '> 每行格式：`年/月/SUC-XXX | 触发关键词 | 标题`。\n\n'
            '## 索引区\n\n' + '\n'.join(rows) + '\n')
    with io.open(out, 'w', encoding='utf-8') as fh:
        fh.write(body)
    print('[SUC-GEN] written=%s rows=%d' % (out, len(rows)))
    if no_code:
        print('[SUC-GEN] 提示：%d 条 keywords 无代码字面词（仅统计，不阻断；机械召回通道不可达，建议人工补）'
              % len(no_code))
        for x in no_code:
            print('    - %s' % x)
    return 0


if __name__ == '__main__':
    sys.exit(main())
