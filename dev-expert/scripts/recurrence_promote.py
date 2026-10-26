#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升格建议扫描（薄 CLI）——判据全部来自 `ledger_judge.py`（单一实现）。

反样本册：RC≥3 且 Tasks≥2 且末核在 30 天窗口内（复发驱动）。
正样本册（--success-index 或自动发现）：hit_count≥3 且 Tasks≥2（复用驱动）。
两册口径有意不同——反册看「复发」，正册看「复用」，禁互相套用。

仅输出建议，不自动改写规则文件（升格由 Agent 读单条自评裁定并落可撤销处置段；
已标「不升/已升格」处置的单条不再列为候选——删段即恢复）。
不跨项目写禁忌不变。hit_count 缺失按 0，禁以缺失推定复用。

退出码：0 = 完成（无论有无建议）；2 = 反册索引缺失。
"""
import argparse
import io
import os
import sys
from datetime import datetime

try:  # 控制台 GBK 兼容：输出含中文/⇒ 时禁崩（SUC-015：留痕优先于美观）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'hooks'))
import ledger_common as LC  # noqa: E402
import ledger_judge as LJ  # noqa: E402


def _discover_suc_index(index_path):
    """正册索引自动发现：索引同级 → 索引/success/ → 记忆根/success/ → LC 解析。"""
    base = os.path.dirname(index_path)
    for cand in (os.path.join(base, 'success_index.md'),
                 os.path.join(base, 'success', 'success_index.md'),
                 os.path.join(os.path.dirname(base), 'success', 'success_index.md')):
        if os.path.isfile(cand):
            return cand
    return LC.success_index_path() or ''


def _has_err_entries(d):
    """目录（含任意层子目录：`errors/<年>/<月>/ERR-XXX.md` 是两层深）是否有 ERR-*.md 单条。"""
    if not os.path.isdir(d):
        return False
    for _base, _dirs, files in os.walk(d):
        if any(n.startswith('ERR-') and n.endswith('.md') for n in files):
            return True
    return False


def _has_suc_entries(d):
    """正册侧对称布局探测：索引落记忆根而单条在 success/ 子目录时，
    旧实现 md_path 拼接恒不命中 ⇒ 全部 SUC 静默 skip（未爆发隐患，先补对称探测）。"""
    if not os.path.isdir(d):
        return False
    for _base, _dirs, files in os.walk(d):
        if any(n.startswith('SUC-') and n.endswith('.md') for n in files):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description='升格建议扫描（判据见 ledger_judge）')
    parser.add_argument('--index', required=True, help='error_index.md 路径')
    parser.add_argument('--errors-dir', default='',
                        help='单条 ERR-XXX.md 目录（默认：索引所在目录或其 errors/ 子目录，按实际含单条者定）')
    parser.add_argument('--success-index', default='',
                        help='正册索引 success_index.md 路径（默认自动发现）')
    parser.add_argument(
        '--target',
        default='CLAUDE.md / AGENTS.md / project_memory.md（项目级记忆；具体项目的规则文件名不同则用 --target 覆盖）',
        help='建议 promote 的目标（默认项目级 Agent 记忆；若项目用特定规则文件如 主规则.mdc，用 --target 覆盖）')
    args = parser.parse_args()

    if not os.path.isfile(args.index):
        print('[RECUR-PROMOTE] 错误：反册索引不存在: %s' % args.index, file=sys.stderr)
        return 2
    errors_dir = args.errors_dir
    if not errors_dir:
        # 两种布局都认：索引在册目录内（errors/errors_index.md，条目在年/月子目录）
        # 与索引在记忆根、册在 errors/ 子目录（error_index.md）。
        base = os.path.dirname(args.index)
        errors_dir = base if _has_err_entries(base) else os.path.join(base, 'errors')

    rows = LC.index_rows(args.index, 'ERR')
    if not rows:
        print('[RECUR-PROMOTE] 索引无 ERR 条目')
        return 0
    today = datetime.now()
    # 判据单源：verdict 一律取 LJ.err_promote_candidates，禁在本 CLI 重写布尔
    # （历史教训：两处实现必漂移——ERR-226 族）
    cand = {eid for eid, _d in LJ.err_promote_candidates(args.index, errors_dir, today)}
    suggestions = 0
    print('[RECUR-PROMOTE] 扫描 %d 条 ERR，硬规则：>=%d次 / >=%d任务 / %d天窗口'
          % (len(rows), LJ.RECURRENCE_THRESHOLD, LJ.MIN_TASKS, LJ.WINDOW_DAYS))
    for r in rows:
        md_path = LC.ledger_md_path(errors_dir, r['eid'])  # 扁平/年月经兼容
        rc = LJ.parse_recurrence(md_path) if os.path.isfile(md_path) else None
        if not rc or not rc['count']:
            continue  # 字段未扩展/单条缺失，跳过
        count = LJ.to_int(rc['count'])
        tasks = LJ.tasks_of(md_path)
        last = LJ.to_date(rc['last']) or LJ.to_date(r['date'])
        in_window = (today - last).days <= LJ.WINDOW_DAYS if last else False
        denied = LJ.is_promote_denied(md_path)
        ok = r['eid'] in cand
        tag = '[PROMOTE]' if ok else '[skip]'
        print('[RECUR-PROMOTE] %s %s | count=%d tasks=%d last=%s window=%s%s'
              % (r['eid'], tag, count, tasks, rc['last'] or r['date'] or '-',
                 in_window, '（已标不升，删段即恢复）' if denied else ''))
        if ok:
            suggestions += 1
            print('      → 建议写入 %s：防重踩规则（来自 %s：%s）'
                  % (args.target, r['eid'], r['desc']))

    suc_suggestions = 0
    suc_index = args.success_index or _discover_suc_index(args.index)
    suc_rows = LC.index_rows(suc_index, 'SUC') if suc_index and os.path.isfile(suc_index) else []
    if suc_rows:
        # 单条目录探测与反册对称：索引同级 → 索引/success/ → 记忆根/success/
        suc_dir = os.path.dirname(suc_index)
        if not _has_suc_entries(suc_dir):
            for cand in (os.path.join(suc_dir, 'success'),
                         os.path.join(os.path.dirname(suc_dir), 'success')):
                if _has_suc_entries(cand):
                    suc_dir = cand
                    break
        print('[SUC-PROMOTE] 扫描 %d 条 SUC，正册判据：hit_count>=%d（复用） / Tasks>=%d'
              % (len(suc_rows), LJ.SUC_HIT_THRESHOLD, LJ.MIN_TASKS))
        # 判据单源：候选取 LJ.suc_promote_candidates，达标判据取 LJ.suc_promote_pass
        # （pass 返回编号列表，禁按 5 元组解包）
        pass_set = set(LJ.suc_promote_pass(LJ.suc_promote_candidates(suc_index, suc_dir)))
        for r in suc_rows:
            md_path = LC.ledger_md_path(suc_dir, r['eid'])  # 扁平/年月经兼容
            rc = LJ.parse_recurrence(md_path) if os.path.isfile(md_path) else None
            if not rc or rc['hit'] == '':
                print('[SUC-PROMOTE] %s [skip] | hit_count 缺失（禁以缺失推定复用）'
                      % r['eid'])
                continue
            hits = LJ.to_int(rc['hit'])
            tasks = LJ.tasks_of(md_path)
            denied = LJ.is_promote_denied(md_path)
            ok = r['eid'] in pass_set
            tag = '[PROMOTE]' if ok else '[skip]'
            print('[SUC-PROMOTE] %s %s | hits=%d tasks=%d%s'
                  % (r['eid'], tag, hits, tasks,
                     '（已标不升，删段即恢复）' if denied else ''))
            if ok:
                suc_suggestions += 1
                print('      → 建议升格到 %s：已验证做法（来自 %s：%s）；升格须写回滚点'
                      % (args.target, r['eid'], r['desc']))
    print('[RECUR-PROMOTE] 共 %d 条 ERR 满足 promote 条件；正册 %d 条满足升格条件'
          % (suggestions, suc_suggestions))
    return 0


if __name__ == '__main__':
    sys.exit(main())
