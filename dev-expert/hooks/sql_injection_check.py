#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook (GLOBAL): SQL 注入风险检查。

检测修改文件中的 SQL 注入风险模式，覆盖 PHP / Python / JS / Java / Go：

风险模式（命中即警告）：
  1. PHP 用户输入直接入 SQL：$_GET/$_POST/$_REQUEST/$_COOKIE 出现在 SQL 字符串中
  2. PHP 字符串拼接 SQL："SELECT ..." . $var
  3. PHP 变量插值 SQL（双引号）："SELECT ... $var" / "SELECT ... {$var}"
  4. Python f-string SQL：f"SELECT ... {var}"
  5. Python % 格式化 SQL："SELECT ... %s" % var（仅当含用户输入标记时）
  6. JS 模板字符串 SQL：`SELECT ... ${var}`
  7. Java 字符串拼接 SQL："SELECT ..." + var

SQL 关键字覆盖：
  - SQL 标准：SELECT / INSERT INTO / UPDATE / DELETE FROM / DROP TABLE /
    ALTER TABLE / CREATE TABLE / UNION SELECT / TRUNCATE TABLE
  - MySQL/MariaDB 特有：REPLACE INTO / LOAD DATA INFILE / LOAD DATA LOCAL INFILE /
    INTO OUTFILE / INTO DUMPFILE / GRANT / REVOKE / CALL

