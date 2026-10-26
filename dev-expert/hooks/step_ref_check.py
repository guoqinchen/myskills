#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨文件步骤号一致性检查器。

扫描 SKILL.md / README.md / FAQ.md 中所有形如「<reference名> 第<中文数字>步」的引用，
比对目标 reference 文件实际「第N步」章节号，报告不匹配项。

reference 名单按 `references/*.md` 动态发现（含 25 个专项 reference），禁硬编码白名单；
步骤标题 H2/H3 均认（`root-cause-debugging`/`dev-navigation` 用 H2）；同一句出现多个
步骤号时逐个回溯最近的 reference 名，禁只查首个。

用于防止步骤号漂移（如 v1.9.0 新增「第二步点五」导致后续步骤号 +1 后，
历史变更日志/FAQ 中的步骤号引用未同步更新）。

用法：
  python step_ref_check.py [--root <技能根目录>]

退出码：
  0 = 全部匹配
  1 = 发现不匹配
  3 = 校验器自身错误（如 references 目录不存在；与 rc=1 分流，供下游区分「真悬空」与「自身失败」）
"""
import argparse
import os
import re
import sys

# 中文数字映射
CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# 步骤号引用与 reference 名分开扫描：同一句可有多个「第N步」，逐个回溯最近的 ref
CN_STEP_RE = re.compile(r'第([一二三四五六七八九十]+)步')
REF_TOKEN_RE = re.compile(r'`?([a-z][a-z0-9-]+)(?:\.md)?`?')
REF_WINDOW = 120  # 「第N步」向左回溯上限；再按句末/换行截断，防跨句误配


def left_context(content, pos):
    """取「第N步」左侧同一句内的文本：上限 REF_WINDOW，截断在最近句末/换行/表格分隔后。"""
    seg = content[max(0, pos - REF_WINDOW):pos]
    cut = max(seg.rfind('。'), seg.rfind('；'), seg.rfind('\n'), seg.rfind('|'))
    return seg[cut + 1:] if cut >= 0 else seg

# 匹配目标文件中的「第N步」章节标题（H2/H3 均认）
STEP_HEAD_RE = re.compile(r'^#{2,3}\s*第([一二三四五六七八九十]+)步', re.MULTILINE)


def discover_refs(ref_root):
    """目录实存 ∪ routing.md 登记：新增 ref 自动覆盖，删除文件后仍能报悬空。"""
    refs_dir = os.path.join(ref_root, "references")
    names = set()
    try:
        names = {os.path.splitext(n)[0] for n in os.listdir(refs_dir) if n.endswith(".md")}
    except OSError:
        return set()
    try:
        with open(os.path.join(refs_dir, "routing.md"), encoding="utf-8", errors="ignore") as f:
            names |= set(re.findall(r'references/([a-z0-9-]+)\.md', f.read()))
    except (OSError, UnicodeDecodeError):
        pass
    return names


def cn_to_int(cn):
    """中文数字转整数（支持一到九十九）。"""
    if cn == "十":
        return 10
    if cn.startswith("十"):
        return 10 + CN_NUM.get(cn[1:], 0)
    if cn.endswith("十"):
        return CN_NUM.get(cn[:-1], 0) * 10
    if "十" in cn:
        parts = cn.split("十")
        return CN_NUM.get(parts[0], 0) * 10 + CN_NUM.get(parts[1], 0)
    return CN_NUM.get(cn, 0)


def int_to_cn(n):
    """整数转中文数字（支持一到十）。"""
    cn_map = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
              6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
    return cn_map.get(n, str(n))


def find_step_heads(content):
    """在文件内容中查找所有「第N步」章节，返回步骤号集合。"""
    steps = {}
    for m in STEP_HEAD_RE.finditer(content):
        cn = m.group(1)
        n = cn_to_int(cn)
        if n > 0:
            steps[n] = cn
    return steps


def check_file(ref_root, src_path, src_name, known_refs):
    """检查单个源文件中的所有步骤号引用（同句多号逐个回溯最近 ref）。"""
    try:
        with open(src_path, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as e:
        # UnicodeDecodeError 是 ValueError 子类（非 OSError）：文件被存成 GBK 时
        # 旧实现穿透 except 以 exit 1 崩溃，被下游 step_ref_guard 误判为「发现不匹配」假告警
        print("[STEP-CHECK] 错误：读取 %s 失败: %s" % (src_name, e), file=sys.stderr)
        return [], 0

    issues = []
    checked = 0
    seen = set()  # 去重：(ref, expected)
    for m in CN_STEP_RE.finditer(content):
        cn_step = m.group(1)
        expected = cn_to_int(cn_step)
        if expected <= 0:
            continue
        left = left_context(content, m.start())
        names = [c.group(1) for c in REF_TOKEN_RE.finditer(left)]
        ref_name = next((n for n in reversed(names) if n in known_refs), None)
        if ref_name is None:
            continue
        key = (ref_name, expected)
        if key in seen:
            continue
        seen.add(key)
        ref_path = os.path.join(ref_root, "references", ref_name + ".md")
        ctx = (left + m.group(0)).replace("\n", " ").strip()[-80:]
        if not os.path.isfile(ref_path):
            issues.append({
                "src": src_name,
                "ref": ref_name,
                "expected_cn": cn_step,
                "expected_n": expected,
                "actual": "文件不存在（悬空引用）",
                "context": ctx,
            })
            continue
        try:
            with open(ref_path, encoding="utf-8") as f:
                ref_content = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        actual_steps = find_step_heads(ref_content)
        checked += 1
        if expected not in actual_steps:
            actual_str = "、".join(
                "第%s步" % actual_steps[k] for k in sorted(actual_steps)
            ) if actual_steps else "无步骤章节"
            issues.append({
                "src": src_name,
                "ref": ref_name,
                "expected_cn": cn_step,
                "expected_n": expected,
                "actual": actual_str,
                "context": ctx,
            })
    return issues, checked


def _fix_stdout_encoding():
    """Windows 默认控制台为 GBK，直接 print emoji（✅/❌）会抛 UnicodeEncodeError。
    若 stdout 编码非 utf-8 且无缓冲能力，回退到对无法编码字符做替换，保证脚本不崩。"""
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") not in (
            "utf8",
        ):
            import io
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
    except Exception:
        pass


def main():
    _fix_stdout_encoding()
    parser = argparse.ArgumentParser(
        description="跨文件步骤号一致性检查器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        default=None,
        help="技能根目录（默认：脚本上级目录）",
    )
    args = parser.parse_args()
    root = args.root or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    refs_dir = os.path.join(root, "references")
    if not os.path.isdir(refs_dir):
        print("[STEP-CHECK] 错误：references 目录不存在: %s" % refs_dir, file=sys.stderr)
        return 3  # 校验器自身错误，与「发现不匹配」的 rc=1 分流（下游据码判定，防误报）

    src_files = ["SKILL.md", "README.md", "FAQ.md"]
    known_refs = discover_refs(root)
    all_issues = []
    total_checked = 0
    for src in src_files:
        src_path = os.path.join(root, src)
        if not os.path.isfile(src_path):
            continue
        issues, checked = check_file(root, src_path, src, known_refs)
        all_issues.extend(issues)
        total_checked += checked

    print("[STEP-CHECK] 检查完成：扫描 %d 处步骤号引用" % total_checked)
    if not all_issues:
        print("[STEP-CHECK] ✅ 全部匹配")
        return 0
    print("[STEP-CHECK] ❌ 发现 %d 处不匹配：" % len(all_issues))
    for i, issue in enumerate(all_issues, 1):
        print("  %d. [%s] %s 期望 第%s步(%d)，实际 %s" % (
            i, issue["src"], issue["ref"],
            issue["expected_cn"], issue["expected_n"], issue["actual"]
        ))
        print("     上下文: %s" % issue["context"])
    return 1


if __name__ == "__main__":
    sys.exit(main())
