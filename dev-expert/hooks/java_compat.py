#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL): 写 .java 后做 Java 版本兼容性静态扫描（对齐 版本兼容精神）。

对标 php8_compat.py：纯模式匹配，不依赖外部构建工具、不跑编译。
项目 Java 目标版本探测（自文件目录向上最多 6 级）：
- pom.xml            ：<maven.compiler.source|release|target> / <source|release|target>
- build.gradle(.kts) ：sourceCompatibility / targetCompatibility / JavaLanguageVersion.of(N)
探测不到项目版本 → **静默返回 0**（不猜测、不误报）。
命中即 warning 回显 AI，非阻断（exit 0）。
"""
import sys
import os
import re

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

# 特性 → 最低 Java 版本（命中且项目版本低于该值才告警）
FEATURES = [
    (re.compile(r"\b(?:List|Map|Set)\s*\.\s*of\s*\("), 9, "集合工厂 List/Map/Set.of()"),
    (re.compile(r"\.\s*isBlank\s*\(\s*\)"), 11, "String.isBlank()"),
    (re.compile(r"\.\s*strip\s*\(\s*\)"), 11, "String.strip()"),
    (re.compile(r"\bFiles\s*\.\s*readString\s*\("), 11, "Files.readString()"),
    (re.compile(r"\bvar\s+\w+\s*="), 10, "var 局部变量类型推断"),
    (re.compile(r"\bcase\s+[^:\n]+->"), 14, "switch 表达式（case X ->）"),
    (re.compile(r'"""'), 15, "文本块（三引号）"),
    (re.compile(r"(?m)^\s*(?:public\s+|final\s+|abstract\s+)*record\s+\w+\s*\("), 16, "record 声明"),
    (re.compile(r"\bsealed\s+(?:class|interface)"), 17, "sealed 类/接口"),
    (re.compile(r"\binstanceof\s+\w+(?:<[^>]*>)?\s+\w+\s*(?:&&|\)|\{)"), 16, "instanceof 模式匹配"),
]

_VERSION_FILES = ("pom.xml", "build.gradle", "build.gradle.kts")


def _norm(raw):
    """把 1.8 / 8 / 17 / 21 归一为次版本号 int。"""
    raw = str(raw).strip()
    if raw.startswith("1."):
        raw = raw.split(".", 1)[1]
    try:
        return int(raw)
    except Exception:
        return None


def _parse_version(path):
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return None
    if os.path.basename(path).lower() == "pom.xml":
        for pat in (
            r"<maven\.compiler\.(?:source|release|target)>\s*([0-9.]+)\s*<",
            r"<(?:source|release|target)>\s*([0-9.]+)\s*<",
        ):
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                v = _norm(m.group(1))
                if v:
                    return v
        return None
    # gradle
    m = re.search(
        r"(?:sourceCompatibility|targetCompatibility)\s*=?\s*(?:JavaVersion\s*\.\s*)?VERSION_1_(\d+)",
        text,
    )
    if m:
        return int(m.group(1))
    m = re.search(
        r"(?:sourceCompatibility|targetCompatibility)\s*=?\s*[\"']?(?:JavaVersion\s*\.\s*)?VERSION_(\d+)",
        text,
    )
    if m:
        return _norm(m.group(1))
    m = re.search(r"JavaLanguageVersion\s*\.\s*of\s*\(\s*(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def detect_project_java_version(start_dir):
    """自 start_dir 向上最多 6 级探测项目目标 Java 版本；失败返回 None（调用方静默）。"""
    d = start_dir
    for _ in range(6):
        for name in _VERSION_FILES:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                v = _parse_version(p)
                if v:
                    return v
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def _clean_java(text):
    """剥离注释与字符串/字符/文本块字面量**内容**（定界符保留），防注释与文档串误报。

    文本块三引号定界符保留——它本身就是被检测特性（Java 15 文本块），
    剥内容即可消除「字符串里提到 var/strip」的 advisory 噪音而不漏真特性。
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        three = text[i:i + 3]
        if three == '"""':
            out.append('"""')
            end = text.find('"""', i + 3)
            i = n if end < 0 else end + 3
            continue
        if text[i:i + 2] == '//':
            end = text.find('\n', i)
            i = n if end < 0 else end
            continue
        if text[i:i + 2] == '/*':
            end = text.find('*/', i + 2)
            i = n if end < 0 else end + 2
            continue
        if ch in ('"', "'"):
            out.append(ch)
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == ch:
                    j += 1
                    break
                j += 1
            out.append(ch)
            i = j
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def scan(text, project_version):
    hits = []
    for rx, minv, label in FEATURES:
        if rx.search(text) and project_version < minv:
            hits.append(
                "使用了 %s（需 Java %d+），但项目目标版本为 Java %d —— 改用兼容写法或显式提升项目版本"
                % (label, minv, project_version)
            )
    return hits


def main():
    data, _err = LC.read_stdin_payload()
    if not isinstance(data, dict):
        return 0

    tool_input = LC.tool_input_of(data)
    path = (
        tool_input.get("filePath")
        or tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )
    if not path:
        return 0
    path = os.path.abspath(path)
    if os.path.splitext(path)[1].lower() != ".java":
        return 0
    if not os.path.isfile(path):
        return 0

    project_version = detect_project_java_version(os.path.dirname(path))
    if not project_version:
        return 0  # 探测不到项目 Java 版本：静默（不猜测）

    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return 0

    hits = scan(_clean_java(text), project_version)
    if hits:
        LC.emit_context(["[JAVA-COMPAT-WARN] 发现 Java 版本兼容隐患（项目目标 Java %d）：" % project_version]
                        + ["  - " + h for h in hits])
    return 0


if __name__ == "__main__":
    sys.exit(main())
