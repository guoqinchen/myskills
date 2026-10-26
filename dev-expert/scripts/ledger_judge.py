#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正反手册治理判据（升格/归档/退役/反哺/计划状态）——**单一实现**。

分层（与解析层/聚合层分离，禁跨层混判）：
  - 解析原语（front-matter/字段/日期/值域/编号/索引行）一律走 `hooks/ledger_common.py`；
  - 本模块只承载**治理层判据**，被两个手动消费方共用：
      · `recurrence_promote.py`（升格建议 CLI）
      · `metrics_report.py`（M1-M10/R1/R1-SUC 指标聚合）
  - 禁在消费方另写一份判据（ERR-226 族：同一判据两份实现必随演进漂移）。

口径与 `references/error-ledger.md` 同源；裁定权归 **Agent 自评**（ERR-242）——
本模块只产候选与事实，禁含「须用户确认」类裁定文案。

四类候选全部带**处置出口**（候选型指标无出口＝刷屏噪音，ERR-228）：
  升格不升／退役不退役／反哺不反哺 均由单条处置段标记，删段即恢复候选，
  且已处置条数**计数可见**（禁静默跳过，ERR-109：指标报过 ≠ 处理过）。
"""
import os
import re
import sys
from datetime import date as _date, datetime as _dt, timedelta as _td

_HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks')
sys.path.insert(0, _HOOKS_DIR)
import ledger_common as LC  # noqa: E402

# ---- 阈值常量（与 error-ledger.md §2.11/§2.10/§3.4 文字同源；改文字须同批改这里） ----
RECURRENCE_THRESHOLD = 3      # 反册升格：Recurrence-Count ≥ 此值
MIN_TASKS = 2                 # 双册升格：Tasks ≥ 此值
WINDOW_DAYS = 30              # 反册升格：末核落在此窗口内（近期复发）
SUC_HIT_THRESHOLD = 3         # 正册升格：hit_count（被召回消费）≥ 此值——与反册
                              # RECURRENCE_THRESHOLD（复发）是**两个口径**，禁互套
ARCHIVE_MONTHS = 12           # 归档可迁：末核 ≥ 此月数（仍成立的老坑）
ARCHIVE_ZERO_MONTHS = 12      # 归档可迁：首见 ≥ 此月数 且 RC=1（零复用机械近似）
RETIRE_AGE_MONTHS = 12        # 退役候选：year_month 距今 ≥ 此月数
RETIRE_ZERO_REUSE_MONTHS = 6  # 退役候选：零复用 ≥ 此月数（正册条目少，零复用是常态而非信号）
LOWQ_HIT_MIN = 10             # 退役候选·低质命中档：hit_count ≥ 此值
LOWQ_MIN = 5                  # 退役候选·低质命中档：low_quality_hit_count ≥ 此值
M10_NEW_DAYS = 30             # 跨册反哺：首见 ≤ 此天数 ⇒ 新增候选（须处置）；其余存量可见
PLAN_STATES = ('规划中', '进行中', '已完成', '已中止')
ERR_TYPES = ('事实型', '决策失败型')   # 反册 type 二值（与 err_entry_guard 部署态常量同源）
# M6/M7 分类结构健康度阈值（%）：兜底类 >10% ⇒ 垃圾桶化风险；最大桶 >60% ⇒ 该类判据
# 过宽、正在吞并其它层。阈值**只触发评审**，不构成放宽分类或新增类的理由。
# 占比类指标在分母极小时必然失真（1 条单条时两项都 100%）⇒ 样本不足照常输出比率、
# 不告警（口径纪律：分子分母同报，供趋势观察）。
FB_WARN_PCT = 10
TOPCAT_WARN_PCT = 60
MIN_CAT_SAMPLE = 20

# 「已处置」须是**处置结论**而非枚举提及（删段即恢复候选；同款可撤销契约）。
DENIED_RE = re.compile(
    r'(?:处置|评估|评审|记录)[^：:]{0,24}[：:]\s*\*{0,2}(?:不升|已升格)'
    r'|\*{2}(?:不升|已升格|升格记录)\*{0,2}')
_RETIRE_DENIED_RE = re.compile(r'(?m)^#{2,4}\s*退役处置')
_XFEED_DENIED_RE = re.compile(r'(?m)^#{2,4}\s*反哺处置')
_STEP_SEQ_RE = re.compile(r'[①②③④⑤⑥]')
_CMD_RE = re.compile(r'`[^`]+`')
_TASKS_RE = re.compile(r'(?m)^[\s>*\-]*Tasks\s*[:：]\s*(.+)$')
# 日期形态与「数字. 」编号开头是任务名不是任务数，须与纯数字式分档（ERR-235 同族）
_TASKS_NAME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}|^\d+[.、]\s*\S')


# ---------------------------------------------------------------- 基础解析（原语走 LC）

def to_int(v):
    try:
        return int(str(v))
    except Exception:
        return 0


def to_date(v):
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return _dt.strptime(str(v), fmt)
        except Exception:
            continue
    return None


def months_ago(iso, today=None):
    """由 `YYYY-MM-DD` 算月差；空值或非法返回 None（禁静默当 0）。"""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', iso or '')
    if not m:
        return None
    today = today or _date.today()
    try:
        dd = _date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return (today.year - dd.year) * 12 + (today.month - dd.month)


def _read(md_path):
    try:
        with open(md_path, encoding='utf-8', errors='ignore') as fh:
            return fh.read()
    except OSError:
        return ''


def parse_recurrence(md_path):
    """解析单条复发/复用/档位字段 → dict；不可读返回 None。

    日期两键走 LC.date_parse（六形态唯一实现）；**占位日期返回 None**——
    占位＝「原始记录缺失」恒为补录当天，若参与 30 天窗口判定，老条目会被误判
    「近期复发」而进升格候选。
    hit_count/quality/utility 走 front-matter 优先（LC.fm_block），与写侧守卫同源。
    """
    text = _read(md_path)
    if not text:
        return None

    def _date_field(name_cn):
        d = LC.date_parse(text, name_cn)
        return None if (not d['date'] or d['placeholder']) else d['date']

    fm = LC.fm_block(text) or {}

    def _field(name):
        v = LC.value(text, name)
        if not v:
            v = (fm.get(name) or '').strip()
        return v.strip()

    def _num(name):
        # 数值字段取**前导数字**：行内值常带括注说明（`3（2026-09-04 同根因复发：…）`），
        # 整值直传 to_int 会解析失败归 0 ⇒ 升格候选被静默漏判（parity 实测，ERR-052/153）。
        m = re.match(r'\d+', _field(name))
        return m.group(0) if m else ''

    return {
        'count': _num('Recurrence-Count'),
        'first': _date_field('首见'),
        'last': _date_field('末核'),
        'tasks': _num('Tasks'),
        'hit': _num('hit_count'),
        'quality': LC.strip_paren(_field('quality')),
        'utility': LC.strip_paren(_field('utility')),
    }


def tasks_of(md_path):
    """跨任务数（两册共用，禁调用方另写一份解析——ERR-235 三档修法）：
    数字式直取；括注式取前导数字；任务名式（日期/编号开头）与清单式
    **均按分隔符计条目数**；单条不可读返回 0。"""
    m = _TASKS_RE.search(_read(md_path))
    if not m:
        return 0
    raw = m.group(1).strip()
    if raw.isdigit():
        return int(raw)
    m2 = re.match(r'^(\d+)\s*[（(]', raw)
    if m2:
        return int(m2.group(1))
    # 任务名式（日期/编号开头）与清单式同一切分路径：旧实现对任务名式恒返回 1，
    # 跨任务数被低估 ⇒ tasks>=MIN_TASKS 永不成立（升格候选假阴，ERR-235 修法倒退）
    return len([x for x in re.split(r'[,，、;；]', raw) if x.strip()])


def is_promote_denied(md_path):
    """单条是否已标「不升/已升格」处置（命中即不再作为候选；删段即恢复）。"""
    return bool(DENIED_RE.search(_read(md_path)))


def retire_denied(text):
    """该 SUC 是否已标「不退役」处置（M9-SUC 出口；删段即恢复候选）。"""
    return bool(_RETIRE_DENIED_RE.search(text)) and '不退役' in text


def xfeed_denied(text):
    """该 ERR 是否已标「不反哺」处置（M10 出口；删段即恢复候选）。"""
    return bool(_XFEED_DENIED_RE.search(text)) and '不反哺' in text


# ---------------------------------------------------------------- 计划状态（M1）

_RE_STATE_HEAD = re.compile(r'^##\s*状态\s*$', re.M)
_RE_STATE_INLINE = re.compile(r'状态[:：]\s*(' + '|'.join(PLAN_STATES) + ')')
_RE_STATE_PREFIX = re.compile(r'^(' + '|'.join(PLAN_STATES) + r')(?![^\s（(：:·,，。\-—])')


def plan_state(path):
    """plan 状态解析：`## 状态` 节首非空行（可带「已完成（日期）· 摘要」前缀形态）
    → 行内 `状态: X` 回退；不可解析返回空串（禁猜）。"""
    text = _read(path)
    m = _RE_STATE_HEAD.search(text)
    if m:
        for line in text[m.end():].splitlines():
            s = line.strip()
            if not s:
                continue
            if s in PLAN_STATES:
                return s
            m3 = _RE_STATE_PREFIX.match(s)
            if m3:
                return m3.group(1)
            break
    m2 = _RE_STATE_INLINE.search(text)
    return m2.group(1) if m2 else ''


# ---------------------------------------------------------------- 升格候选（R1/R1-SUC）

def err_promote_candidates(err_index, err_dir, today=None):
    """反册升格候选：RC≥3 且 Tasks≥2 且末核在 30 天窗口内，且未标「不升」。

    返回 [(编号, 描述)]；末核取单条 `末核`，缺则回退索引行 date 列。
    """
    out = []
    for r in LC.index_rows(err_index, 'ERR'):
        md_path = LC.ledger_md_path(err_dir, r['eid'])  # 扁平/年月经兼容（禁按前缀硬拼）
        if not os.path.isfile(md_path):
            continue
        if is_promote_denied(md_path):
            continue
        rc = parse_recurrence(md_path)
        if not rc or not rc['count']:
            continue
        last = to_date(rc['last']) or to_date(r['date'])
        in_window = ((today or _dt.now()) - last).days <= WINDOW_DAYS if last else False
        if (to_int(rc['count']) >= RECURRENCE_THRESHOLD
                and tasks_of(md_path) >= MIN_TASKS and in_window):
            out.append((r['eid'], r['desc']))
    return out


def suc_promote_candidates(suc_index, suc_dir):
    """正册升格候选（阈值判定留给调用方）：
    返回 [(编号, hit, tasks, 已标不升, 描述)]。"""
    out = []
    for r in LC.index_rows(suc_index, 'SUC'):
        md_path = LC.ledger_md_path(suc_dir, r['eid'])  # 扁平/年月经兼容（禁按前缀硬拼）
        if not os.path.isfile(md_path):
            continue
        rc = parse_recurrence(md_path)
        if not rc or rc['hit'] == '':
            continue
        out.append((r['eid'], to_int(rc['hit']), tasks_of(md_path),
                    is_promote_denied(md_path), r['desc']))
    return out


def suc_promote_pass(candidates):
    """正册候选中达阈值且未处置的条目（hit≥3 且 tasks≥2 且未标不升）。"""
    return [e for e, h, t, den, _d in candidates
            if h >= SUC_HIT_THRESHOLD and t >= MIN_TASKS and not den]


# ---------------------------------------------------------------- 归档可迁（M9）

def archive_candidates(err_dir, today=None):
    """反册归档可迁候选＋日期不可判清单。

    判据（与 error-ledger §2.10 同源）：末核 ≥12 个月，或 首见 ≥12 个月且 RC=1。
    占位/缺失日期**不参与判定**（占位恒为补录当天，会让他最老的条目伪装成
    「刚核实过」而永久躲过归档筛）——但须显性返回，禁静默跳过。
    """
    cands, undated = [], []
    for base, _dirs, files in os.walk(err_dir):
        for name in sorted(files):
            if not (name.startswith('ERR-') and name.endswith('.md')):
                continue
            text = _read(os.path.join(base, name))
            d1 = LC.date_parse(text, '末核')
            d2 = LC.date_parse(text, '首见')
            a1 = None if d1['placeholder'] else months_ago(d1['date'], today)
            a2 = None if d2['placeholder'] else months_ago(d2['date'], today)
            if d1['placeholder'] or d2['placeholder'] or not (d1['date'] and d2['date']):
                undated.append(name[:-3])
            rc = to_int(LC.value(text, 'Recurrence-Count'))
            if ((a1 is not None and a1 >= ARCHIVE_MONTHS)
                    or (a2 is not None and a2 >= ARCHIVE_ZERO_MONTHS and rc == 1)):
                cands.append(name[:-3])
    return cands, undated


# ---------------------------------------------------------------- 正册退役候选（M9-SUC）

def retire_candidates(suc_dir, today=None):
    """正册退役候选＋已处置计数＋全册最早 year_month（可达性判断）。

    判据四取一：year_month≥12 月 ｜ 零复用≥6 月 ｜ 低质命中（hit≥10 且 lowq≥5
    且 lowq×2≥hit）｜ utility∈{待复核,已失效}。⚠「零复用」「低质」都只作信号、
    **不等于失效**——是否退役须人工裁定（机械只做筛选）。
    """
    cands, denied_n, ym_min = [], 0, None
    for base, _dirs, files in os.walk(suc_dir):
        for name in sorted(files):
            if not (name.startswith('SUC-') and name.endswith('.md')):
                continue
            text = _read(os.path.join(base, name))
            fm = LC.fm_block(text) or {}
            ym = ''
            m = re.match(r'^(\d{4})/(\d{1,2})', (fm.get('year_month') or '').strip())
            if m:
                ym = '%s-%02d' % (m.group(1), int(m.group(2)))
            m_ago = months_ago(ym + '-01', today) if ym else None
            if ym and (ym_min is None or ym < ym_min):
                ym_min = ym
            hc = to_int(LC.value(text, 'hit_count'))
            lq = to_int(LC.value(text, 'low_quality_hit_count'))
            lowq = hc >= LOWQ_HIT_MIN and lq >= LOWQ_MIN and lq * 2 >= hc
            util = LC.strip_paren(LC.value(text, 'utility'))
            hit = ((m_ago is not None and m_ago >= RETIRE_AGE_MONTHS)
                   or (m_ago is not None and m_ago >= RETIRE_ZERO_REUSE_MONTHS and hc == 0)
                   or lowq or util in ('待复核', '已失效'))
            if not hit:
                continue
            if retire_denied(text):
                denied_n += 1
            else:
                cands.append(name[:-3])
    return cands, denied_n, ym_min


# ---------------------------------------------------------------- 跨册反哺候选（M10）

def xfeed_candidates(err_dir, suc_dir, today=None):
    """跨册反哺候选（error-ledger「跨册反哺义务」的机械近似）。

    机械可判的一半：ERR 的「正确做法」含**可照做步骤**特征（≥3 个 ①②③ 序号，
    或 ≥2 序号＋≥2 条反引号命令——宁少不误，候选过量＝指标失效），且该 ERR 编号
    未出现在任一 SUC 单条（无交叉引用）。
    按规则适用范围分列：新增（首见 ≤30 天）为须处置候选；超窗/日期不可判为
    存量可见列（存量不批量追溯，列候选会使其无法按规则清零——ERR-228 族）。
    """
    suc_text = ''
    for base, _dirs, files in os.walk(suc_dir):
        for name in files:
            if name.startswith('SUC-') and name.endswith('.md'):
                suc_text += _read(os.path.join(base, name))
    cutoff = ((today or _date.today()) - _td(days=M10_NEW_DAYS)).isoformat()[:10]
    new, stock, linked, denied = [], [], 0, 0
    for base, _dirs, files in os.walk(err_dir):
        for name in sorted(files):
            if not (name.startswith('ERR-') and name.endswith('.md')):
                continue
            text = _read(os.path.join(base, name))
            how = LC.value(text, '正确做法')
            if not how:
                continue
            seq = len(_STEP_SEQ_RE.findall(how))
            cmd = len(_CMD_RE.findall(how))
            if not (seq >= 3 or (seq >= 2 and cmd >= 2)):
                continue
            eid = name[:-3]
            if eid in suc_text:
                linked += 1
            elif xfeed_denied(text):
                denied += 1
            else:
                d = LC.date_parse(text, '首见')
                if d['date'] and not d['placeholder'] and d['date'] >= cutoff:
                    new.append(eid)
                else:
                    stock.append(eid)
    return {'new': new, 'stock': stock, 'linked': linked, 'denied': denied}
