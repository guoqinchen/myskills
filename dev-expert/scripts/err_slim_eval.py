#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""索引摘要截断的「压缩率 vs 召回损失」评估工具（定档前必跑）。

背景：索引已改为 `err_index_gen.py` 的生成物，压缩摘要只需 `--summary-limit`。
但压缩与召回损失近似 1:1（体积主体＝路径＋关键词列，而关键词是机械召回的命脉），
故**定档前必须先跑本工具**，禁凭估算拍档位。

判据口径：
  - 基线＝不截断（`--summary-limit` 不传）生成的索引；
  - 召回损失＝基线行中**高频触发词**的可见行数在各档位下的保留率（触发词默认从
    基线关键词列自动派生——按频率取 top N，亦可 `--words` 覆写）；
  - 输出每档 shrink%（体积压缩）/ keep%（触发词保留）/ lost%（逐词丢失明细）。
  - 结论由人下：本工具只给数据，禁自动改档。

用法：
  python err_slim_eval.py [--gen PATH_TO_GEN] [--words 词1,词2,...] [--top N]
"""
import argparse
import collections
import io
import os
import re
import subprocess
import sys
import tempfile

try:  # 控制台 GBK 兼容：输出含中文/⇒ 时禁崩（SUC-015：留痕优先于美观）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), 'hooks'))
import ledger_common as LC  # noqa: E402

PY = sys.executable
LIMITS = (200, 120, 80, 60, 40)
ROW = re.compile(r'^\d{4}/\d{2}/ERR-\d+', re.M)
DEFAULT_TOP = 10


def _gen_index(gen, tmp, limit=None):
    cmd = [PY, gen, '--out', tmp]
    if limit:
        cmd += ['--summary-limit', str(limit)]
    try:
        subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', timeout=180)
    except Exception:
        return []
    if not os.path.isfile(tmp):
        return []
    t = io.open(tmp, encoding='utf-8', errors='ignore').read()
    return [x for x in t.splitlines() if ROW.match(x.strip())]


def _derive_words(rows, top):
    """从基线行派生高频触发词：取关键词列（第 2 段，按 `/`、`、` 切分），
    按频率取 top N（同频取更长者——更长＝更具体＝召回价值更高）。"""
    cnt = collections.Counter()
    for r in rows:
        cells = [c.strip() for c in r.strip().strip('|').split('|')]
        if len(cells) < 2:
            continue
        for w in re.split(r'[/，、,；;・]+', cells[1]):
            w = w.strip()
            if len(w) >= 2:
                cnt[w] += 1
    ranked = sorted(cnt.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    return [w for w, _n in ranked[:top]]


def main():
    ap = argparse.ArgumentParser(description='索引摘要截断定档评估')
    ap.add_argument('--gen', default=os.path.join(_HERE, 'err_index_gen.py'),
                    help='err_index_gen.py 路径（默认：本脚本同目录）')
    ap.add_argument('--words', default='',
                    help='召回观测词（逗号分隔；默认从基线关键词列自动派生 top10）')
    ap.add_argument('--top', type=int, default=DEFAULT_TOP,
                    help='自动派生触发词个数（默认 10）')
    args = ap.parse_args()

    if not os.path.isfile(args.gen):
        print('[FAIL] generator missing: %s' % args.gen)
        return 1
    if not LC.memory_root():
        print('[FAIL] 记忆根不可解析（AI_MEMORY_DIR/PROJECT_ROOT/上溯均未命中）')
        return 1
    fd, tmp = tempfile.mkstemp(prefix='_err_slim_eval.', suffix='.md')
    os.close(fd)
    try:
        base = _gen_index(args.gen, tmp, 0)
        if not base:
            print('[FAIL] generator produced no rows (deleted/empty errors dir?)')
            return 1
        words = ([w.strip() for w in args.words.split(',') if w.strip()]
                 if args.words else _derive_words(base, args.top))
        if not words:
            print('[FAIL] 召回观测词为空（基线无关键词列？用 --words 显式指定）')
            return 1
        avg0 = sum(len(x) for x in base) // len(base)
        hits0 = {w: sum(1 for x in base if w in x) for w in words}
        total0 = sum(hits0.values()) or 1
        print('baseline rows=%d avg_chars=%d' % (len(base), avg0))
        print('baseline ' + ' '.join('%s=%d' % (w, hits0[w]) for w in words))
        for lim in LIMITS:
            rows = _gen_index(args.gen, tmp, lim)
            if not rows:
                print('limit=%-3d (no output)' % lim)
                continue
            hits = {w: sum(1 for x in rows if w in x) for w in words}
            tot = sum(hits.values())
            avg = sum(len(x) for x in rows) // len(rows)
            lost = ['%s(%d->%d)' % (w, hits0[w], hits[w])
                    for w in words if hits[w] < hits0[w]]
            print('limit=%-3d avg=%-4d shrink=%d%% keep=%d%% lost=%s'
                  % (lim, avg, int(round((avg0 - avg) * 100.0 / avg0)),
                     int(round(tot * 100.0 / total0)), ','.join(lost) or '-'))
        print('结论由人下：shrink 高而 keep 低的档位＝拿召回换体积，禁选；'
              '两指标接近的档位方可考虑，且改档后须同批重跑本工具确认。')
        return 0
    finally:
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


if __name__ == '__main__':
    sys.exit(main())
