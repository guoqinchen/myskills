#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""领域自进化工具（dev-expert）

接到未被任何子技能覆盖的领域（小程序 / 移动 App 等）时，按技能既有范式
生成专项 reference 并完成四件套注册，全程可机械校验、可回滚。

命令：
  --detect "<任务描述>"     判定是否领域缺口（只读）
  --scaffold <domain>      生成 v0.1 草稿到 references/.drafts/
  --validate <domain>      校验草稿（判据数 / 证据锚 / 必备章节）
  --register <domain>      dry-run 预览注册动作；加 --apply 才落盘
  --check                  全量一致性（孤儿 / 悬空 / 计数）
  --selftest               在临时副本上跑端到端自测

纪律：
  - 任何写入前生成 .bak；写后回读校验
  - 默认 dry-run，--apply 才写盘
  - 域名白名单，防路径遍历
  - 结果可写 --log 文件（规避子进程 stdout 被终端吞没）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path


def _fix_stdio():
    """stdout 固定 UTF-8：Windows 管道默认 cp936 会把中文结果写成 GBK 字节。"""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


DOMAIN_RE = re.compile(r"^[a-z][a-z0-9-]{2,30}$")
SUBSECTION_INDEX = "## 子技能索引"
SUBSECTION_MAP = "## 专项 reference 映射"
ROUTE_HEADER = "| 领域 | 触发信号 |"
FRAMEWORK_DOCS = {"routing.md", "agent-reasoning-patterns.md"}
PLACEHOLDER_RE = re.compile(r"^\s*(?:$|—|-|待补|TODO|TBD)\s*$")
# 中文 2 字命中时过滤通用词，避免"帮我/这个"把任意任务都判成已覆盖
STOP_GRAMS = {"帮我", "我的", "我们", "这个", "那个", "一下", "一个", "什么", "怎么", "如何", "需要", "可以", "现在"}


class Result:
    def __init__(self, name: str):
        self.name = name
        self.lines: list[str] = []
        self.ok = True
        self.data: dict = {}

    def info(self, msg: str) -> None:
        self.lines.append(msg)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.lines.append("FAIL: " + msg)

    def render(self) -> str:
        head = f"{self.name}=" + ("PASS" if self.ok else "FAIL")
        return "\n".join([head] + ["  " + x for x in self.lines])


def read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    parts = cells(line)
    return bool(parts) and all(p and set(p) <= set("-: ") for p in parts)


def table_line_indexes(lines: list[str], header_prefix: str) -> list[int]:
    start = None
    for i, line in enumerate(lines):
        if line.startswith(header_prefix):
            start = i
            break
    if start is None:
        return []
    out: list[int] = []
    i = start + 1
    while i < len(lines) and lines[i].strip().startswith("|"):
        out.append(i)
        i += 1
    return out


