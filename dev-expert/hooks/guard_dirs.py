#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook (GLOBAL): 拦截对数据/依赖目录的写操作。

对齐 安全红线与受保护目录：uploads(上传目录,禁手改源码)、backup(回滚存放)、
vendor/node_modules(依赖) 不应由 AI 直接编辑源码写入。命中即 exit 2 阻断。
- 仅检查目标文件路径本身所在目录，不误伤其父级正常目录。
- 输出清晰拒绝原因，便于 AI 立即感知并改向。
"""
import sys
import os

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

# 禁止 AI 直接写入的目录（数据/依赖/回滚，大小写不敏感）
FORBIDDEN = {"uploads", "backup", "vendor", "node_modules"}
ROOT_MARKERS = (".git", ".ai-memory", ".codebuddy")


def _project_root(path):
    """项目根：PROJECT_ROOT env → 上溯标记目录 → None（无根可证）。"""
    env = os.environ.get("PROJECT_ROOT", "")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if any(os.path.exists(os.path.join(d, m)) for m in ROOT_MARKERS):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            return None
        d = nd


def _forbidden_parts(path):
    """待判目录段：相对项目根；无根（或根非祖先）时退化为末 4 段，防父目录同名误伤。"""
    ap = os.path.abspath(path)
    root = _project_root(path)
    if root:
        rel = os.path.relpath(ap, root)
        if not rel.startswith(".."):
            return rel.replace("\\", "/").lower().split("/")[:-1]
    return ap.replace("\\", "/").lower().split("/")[-4:]


def main():
    LC.fix_stdio()
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

    if any(part in FORBIDDEN for part in _forbidden_parts(path)):
        print("[GUARD-BLOCK] 拒绝写入受保护目录：%s" % path)
        print("该目录(uploads/backup/vendor/node_modules)不应由 AI 直接编辑源码，"
              "如确需改动请先在计划中明确并说明理由。")
        return 2  # 阻断
    return 0


if __name__ == "__main__":
    sys.exit(main())
