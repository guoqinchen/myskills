#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse: 反样本册（errors/）写入守卫（L1 治本——把约束前移到写入侧）。

校验（命中任一即 exit 2 拒绝，理由经 stdout 回传）：
- 写 `**/ERR-*.md`：须有 front-matter；`err/keywords/summary/type/category`
  必填且非空（**新建**另强制 `year_month`）；`type` ∈ {事实型, 决策失败型}；
  决策失败型正文须含 `错判点/正确判据/盲区` 三栏；`category` 须在值域内
  （兜底类「其他」须带非空括注）；`quality`/`utility` 存在时须为枚举档位；
  新建条目首见/末核须行内式且非占位；触发词须含可机械命中的代码字面词；
  新建条目的编号不得已被占用（索引 ∪ 磁盘并集）。
- 写册索引（`error_index.md`/`errors_index.md`）：**拒绝**（索引为
  `scripts/err_index_gen.py` 生成物），提示重跑生成器。

路径判别经 `ledger_common.ledger_target`（技能自有约定，禁硬编码任何项目目录）。
判据（值域/日期/触发词/编号）全部经 `ledger_common` 单源，禁在本文件另写正则
（ERR-226/099 族：同一判据两份实现必漂移）。

失败放行：载荷非法/缺字段/任何异常 → `exit 0` 并留痕（禁 fail-close 静默）。
逃生门：内容含独立成行的 `hook-allow` → 放行。
"""
import io
import os
import re
import sys

_HOOK_NAME = "err_entry_guard"
ALLOW_MARK = "hook-allow"
_BOM = '﻿'

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

try:  # 控制台 GBK 兼容（拒绝理由与留痕告警含中文；禁让写崩被 fail-open 吞掉）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FM_KEYS = ("err", "keywords", "summary", "type", "category")
# `year_month` 亦为新建必填：索引生成器逐条读取该键决定年月归组，缺失时生成直接 FAIL
# ⇒ 守卫必填集不含它就会出现「守卫放行 → 索引生成失败」的门禁口径分裂（ERR-226 族）。
FM_KEYS_NEW = FM_KEYS + ("year_month",)
VALID_TYPES = ("事实型", "决策失败型")
THREE_FIELDS = ("错判点", "正确判据", "盲区")
# 质量与效用双档位：枚举档位，禁 0-100 主观分；存在时才校验（存量不回写不受影响）。
VALID_QUALITY = ("可用", "待补", "不可用")
VALID_UTILITY = ("现行", "待复核", "已失效")

PATH_KEYS = ("file_path", "filePath", "path", "file")
CONTENT_KEYS = ("content", "new_str", "new_string", "text", "fileText",
                "newText", "new_text")


def _log_failopen(exc):
    """fail-open 留痕（禁静默——「未校验」与「校验通过」不可区分即假绿）。"""
    sys.stderr.write("[ERR-ENTRY] 本次写入未校验（fail-open）: %r\n" % (exc,))


def _payload():
    payload, err = LC.read_stdin_payload()
    if err is not None:
        _log_failopen(err)
        sys.stderr.write("[ERR-ENTRY] 载荷解析失败（BOM/JSON 非法），本条未校验: %s\n" % err)
    return payload if isinstance(payload, dict) else {}


def _field(payload, keys):
    ti = payload.get("tool_input") or {}
    for k in keys:
        v = ti.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _realign(s, nl):
    """把片段的行尾统一到目标文件的行尾（`\n` ↔ `\r\n`）。"""
    return s.replace('\r\n', '\n').replace('\n', nl)


def _merged_content(path, content, payload):
    """合成「写入后完整内容」——**禁把片段当全文**（ERR-212 治本）。

    直接校验 new_str 片段会把「改正文一行」误判为「缺 front-matter」而拒绝。优先级：
    1) `old_str/new_str` 能在文件里定位 ⇒ 按合并结果判定（能发现「编辑把
       front-matter 删了」这类破坏）；
    2) 键名变体（`old_string/new_string`）同样尝试，并对 CRLF 文件行尾归一后重试；
    3) 都拿不到 ⇒ 按「正文增量编辑」用**文件当前内容**判定（front-matter 存在性
      是文件自身属性，片段只承载被替换行）；片段首行是 `---`（整体重写）⇒ 以片段为准。
    已知收窄（明示）：路径 3 不校验片段内 fm 键新值，只保文件整体结构与片段内其它规则。
    """
    old_s = _field(payload, ("old_str", "old_string", "oldText", "old_text"))
    new_s = _field(payload, ("new_str", "new_string", "newText", "new_text"))
    if not os.path.isfile(path):
        return content                      # 新建：片段即全文
    try:
        cur = io.open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return content
    if old_s and new_s:
        nl = '\r\n' if '\r\n' in cur else '\n'
        for o, n in ((old_s, new_s), (_realign(old_s, nl), _realign(new_s, nl))):
            if o and o in cur:
                return cur.replace(o, n, 1)
    if content.lstrip(_BOM).lstrip().startswith('---'):
        return content                      # 整体重写：缺 fm 如实报错
    sys.stderr.write(
        '[ERR-ENTRY] 编辑 %s：未取到可定位的 old_str（键名/内容失配），按「正文增量编辑」'
        '处理——front-matter 存在性以**文件当前内容**判定（片段内 fm 键新值本次不校验）\n'
        % os.path.basename(path))
    return cur


def main():
    payload = _payload()
    path = _field(payload, PATH_KEYS)
    content = _field(payload, CONTENT_KEYS)
    if not path or not content:
        sys.exit(0)
    content = _merged_content(path, content, payload)

    kind = LC.ledger_target(path)
    if kind is None:
        sys.exit(0)                          # 非反册写目标：本守卫不管

    if any(ln.strip() == ALLOW_MARK for ln in content.splitlines()):
        sys.exit(0)

    if kind == 'err_index':
        sys.stdout.write(
            "[ERR-ENTRY] 索引为生成物，禁手工编辑：改单条后重跑 "
            "`python scripts/err_index_gen.py --out <err_index_path() 解析出的索引>`")
        sys.exit(2)

    errs = []
    # 新建＝目标文件尚不存在；编辑＝文件已存在。存量条目可能本就字段不全，
    # 若对编辑也强制全字段 ⇒ 这些条目被永久锁死、连改自己都改不了。
    is_new = not os.path.isfile(path)
    # 编辑语义 + 目标路径不存在 ⇒ 真因是**路径错**，不是缺 fm（失败信息须指真因）。
    _edit_intent = bool(_field(payload, ("old_str", "old_string", "oldText", "old_text"))
                        or _field(payload, ("new_str", "new_string", "newText", "new_text")))
    fm = None
    if is_new and _edit_intent:
        errs.append("目标文件不存在：%s（编辑语义但路径不存在 ⇒ 核年/月目录与编号，"
                    "禁凭印象拼路径；若确为新建请改用写入类工具）" % path)
    else:
        fm = LC.fm_block(content)
        if fm is None:
            errs.append("缺 YAML front-matter（新建与编辑均须有）")
    if fm is not None:
        if is_new:
            for k in FM_KEYS_NEW:
                if not fm.get(k):
                    errs.append("front-matter 缺字段: %s" % k)
            # year_month 须 YYYY/MM：畸形值令索引行与编号从消费方消失 ⇒ 撞号（与 err_index_gen 同口径）
            _ym = str(fm.get('year_month', '')).strip()
            if _ym and not re.match(r'^\d{4}/\d{2}$', _ym):
                errs.append("year_month 非法: %r（须 YYYY/MM，如 2026/10）" % _ym)
            if not LC.code_tokens(fm.get('keywords', '')):
                errs.append("keywords 无可机械命中的代码字面词：%s"
                            "（须含函数名/文件路径/后缀等真实会出现的字面词）"
                            % (fm.get('keywords', '')[:60],))
        t = fm.get("type", "")
        if t and t not in VALID_TYPES:
            errs.append("type 取值非法: %s（须为 事实型 或 决策失败型）" % t)
        cat_raw = fm.get("category", "")
        if cat_raw:
            cats = LC.load_categories()
            if not cats:
                sys.stderr.write("[ERR-ENTRY] category 值域不可用（域值表缺失），本次未校验（判据失效）\n")
            else:
                base = LC.strip_paren(cat_raw)
                if base not in cats:
                    errs.append("category 取值非法: %s（须为根因分类表内值；限定语请放括注内）"
                                % base)
                elif base == LC.FALLBACK_CAT and not re.match(
                        r'^\s*' + re.escape(LC.FALLBACK_CAT)
                        + r'\s*[（(]\s*[^\s（()）]', cat_raw):
                    errs.append(
                        "category 选兜底类「%s」时须在括注内写明真实根因，如「%s（流程缺失："
                        "评审环节无独立证据源）」" % (LC.FALLBACK_CAT, LC.FALLBACK_CAT))
        for _key, _vals in (("quality", VALID_QUALITY), ("utility", VALID_UTILITY)):
            _v = (fm.get(_key) or "").strip()
            if not _v:
                _m = re.search(r'(?:^|\n)\s*(?:[>\-*]\s*)?' + _key + r'\s*[:：]\s*([^\n]+)', content)
                _v = _m.group(1).strip() if _m else ""
            if _v and LC.strip_paren(_v) not in _vals:
                errs.append("%s 取值非法: %s（须为 %s 之一；来源/限定语请放括注内）"
                            % (_key, LC.strip_paren(_v), "/".join(_vals)))
        if is_new:
            for _nm, _en in (("首见", "First-Seen"), ("末核", "Last-Seen")):
                _d = LC.date_parse(content, _nm)
                _tag = "%s(%s)" % (_nm, _en)
                if not _d["date"]:
                    errs.append(
                        "缺或非法 %s: 新建条目正文须写 `- %s: YYYY-MM-DD`" % (_tag, _tag))
                elif _d["placeholder"]:
                    errs.append(
                        "%s 用了占位值 %s: 新建条目的日期必然可考，禁占位"
                        "（占位仅限存量补录，须写「（占位：原始记录缺失）」）"
                        % (_tag, _d["date"]))
                elif _d["form"] != "inline":
                    errs.append(
                        "%s 形态不规范（实测形态=%s）: 须写行内式 `- %s: YYYY-MM-DD`"
                        % (_tag, _d["form"] or "?", _tag))
        if t == "决策失败型":
            miss = [x for x in THREE_FIELDS if x not in content]
            if miss:
                errs.append("决策失败型缺三栏: %s" % "/".join(miss))
        eid = fm.get("err", "")
        m = re.match(r'^ERR-(\d+)$', eid)
        if m:
            used = LC.ids_used('err')
            n = int(m.group(1))
            mb = re.match(r'^ERR-(\d+)\.md$', os.path.basename(path))
            same = bool(mb and int(mb.group(1)) == n)
            # 文件名补零位数与编号不同（如 ERR-047.md vs 47），只可比数值不可拼串
            if n in used and not same:
                errs.append("编号已占用: %s（用 scripts/err_next_id.py 取号）" % eid)

    if errs:
        sys.stdout.write("[ERR-ENTRY] 拒绝写入 %s：\n  - %s"
                         % (os.path.basename(path), "\n  - ".join(errs)))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.exit(main())  # SystemExit 继承 BaseException，不会被下方 except 吞掉
    except Exception as exc:
        _log_failopen(exc)
        sys.exit(0)
