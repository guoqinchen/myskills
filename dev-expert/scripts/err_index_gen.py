#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 ERR 单条 front-matter 生成反册索引（L3：单一数据源在单条，索引为生成物）。

- 行内容 = 单条 front-matter 的 `year_month` / `err` / `keywords` / `summary`（3 列主模板）。
- 头部说明从 `--header-from`（默认当前索引）的第一个 `##` 之前提取，原样保留。
- 活跃/归档由单条 front-matter 的 `archive: true` 决定；归档区不参与召回
  （`ledger_common.load_triggers` 遇「## 归档区」停止，两侧同源）。
- 缺 front-matter 或缺关键字段 ⇒ 报错并列写（禁静默跳过，防半迁移），退出码 1 不写盘。
- 默认不写盘；`--out FILE` 才写。

用法：
  python err_index_gen.py [--index FILE] [--header-from FILE] [--out FILE] [--summary-limit N]
"""
import argparse
import io
import os
import re
import sys

try:  # 控制台 GBK 兼容（索引内容与归档区说明含中文/⇒ 符号）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks'))
import ledger_common as LC  # noqa: E402

FILE_RE = re.compile(r'^ERR-(\d+)\.md$')
ARCHIVE_NOTE = ('（单条数≥30 / 索引>50 行 / 单条>500 行 ⇒ 触发归档评审；'
                '实际迁移限「末核>12个月且非环境级」或「连续 12 个月零复用且 '
                'Recurrence-Count=1」，索引移入此处；单条不移动目录）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', help='索引路径（默认按记忆根解析）')
    ap.add_argument('--header-from', help='头部说明来源（默认当前索引）')
    ap.add_argument('--out', help='写入路径（缺省＝stdout）')
    ap.add_argument('--summary-limit', type=int, default=0,
                    help='摘要最大字符数；0=不截断（只影响索引展示层）')
    args = ap.parse_args()

    root = LC.memory_root()
    if not root:
        sys.stderr.write('[ERR-GEN] 记忆根不可用（设 AI_MEMORY_DIR 或在含 .ai-memory/ 的目录运行）\n')
        sys.exit(3)
    errd = os.path.join(root, 'errors')
    # 默认路径经 LC 解析（复数索引布局 errors/errors_index.md 亦可定位）；
    # 禁写死根下 error_index.md——头部说明会整段丢失且误导 Agent
    idx_path = args.index or LC.err_index_path() or os.path.join(root, 'error_index.md')
    header_src = args.header_from or idx_path

    header = ''
    if os.path.isfile(header_src):
        ht = io.open(header_src, encoding='utf-8', errors='ignore').read()
        cut = ht.find('## ')
        header = ht[:cut].rstrip() if cut > 0 else ht.rstrip()

    entries, bad, not_usable = [], [], []
    if os.path.isdir(errd):
        for dp, _dn, fn in os.walk(errd):
            for f in sorted(fn):
                m = FILE_RE.match(f)
                if not m:
                    continue
                text = io.open(os.path.join(dp, f), encoding='utf-8', errors='ignore').read()
                fm = LC.fm_block(text)
                if fm is None:
                    bad.append((f, 'no front-matter'))
                    continue
                miss = [k for k in ('err', 'year_month', 'keywords', 'summary')
                        if not fm.get(k)]
                if miss:
                    bad.append((f, 'missing ' + ','.join(miss)))
                    continue
                # year_month 须 YYYY/MM：畸形值（2026-8 / 2026-08-01）会令索引行与
                # 编号双双从消费方消失（_MAIN_ID_RE 不匹配），且 ids_used 漏计 ⇒ 撞号
                if not re.match(r'^\d{4}/\d{2}$', str(fm['year_month']).strip()):
                    bad.append((f, 'year_month 非法（须 YYYY/MM）: %r' % fm['year_month']))
                    continue
                if not LC.code_tokens(fm.get('keywords', '')):
                    not_usable.append(f)  # 告警不阻断：整册索引生成失败比个别不可用更糟
                entries.append((int(m.group(1)), fm))

    if bad:
        # 半迁移防线（docstring 契约）：缺 front-matter/缺关键字段 ⇒ 列写后退出 1 不写盘——
        # 带病写出的索引会静默丢失这些条目，退出码 0 被自动化读成成功。
        print('[FAIL] bad entries=%d（退出 1 不写盘，防半迁移索引）' % len(bad))
        for f, why in bad[:10]:
            print('  - %s: %s' % (f, why))
        sys.exit(1)
    if not_usable:
        # 仅「触发词不可用」告警：个别不可用不该阻断整册索引生成（docstring:76 口径）
        print('[GEN][warn] 触发词不可用（机械召回不可达）%d 条：%s'
              '（告警不阻断，索引照常生成）'
              % (len(not_usable), ', '.join(not_usable[:10])))

    entries.sort(key=lambda x: x[0])
    active = [e for e in entries if str(e[1].get('archive', '')).lower() != 'true']
    archive = [e for e in entries if str(e[1].get('archive', '')).lower() == 'true']

    out = []
    if header:
        out.append(header)
        out.append('')

    def row(fm):
        """索引行；多行值压成单行（keywords 换行→`/` 连接，summary 换行→空格），
        防一条索引行裂成多行被下游当成独立行解析。值内半角 `|` 改写为全角 `｜`
        （半角 `|` 是列分隔符，值内出现会使行多胞）。"""
        kw = '/'.join(x.strip() for x in str(fm['keywords']).splitlines() if x.strip())
        s = ' '.join(x.strip() for x in str(fm['summary']).splitlines() if x.strip())
        lim = args.summary_limit
        if lim and len(s) > lim:
            s = s[:lim].rstrip() + '…'
        kw = kw.replace('|', '｜')
        s = s.replace('|', '｜')
        return '%s/%s | %s | %s' % (fm['year_month'], fm['err'], kw, s)

    out.append('## 活跃坑')
    for _n, fm in active:
        out.append(row(fm))
    out.append('')
    out.append('## 归档区')
    out.append(ARCHIVE_NOTE)
    for _n, fm in archive:
        out.append(row(fm))
    content = '\n'.join(out) + '\n'

    if not args.out:
        sys.stdout.write(content)
        print('[GEN] rows=%d active=%d archive=%d (no --out, stdout only)'
              % (len(entries), len(active), len(archive)), file=sys.stderr)
        sys.exit(0)

    with io.open(args.out, 'w', encoding='utf-8') as f:
        f.write(content)
    print('[GEN] written=%s rows=%d active=%d archive=%d'
          % (args.out, len(entries), len(active), len(archive)))
    sys.exit(0)


if __name__ == '__main__':
    main()
