#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ERR 单条字段合规校验（只读）。判据见 `references/error-ledger.md`
「根因分类（值域纪律）」与「决策失败型三栏」两节（**引节名、禁引行号**——行号随编辑漂移）。

校验项：
  ① `类型:` 取值须为 事实型 | 决策失败型
  ② 决策失败型须含 错判点 / 正确判据 / 盲区 三栏
  ③ 统计 `Recurrence-Count` / `Tasks` 缺失清单（仅统计，不判不合规——历史条目禁机械补 1）
  ④ `category` 值域（真源＝error-ledger.md §2.6 表；括注剥离后比对）
  ⑤ 引用行号失真（行号越界 / 临时资产引用 ⇒ 判不合规）
  ⑥ 引用未能验证（工作区外/已删除 ⇒ 仅统计，「没验证到」≠「验证失败」）
  ⑦ 命中统计键（hit_count/last_hit_at/low_quality_hit_count，存在时校验）
  ⑧ 首见/末核（行内式规范形态；存量六形态由 ledger_common 统一解析）

解析全部经 `ledger_common` 单源（禁在本文件另写正则——ERR-226/099 族：
同一判据两份实现必漂移，表现为「校验器 PASS、消费方拿空值」的静默失效）。

退出码与 verdict 同源：0=PASS / 1=FAIL（禁恒 return 0——凭退出码判定的自动化
会把不合规读成通过，ERR-239）。用法：
  python err_fields_check.py [--report FILE]
