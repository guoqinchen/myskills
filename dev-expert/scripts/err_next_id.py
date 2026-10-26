#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正反两册下一个可用编号（L2：编号自动分配，禁凭印象填号）。

同时扫描册索引与磁盘单条，取最大编号 +1，并校验该号在两处均未占用。只读、不写盘。
口径＝`ledger_common.ids_used`（索引 ∪ 磁盘并集，单一实现；ERR-226 族教训：
取号避开并集、占用判定只判磁盘 ⇒ 幽灵索引行会让占用判定放行被刻意避开的编号）。

用法：
  python err_next_id.py [--book err|suc]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks'))
import ledger_common as LC  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', choices=('err', 'suc'), default='err',
                    help='册别：err=反样本册（默认）/ suc=正样本册')
    args = ap.parse_args()

    if LC.memory_root() is None:
        print('[FAIL] 记忆根不可解析：设 AI_MEMORY_DIR，或把记忆根按技能约定放在 '
              '{PROJECT_ROOT}/.ai-memory')
        sys.exit(3)  # 环境/自身错误＝3（禁与「发现问题＝1」混淆）

    idx = LC.ids_index(args.book)
    fil = LC.ids_files(args.book)
    # 并集口径经 LC.ids_used 单源（禁在本文件内联重写——第二份实现必漂移）
    alln = LC.ids_used(args.book)
    cur = max(alln) if alln else 0
    nxt = cur + 1
    prefix = 'ERR' if args.book == 'err' else 'SUC'

    print('[%s-NEXT-ID] index_ids=%d file_ids=%d max=%d'
          % (prefix, len(idx), len(fil), cur))
    print('[%s-NEXT-ID] next=%s-%d' % (prefix, prefix, nxt))
    if idx != fil:
        print('[WARN] index ids != file ids (diff=%s)'
              % sorted(idx ^ fil)[:5])
    print('[%s-NEXT-ID] OK' % prefix)
    sys.exit(0)


if __name__ == '__main__':
    main()
