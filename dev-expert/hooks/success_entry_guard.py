#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse: 正样本册（success/）写入守卫——与 `err_entry_guard.py` 对称。

校验（命中任一即 exit 2 拒绝，理由经 stdout 回传）：
- 写 `**/SUC-*.md`：须有 front-matter；**新建**时 `suc`/`year_month`/`type`/
  `keywords`/`summary` 必填且非空；`type` ∈ 类型判定三值（真源＝error-ledger.md
  §3.2 表，经 `ledger_common` 解析）；正文须含 `类型`/`场景`/`做法`/`验证证据`/
  `Recurrence-Count`/`Tasks`/`Revisit if`（`Revisit if` 是正册唯一失效声明，
  缺失即永远不被退役评审看见）；`utility` 存在时须为枚举档位；触发词须含可机械
  命中的代码字面词；新建条目编号不得已被占用（索引 ∪ 磁盘并集）。
- 写册索引（`success_index.md`）：**拒绝**（索引为 `scripts/success_index_gen.py`
  生成物），提示重跑生成器。
- 非正册路径：放行。

复用纪律（禁另写第二份，ERR-226 族）：协议层（载荷解析含 BOM 剥、编辑内容合成、
fail-open 留痕、front-matter 解析）从 `err_entry_guard` 导入；判据经
`ledger_common` 单源——写入侧与存量扫描侧（`success_fields_check.py`）必须同一口径，
否则会出现「守卫放行 → 扫描 FAIL」的门禁口径分裂。

失败放行：依赖缺失/任何异常 → `exit 0` 并留痕（禁 fail-close 静默）。
逃生门：内容含独立成行的 `hook-allow` → 放行。
"""
import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402
from err_entry_guard import (_field, _log_failopen, _merged_content,  # noqa: E402
                             _payload, ALLOW_MARK)

try:  # 控制台 GBK 兼容（拒绝理由与留痕告警含中文；禁让写崩被 fail-open 吞掉）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FM_KEYS = ("suc", "year_month", "type", "keywords", "summary")
# 正文必填：模板逐字段对齐；`Revisit if` 为唯一失效声明（与 `utility` 档位构成
# 「自述＋现行状态」两层），必须拦在写入口。
BODY_KEYS = ("类型", "场景", "做法", "验证证据", "Recurrence-Count", "Tasks",
             "Revisit if")
VALID_UTILITY = ("现行", "待复核", "已失效")


def main():
    payload = _payload()
    path = _field(payload, ("file_path", "filePath", "path", "file"))
    content = _field(payload, ("content", "new_str", "new_string", "text", "fileText",
                               "newText", "new_text"))
    if not path or not content:
        sys.exit(0)                          # 协议通：无内容即无可校验

    kind = LC.ledger_target(path)
    if kind is None:
        sys.exit(0)
    if kind == 'suc_index':
        sys.stdout.write(
            "[SUC-ENTRY] 拒绝写入 %s：索引是 success_index_gen.py 的生成物，"
            "禁手工编辑；请改单条后重跑：\n  python scripts/success_index_gen.py "
            "--out <记忆根>/success/success_index.md" % os.path.basename(path))
        sys.exit(2)
    if kind != 'suc':
        sys.exit(0)                          # 反册目标不归本守卫

    if any(ln.strip() == ALLOW_MARK for ln in content.splitlines()):
        sys.exit(0)

    errs = []
    is_new = not os.path.isfile(path)
    _edit_intent = bool(_field(payload, ("old_str", "old_string", "oldText", "old_text"))
                        or _field(payload, ("new_str", "new_string", "newText", "new_text")))
    if is_new and _edit_intent:
        errs.append("目标文件不存在：%s（编辑语义但路径不存在 ⇒ 先核 success/<年>/<月>/ "
                    "与编号，禁凭印象拼路径）" % path)
    else:
        content = _merged_content(path, content, payload)
        fm = LC.fm_block(content)
        if fm is None:
            errs.append("缺 YAML front-matter（新建与编辑均须有）")
        else:
            if is_new:
                for k in FM_KEYS:
                    if not fm.get(k):
                        errs.append("front-matter 缺字段: %s" % k)
                if not LC.code_tokens(fm.get('keywords', '')):
                    errs.append("keywords 无可机械命中的代码字面词：%s"
                                "（须含函数名/文件路径/后缀等真实会出现的字面词）"
                                % (fm.get('keywords', '')[:60],))
            t = fm.get("type", "")
            if t:
                valid = LC.load_success_types()
                if not valid:
                    sys.stderr.write("[SUC-ENTRY] 类型值域解析为空（域值表缺失或结构变化），"
                                     "② 本次不判不合规\n")
                elif t not in valid:
                    errs.append("type 取值非法: %s（须为类型判定三值之一；真源＝"
                                "error-ledger.md §3.2 表，禁自造值）" % t)
            if is_new:
                miss = [k for k in BODY_KEYS if not LC.present(content, k)]
                if miss:
                    errs.append("正文缺字段: %s（`Revisit if` 是正册唯一失效声明，必填）"
                                % "/".join(miss))
            u = (fm.get("utility") or "").strip()
            if not u:
                m = re.search(r'(?:^|\n)\s*(?:[>\-*]\s*)?utility\s*[:：]\s*([^\n]+)', content)
                u = m.group(1).strip() if m else ""
            if u and LC.strip_paren(u) not in VALID_UTILITY:
                errs.append("utility 取值非法: %s（须为 %s 之一）"
                            % (LC.strip_paren(u), "/".join(VALID_UTILITY)))
            eid = fm.get("suc", "")
            m = re.match(r'^SUC-(\d+)$', eid)
            if m and is_new:
                n = int(m.group(1))
                used = LC.ids_used('suc')
                if n in used:
                    errs.append("编号已占用: %s（用 scripts/err_next_id.py --book suc 取号）"
                                % eid)

    if errs:
        sys.stdout.write("[SUC-ENTRY] 拒绝写入 %s：\n  - %s"
                         % (os.path.basename(path), "\n  - ".join(errs)))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail-open 但必须留痕（静默比崩溃更隐蔽）
        try:
            _log_failopen(exc)
        except Exception:
            sys.stderr.write("[SUC-ENTRY] fail-open: %r\n" % (exc,))
        sys.exit(0)