安全模式（同行出现则跳过，不误报）：
  - 预处理语句：prepare( / prepare "
  - 参数绑定：bindParam / bindValue / bind_param
  - ORM 查询构造器：->where( / ->table( / ::table( / .where(
  - 批量执行：executemany

非阻断：命中经 PostToolUse JSON 契约（hookSpecificOutput.additionalContext）回显 AI，exit 0（与 select_star.py 一致）。
"""
import sys
import os
import re

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

# 受检查的文件扩展名
TEXT_EXT = {".php", ".phtml", ".php3", ".php5", ".py", ".js", ".jsx",
            ".ts", ".tsx", ".java", ".go", ".rb", ".sql", ".inc"}

# SQL 关键字前缀（匹配 SQL 语句开头）
# 覆盖 SQL 标准 + MySQL/MariaDB/PostgreSQL 特有高危语法
SQL_KEYWORDS = (
    r"(?:SELECT\s|INSERT\s+INTO|UPDATE\s|DELETE\s+FROM|DROP\s+TABLE|"
    r"ALTER\s+TABLE|CREATE\s+TABLE|UNION\s+SELECT|TRUNCATE\s+TABLE|"
    r"REPLACE\s+INTO|"
    r"LOAD\s+DATA\s+INFILE|LOAD\s+DATA\s+LOCAL\s+INFILE|"  # MySQL/MariaDB 读文件
    r"INTO\s+OUTFILE|INTO\s+DUMPFILE|"                      # MySQL/MariaDB 写文件
    r"GRANT\s|REVOKE\s|"                                    # 权限操纵
    r"CALL\s)"                                              # 存储过程调用
)

# 风险模式：(正则, 描述)
RISK_PATTERNS = [
    # PHP: $_GET/$_POST/$_REQUEST/$_COOKIE 直接出现在 SQL 字符串中
    (re.compile(
        r'["\'][^"\']*' + SQL_KEYWORDS + r'[^"\']*\$_(?:GET|POST|REQUEST|COOKIE|SERVER)\s*\[',
        re.IGNORECASE),
     "PHP 用户输入直接入 SQL（$_GET/$_POST/$_REQUEST）"),

    # PHP: 字符串拼接 SQL "SELECT ..." . $var 或 "SELECT ..." . $obj->prop
    (re.compile(
        r'["\']\s*' + SQL_KEYWORDS + r'.*?["\']\s*\.\s*\$',
        re.IGNORECASE),
     "PHP 字符串拼接 SQL"),

    # PHP: 双引号变量插值 SQL "SELECT ... $var" 或 "SELECT ... {$var}"
    (re.compile(
        r'"[^"]*' + SQL_KEYWORDS + r'[^"]*\$(?:[a-zA-Z_]|\{)',
        re.IGNORECASE),
     "PHP 变量插值 SQL（双引号内 $var）"),

    # Python: f-string SQL f"SELECT ... {var}" 或 f'SELECT ... {var}'
    (re.compile(
        r'f["\']\s*' + SQL_KEYWORDS + r'[^"\']*\{',
        re.IGNORECASE),
     "Python f-string SQL（变量插值）"),

    # Python: % 格式化 SQL "SELECT ... %s" % var（仅当 var 是用户输入相关时；
    # 括号元组与无括号单值两种写法均覆盖：% uid 与 % (uid,)）
    (re.compile(
        r'["\']\s*' + SQL_KEYWORDS + r'[^"\']*%s[^"\']*["\']\s*%\s*\(?',
        re.IGNORECASE),
     "Python % 格式化 SQL（疑似拼接）"),

    # JS: 模板字符串 SQL `SELECT ... ${var}`
    (re.compile(
        r'`\s*' + SQL_KEYWORDS + r'[^`]*\$\{',
        re.IGNORECASE),
     "JS 模板字符串 SQL（变量插值）"),

    # Java: 字符串拼接 SQL "SELECT ..." + var
    (re.compile(
        r'"\s*' + SQL_KEYWORDS + r'[^"]*"\s*\+\s*\w',
        re.IGNORECASE),
     "Java 字符串拼接 SQL"),
]

# 安全模式（同行出现则跳过）
SAFE_PATTERNS = [
    re.compile(r'\bprepare\s*\(', re.IGNORECASE),      # PDO/MySQLi prepare
    re.compile(r'\bprepare\s+"', re.IGNORECASE),        # Python DB-API prepare
    re.compile(r'\bbindParam\b', re.IGNORECASE),        # PDO bindParam
    re.compile(r'\bbindValue\b', re.IGNORECASE),        # PDO bindValue
    re.compile(r'\bbind_param\b', re.IGNORECASE),       # MySQLi bind_param
    re.compile(r'->where\s*\(', re.IGNORECASE),         # ORM where
    re.compile(r'->table\s*\(', re.IGNORECASE),         # ORM table
    re.compile(r'::table\s*\(', re.IGNORECASE),         # ORM static table
    re.compile(r'\.where\s*\(', re.IGNORECASE),         # JS ORM where
    re.compile(r'\bexecutemany\b', re.IGNORECASE),      # Python executemany
]

# 跳过注释行的逻辑（与 select_star.py 一致）
def _is_comment(s):
    return (s.startswith("//") or s.startswith("#") or
            s.startswith("*") or s.startswith("/*"))


def find_sql_injection_risks(text):
    """逐行扫描，跳过注释，返回 (行号, 描述, 行内容) 列表。

    对每行：
    1. 块注释剥离经 `LC.strip_block_comments` 单源（字符串内的 `/*` 不算注释开起）
    2. 跳过单行注释行
    3. 检查是否含风险模式
    4. 若命中风险模式，检查同行是否有安全模式（有则跳过）
    """
    hits = []
    for i, line in LC.strip_block_comments(text):
        s = line.strip()

        # 单行注释跳过
        if _is_comment(s):
            continue

        # 检查风险模式
        for pattern, desc in RISK_PATTERNS:
            if pattern.search(line):
                # 检查同行是否有安全模式
                is_safe = any(sp.search(line) for sp in SAFE_PATTERNS)
                if not is_safe:
                    hits.append((i, desc, s[:100]))
                    break  # 同行只报一次
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
    if os.path.splitext(path)[1].lower() not in TEXT_EXT:
        return 0
    if not os.path.isfile(path):
        return 0

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return 0

    hits = find_sql_injection_risks(text)
    if hits:
        lines = ["[SQL-INJECTION-WARN] 发现 SQL 注入风险（字符串拼接/变量插值）："]
        lines += ["  行 %d [%s] %s" % (n, d, p) for n, d, p in hits]
        lines.append("建议改用预处理语句（prepare + bindParam/bindValue）或 ORM 查询构造器。")
        LC.emit_context(lines)  # PostToolUse 送达契约：stdout 只出 JSON（裸 print 不回传 Agent）
    return 0


if __name__ == "__main__":
    sys.exit(main())
