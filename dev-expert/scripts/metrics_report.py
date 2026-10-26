#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结果指标只读聚合（M1-M10 / R1 / R1-SUC / M9 / M9-SUC / M10）。

口径与 `references/error-ledger.md` 同源；判据（升格/归档/退役/反哺/阈值/计划状态）
全部来自 `ledger_judge.py`（单一实现），解析原语来自 `hooks/ledger_common.py`——
禁在本文件另写一份判据或解析（ERR-226/099 族）。

纪律：
  - 每项指标同报分子与分母；分母=0 或样本不足 ⇒ 输出「样本不足，不输出比率」；
  - 指标仅用于定位瓶颈，**禁用于个人绩效**；
  - 候选型指标（R1/R1-SUC/M9-SUC/M10）全部带处置出口且已处置条数**计数可见**
    （候选无出口＝刷屏噪音，ERR-228；报过 ≠ 处理过，ERR-109）；
  - 文案由检测结果驱动，禁无条件固定提示冒充结论（ERR-232）；
  - 升格/退役/反哺裁定归 **Agent 自评**（ERR-242）——本工具只产候选与事实。

用法：`python metrics_report.py [--out PATH]`（默认只 stdout；--out 另落盘一份）。
"""
import argparse
import io
import os
import re
import sys
from datetime import date as _date, datetime as _dt, timedelta as _td

try:  # 控制台 GBK 兼容：输出含 ⇒/⚠ 等符号时禁崩（SUC-015：留痕优先于美观）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), 'hooks'))
sys.path.insert(0, _HERE)
import ledger_common as LC  # noqa: E402
import ledger_judge as LJ  # noqa: E402


def ratio_line(name, num, den, note=''):
    if den <= 0:
        return '%s 样本不足，不输出比率（分子=%d 分母=0）%s' % (name, num, note)
    return '%s %d/%d = %.1f%%%s' % (name, num, den, num * 100.0 / den, note)


def _ledger_files(d, prefix):
    out = []
    for base, _dirs, files in os.walk(d):
        out += [os.path.join(base, n) for n in files
                if n.startswith(prefix + '-') and n.endswith('.md')]
    return sorted(out)


def _read(path):
    try:
        with io.open(path, encoding='utf-8', errors='ignore') as fh:
            return fh.read()
    except OSError:
        return ''


def _plan_dir():
    """定位项目 Plan 目录（M1 消费）：PROJECT_ROOT → cwd → cwd 逐级上溯，首个存在者。"""
    cands = []
    env = os.environ.get('PROJECT_ROOT')
    if env:
        cands.append(os.path.join(env, 'Plan'))
    cands.append(os.path.join(os.getcwd(), 'Plan'))
    d = os.getcwd()
    while True:
        cands.append(os.path.join(d, 'Plan'))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    for c in cands:
        if os.path.isdir(c):
            return c
    return ''


def main():
    lines = ['[METRICS] 结果指标只读聚合（用途：定位瓶颈；禁用于个人绩效）']
    root = LC.memory_root()
    if not root:
        lines.append('[METRICS] 记忆根不可解析（AI_MEMORY_DIR/PROJECT_ROOT/上溯均未命中）'
                     ' ⇒ 除 M1 外全部指标样本不足')
    errdir = os.path.join(root, 'errors') if root else ''
    sucdir = os.path.join(root, 'success') if root else ''
    errs = _ledger_files(errdir, 'ERR') if errdir else []
    sucs = _ledger_files(sucdir, 'SUC') if sucdir else []
    # 索引路径经 LC 单源解析（复数索引/索引落根布局均可定位）；禁写死册目录名——
    # 定位失败时禁把「索引没找到」呈现成「0 条」（假绿），须显式告警
    eidx = LC.err_index_path() or ''
    sidx = LC.success_index_path() or ''
    if root and not (eidx and os.path.isfile(eidx)):
        lines.append('[METRICS][warn] 反册索引未定位（LC 解析未命中）：R1 相关指标样本不足')
    if root and not (sidx and os.path.isfile(sidx)):
        lines.append('[METRICS][warn] 正册索引未定位（LC 解析未命中）：R1-SUC 相关指标样本不足')

    # ---- M1 计划收敛率 ----
    pdir = _plan_dir()
    plans = ([os.path.join(pdir, n) for n in os.listdir(pdir)
              if n.endswith('_plan.md')] if pdir else [])
    done = parsed = 0
    unparsed = []
    for p in sorted(plans):
        st = LJ.plan_state(p)
        if st:
            parsed += 1
            if st == '已完成':
                done += 1
        else:
            unparsed.append(os.path.basename(p)[:-3])
    lines.append('[METRICS] M1 计划收敛率: ' + ratio_line(
        'M1', done, parsed, '（plan 总数=%d%s）'
        % (len(plans), '' if pdir else '，Plan 目录未定位')))
    if unparsed:
        lines.append('[METRICS] M1 附 状态不可解析: %d 个（未计入分母）%s'
                     % (len(unparsed), '，如：' + '、'.join(unparsed[:5])))

    # ---- M2/M3 反册 ----
    rec_ge2 = rec_has = full = 0
    for p in errs:
        text = _read(p)
        fm = LC.fm_block(text) or {}
        # RC 解析经 LJ.parse_recurrence 单源（禁在本文件另写前导数字正则——LJ._num 族）
        _rc = LJ.parse_recurrence(p)
        n = int(_rc['count']) if _rc and _rc['count'] else None
        if n is not None:
            rec_has += 1
            if n >= 2:
                rec_ge2 += 1
        ty = (fm.get('type') or '').strip() or LC.value(text, '类型')
        if (ty in LJ.ERR_TYPES and n is not None and LC.value(text, 'Tasks')):
            full += 1
    lines.append('[METRICS] M2 ERR 复发率: ' + ratio_line(
        'M2', rec_ge2, rec_has, '（ERR 总数=%d）' % len(errs)))
    lines.append('[METRICS] M3 ERR 字段完整率: ' + ratio_line(
        'M3', full, len(errs), '（口径＝类型＋Recurrence-Count＋Tasks 三者齐备）'))

    # ---- R1 规则阈值巡检 ----
    idx_rows = len(LC.index_rows(eidx, 'ERR'))
    trig = (len(errs) >= 30) or (idx_rows > 50)
    lines.append('[METRICS] R1 规则阈值巡检：ERR 单条 %d 条 / 索引活跃行 %d 行 ⇒ %s'
                 % (len(errs), idx_rows,
                    '触发归档评审（人工裁定，不自动迁移）' if trig else '未触发'))

    # ---- M4/M5 正册 ----
    suc_types = LC.load_success_types()
    suc_hit = suc_full = 0
    for p in sucs:
        text = io.open(p, encoding='utf-8', errors='ignore').read()
        fm = LC.fm_block(text) or {}
        if LC.value(text, 'hit_count') or (fm.get('hit_count') or '').strip():
            suc_hit += 1
        ty = (fm.get('type') or '').strip() or LC.value(text, '类型')
        _rc = LJ.parse_recurrence(p)
        m = int(_rc['count']) if _rc and _rc['count'] else None
        if (ty and m is not None and LC.value(text, 'Tasks')
                and (not suc_types or ty in suc_types)):
            suc_full += 1
    lines.append('[METRICS] M4 SUC 消费覆盖率: ' + ratio_line(
        'M4', suc_hit, len(sucs), '（SUC 总数=%d）' % len(sucs)))
    lines.append('[METRICS] M5 SUC 字段完整率: ' + ratio_line(
        'M5', suc_full, len(sucs),
        '（口径＝类型＋Recurrence-Count＋Tasks 三者齐备，对齐 M3 同构）'))
    if not suc_types:
        lines.append('[METRICS] M5 口径降级：类型值域解析为空（域值表不可达），'
                     '本项只判三字段齐备、不判类型值域')

    # ---- M6/M7 分类结构健康度 ----
    cats = LC.load_categories()
    cat_of = {}
    for p in errs:
        text = io.open(p, encoding='utf-8', errors='ignore').read()
        fm = LC.fm_block(text) or {}
        k = LC.strip_paren((fm.get('category') or '').strip())
        if k:
            cat_of[k] = cat_of.get(k, 0) + 1
    cat_total = sum(cat_of.values())
    fb_n = cat_of.get(LC.FALLBACK_CAT, 0)
    lines.append('[METRICS] M6 兜底类占比: ' + ratio_line(
        'M6', fb_n, cat_total, '（兜底类「%s」/ 有 category 的 ERR %d 条，阈值 %d%%）'
        % (LC.FALLBACK_CAT, cat_total, LJ.FB_WARN_PCT)))
    top_k, top_n = '', 0
    for k, v in cat_of.items():
        if v > top_n:
            top_k, top_n = k, v
    lines.append('[METRICS] M7 最大分类桶占比: ' + ratio_line(
        'M7', top_n, cat_total, '（最大桶「%s」，阈值 %d%%）'
        % (top_k, LJ.TOPCAT_WARN_PCT)))
    if cat_total >= LJ.MIN_CAT_SAMPLE:
        if fb_n * 100.0 / cat_total > LJ.FB_WARN_PCT:
            lines.append('[METRICS] ⚠ R2 兜底类告警: 占比 %.1f%% > %d%% ⇒ 兜底类有'
                         '垃圾桶化风险，须评审「既有类判据不足需补」或「根本不是分类问题」'
                         % (fb_n * 100.0 / cat_total, LJ.FB_WARN_PCT))
        if top_n * 100.0 / cat_total > LJ.TOPCAT_WARN_PCT:
            lines.append('[METRICS] ⚠ R2 分类集中度告警: 最大桶「%s」占 %.1f%% > %d%% ⇒ '
                         '该类判据过宽、正在吞并其它层，须评审收窄'
                         % (top_k, top_n * 100.0 / cat_total, LJ.TOPCAT_WARN_PCT))
    if not cats:
        lines.append('[METRICS] M6/M7 口径降级: category 值域解析为空（域值表不可达），'
                     '本项只统计实际分布、不判值域合规（解析失效须告警，禁静默放行）')

    # ---- R1 升规则候选（反册） ----
    cands = LJ.err_promote_candidates(eidx, errdir) if eidx else []
    lines.append('[METRICS] R1 升规则候选 %d 条%s'
                 % (len(cands), ('：' + '、'.join(e for e, _d in cands)) if cands else '（无）'))
    if cands:
        lines.append('[METRICS] R1 处置状态：以上 %d 条**均未处置**（无「不升」/「已升格」'
                     '标记）——须逐条裁定：升规则（Agent 自评裁定后落笔）或标「不升」'
                     '（在 ERR 单条 append 理由）' % len(cands))
        ok_n, miss = 0, []
        for cid, _d in cands:
            md = os.path.join(errdir, cid + '.md')
            if not os.path.isfile(md):
                for base, _dirs, files in os.walk(errdir):
                    if cid + '.md' in files:
                        md = os.path.join(base, cid + '.md')
                        break
            rc = LJ.parse_recurrence(md) if os.path.isfile(md) else None
            q = (rc or {}).get('quality', '')
            u = (rc or {}).get('utility', '')
            if q == '可用' and u == '现行':
                ok_n += 1
            else:
                miss.append('%s(%s/%s)' % (cid, q or '缺', u or '缺'))
        lines.append('[METRICS] R1 判据提示：升规则须 quality=可用 且 utility=现行；'
                     '本批候选 %d/%d 条**已具备**该两字段%s'
                     % (ok_n, len(cands), '' if not miss else '，未满足：' + '、'.join(miss)))
    else:
        lines.append('[METRICS] R1 判据提示：升规则须 quality=可用 且 utility=现行'
                     '（无候选，本项不适用）')

    # ---- R1-SUC 正册升格候选 ----
    sc = LJ.suc_promote_candidates(sidx, sucdir) if sidx else []
    sp = LJ.suc_promote_pass(sc)
    sden = len([1 for _e, _h, _t, den, _d in sc if den])
    lines.append('[METRICS] R1-SUC 正册升格候选 %d 条%s'
                 % (len(sp), ('：' + '、'.join(sp)) if sp else '（无）'))
    lines.append('[METRICS] R1-SUC 处置状态：%s'
                 % (('以上 %d 条均未处置（无「不升」/「已升格」标记）——须逐条裁定：'
                     '升格（Agent 自评裁定后落笔）或在该 SUC 单条标「不升」；'
                     '另已处置 %d 条（不升/已升格）' % (len(sp), sden)) if sp
                    else '无待处置候选；另已处置 %d 条（不升/已升格）' % sden))

    # ---- M9 归档可迁 ----
    ac, und = LJ.archive_candidates(errdir) if errdir else ([], [])
    lines.append('[METRICS] M9 归档可迁: %d/%d（判据：末核≥12月 或 首见≥12月且RC=1；'
                 '0 条＝评审已执行且无可迁）%s'
                 % (len(ac), len(errs),
                    '' if not ac else '，候选：' + '、'.join(ac[:10])))
    lines.append('[METRICS] M9 附 日期不可判（占位/缺失，不参与归档判定）: %d 条%s'
                 % (len(und), '' if not und else '，如：' + '、'.join(und[:8])))

    # ---- M9-SUC 正册退役候选 ----
    rc_, rden, ym_min = LJ.retire_candidates(sucdir) if sucdir else ([], 0, None)
    lines.append('[METRICS] M9-SUC 正册退役候选: %d/%d（判据四取一：year_month≥12月 ｜ '
                 '零复用≥6月 ｜ 低质命中 lowq≥5 且占比≥50%% 且 hit_count≥10 ｜ '
                 'utility∈{待复核,已失效}；**「零复用」与「低质」都只作信号、不等于失效**，'
                 '是否退役须人工裁定；「不退役」出口＝单条标「退役处置」段）%s%s'
                 % (len(rc_), len(sucs),
                    '' if not rc_ else '，候选：' + '、'.join(rc_[:10]),
                    ('；另已处置 %d 条（不退役）' % rden) if rden else ''))
    if ym_min:
        min_ago = LJ.months_ago(ym_min + '-01') or 0
        if min_ago < 12:
            reach = ('时间档两条均不可达（零复用档需 ≥6 月）' if min_ago < 6
                     else '仅「零复用≥6月」时间档可达，「year_month≥12月」档不可达')
            if rc_:
                tail = ('本项 %d 条来自**信号档**（低质命中 / utility），禁读作「时间档已评审」'
                        % len(rc_))
            elif rden:
                tail = ('信号档命中 %d 条、**均已裁定处置（不退役）**⇒ 净候选 0（≠ 未判）；'
                        '时间档未达阈值 ⇒ 全部判据尚未走完，禁读作「已评审且无可迁」' % rden)
            else:
                tail = ('信号档（低质命中 / utility 自报状态）无时间门槛、**已可达并已判**：'
                        '本项 0 条＝两条信号判据均无命中（≠ 未判）；时间档未达阈值 ⇒ '
                        '全部判据尚未走完，禁读作「已评审且无可迁」')
            lines.append('[METRICS] M9-SUC 可达性：全册最早 year_month=%s（距今 %d 月）⇒ %s；%s'
                         % (ym_min, min_ago, reach, tail))

    # ---- M10 跨册反哺 ----
    xf = LJ.xfeed_candidates(errdir, sucdir) if errdir else {
        'new': [], 'stock': [], 'linked': 0, 'denied': 0}
    total_steps = xf['linked'] + len(xf['new']) + len(xf['stock']) + xf['denied']
    lines.append('[METRICS] M10 跨册反哺: 步骤化「正确做法」%d 条 → 已交叉引用 %d / '
                 '新增未引用 %d（候选，首见≤%d天）／存量未引用 %d（仅可见：规则「存量不批量'
                 '追溯」，不要求清零）／已标不反哺 %d（判「不反哺」须在该 ERR append '
                 '`## 反哺处置` + `**处置：不反哺**（理由）`，删段即恢复候选）%s'
                 % (total_steps, xf['linked'], len(xf['new']), LJ.M10_NEW_DAYS,
                    len(xf['stock']), xf['denied'],
                    '' if not xf['new'] else '，新增候选如：' + '、'.join(xf['new'][:8])))

    text = '\n'.join(lines) + '\n'
    ap = argparse.ArgumentParser(description='结果指标只读聚合（判据见 ledger_judge）')
    ap.add_argument('--out', default='', help='报告另落盘路径（默认只 stdout）')
    args = ap.parse_args()
    if args.out:
        with io.open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
