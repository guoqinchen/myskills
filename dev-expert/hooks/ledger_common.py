#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正反两册**共享判据模块**（单一实现；hooks 与 scripts 共用，禁在消费方复制第二份）。

收敛来源（技能侧原有三处分散实现，ERR-226 族——同一判据两份实现必随演进漂移）：
  - `errors_recall_guard.py` 的 `resolve_index_path`/`parse_row`/`load_triggers`/`tokenize`
  - `errors_dup_guard.py` 的同构副本
  - 既有机械层的判据（编号并集/触发词/日期/值域/引用验真）——本模块按**技能自有约定**
    实现：记忆根 `.ai-memory/`（`AI_MEMORY_DIR` 可覆写）、索引名
    `error_index.md`/`success_index.md`（兼容识别复数索引名 `errors_index.md`，
    供接入既有记忆体系）。

对外 API（按消费方分组）：
  路径与编号：
    memory_root() / err_index_path() / success_index_path()
    ids_files(book) / ids_index(book) / ids_used(book) / ids_next(book)
  索引解析：
    parse_row(line) / load_triggers(index_path)
  触发词判据：
    tokenize(keyword) -> (strong, boundary) / code_tokens(keyword) -> [str]
  日期字段：
    date_parse(text, name) / date_field_ok(text, name) / date_canonical(text, name)
  引用行号验真：
    check_refs(text, root) -> (hard, unver)
  根因分类/正册类型值域：
    load_categories() / load_success_types() / strip_paren(v) / FALLBACK_CAT
  写侧路径判别：
    ledger_target(path) -> 'err'|'suc'|'err_index'|'suc_index'|None
  hook 载荷 IO（stdin 单源；hooks 与 scripts 共用）：
    read_stdin_payload() -> (payload, err) / tool_input_of(payload) -> dict
    emit_context(lines, event='PostToolUse') -> None
    fix_stdio() -> None（stdout/stderr 固定 UTF-8；emit_context 内已自动调用）

设计纪律：
  - 解析失败/域值缺失 ⇒ 返回空集或 None，由调用方**显式告警并降级**，禁静默放行；
  - 本模块不写盘（记账在 `errors_recall_guard.py` 的 bump，禁移入此处）；
  - 依赖仅标准库。
