#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUC 单条字段合规校验（只读；与 `err_fields_check.py` 口径对称）。

校验项（判据见 `references/error-ledger.md` §3）：
  ① front-matter 五键（suc/year_month/type/keywords/summary）
  ② `type` 三值（真源＝error-ledger.md §3.2 类型判定表）
  ③ 统计 `Recurrence-Count` / `Tasks` 缺失（仅统计）
  ④ 引用行号失真（越界/临时资产 ⇒ 判不合规）
  ⑤ 引用未能验证（仅统计）
  ⑥ 命中统计键（hit_count/last_hit_at/low_quality_hit_count，存在时校验）
  ⑦ 正文必填（`Revisit if`/`验证证据`/`做法`/`场景` ⇒ **判不合规**——
     `Revisit if` 是正册唯一失效声明，缺失即永远不被退役评审看见）
  ⑧ `utility` 档位（存在时校验：现行/待复核/已失效）

解析全部经 `ledger_common` 单源。退出码与 verdict 同源：0=PASS / 1=FAIL（ERR-239）。
用法：python success_fields_check.py [--report FILE]
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

FM_KEYS = ('suc', 'year_month', 'type', 'keywords', 'summary')
BODY_KEYS = ('Revisit if', '验证证据', '做法', '场景')
VALID_UTILITY = ('现行', '待复核', '已失效')


def main():
    root = LC.memory_root()
    if not root:
        sys.stderr.write('[SUC-FIELDS] 记忆根不可用（设 AI_MEMORY_DIR 或在含 .ai-memory/ 的目录运行）\n')
        return 3  # 环境/自身错误＝3（禁与「校验 FAIL＝1」混淆）
    sucdir = os.path.join(root, 'success')
    if not os.path.isdir(sucdir):
        # 册目录缺失＝配置错误，禁输出 PASS 读成「账本健康」
        print('[SUC-FIELDS] success dir missing: %s（无法校验 ⇒ 退出 3）' % sucdir)
        return 3
    files = []
    for base, _dirs, names in os.walk(sucdir):
        for name in names:
            if name.startswith('SUC-') and name.endswith('.md'):
                files.append(os.path.join(base, name))
    files.sort()

    valid_types = LC.load_success_types()
    if not valid_types:
        print('[SUC-FIELDS] 类型值域解析为空（域值表缺失或结构变化），② 本次不判不合规')
    bad_fm, bad_type, no_rec, no_tasks = [], [], [], []
    bad_ref, unver_ref, bad_hit, miss_body, bad_util = [], [], [], [], []
    for path in files:
        rel = os.path.relpath(path, root).replace('\\', '/')
        text = io.open(path, encoding='utf-8', errors='ignore').read()
        fm = LC.fm_block(text) or {}
        miss = [k for k in FM_KEYS if not (fm.get(k) or '').strip()]
        if miss:
            bad_fm.append('%s (缺/空 %s)' % (rel, '/'.join(miss)))
        t = (fm.get('type') or '').strip()
        if t and valid_types and t not in valid_types:
            bad_type.append('%s (type=%s)' % (rel, t))
        _hard, _unver = LC.check_refs(text, root)
        for r in _hard:
            bad_ref.append('%s %s' % (rel, r))
        for r in _unver:
            unver_ref.append('%s %s' % (rel, r))
        if not LC.present(text, 'Recurrence-Count'):
            no_rec.append(rel)
        if not LC.present(text, 'Tasks'):
            no_tasks.append(rel)
        miss_b = [k for k in BODY_KEYS if not LC.present(text, k)]
        if miss_b:
            miss_body.append('%s (缺 %s)' % (rel, '/'.join(miss_b)))
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
        u = (fm.get('utility') or '').strip() or LC.value(text, 'utility')
        if u and LC.strip_paren(u) not in VALID_UTILITY:
            bad_util.append('%s (utility=%s)' % (rel, LC.strip_paren(u)))

    lines = ['[SUC-FIELDS] SUC files=%d' % len(files)]
    lines.append('[SUC-FIELDS] ① front-matter 不合规: %d' % len(bad_fm))
    lines += ['    - %s' % x for x in bad_fm]
    lines.append('[SUC-FIELDS] ② type 值域不合规: %d' % len(bad_type))
    lines += ['    - %s' % x for x in bad_type]
    lines.append('[SUC-FIELDS] ③ 缺 Recurrence-Count: %d / 缺 Tasks: %d（仅统计）'
                 % (len(no_rec), len(no_tasks)))
    lines.append('[SUC-FIELDS] ④ 引用行号失真: %d（与 errors 册同一实现；仅「行号越界」与'
                 '「临时资产引用」判不合规）' % len(bad_ref))
    lines += ['    - %s' % x for x in bad_ref]
    lines.append('[SUC-FIELDS] ⑤ 引用未能验证: %d（工作区外路径，仅统计——'
                 '「没验证到」≠「验证失败」）' % len(unver_ref))
    lines += ['    - %s' % x for x in unver_ref[:8]]
    lines.append('[SUC-FIELDS] ⑥ 命中统计键不合规: %d（存在时校验；存量未回写不判不合规）'
                 % len(bad_hit))
    lines += ['    - %s' % x for x in bad_hit]
    lines.append('[SUC-FIELDS] ⑦ 正文必填缺失: %d（`Revisit if` 是正册唯一失效声明，'
                 '缺失即永远不被退役评审看见 ⇒ 判不合规）' % len(miss_body))
    lines += ['    - %s' % x for x in miss_body]
    lines.append('[SUC-FIELDS] ⑧ utility 档位不合规: %d（取值 现行/待复核/已失效；'
                 '仅存在时校验）' % len(bad_util))
    lines += ['    - %s' % x for x in bad_util]
    verdict = 'PASS' if (not bad_fm and not bad_type and not bad_ref and not bad_hit
                         and not miss_body and not bad_util) else 'FAIL'
    lines.append('[SUC-FIELDS] 结论: %s' % verdict)
    text = '\n'.join(lines) + '\n'
    sys.stdout.write(text)
    if '--report' in sys.argv:
        # 禁 sys.argv[index+1] 裸取：末位参数 ⇒ IndexError ⇒ traceback + exit 1 被读成 FAIL
        try:
            rp = sys.argv[sys.argv.index('--report') + 1]
            if not rp.startswith('-'):
                with io.open(rp, 'w', encoding='utf-8') as fh:
                    fh.write(text)
                print('[SUC-FIELDS] report=%s' % rp)
            else:
                sys.stderr.write('[SUC-FIELDS] --report 缺路径参数（未写报告）\n')
        except (IndexError, OSError) as exc:
            sys.stderr.write('[SUC-FIELDS] --report 处理失败: %s\n' % exc)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