"""
import io
import os
import re
import sys

try:  # 控制台 GBK 兼容：输出含 ⇒ 等符号时禁崩（SUC-015：留痕优先于美观）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks'))
import ledger_common as LC  # noqa: E402


def main():
    root = LC.memory_root()
    if not root:
        sys.stderr.write('[ERR-FIELDS] 记忆根不可用（设 AI_MEMORY_DIR 或在含 .ai-memory/ 的目录运行）\n')
        return 3  # 环境/自身错误＝3（禁与「校验 FAIL＝1」混淆）
    errd = os.path.join(root, 'errors')
    if not os.path.isdir(errd):
        # 册目录缺失＝配置错误（AI_MEMORY_DIR 指错等），禁输出 PASS 读成「账本健康」
        print('[ERR-FIELDS] errors dir missing: %s（无法校验 ⇒ 退出 3）' % errd)
        return 3
    files = []
    for base, _dirs, names in os.walk(errd):
        for name in names:
            if name.startswith('ERR-') and name.endswith('.md'):
                files.append(os.path.join(base, name))
    files.sort()

    valid_cats = LC.load_categories()
    if not valid_cats:
        print('[ERR-FIELDS] category 值域解析为空（域值表缺失或结构变化），④ 本次不判不合规')
    bad_type, bad_cat, bad_ref, unver_ref, missing_cols = [], [], [], [], []
    no_rec, no_tasks, bad_hit, miss_date = [], [], [], []
    for path in files:
        rel = os.path.relpath(path, root).replace('\\', '/')
        text = io.open(path, encoding='utf-8', errors='ignore').read()
        t = LC.fm_value(text, 'type') or LC.value(text, '类型')
        if t not in ('事实型', '决策失败型'):
            bad_type.append('%s (类型=%s)' % (rel, t or 'MISSING'))
        c = LC.strip_paren(LC.fm_value(text, 'category') or LC.value(text, '根因分类'))
        if valid_cats and c not in valid_cats:
            bad_cat.append('%s (category=%s)' % (rel, c or 'MISSING'))
        _hard, _unver = LC.check_refs(text, root)
        for r in _hard:
            bad_ref.append('%s %s' % (rel, r))
        for r in _unver:
            unver_ref.append('%s %s' % (rel, r))
        if t == '决策失败型':
            miss = [k for k in ('错判点', '正确判据', '盲区') if not LC.present(text, k)]
            if miss:
                missing_cols.append('%s (缺 %s)' % (rel, '/'.join(miss)))
        if not LC.present(text, 'Recurrence-Count'):
            no_rec.append(rel)
        if not LC.present(text, 'Tasks'):
            no_tasks.append(rel)
        # ⑧ 与写侧同口径：行内式（`- 首见(First-Seen): YYYY-MM-DD`）
        for _nm in ('首见', '末核'):
            _d = LC.date_parse(text, _nm)
            if not _d['date']:
                miss_date.append('%s (缺 %s)' % (rel, _nm))
            elif _d['form'] != 'inline':
                miss_date.append('%s (%s 形态非行内式: 实测=%s)' % (rel, _nm, _d['form']))
        # ⑦ 存在时校验类型；存量未回写不判不合规
        raw_hit = LC.fm_value(text, 'hit_count')
        if raw_hit and not re.match(r'^\d+$', raw_hit.strip()):
            bad_hit.append('%s (hit_count=%s 非非负整数)' % (rel, raw_hit.strip()))
        raw_last = LC.fm_value(text, 'last_hit_at')
        if raw_last and raw_last.strip() != 'null' and not re.match(
                r'^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?$', raw_last.strip()):
            bad_hit.append('%s (last_hit_at=%s 非 ISO 日期或 null)' % (rel, raw_last.strip()))
        raw_lowq = LC.fm_value(text, 'low_quality_hit_count')
        if raw_lowq and not re.match(r'^\d+$', raw_lowq.strip()):
            bad_hit.append('%s (low_quality_hit_count=%s 非非负整数)' % (rel, raw_lowq.strip()))

    lines = ['[ERR-FIELDS] ERR files=%d' % len(files)]
    lines.append('[ERR-FIELDS] ① 类型值不合规: %d' % len(bad_type))
    lines += ['    - %s' % x for x in bad_type]
    lines.append('[ERR-FIELDS] ② 决策失败型缺三栏: %d' % len(missing_cols))
    lines += ['    - %s' % x for x in missing_cols]
    lines.append('[ERR-FIELDS] ③ 缺 Recurrence-Count: %d / 缺 Tasks: %d（仅统计，历史条目不判不合规）'
                 % (len(no_rec), len(no_tasks)))
    lines += ['    - 缺RC: %s' % x for x in no_rec[:8]]
    lines.append('[ERR-FIELDS] ④ category 值域不合规: %d（真源=error-ledger.md 根因分类表，括注已剥离后比对）'
                 % len(bad_cat))
    lines += ['    - %s' % x for x in bad_cat]
    lines.append('[ERR-FIELDS] ⑤ 引用行号失真: %d（仅「行号越界」与「临时资产引用」判不合规；'
                 '裸文件名不归判据、URL 已剔除）' % len(bad_ref))
    lines += ['    - %s' % x for x in bad_ref]
    lines.append('[ERR-FIELDS] ⑥ 引用未能验证: %d（工作区外路径无法验证，仅统计——'
                 '「没验证到」≠「验证失败」）' % len(unver_ref))
    lines += ['    - %s' % x for x in unver_ref[:8]]
    lines.append('[ERR-FIELDS] ⑦ 命中统计键不合规: %d（hit_count 须非负整数／last_hit_at 须 ISO '
                 '日期或 null／low_quality_hit_count 须非负整数；缺失不判——存量未回写）' % len(bad_hit))
    lines += ['    - %s' % x for x in bad_hit]
    lines.append('[ERR-FIELDS] ⑧ 首见/末核不合规: %d（判据＝**行内式** '
                 '`- 首见(First-Seen): YYYY-MM-DD`，与写侧 err_entry_guard 新建要求同口径；'
                 '解析唯一实现＝ledger_common.date_parse）' % len(miss_date))
    lines += ['    - %s' % x for x in miss_date[:8]]
    verdict = 'PASS' if (not bad_type and not bad_cat and not bad_ref and not missing_cols
                         and not bad_hit and not miss_date) else 'FAIL'
    lines.append('[ERR-FIELDS] 结论: %s' % verdict)
    text = '\n'.join(lines) + '\n'
    sys.stdout.write(text)
    if '--report' in sys.argv:
        # 禁 sys.argv[index+1] 裸取：末位参数 ⇒ IndexError ⇒ traceback + exit 1 被读成 FAIL
        try:
            rp = sys.argv[sys.argv.index('--report') + 1]
            if not rp.startswith('-'):
                with io.open(rp, 'w', encoding='utf-8') as fh:
                    fh.write(text)
                print('[ERR-FIELDS] report=%s' % rp)
            else:
                sys.stderr.write('[ERR-FIELDS] --report 缺路径参数（未写报告）\n')
        except (IndexError, OSError) as exc:
            sys.stderr.write('[ERR-FIELDS] --report 处理失败: %s\n' % exc)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