"""
import io
import json
import os
import re
import sys

# ---------------------------------------------------------------- 路径与编号

_BOOKS = {
    'err': {'prefix': 'ERR', 'dir': 'errors',
            'indexes': ('error_index.md', 'errors_index.md')},
    'suc': {'prefix': 'SUC', 'dir': 'success',
            'indexes': ('success_index.md',)},
}
_ID_RE = {'err': re.compile(r'^ERR-(\d+)\.md$', re.I),
          'suc': re.compile(r'^SUC-(\d+)\.md$', re.I)}
_ROW_ID_RE = {'err': re.compile(r'^(?:\d{4}/\d{2}/)?ERR-\d+\b'),
              'suc': re.compile(r'^(?:\d{4}/\d{2}/)?SUC-\d+\b')}
# 3 列主模板的行首形态（生成器确定性写入 `年/月/` 前缀）——据此与旧模板区分
_MAIN_ID_RE = re.compile(r'^\d{4}/\d{2}/(?:ERR|SUC)-\d+\b')


def memory_root():
    """记忆根目录；无法确定时返回 None（调用方静默或告警，禁猜测）。

    解析顺序（与技能既有召回守卫一致）：`AI_MEMORY_DIR` → `PROJECT_ROOT/.ai-memory`
    → cwd 逐级上溯 → 本文件所在目录逐级上溯（找含 `error_index.md` 的 `.ai-memory/`）。
    """
    env = os.environ.get('AI_MEMORY_DIR', '')
    if env:
        return os.path.abspath(env)
    roots = []
    proj = os.environ.get('PROJECT_ROOT', '')
    if proj:
        roots.append(os.path.abspath(proj))
    starts = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for start in starts:
        d = os.path.abspath(start)
        while True:
            roots.append(d)
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    seen = set()
    for r in roots:
        if r in seen:
            continue
        seen.add(r)
        # 探测口径与 `_index_path` 对齐：全部候选索引名 ×（根、册目录）两个位置，
        # 禁只认单名（`errors_index.md` 复数布局下曾全链降级）
        for book in _BOOKS.values():
            for n in book['indexes']:
                for base in (os.path.join(r, '.ai-memory'),
                             os.path.join(r, '.ai-memory', book['dir'])):
                    if os.path.isfile(os.path.join(base, n)):
                        return os.path.join(r, '.ai-memory')
    return None


def _index_path(book):
    """册索引路径：按索引名候选在记忆根/册目录下找首个存在者；均不存在时返回默认名路径
    （供生成器写入与守卫拒绝分支使用——默认名＝技能约定 `error_index.md`）。"""
    cfg = _BOOKS[book]
    root = memory_root()
    if not root:
        return None
    cands = [os.path.join(root, n) for n in cfg['indexes']]
    cands += [os.path.join(root, cfg['dir'], n) for n in cfg['indexes']]
    for c in cands:
        if os.path.isfile(c):
            return c
    return cands[0]


def err_index_path():
    return _index_path('err')


def success_index_path():
    return _index_path('suc')


def _book_dir(book):
    root = memory_root()
    return os.path.join(root, _BOOKS[book]['dir']) if root else None


def ids_files(book):
    """磁盘单条编号集合（按文件名，不读内容）。"""
    d = _book_dir(book)
    out = set()
    if d and os.path.isdir(d):
        for _dp, _dn, fn in os.walk(d):
            for f in fn:
                m = _ID_RE[book].match(f)
                if m:
                    out.add(int(m.group(1)))
    return out


def ids_index(book, index_path=None):
    """索引行编号集合（行首 `[年/月/]<前缀>-<编号>`）。

    行首锚定容许前导 `|`（旧表格索引行的单元格形态）：旧实现只认行首，
    旧表格下编号从并集漏计 ⇒ 取号撞号。与 `index_rows`/`parse_row` 共用
    同一行提取内核（剥 `|`）。
    """
    idx = index_path or _index_path(book)
    if not idx or not os.path.isfile(idx):
        return set()
    try:
        with io.open(idx, encoding='utf-8', errors='ignore') as fh:
            text = fh.read()
    except OSError:
        return set()
    out = set()
    for line in text.splitlines():
        s = line.strip().lstrip('|').strip()
        m = re.match(r'(?:\d{4}/\d{2}/)?%s-(\d+)\b' % _BOOKS[book]['prefix'], s)
        if m:
            out.add(int(m.group(1)))
    return out


def ids_used(book, index_path=None):
    """占用判定唯一口径＝索引 ∪ 磁盘（与取号一致；ERR-226 族教训）。"""
    return ids_index(book, index_path) | ids_files(book)


_MD_INDEX_CACHE = {}


def ledger_md_index(book_dir):
    """book_dir 下全部单条的 {文件名: 路径}（懒建缓存）。

    升格/归档扫描需要「编号 → 单条路径」：索引行前缀是 `年/月/`，
    但单条可能落在扁平布局（`errors/ERR-XXX.md`，error-ledger §0 称受支持）
    或与索引前缀不一致的层级——按前缀拼接会恒不命中并**静默跳过**条目。
    """
    idx = _MD_INDEX_CACHE.get(book_dir)
    if idx is None:
        idx = {}
        if os.path.isdir(book_dir):
            for dp, _dn, fn in os.walk(book_dir):
                for f in fn:
                    if f.endswith('.md'):
                        idx.setdefault(f, os.path.join(dp, f))
        _MD_INDEX_CACHE[book_dir] = idx
    return idx


def ledger_md_path(book_dir, eid):
    """单条路径解析：索引缓存查表，未命中返回规范拼接路径（调用方 isfile 判空）。"""
    return ledger_md_index(book_dir).get(eid + '.md') or os.path.join(
        book_dir, eid + '.md')


def ids_next(book, index_path=None):
    u = ids_used(book, index_path)
    return (max(u) + 1) if u else 1


# ---------------------------------------------------------------- 索引解析

SEP_RE = re.compile(r"[/，、,；;・]")

# 最近一次 `index_rows` 的数据行跳过计数（空关键词行对消费方不可见，禁静默）
_SKIP_STATS = {'empty_keyword': 0}


def index_skip_stats():
    """最近一次 index_rows 的跳过统计；消费方须在检出 >0 时显式告警。"""
    return dict(_SKIP_STATS)


def _looks_like_keyword(s):
    return bool(SEP_RE.search(s)) or len(s) > 16


def parse_row(line):
    """解析一行索引 → (entry_id, keyword, desc)；非数据行返回 None。

    列序兼容（与本技能 hooks 实码及既有索引同口径）：
    - 3 段主模板 `年/月/ERR-XXX | 触发关键词 | 标题`（描述内含 `|` 时回拼，禁截列）；
    - ≥6 列旧模板 `ERR-ID | 描述 | 根因分类 | 触发关键词 | 日期 | RC`（右侧定列取触发词）；
    - 4~5 段旧写法（第二段为描述）整体右移一列。
    """
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 2 or not cells[0]:
        return None
    # 3 列主模板（行首 `年/月/<前缀>-<编号>`，生成器确定性写入）⇒ 第 2 格即触发词，
    # 其余整段回拼为描述（描述值内可能含 `|`，不得截列）。
    if _MAIN_ID_RE.match(cells[0]):
        return cells[0], cells[1], "|".join(cells[2:]).strip()
    if len(cells) >= 6:
        return cells[0], cells[-3], "|".join(cells[1:-4]).strip()
    err_id, second = cells[0], cells[1]
    third = "|".join(cells[2:]) if len(cells) > 2 else ""
    if third and "|" in third:
        rest = cells[2:]
        keyword = rest[1] if len(rest) > 1 else ""
        if keyword and _looks_like_keyword(keyword):
            return err_id, keyword, second
    if len(cells) >= 4:
        # 4~5 列旧模板定列：`ID | 描述 | (分类) | 触发词 (| 日期)`——触发词取第 4 格。
        # 禁 looks-like 猜列回退：实测旧 4 列行会把「描述」当触发词、真触发词漏报。
        return err_id, cells[3], second
    return err_id, second, third


def index_rows(index_path, prefix=None):
    """解析册索引活跃区 → [{id, prefix, keyword, desc, date}]；遇「## 归档区」停止。

    与 `load_triggers` 同一解析内核（`parse_row`），禁另写第二份（ERR-226 族：
    同一格式两份实现 ⇒ 口径分裂）。`prefix` 取 `'ERR'`/`'SUC'`/None（None＝两册都收，
    保持 `load_triggers` 既有行为）；`date` 取行内首个 `YYYY-MM-DD` 形态 cell
    （治理层升格窗口/归档判据消费；无则空串）。

    空关键词数据行**禁静默跳过**：计入 `index_skip_stats()`，由消费方显式告警
    （这些行对召回/查重/升格/metrics 全部不可见，静默即假绿）。
    """
    if not index_path or not os.path.isfile(index_path):
        _SKIP_STATS['empty_keyword'] = 0
        return []
    id_res = []
    if prefix is None or prefix.upper() == 'ERR':
        id_res.append(_ROW_ID_RE['err'])
    if prefix is None or prefix.upper() == 'SUC':
        id_res.append(_ROW_ID_RE['suc'])
    out = []
    _SKIP_STATS['empty_keyword'] = 0
    try:
        with open(index_path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if s.startswith('##'):
                    if '归档' in s:
                        break
                    continue
                if s.startswith('#') or s.startswith('>'):
                    continue
                if s.startswith('|') and ('ERR-ID' in s or 'SUC-XXX' in s
                                          or set(s) <= set('|-: ')):
                    continue
                row = parse_row(s.lstrip('|'))
                if not row or not row[1]:
                    if row:  # 解析成功但关键词为空＝数据行，须计数告警
                        _SKIP_STATS['empty_keyword'] += 1
                    continue
                if not any(r.match(row[0]) for r in id_res):
                    continue
                m = re.match(r'^(\d{4}/\d{2}/)?', row[0])
                date = ''
                for c in row[0].split('|') + s.strip('|').split('|'):
                    dm = re.match(r'^\s*(\d{4}-\d{2}-\d{2})', c)
                    if dm:
                        date = dm.group(1)
                        break
                out.append({'id': row[0], 'eid': row[0][len(m.group(1) or ''):],
                            'prefix': m.group(1) or '',
                            'keyword': row[1], 'desc': row[2], 'date': date})
    except OSError:
        return []
    return out


def load_triggers(index_path):
    """解析册索引 → [(entry_id, keyword, desc)]；遇「## 归档区」停止（归档条目不参与召回）。

    契约＝元组列表（既有消费方按元组解包，禁改返回形态）；富行解析走 `index_rows`。
    """
    return [(r['id'], r['keyword'], r['desc'])
            for r in index_rows(index_path) if r['keyword']]


# ---------------------------------------------------------------- 触发词判据

WORD_ASCII_RE = re.compile(r"^[0-9a-z_]+$")
MIN_ASCII_BOUNDARY_LEN = 4  # 4~5 字母纯词走词边界匹配（form/table/special…）

# 停用词：通用写入内容中高频、与条目语义无对应的词（实测误报主源）。
# 判据＝「单独出现不构成该条目的触发场景」；禁收录条目专属代码词。
STOPWORDS = frozenset((
    "class", "data", "html", "null", "eval", "exec", "popen", "crlf",
    "grep", "glob", "emit", "python", "encoding",
    "create", "select", "insert", "update", "delete", "table", "where",
    "index", "value", "string", "array", "object", "return",
    "true", "false", "function", "public", "private", "static", "echo", "print",
    "error", "warning", "allowed", "unexpected", "cannot", "identifier",
    "触发词", "边界", "新增", "tokenize", "markdown",
    "path", "code", "exit",
))
WRAP_CHARS = "`*「」『』《》\"'"
CODE_SEG_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.$\-]{4,}")
_WRAP_PAIR_RE = re.compile(r"([`*「」『』《》\"'])([^`*「」『』《》\"']*)\1")
_WRAP_PLAIN_RE = re.compile(r"[A-Za-z0-9_.$>\- ]+")
_WRAP_PLAIN_NOSP_RE = re.compile(r"[A-Za-z0-9_.$>\-]+")


def is_codeish(seg):
    """长句提取片段判据：须含代码信号字符（_ . $ 数字）/ 大写字母 / 长度>=10 之一。"""
    core = seg.strip("_.-$")
    if len(core) < 6 or not core.isascii():
        return None
    if re.search(r"[_.$\d]", core):
        return core
    if any(ch.isupper() for ch in core):
        return core
    return core if len(core) >= 10 else None


def tokenize(keyword):
    """返回 (strong, boundary)：strong 走子串匹配，boundary 走词边界匹配。

    - 仅按分隔符切词，**不按空格切**（多词短语须保持整体，防子串误报）；
    - ASCII ≥6 子串；4~5 纯字母数字走词边界（救回 form/table 类高频词）；
    - 候选来源：整体候选（剥 WRAP_CHARS 包裹）/ 成对包裹直通 / 长句提取代码片段
      （收紧判据防通用英文词）；均过 STOPWORDS；
    - 中文 ≥2 字保留（子串误报极低）。
    """
    strong, boundary = [], []
    for t in SEP_RE.split(keyword or ''):
        t = t.strip()
        if not t:
            continue
        cands = []
        u = t.strip(WRAP_CHARS)
        if u and ' ' not in u:
            cands.append(u)
        elif u and ' ' in u and len(u) >= 6 and _WRAP_PLAIN_RE.fullmatch(u):
            cands.append(u)
            cands.extend(u.split())
        for m in _WRAP_PAIR_RE.finditer(t):
            inner = m.group(2).strip()
            if not inner or _WRAP_PAIR_RE.search(inner):
                continue
            if not inner.isascii():
                continue
            if ' ' in inner:
                if _WRAP_PLAIN_RE.fullmatch(inner):
                    cands.append(inner)
                    cands.extend(inner.split())
                continue
            plain = inner.strip("()[]{}:;,.!?，。；：、")
            if plain and _WRAP_PLAIN_NOSP_RE.fullmatch(plain):
                cands.append(plain)
        if ' ' in t:
            for seg in CODE_SEG_RE.findall(t):
                c = is_codeish(seg)
                if c:
                    cands.append(c)
        for c in cands:
            low = c.lower()
            if low in STOPWORDS:
                continue
            if c.isascii():
                if len(c) >= 6:
                    strong.append(low)
                elif len(c) >= MIN_ASCII_BOUNDARY_LEN and WORD_ASCII_RE.match(low):
                    boundary.append(low)
            else:
                # 非 ASCII 亦取小写形：hay（写入内容）整体小写化，混合 token
                # （如「内联JS字符串拼接」）若保留原写法则永远匹配不上。
                if len(c) >= 2:
                    strong.append(low)
    return list(dict.fromkeys(strong)), list(dict.fromkeys(boundary))


def code_tokens(keyword):
    """触发词承载的**可机械命中的 ASCII 代码字面词**（可用性判据，与召回匹配同源）。

    形态枚举（缺一即误判）：单行 `a/b/c`、块式 YAML 解析后的换行分隔、全角标点分隔。
    """
    out = []
    for t in SEP_RE.split((keyword or '').replace('\r', '').replace('\n', '/')):
        t = t.strip()
        if not t:
            continue
        cands = []
        u = t.strip(WRAP_CHARS)
        if u and ' ' not in u:
            cands.append(u)
        if ' ' in t:
            for seg in CODE_SEG_RE.findall(t):
                c = is_codeish(seg)
                if c:
                    cands.append(c)
        for c in cands:
            if c.isascii() and c.lower() not in STOPWORDS and is_codeish(c):
                out.append(c.lower())
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------- 日期字段

_DATE = r'\d{4}-\d{2}-\d{2}'
_FORMS = {'首见': ('首见', 'First-Seen'), '末核': ('末核', 'Last-Seen')}
_ALIAS = {'First-Seen': '首见', 'Last-Seen': '末核'}
_PRE = r'(?m)^[ \t>*\-]{0,4}\**[ \t]*'
_PAREN = r'(?:[（(][^）)\n]{0,60}?[）)])?'
_PLACEHOLDER = re.compile(r'占位')
_DATE_ANY = re.compile(_DATE)


def _date_names(name):
    key = _ALIAS.get(name, name)
    return '|'.join(re.escape(x) for x in _FORMS.get(key, (key,)))


def _date_line_of(text, pos):
    start = text.rfind('\n', 0, pos) + 1
    end = text.find('\n', pos)
    return text[start:end if end != -1 else len(text)]


def _date_pack(date, raw, form):
    return {'date': date or '', 'raw': raw.strip()[:120], 'form': form,
            'placeholder': bool(date) and bool(_PLACEHOLDER.search(raw))}


def date_parse(text, name):
    """解析「首见/末核」字段；形态判定顺序：行内带冒号 → 括注载日期 → 标题式 → 内嵌兜底。

    规范形态（新建唯一允许）＝行内式且非占位（`date_canonical` 判）。
    """
    pat_inline = re.compile(_PRE + r'(?:' + _date_names(name) + r')' + _PAREN
                            + r'[ \t]*[:：][ \t]*\**[ \t]*(' + _DATE + r')')
    m = pat_inline.search(text)
    if m:
        return _date_pack(m.group(1), _date_line_of(text, m.start()), 'inline')
    pat_paren = re.compile(_PRE + r'(?:' + _date_names(name) + r')[ \t]*[（(][ \t]*(' + _DATE + r')')
    m = pat_paren.search(text)
    if m:
        return _date_pack(m.group(1), _date_line_of(text, m.start()), 'paren')
    pat_head = re.compile(r'(?m)^#{1,4}[ \t]*(?:' + _date_names(name) + r')[ \t]*' + _PAREN + r'[ \t]*$')
    h = pat_head.search(text)
    if h:
        for line in text[h.end():].splitlines():
            s = line.strip()
            if not s:
                continue
            d = _DATE_ANY.search(s)
            return _date_pack(d.group(0) if d else '', s, 'head')
        return _date_pack('', '', 'head')
    m = re.compile(r'(?:' + _date_names(name) + r')[ \t]+(' + _DATE + r')').search(text)
    if m:
        return _date_pack(m.group(1), _date_line_of(text, m.start()), 'embedded')
    return _date_pack('', '', '')


def date_field_ok(text, name):
    return bool(date_parse(text, name)['date'])


def date_canonical(text, name):
    d = date_parse(text, name)
    return d['form'] == 'inline' and bool(d['date']) and not d['placeholder']


# ---------------------------------------------------------------- 引用行号验真

_URL_RE = re.compile(r'[A-Za-z][A-Za-z0-9+.\-]*://\S+')
_REF_RE = re.compile(
    r'([^\s，。；、（）()\[\]"\'`]{2,150}?\.[A-Za-z0-9_]{1,10})\s*[:：]\s*(\d{1,7})(?!\d)')
# 临时资产目录判据（可被清空，禁作长期依据；只认 tmp/ 通用命名）
_TEMP_DIRS = ('tmp/',)


def _strip_dotslash(p):
    while p.startswith('./'):
        p = p[2:]
    return p


def check_refs(text, root):
    """返回 (hard, unver)：hard＝行号越界/临时资产引用（判不合规）；
    unver＝工作区外或已删除（仅统计——「没验证到」≠「验证失败」）。

    口径：裸文件名（不含目录分隔符）不归判据；URL 先剔除。
    """
    hard, unver = [], []
    scanned = _URL_RE.sub(' ', text)
    for m in _REF_RE.finditer(scanned):
        raw, ln = m.group(1), int(m.group(2))
        if '/' not in raw and '\\' not in raw:
            continue
        p = raw.replace('\\', '/')
        if _strip_dotslash(p).startswith(_TEMP_DIRS):
            hard.append('%s:%d (临时资产引用，临时脚本区可被清空)' % (raw, ln))
            continue
        ap = p if os.path.isabs(p) else os.path.join(root, p)
        if not os.path.isfile(ap):
            unver.append('%s:%d (工作区外或已删除，无法验证)' % (raw, ln))
            continue
        try:
            with open(ap, encoding='utf-8', errors='ignore') as fh:
                total = sum(1 for _ in fh)
        except Exception:
            unver.append('%s:%d (读取失败，无法验证)' % (raw, ln))
            continue
        if ln > total:
            hard.append('%s:%d (行号越界，该文件共 %d 行)' % (raw, ln, total))
    return hard, unver


# ---------------------------------------------------------------- 值域（根因分类/正册类型）

# 兜底类名（与 error-ledger.md §2.6 根因分类表末行「其他」同源）。
# 声明在代码而非表格的原因：表格解析只取**第一列为值域集**，无法承载「哪一行是兜底」
# 这类属性标记。故此项是**唯一的手工耦合点**：改表格那一行的类名须同批改本常量，
# 否则「选兜底类须写括注」的硬拦与占比统计会作用在值域外的名字上（静默失效）。
FALLBACK_CAT = "其他"


def strip_paren(v):
    """剥离限定语括注：`业务逻辑（无长度保护）` → `业务逻辑`（兼容中英文括号）。"""
    return re.split(r'\s*[（(]', (v or '').strip(), 1)[0].strip()


def _domain_paths():
    """域值表路径（按优先级，**单源禁双份**）：

    1. 环境变量 `ERR_CATEGORY_RULES`（项目自有值域表覆写，供接入方用自己的规则表）；
    2. 本技能 `references/error-ledger.md`（真源；仅在技能树内可达）。

    钩子随项目部署后 references 不在可达范围 ⇒ 返回空 ⇒ 调用方**显式告警降级**
    （禁静默放行）；需完整值域校验的项目用 `ERR_CATEGORY_RULES` 指向其表。
    禁在钩子目录另放部署件——双份真源必漂移（ERR-226 族）。
    """
    out = []
    env = os.environ.get('ERR_CATEGORY_RULES', '')
    if env:
        out.append(env)
    here = os.path.dirname(os.path.abspath(__file__))
    out.append(os.path.join(os.path.dirname(here), 'references', 'error-ledger.md'))
    return out


def _table_first_column(path, section, head_prefix):
    """从 markdown 表格取 `<section>` 节内、表头以 `head_prefix` 开头的表第一列集合。

    节名匹配容错：H2/H3 均可、可带编号前缀（`### 2.6 根因分类（值域纪律）` 亦命中）；
    节内块注行（`>`）与空行跳过，禁当表格结束。
    """
    if not path or not os.path.isfile(path):
        return set()
    sec_re = re.compile(r'^#{2,3}\s*(?:\d+(?:\.\d+)*[\.、]?\s*)?' + re.escape(section))
    try:
        with io.open(path, encoding='utf-8') as fh:
            rows = fh.read().splitlines()
    except OSError:
        return set()
    vals, in_sec, seen_head = [], False, False
    for line in rows:
        if sec_re.match(line):
            in_sec = True
            continue
        if in_sec and line.startswith('#'):
            break
        if not in_sec:
            continue
        s = line.strip()
        if not s or s.startswith('>'):
            continue
        if not (s.startswith('|') and s.endswith('|')):
            # 表头前的引导语（bullet/正文）跳过——真源文档中表格常前接说明 bullet；
            # 表头后的非表行＝表格已结束，停。
            if seen_head:
                break
            continue
        cells = [c.strip().strip('`') for c in s.strip('|').split('|')]
        if not seen_head:
            if cells and cells[0].startswith(head_prefix):
                seen_head = True
            continue
        if cells and all(set(c) <= set('-: ') for c in cells):
            continue
        if cells and cells[0] and not cells[0].startswith('**'):
            vals.append(cells[0])
    return set(vals)


def _resolve_domain(section, head_prefix):
    """按候选路径取首个非空值域（env 覆写优先；单源解析，禁双份）。"""
    for p in _domain_paths():
        v = _table_first_column(p, section, head_prefix)
        if v:
            return v
    return set()


def load_categories():
    """根因分类值域（真源＝error-ledger.md §2.6 根因分类表第一列）。"""
    return _resolve_domain('根因分类', '类别')


def load_success_types():
    """正册类型三值（真源＝error-ledger.md §3.2 类型判定表第一列）。"""
    return _resolve_domain('准入与类型判定', '类型')


# ---------------------------------------------------------------- 写侧路径判别

_ERR_FILE_RE = re.compile(r'[\\/]ERR-\d+\.md$', re.I)
_SUC_FILE_RE = re.compile(r'[\\/]SUC-\d+\.md$', re.I)
_ERR_IDX_RE = re.compile(r'(?:^|[\\/])(?:error|errors)_index\.md$', re.I)
_SUC_IDX_RE = re.compile(r'(?:^|[\\/])success_index\.md$', re.I)


def ledger_target(path):
    """判别写目标属于正反手册哪类：err/suc 单条、err_index/suc_index 索引、或 None。"""
    low = (path or '').replace('\\', '/')
    if _ERR_IDX_RE.search(low):
        return 'err_index'
    if _SUC_IDX_RE.search(low):
        return 'suc_index'
    if _ERR_FILE_RE.search(low):
        return 'err'
    if _SUC_FILE_RE.search(low):
        return 'suc'
    return None


# ---------------------------------------------------------------- 字段解析（单条正文/ front-matter）

_BOM = '﻿'
FM_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$')
FM_BLOCK_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.S)
PAREN = r'\s*(?:[（(][^）)]*[）)]?)?'


def fm_block(text):
    """解析 front-matter → dict；**支持 `key: |-` block scalar**（多行值）。

    无 front-matter 返回 None。块标尺漏掉会把 `keywords` 读成字面量 `|-`
    ⇒ 索引第 2 段全丢而校验器仍报 PASS（假绿）。
    """
    m = FM_BLOCK_RE.match((text or '').lstrip(_BOM).lstrip())
    if not m:
        return None
    out, cur, block = {}, None, False
    for line in m.group(1).splitlines():
        kv = FM_KEY_RE.match(line)
        if kv:
            cur = kv.group(1)
            val = kv.group(2).strip()
            block = val in ('|', '|-', '>', '>-')
            out[cur] = '' if block else val
        elif block and cur and line.startswith((' ', '\t')):
            out[cur] = (out[cur] + ' ' + line.strip()).strip()
        elif block and cur and not line.strip():
            continue
        else:
            block = False
    return out


def inline_match(text, name):
    """正文行内式字段（行首或紧随 `|` 之后；前缀可 `>`/`-`/`*`/无；栏名可带括注）。"""
    pat = r'(?:^|\|)\s*(?:[>\-*]\s*)?' + re.escape(name) + PAREN + r'[:：](.*)$'
    return re.search(pat, text, re.M)


def head_match(text, name):
    return re.search(r'^#{1,4}\s*' + re.escape(name) + PAREN + r'\s*$', text, re.M)


def present(text, name):
    return bool(inline_match(text, name) or head_match(text, name))


def value(text, name):
    m = inline_match(text, name)
    if m:
        return m.group(1).strip()
    h = head_match(text, name)
    if h:
        for line in text[h.end():].splitlines():
            s = line.strip()
            if s:
                return s
    return ''


def fm_value(text, key):
    """取 front-matter 键值（单值形态；block scalar 取拼接值）。

    判定源唯一化：`type` 等键在 front-matter 与正文各存一份（双写）时，
    一律以 front-matter 为准，正文仅作缺 front-matter 时的回退，
    避免「改一处不同步」导致守卫与校验结论相反。
    """
    fm = fm_block(text)
    if fm is None:
        return ''
    return (fm.get(key) or '').strip()


def int_value(text, name):
    """取该字段的首个数字（值形态多样：`1`、`1 | Tasks: 1（说明）`、`1（说明）`）。"""
    raw = value(text, name)
    m = re.match(r'\d+', raw)
    return int(m.group(0)) if m else None


# --------------------------------------------- hook 载荷 IO（stdin 单源）

def fix_stdio():
    """把 stdout/stderr 固定为 UTF-8：Windows 默认 locale（cp936）会把中文提示写成
    GBK 字节，消费方按 UTF-8 解码即乱码。"""
    for name in ('stdout', 'stderr'):
        stream = getattr(sys, name, None)
        if stream is None or not hasattr(stream, 'reconfigure'):
            continue
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, OSError):
            pass


def read_stdin_payload():
    """读取 hook 挂载载荷（stdin 的 JSON），返回 `(payload, err)`。

    `payload` 为 dict 或 None（空载荷 / 解析失败）；`err` 为异常或 None
    （调用方按需 fail-open 留痕，禁静默）。
    显式 UTF-8 解码：stdin 默认按 locale（中文 Windows=GBK）解码会把 UTF-8
    字节流解成乱码，并把 JSON 的 `\\n` 转义反斜杠当 GBK 尾字节吞掉——中文载荷的
    front-matter 结构随之崩坏，写侧守卫误拒合规条目。
    """
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', errors='replace')
    except Exception:
        try:
            raw = sys.stdin.read()
        except Exception as exc2:
            return None, exc2
    raw = raw.lstrip(_BOM)
    if not raw.strip():
        return None, None
    try:
        return json.loads(raw), None
    except Exception as exc:
        return None, exc


def tool_input_of(payload):
    """取 `payload['tool_input']` 且限定 dict；非 dict（None/str/list）返 `{}`。

    防畸形载荷在下游 `.get` 抛 AttributeError——违反「异常一律放行 exit 0」。
    """
    ti = payload.get('tool_input') if isinstance(payload, dict) else None
    return ti if isinstance(ti, dict) else {}


def emit_context(lines, event='PostToolUse'):
    """PostToolUse 送达契约：stdout 只输出这一个 JSON，禁与裸 print 混排。

    `hookSpecificOutput.additionalContext` 在 PostToolUse 可达 Agent；
    裸 print 的 stdout 不回传 Agent（PreToolUse exit 2 才是拒绝回传通道）。
    形状与 `step_ref_guard.py`/`graph_impact.py` 既有 emit() 逐字一致。
    """
    fix_stdio()
    msg = '\n'.join(lines)
    print(json.dumps({
        'systemMessage': msg,
        'hookSpecificOutput': {'hookEventName': event, 'additionalContext': msg},
    }, ensure_ascii=False))


# --------------------------------------------- 源码注释状态（扫描器共用单源）

def _block_open_pos(line):
    """首个位于字符串/模板字面量之外的 `/*` 位置；无则 -1。

    字符串内的 `/*`（`$glob = "/*";`、路径通配、JS 正则字面量）不是注释开起——
    旧实现按子串命中即入块注释态，会把后续整段真实代码吞掉（静默漏检）。
    """
    quote = None
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if quote:
            if ch == '\\':
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ('"', "'", '`'):
            quote = ch
        elif ch == '/' and i + 1 < n and line[i + 1] == '*':
            return i
        i += 1
    return -1


def strip_block_comments(text):
    """逐行剥离块注释，返回 [(行号, 代码行)]。

    - `/*` 须在字符串/模板字面量之外才算注释开起（见 `_block_open_pos`）；
    - 闭合同行的**后续代码保留**（`/* c */ SELECT ...` 后半仍须进扫描）；
    - 单行注释（`//`、`#`）与块注释内续行（行首 `*`）由调用方按各自口径再判。
    """
    out = []
    in_block = False
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw
        if in_block:
            end = line.find('*/')
            if end < 0:
                continue
            in_block = False
            line = line[end + 2:]
        while True:
            pos = _block_open_pos(line)
            if pos < 0:
                break
            end = line.find('*/', pos + 2)
            if end < 0:
                line = line[:pos]
                in_block = True
                break
            line = line[:pos] + line[end + 2:]
        out.append((i, line))
    return out
