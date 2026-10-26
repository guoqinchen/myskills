#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook (GLOBAL): 在 AI 写/改已存在的源码文件前，自动备份为 <file>.bak。

项目无关：仅依据 stdin 传入的文件路径做备份，可在任意项目中生效。
设计原则（对齐本项目 Rules 铁律：无 Git，.bak 是唯一回滚手段）：
- 非阻塞：任何情况下都 exit 0，绝不影响原工具执行。
- 仅对「已存在」的源码类文件生效；新文件、二进制、敏感目录一律跳过。
- 若 .bak 已存在且与当前文件内容一致，则跳过，避免无意义覆盖/抖动。
- 多版本备份：保留最近 MAX_VERSIONS 个历史版本（.bak / .bak.1 / ... / .bak.<MAX_VERSIONS-1>），
  每次备份前轮转旧版本，超出上限的自动删除。
- 备份失败也静默放行（exit 0），不让备份逻辑阻断用户工作。
"""
import sys
import os
import shutil
import filecmp

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

# 保留最近 N 个历史版本（.bak / .bak.1 / ... / .bak.<N-1>）
MAX_VERSIONS = 10

# 仅备份源码/配置类文件，避免 .bak 污染图片等二进制
# 22 类扩展名（含 `.htaccess`）+ DOTFILE_SUFFIXES 额外 3 个 = 生效 25 种
BACKUP_EXT = {
    ".php", ".html", ".htm", ".js", ".css", ".json", ".py", ".txt",
    ".md", ".conf", ".xml", ".sql", ".inc", ".tpl", ".vue", ".ts",
    ".tsx", ".jsx", ".yml", ".yaml", ".ini", ".htaccess",
}
# 点文件名（`.htaccess`/`.gitignore` 等无扩展名形态）：splitext(".htaccess") 的
# 扩展名为空串，仅靠 BACKUP_EXT 判定不生效，须按文件名后缀 endswith 补判
DOTFILE_SUFFIXES = (".htaccess", ".gitignore", ".env", ".editorconfig")

# 跳过这些目录（对齐 排查跳过目录清单 排查/忽略清单）
EXCLUDE_DIRS = {
    "backup", "vendor", "runtime", "node_modules", "uploads",
    ".git", ".codebuddy", "ecachefiles",
}


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
    norm = path.replace("\\", "/").lower()

    # 不备份 .bak / .broken 自身
    if norm.endswith(".bak") or norm.endswith(".broken"):
        return 0
    # 跳过敏感/忽略目录
    if any(part in EXCLUDE_DIRS for part in norm.split("/")):
        return 0
    # 仅备份源码/配置类扩展名
    # 扩展名判定：集合命中或点文件名后缀命中（.htaccess 无扩展名形态）
    if (os.path.splitext(norm)[1] not in BACKUP_EXT
            and not norm.endswith(DOTFILE_SUFFIXES)):
        return 0
    # 新文件无需回滚
    if not os.path.isfile(path):
        return 0

    bak = path + ".bak"
    try:
        # 内容一致则跳过（无需备份也无需轮转）
        if os.path.exists(bak) and filecmp.cmp(bak, path, shallow=False):
            return 0

        # 轮转旧备份：.bak.(N-1) → .bak.N，删除超出 MAX_VERSIONS 的
        # 从最旧开始处理，避免覆盖
        oldest = "%s.bak.%d" % (path, MAX_VERSIONS - 1)
        if os.path.exists(oldest):
            os.remove(oldest)
        for i in range(MAX_VERSIONS - 2, 0, -1):
            src = "%s.bak.%d" % (path, i)
            dst = "%s.bak.%d" % (path, i + 1)
            if os.path.exists(src):
                os.rename(src, dst)
        # .bak → .bak.1
        if os.path.exists(bak):
            os.rename(bak, "%s.bak.1" % path)

        # 备份当前文件
        shutil.copy2(path, bak)
    except Exception as e:
        sys.stderr.write("[BACKUP-WARN] 备份失败（%s）：%s；本次写入放行，但回滚网未建立\n"
                         % (path, e))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