class Toolkit:
    def __init__(self, root: Path):
        self.root = root
        self.ref_dir = root / "references"
        self.routing = self.ref_dir / "routing.md"
        self.readme = root / "README.md"
        self.keywords = root / "scripts" / "domain_keywords.json"
        self.draft_dir = self.ref_dir / ".drafts"

    # ---------- 基础 ----------
    def load_domains(self) -> dict:
        data = json.loads(read_text(self.keywords))
        return data.get("domains", {})

    def registered(self, domain: str) -> bool:
        if (self.ref_dir / f"{domain}.md").exists():
            return True
        mapping = self.special_mapping()
        return f"{domain}.md" in mapping

    def special_mapping(self) -> set[str]:
        lines = read_text(self.routing).splitlines()
        idxs = table_line_indexes(lines, "| 专项 reference |")
        out: set[str] = set()
        for i in idxs:
            row = cells(lines[i])
            if len(row) < 2 or is_separator(lines[i]):
                continue
            m = re.search(r"references/([\w.-]+\.md)", row[1])
            if m:
                out.add(m.group(1))
        return out

    def subskills(self) -> set[str]:
        lines = read_text(self.routing).splitlines()
        start = next((i for i, l in enumerate(lines) if l.startswith(SUBSECTION_INDEX)), None)
        if start is None:
            return set()
        out: set[str] = set()
        i = start + 1
        while i < len(lines) and not lines[i].startswith("## "):
            if lines[i].strip().startswith("|") and not is_separator(lines[i]):
                row = cells(lines[i])
                if len(row) >= 3:
                    m = re.search(r"references/([\w.-]+\.md)", row[2])
                    if m:
                        out.add(m.group(1))
            i += 1
        return out

    def declare_gap(self, domain: str, hits: list[str], meta: dict) -> str:
        nearest = ", ".join(meta.get("nearest", [])) or "（无）"
        return (
            f"[DOMAIN-GAP: {domain}] 命中词：{'、'.join(hits)}\n"
            f"  本领域无专项判据；以下结论将以通用判据（{nearest}）替代，可能与领域规范不符。\n"
            f"  可进化：--scaffold {domain} → 取证填充 → --validate → --register --apply"
        )

    # ---------- 三路信号 ----------
    def route_hits(self, text: str) -> list[str]:
        """「领域路由表」触发信号命中 → 命中的首选 reference 列表（整段或 2 字词命中）。"""
        lines = read_text(self.routing).splitlines()
        hits: list[str] = []
        for i in table_line_indexes(lines, ROUTE_HEADER):
            if is_separator(lines[i]):
                continue
            row = cells(lines[i])
            if len(row) < 3:
                continue
            matched = False
            for seg in re.split(r"[、,，/]", row[1]):
                seg = seg.strip(" `*")
                if len(seg) < 2:
                    continue
                if re.fullmatch(r"[A-Za-z0-9 .+#/-]+", seg):
                    # ASCII 触发词须整词命中，禁 2-gram（否则 "it" 会同时命中 JUnit/audit/critique）
                    if re.search(r"(?<![A-Za-z0-9])" + re.escape(seg) + r"(?![A-Za-z0-9])", text, re.I):
                        matched = True
                        break
                    continue
                if seg in text:
                    matched = True
                    break
                grams = {seg[j:j + 2] for j in range(len(seg) - 1)}
                if any(g in text for g in grams if g not in STOP_GRAMS):
                    matched = True
                    break
            if matched:
                hits.extend(re.findall(r"`([^`]+)`", row[2]))
        return sorted(set(hits))

    def exclusion_hits(self, text: str) -> list[tuple[str, str]]:
        """扫各 reference 的「不适用/不覆盖/不在范围」声明，取其中的技术术语；命中即强缺口信号。"""
        marks = ("不适用", "不覆盖", "不在范围")
        seen: set[tuple[str, str]] = set()
        out: list[tuple[str, str]] = []
        for p in sorted(self.ref_dir.glob("*.md")):
            for line in read_text(p).splitlines():
                if not any(m in line for m in marks):
                    continue
                for tok in re.findall(r"[A-Za-z][A-Za-z0-9.+#/-]{1,24}", line):
                    if not re.search(r"(?<![A-Za-z0-9])" + re.escape(tok) + r"(?![A-Za-z0-9])", text, re.I):
                        continue
                    key = (tok.lower(), p.stem)
                    if key not in seen:
                        seen.add(key)
                        out.append((tok, p.stem))
        return out

    def unknown_terms(self, text: str) -> list[str]:
        """任务中的 ASCII 技术词，若在全部 reference 文本中均未出现 ⇒ 可能是新领域术语。"""
        corpus = "\n".join(read_text(p) for p in self.ref_dir.glob("*.md")).lower()
        stop = {"the", "and", "for", "with", "api", "json", "http", "https", "www", "com", "app", "url"}
        out: list[str] = []
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{2,24}", text):
            if tok.lower() in stop or tok.lower() in corpus or tok in out:
                continue
            out.append(tok)
        return out[:8]

    # ---------- detect ----------
    def detect(self, text: str) -> Result:
        res = Result("DETECT")
        domains = self.load_domains()
        route = self.route_hits(text)
        excl = self.exclusion_hits(text)
        unknown = self.unknown_terms(text)

        cache_gaps: dict[str, list[str]] = {}
        for name, meta in domains.items():
            hits: list[str] = []
            for kw in meta.get("keywords", []):
                if re.fullmatch(r"[A-Za-z0-9 .+-]+", kw):
                    if re.search(r"(?<![A-Za-z0-9])" + re.escape(kw) + r"(?![A-Za-z0-9])", text, re.I):
                        hits.append(kw)
                elif kw in text:
                    hits.append(kw)
            if hits and not self.registered(name):
                cache_gaps[name] = hits

        if excl and not route:
            verdict = "GAP"
            why = "强信号：reference 明确声明不覆盖该技术"
        elif cache_gaps:
            verdict = "GAP"
            why = "已知领域且无对应专项判据"
        elif not route:
            if unknown:
                verdict = "GAP"
                why = "无任何 reference 命中，且含未登记技术词（按未覆盖处理，请语义复核）"
            else:
                verdict = "UNSURE"
                why = "无 reference 命中且无技术词，需语义判定"
        elif unknown:
            verdict = "UNSURE"
            why = "有 reference 命中，但存在未登记技术词，需语义裁决"
        else:
            verdict = "COVERED"
            why = "有 reference 命中，无排除/未登记信号"

        res.info(f"VERDICT={verdict}（{why}）")
        if route:
            res.info("route_hits: " + ", ".join(route))
        for tok, ref in excl:
            res.info(f"exclusion: {tok} ← {ref}（该文件声明不适用）")
        if unknown:
            res.info("unknown_terms: " + ", ".join(unknown))
        for name, hits in cache_gaps.items():
            res.info(self.declare_gap(name, hits, domains.get(name, {})))
        if verdict == "GAP" and not cache_gaps and not excl:
            res.info("无专项判据：`--scaffold <domain> --title <中文名>` 生成后取证填充。")
        res.data = {
            "verdict": verdict,
            "reason": why,
            "route_hits": route,
            "exclusions": [{"term": t, "ref": r} for t, r in excl],
            "cache_gaps": cache_gaps,
            "unknown_terms": unknown,
        }
        return res

    # ---------- scaffold ----------
    def scaffold(self, domain: str, title: str, force: bool = False) -> Result:
        res = Result("SCAFFOLD")
        if not DOMAIN_RE.match(domain):
            res.fail(f"域名非法：{domain}（须 ^[a-z][a-z0-9-]{{2,30}}$）")
            return res
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        target = self.draft_dir / f"{domain}.md"
        if target.exists() and not force:
            res.fail(f"草稿已存在：{target}（加 --force 覆盖）")
            return res
        template = (
            f"# {title}专项（{domain}）\n\n"
            "> 版本: 0.1-provisional ｜ 证据源: （官方文档 URL / 项目路径）｜ 已验证任务: 0\n"
            "> 每条判据须带**证据锚**（官方文档 `URL#章节` 或项目 `文件:行号`），无锚不得注册。\n\n"
            "## 输入要求\n\n"
            f"- 何时加载：任务涉及 {title} 的工程实现 / 排错 / 审核时\n"
            "- 不适用：（填写：与相邻领域的边界，如不含 H5 / 不含后端）\n\n"
            "## 核心判据（≥5 条）\n\n"
            "| 判据 | 反例（常见错配） | 证据锚 | Revisit if |\n"
            "|---|---|---|---|\n"
            "| — | — | — | — |\n"
            "| — | — | — | — |\n"
            "| — | — | — | — |\n"
            "| — | — | — | — |\n"
            "| — | — | — | — |\n\n"
            "## 执行流程（写入 Step 挂接，缺则不得注册）\n\n"
            "- Step 2 方案：按判据给出候选与取舍（禁止只给结论）\n"
            "- Step 3 执行：逐步对照判据，偏离处显式标注理由\n"
            "- Step 4 验证：按「## 验证清单」逐项取证\n\n"
            "## 输出格式\n\n"
            "- 交付须含：采用了哪些判据 / 未覆盖项 / 证据位置\n\n"
            "## 失败回退机制\n\n"
            "| 失败类型 | 回退动作 |\n"
            "|---|---|\n"
            "| 判据与本领域文档冲突 | 以官方文档为准，标 `[PROV]` 并登记 Revisit |\n"
            "| 本文件无对应判据 | 声明缺口，回 `routing.md`「领域缺口识别与进化」补判据 |\n\n"
            "## 关联 reference\n\n"
            "- 通用实现 → `code-generation`\n"
            "- 接口契约 → `api-design`\n"
            "- 风格对齐 → `style-alignment`\n\n"
            "## 验证清单\n\n"
            "- [ ] ≥5 条判据，均可判真假\n"
            "- [ ] 每条有证据锚，可回源\n"
            "- [ ] 执行流程已挂接 Step 2/3/4\n"
            "- [ ] 1 个真实任务 E2E 通过\n"
        )
        write_text(target, template)
        res.info(f"已生成草稿：{target}")
        res.info("下一步：填充判据（每条带锚）→ --validate")
        return res

    # ---------- validate ----------
    def _draft_path(self, domain: str) -> Path:
        draft = self.draft_dir / f"{domain}.md"
        return draft if draft.exists() else self.ref_dir / f"{domain}.md"

    def validate(self, domain: str) -> Result:
        res = Result("VALIDATE")
        path = self._draft_path(domain)
        if not path.exists():
            res.fail(f"找不到草稿或 reference：{path}")
            return res
        text = read_text(path)
        required = ("## 输入要求", "## 核心判据", "## 执行流程", "## 输出格式",
                    "## 失败回退机制", "## 关联 reference", "## 验证清单")
        for sec in required:
            if sec not in text:
                res.fail(f"缺章节：{sec}")
        if not re.search(r"(?:^version:|\b版本[:：])\s*\S+", text, re.M):
            res.fail("缺版本标记（首版须为 0.1-provisional）")
        if "Step" not in text:
            res.fail("执行流程未挂接七步闭环（须出现 Step N）")
        if re.search(r"\b(TODO|TBD)\b", text):
            res.fail("含 TODO/TBD 占位")

        lines = text.splitlines()
        try:
            start = lines.index("## 核心判据（≥5 条）")
        except ValueError:
            start = next((i for i, l in enumerate(lines) if l.startswith("## 核心判据")), -1)
        rows: list[list[str]] = []
        if start >= 0:
            i = start + 1
            while i < len(lines) and not lines[i].startswith("## "):
                if lines[i].strip().startswith("|") and not is_separator(lines[i]):
                    row = cells(lines[i])
                    if row and row[0] != "判据":
                        rows.append(row)
                i += 1
        res.info(f"判据行数：{len(rows)}")
        if len(rows) < 5:
            res.fail(f"判据不足 5 条（实际 {len(rows)}）")
        bad = 0
        for n, row in enumerate(rows, 1):
            if len(row) < 4:
                bad += 1
                res.fail(f"第 {n} 行缺列（须 判据|反例|证据锚|Revisit if）")
                continue
            if PLACEHOLDER_RE.match(row[0]):
                bad += 1
                res.fail(f"第 {n} 行判据为空或占位")
            if PLACEHOLDER_RE.match(row[2]):
                bad += 1
                res.fail(f"第 {n} 行证据锚为空（无锚不得注册）")
            if PLACEHOLDER_RE.match(row[3]):
                bad += 1
                res.fail(f"第 {n} 行缺 Revisit if")
        if bad:
            res.fail(f"不合格判据行：{bad}")
        res.info(f"文件：{path}")
        return res

    # ---------- register ----------
    def register(self, domain: str, apply: bool, title: str | None = None,
                 keywords: list[str] | None = None, nearest: list[str] | None = None) -> Result:
        res = Result("REGISTER")
        if not DOMAIN_RE.match(domain):
            res.fail(f"域名非法：{domain}")
            return res
        val = self.validate(domain)
        res.lines.extend(val.lines)
        if not val.ok:
            res.fail("校验未通过，拒绝注册")
            return res
        if self.registered(domain):
            res.info(f"{domain} 已注册，跳过（幂等）")
            return res

        meta = self.load_domains().get(domain, {})
        title = title or meta.get("title", domain)
        keywords = (keywords or meta.get("keywords", []))[:5]
        nearest = nearest or meta.get("nearest", []) or ["code-generation"]
        boundary = meta.get("boundary", "")

        route_row = (
            f"| {title} | {'、'.join(keywords)} | `{domain}` | "
            f"{', '.join('`' + n + '`' for n in nearest)} | {boundary}；未确认领域前禁按最近邻冒充 |"
        )
        map_row = f"| `{domain}` | `references/{domain}.md` |"

        routing_text = read_text(self.routing)
        nl = "\r\n" if "\r\n" in routing_text else "\n"
        lines = routing_text.split(nl)
        route_idxs = table_line_indexes(lines, ROUTE_HEADER)
        map_idxs = table_line_indexes(lines, "| 专项 reference |")
        if not route_idxs or not map_idxs:
            res.fail("路由表或专项映射表未找到（结构可能已变更）")
            return res

        res.info(f"将新增：references/{domain}.md")
        res.info(f"将插入领域路由表，行内容：{route_row}")
        res.info(f"将插入专项映射，行内容：{map_row}")
        res.info("将同步 README / routing 的计数口径")
        if not apply:
            res.info("dry-run：未写任何文件（加 --apply 落盘）")
            return res

        new_lines = list(lines)
        insert_at = map_idxs[-1] + 1
        new_lines.insert(insert_at, map_row)
        insert_at = route_idxs[-1] + 1
        new_lines.insert(insert_at, route_row)
        new_routing = nl.join(new_lines)

        draft = self.draft_dir / f"{domain}.md"
        target = self.ref_dir / f"{domain}.md"
        shutil.copy2(draft, target)

        backup(self.routing)
        write_text(self.routing, new_routing)
        self.sync_counts(res)

        if f"`{domain}`" not in read_text(self.routing):
            res.fail("写后回读失败：routing 未含新领域行")
        if not target.exists():
            res.fail("写后回读失败：reference 未落盘")
        if res.ok:
            res.info(f"注册完成：{target}")
            try:
                draft.unlink()
                res.info("草稿已清理（正式文件已落 references/）")
            except OSError:
                pass
        return res

    # ---------- counts ----------
    def _facts(self) -> tuple[int, int, int]:
        refs = {p.name for p in self.ref_dir.glob("*.md")}
        subs = self.subskills()
        spec = self.special_mapping() - FRAMEWORK_DOCS
        return len(refs), len(subs), len(spec)

    def sync_counts(self, res: Result | None = None) -> None:
        total, subs, spec = self._facts()
        readme_text = read_text(self.readme)
        new_readme = re.sub(r"共 \d+ 个 md", f"共 {total} 个 md", readme_text)
        new_readme = re.sub(r"\d+ 个专项 reference", f"{spec} 个专项 reference", new_readme)
        if new_readme != readme_text:
            backup(self.readme)
            write_text(self.readme, new_readme)
        routing_text = read_text(self.routing)
        new_routing = re.sub(r"专项计 \d+ 个", f"专项计 {spec} 个", routing_text)
        new_routing = re.sub(r"README「\d+ 个专项 reference」", f"README「{spec} 个专项 reference」", new_routing)
        if new_routing != routing_text:
            backup(self.routing)
            write_text(self.routing, new_routing)
        if res:
            res.info(f"计数：md={total} 子技能={subs} 专项={spec}")

    # ---------- check ----------
    def check(self) -> Result:
        res = Result("CHECK")
        refs = {p.name for p in self.ref_dir.glob("*.md")}
        subs = self.subskills()
        spec = self.special_mapping()
        declared_ok = True

        orphans = sorted(refs - spec - subs - FRAMEWORK_DOCS)
        dangling = sorted(spec - refs)
        if orphans:
            res.fail(f"孤儿 reference（既非子技能也非专项映射）：{orphans}")
            declared_ok = False
        if dangling:
            res.fail(f"悬空注册（映射指向不存在文件）：{dangling}")
            declared_ok = False

        total, nsubs, nspec = len(refs), len(subs), len(spec - FRAMEWORK_DOCS)
        readme_text = read_text(self.readme)
        routing_text = read_text(self.routing)
        m = re.search(r"共 (\d+) 个 md", readme_text)
        if not m or int(m.group(1)) != total:
            res.fail(f"README 计数不符：声明 {m.group(1) if m else '缺失'}，实际 {total}")
            declared_ok = False
        m2 = re.search(r"(\d+) 个专项 reference", readme_text)
        if not m2 or int(m2.group(1)) != nspec:
            res.fail(f"README 专项计数不符：声明 {m2.group(1) if m2 else '缺失'}，实际 {nspec}")
            declared_ok = False
        m3 = re.search(r"专项计 (\d+) 个", routing_text)
        if not m3 or int(m3.group(1)) != nspec:
            res.fail(f"routing 专项计数不符：声明 {m3.group(1) if m3 else '缺失'}，实际 {nspec}")
            declared_ok = False

        drafts = sorted(p.name for p in self.draft_dir.glob("*.md")) if self.draft_dir.exists() else []
        if drafts:
            res.info(f"待定草稿（未注册，不参与计数）：{drafts}")
        if declared_ok:
            res.info(f"一致：md={total} 子技能={nsubs} 专项={nspec}；无孤儿/悬空")
        return res

    # ---------- selftest ----------
    def selftest(self) -> Result:
        res = Result("SELFTEST")
        tmp = Path(tempfile.mkdtemp(prefix="domain_evolve_"))
        try:
            clone = tmp / "skill"
            shutil.copytree(self.root, clone, ignore=shutil.ignore_patterns("__pycache__", ".drafts"))
            tk = Toolkit(clone)

            d = tk.detect("帮我做个微信小程序，WXML 双列布局 + 分包")
            res.info("case1 detect+：" + ("PASS" if "DOMAIN-GAP: miniprogram" in d.render() else "FAIL"))
            d2 = tk.detect("帮我实现登录接口并补单元测试")
            res.info("case2 detect-：" + ("PASS" if "DOMAIN-GAP" not in d2.render() else "FAIL"))
            d3 = tk.detect("帮我写个 Unity 小游戏")
            res.info("case2a 词表外领域不漏判：" + ("PASS" if "VERDICT=GAP" in d3.render() else "FAIL"))
            d4 = tk.detect("Android 原生 App 上架")
            r4 = d4.render()
            res.info("case2b 排除声明硬信号：" + ("PASS" if "VERDICT=GAP" in r4 and "exclusion:" in r4 else "FAIL"))
            d5 = tk.detect("帮我实现登录接口并补单元测试")
            res.info("case2c 已覆盖不误报：" + ("PASS" if "VERDICT=COVERED" in d5.render() else "FAIL"))

            sc = tk.scaffold("miniprogram", "小程序开发")
            draft = tk.draft_dir / "miniprogram.md"
            v_bad = tk.validate("miniprogram")
            res.info("case3 scaffold：" + ("PASS" if sc.ok and draft.exists() else "FAIL"))
            res.info("case4 validate-（空锚应拒）：" + ("PASS" if not v_bad.ok else "FAIL"))

            good = read_text(draft)
            rows = "".join(
                f"| 判据{i} 示例 | 常见错配{i} | 官方文档#{i} | 版本变更 |\n" for i in range(1, 6)
            )
            good = re.sub(r"(\|---\|---\|---\|---\|\n)(?:\| — \| — \| — \| — \|\n)+", r"\1" + rows, good)
            write_text(draft, good)
            v_ok = tk.validate("miniprogram")
            res.info("case5 validate+：" + ("PASS" if v_ok.ok else "FAIL"))

            h_before = digest(tk.routing)
            dry = tk.register("miniprogram", apply=False)
            res.info("case6 dry-run 零写盘：" + ("PASS" if dry.ok and digest(tk.routing) == h_before else "FAIL"))

            ap = tk.register("miniprogram", apply=True)
            ok_ap = (ap.ok and (tk.ref_dir / "miniprogram.md").exists()
                     and "`miniprogram`" in read_text(tk.routing)
                     and not (tk.draft_dir / "miniprogram.md").exists())
            res.info("case7 apply：" + ("PASS" if ok_ap else "FAIL"))
            chk = tk.check()
            res.info("case8 check：" + ("PASS" if chk.ok else "FAIL"))

            broken = good.replace("| 官方文档#2 |", "| — |")
            write_text(tk.draft_dir / "miniprogram.md", broken)
            v_bad2 = tk.validate("miniprogram")
            res.info("case9 无锚拒注册：" + ("PASS" if not v_bad2.ok else "FAIL"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return res


def main(argv: list[str] | None = None) -> int:
    _fix_stdio()
    ap = argparse.ArgumentParser(description="dev-expert 领域自进化工具")
    ap.add_argument("--root", default=None, help="技能根目录（默认按脚本位置推导）")
    ap.add_argument("--log", default=None, help="把结果写入日志文件")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--detect", metavar="TEXT")
    g.add_argument("--scaffold", metavar="DOMAIN")
    g.add_argument("--validate", metavar="DOMAIN")
    g.add_argument("--register", metavar="DOMAIN")
    g.add_argument("--check", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--apply", action="store_true", help="register 时真正写盘")
    ap.add_argument("--force", action="store_true", help="scaffold 覆盖已有草稿")
    ap.add_argument("--json", action="store_true", help="机器可读输出（detect 含 signals）")
    ap.add_argument("--title", default=None, help="领域中文名（词表外领域必填）")
    ap.add_argument("--keywords", default=None, help="触发词，逗号分隔（覆盖词表缓存）")
    ap.add_argument("--nearest", default=None, help="协同 reference，逗号分隔")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    tk = Toolkit(root)

    if args.detect is not None:
        if len(args.detect) > 2000:
            res = Result("DETECT")
            res.fail("任务文本超过 2000 字符，请截取关键段")
        else:
            res = tk.detect(args.detect)
    elif args.scaffold:
        domains = tk.load_domains()
        res = tk.scaffold(args.scaffold, args.title or domains.get(args.scaffold, {}).get("title", args.scaffold), args.force)
    elif args.validate:
        res = tk.validate(args.validate)
    elif args.register:
        kws = [x.strip() for x in args.keywords.split(",") if x.strip()] if args.keywords else None
        nrs = [x.strip() for x in args.nearest.split(",") if x.strip()] if args.nearest else None
        res = tk.register(args.register, args.apply, args.title, kws, nrs)
    elif args.check:
        res = tk.check()
    else:
        res = tk.selftest()

    if args.json:
        out = json.dumps({"ok": res.ok, **res.data}, ensure_ascii=False, indent=2)
    else:
        out = res.render()
    print(out)
    if args.log:
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        write_text(Path(args.log), out + "\n")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
