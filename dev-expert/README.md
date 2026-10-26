# 编程专家 - dev-expert - 一招吃遍天下鲜

一个覆盖编程全生命周期的全栈编程助手：说需求，它自动选对工具并组合执行，你不必记任何名字。

```
                    _ooOoo_
                   88" . "88
                   (| -_- |)
                   O\  =  /O
                ____/`---'\____
              .'  \\|     |//  `.
             /  \\|||  :  |||//  \
            /  _||||| -:- |||||-  \
            |   | \\\  -  /// |   |
            | \_|  ''\---/''  |   |
            \  .-\__  `-`  ___/-. /
          ___`. .'  /--.--\  `. . __
       ."" '<  `.___\_<|>_/___.'  >'"".
      | | :  `- \`.;`\ _ /`;.`/ - ` : | |
      \  \ `-.   \_ __\ /__ _/   .-` /  /
 =====`-.____`-.___\_____/___.-`____.-'=====
                    `=---='
 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          佛祖保佑       永无BUG
```

> 📌 Github 上吹得再牛的技能，没有实战写不出任何有用的东西。纸上谈兵的都是扯蛋……
> 🚀 **第一次用？只看这段**：直接说你的目标（如"帮我给后台加个导出按钮"），路由、组合、验证它全包了；只有"报错 / 不确定能不能做"时才需要查 FAQ。

> 📌 **TL;DR**
>
> - **是什么**：19 个子技能的全链路编程助手；说需求即自动匹配 + 自动组合，无需记名字。
> - **怎么用**：自然对话说目标，带上「目标 + 约束 + 验收」最省事；边界与报错查 FAQ。
> - **护栏**：hooks 是可选增强（备份 / lint / 安全）；红线（直拼 SQL、盲写库、跳过验证）踩了会被拦。
> - **深入**：细节在 `references/*.md`，本文件只给入口与导航。
> - **知识图谱**：`@project-knowledge-graph` 纯正则建依赖图、查询近零 token（见附录 A）；高级进阶功能，须按自身环境适配。

### ⚠️ 注意

> 本技能的目的是跨工具快速迁移：工具不好用就换，进度 / 规范 / 踩坑错误册 / 图谱都不被任何工具束缚，可随工具迁移。
> hooks 与 scripts（知识图谱）属高级进阶功能，须按自身运行时适配后生效。

## 子技能列表

> 19 个子技能一表速览。**你不需要背它们**——上表只帮你判断交付结果是否符合预期，说需求即自动匹配。

| 子技能 | 功能 | 触发关键词 |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 软件项目总控 | 通用软件项目从需求到交付的总控：边界、行为契约、架构、数据/API/集成、测试、安全、发布、回滚、监控、告警、巡检和沉淀 | 软件项目, API服务, 后端服务, 后台模块, CLI工具, 数据脚本, 自动化任务, 插件项目, 完整功能, 项目交付, 部署, 发布, 回滚, 运维, 监控, 告警, 巡检 |
| 网站项目总控 | 从需求到上线的建站项目总控：站点规划、内容SEO、前端设计、CMS/API/数据、测试安全、性能部署、验收运维 | 做网站, 建站, 企业官网, 营销页, CMS网站, 网站上线, 网站交付 |
| API设计 | 根据业务需求设计RESTful或GraphQL API接口，长任务采用 Init-Step-Poll 契约 | API设计, RESTful, GraphQL, 接口规范, AJAX防卡死, Init-Step-Poll, 长任务接口, 轮询接口 |
| Bug诊断 | 分析错误日志和异常堆栈，定位Bug根因并给出修复方案 | Bug诊断, debug, 报错, 异常堆栈 |
| Karpathy编码规范 | 提供Karpathy核心编码哲学：思考优先、简洁至上 | Karpathy编码规范, Karpathy, 编码哲学 |
| Spec驱动开发 | 编码前对齐需求规格，使用OpenSpec artifact flow | Spec驱动开发, spec, 需求对齐 |
| 代码审查 | 审查代码质量，发现Bug、安全漏洞和代码缺陷 | 代码审查, code review, 代码缺陷 |
| 代码生成 | 根据功能需求生成高质量代码，含错误处理和边界条件 | 代码生成, 生成代码, 实现功能 |
| 任务拆解与执行 | 将复杂需求拆分为原子任务，按Wave分组执行 | 任务拆解与执行, 任务分解, Wave执行 |
| 技术选型 | 根据项目需求推荐合适技术栈、框架和工具，并给出运行时基线与版本策略 | 技术选型, 技术栈, 框架选型, 运行时基线, 版本策略 |
| 文档生成 | 根据代码生成技术文档、README、API文档、部署说明和运维文档 | 文档生成, API文档, README, 部署说明, 回滚说明, 运维文档 |
| 测试用例生成 | 生成单元测试、集成测试、安全测试、性能测试和长任务测试 | 测试用例生成, 单元测试, 测试用例, 安全测试, 性能测试, 长任务测试 |
| 重构建议 | 分析代码结构，识别坏味道并提供重构方案 | 重构建议, 重构, 坏味道, 代码异味 |
| 项目记忆管理 | 捕获上下文和决策，实现跨会话项目记忆沉淀，并治理工作产物生命周期（计划 / 错误册 / 图谱 / 生成产物） | 项目记忆管理, 项目记忆, 跨会话, 产物生命周期 |
| CMS二次开发 | PHP+MySQL CMS 二次开发全链路：CMS探测/PHP版本/数据库规范/安全红线/插件开发/长任务防卡死 | CMS, 帝国CMS, WordPress, ThinkPHP, PHP8兼容, 二次开发, 插件开发, 批量任务, 导入导出, 生成静态页 |
| 前端设计 | UI/UX 与前端实现设计：设计思维、信息架构、视觉规范、品牌、Banner、图标、社媒图、响应式、可访问性、安全性、命名规范、目录规范、代码质量、ESLint基线、性能实现、浏览器验证、进度轮询 | 前端设计, UI设计, UX, 交互设计, 响应式, 设计系统, 前端安全, 命名规范, 目录规范, ESLint, 代码质量, 性能实现, 品牌设计, Banner, 图标, 社媒图, 进度条, 轮询状态 |
| MySQL数据库 | MySQL 数据建模、SQL安全、索引设计、事务边界、慢查询诊断、迁移回滚和数据安全 | MySQL, 数据库设计, SQL, 索引, 事务, 慢查询, EXPLAIN, DDL, 迁移, 表结构, SQL优化 |
| 性能基准测试 | 量化性能验证：识别触发面、测量耗时/内存/吞吐量、生成瓶颈报告、优化前后A/B对比 | 性能测试, benchmark, 基准测试, 耗时分析, 内存分析, 吞吐量, QPS, 瓶颈分析, 性能对比 |
| 项目知识图谱 | 为项目自动构建代码结构依赖图谱（节点+依赖边），跨模块改动/重构/审查时查依赖闭包与影响面；纯 agent 受众，不生成 mermaid 可视化 | 依赖图, 模块关系, 谁依赖, 影响面, 代码结构图谱, 画依赖图, 依赖分析, 改这个会影响哪些文件 |

## 使用方法

### 3 分钟上手

| 你想做什么 | 推荐说法 | 会进入 |
| ------------------ | ------------------------------------------------- | ------------------------------------ |
| 写一个功能 | "帮我实现登录接口，要求有参数校验和测试" | 代码生成 + 测试用例生成 |
| 修一个报错 | "这个报错帮我定位原因并给修复方案" | Bug诊断 |
| 检查代码有没有问题 | "审查这个文件，重点看安全和性能" | 代码审查 |
| 做 CMS/PHP 二开 | "这是 WordPress/帝国CMS 项目，帮我加一个后台功能" | CMS二次开发 |
| 设计接口 | "设计一个订单导出接口，数据量大，需要进度条" | API设计 + Init-Step-Poll |
| 换电脑继续上次任务 | "继续上次任务，先恢复 handoff" | 项目记忆管理 |
| 顺带做两件事 | "实现导出接口，顺带生成接口文档" | 代码生成 + 文档生成 |
| 不知道功能叫啥 | "帮我看看这段代码安不安全" | 代码审查（描述目标即可，不必记名字） |

### 需求怎么说最省事

万能公式：**目标 + 约束 + 验收**。越齐，追问越少。

- ❌ 太模糊：`帮我把系统优化一下` → 会触发 Wayfinder 探索，先和你对齐再动手（不是错，但慢）。
- ✅ 直接命中：`用户列表接口响应超过 2s，帮我定位慢查询并加索引，目标降到 200ms 内` → 命中 `mysql-database` + `performance-benchmark`。
- ✅ 带约束：`给后台加一个导出用户的功能：范围=按筛选条件、格式=CSV、要鉴权+限频、能正确导出 1 万行且带表头`。
- ✅ 顺带式：`实现登录接口，并生成单元测试`；`定位这个报错，顺带看看附近代码有没有安全隐患`。
- ✅ 纠正：`刚才那个修复不对，第 12 行的判空应该用 if x is None 而不是 if not x` → 重做并复跑验证。

> 关键：**说目标比背名字更稳**。不确定叫啥就直接描述；命中不了会问你一句，不会偷偷用错技能。

### 一次交互的输入与产出（示例）

**覆盖范围内**

- 输入：`实现登录接口，要参数校验和单元测试`
- 技能路径：路由「代码生成」+「测试用例生成」→ Step 2 方案 → Step 3 实现 → Step 4 验证
- 产出（收尾报告 5 字段，示意）：`任务` 登录接口 + 参数校验 + 单测 ｜ `完成情况` 3 文件改动，测试 8 例通过 ｜ `关键决策` 校验放 DTO 层、密码用 bcrypt ｜ `验证证据` `pytest -q` → `8 passed`（原始输出）｜ `待办` 未做限流（未要求）

**未覆盖领域**

- 输入：`帮我做个微信小程序，WXML 分包 + setData 卡顿`
- 技能路径：`--detect` → `VERDICT=GAP` → 打 `[DOMAIN-GAP: miniprogram]`
- 产出：缺口声明（本领域无专项判据，以下用通用判据替代，可能与领域规范不符）+ 二选一（A 仅声明继续 / B 取证生成专项判据）

### ⚠️ 上手前先扫一眼红线

- **不覆盖的领域**：用户调研、工时排期、容器深度编排、IDE 配置、缺陷跟踪流程、安全深度扫描（只做边界说明）。
- **仅覆盖判据 / 载体 / 度量口径层（不含组织决策）**：`technical-strategy`、`tech-influence`、`engineering-metrics`。
- **执行禁区**：直拼 SQL、Shell 写中文/UTF-8 文件、跨模块扩散修改、硬编码密钥、跳过验证直接交付、为让验收通过而改测试 / 放宽断言、安全/数据类失败重试、凭猜测补业务规则、快速通道执行数据库写入、跨模块(≥2)/批量替换(>10处) 走快速通道。
- **关键限制**：流程按任务档位剪裁（**轻量 / 常规 / 复杂 / 大项目**，执行集见 `references/routing.md`「档位 → 最小执行集」）；单次最多加载 3 个协同 reference（**Step 强制加载集不计**）；子 Agent 禁止写/改代码（只做检索收集）；代码审查是**只读**的、不自动改写实现；Laravel / Java / JS 等专项 reference 不支持 `@` 显式调用（用关键词触发）；涉库写入 / 权限 / 生产配置须先给方案与回滚路径；未覆盖领域（小程序 / App / Unity 等）须先声明 `[DOMAIN-GAP]`，禁按最近邻冒充。

> ⚠️ 红线不是建议：直拼 SQL / 盲写库 / 跳过验证直接交付，踩了会被安全闸门拦截、交付判无效。

### 文档阅读顺序

| 场景 | 先看 | 再看 |
| -------------------------- | --------------------------------------------------- | ------------------------------------- |
| 只想知道怎么用 | 本文件「3 分钟上手」与「子技能列表」 | `FAQ.md` |
| 不知道该用哪个技能 | 本文件「子技能列表」 | `references/routing.md` 领域路由表 / 优先级矩阵 |
| 遇到报错、卡住、看不懂提示 | `FAQ.md` | 对应 `references/*.md` 的失败回退机制 |
| 长任务执行 / 续做 / 可靠交付 | `FAQ.md` 第九节 | `references/task-decomposition-and-execution.md` |
| 要改技能执行规则 | `SKILL.md`（薄入口 + 强制加载表） | 对应 `references/*.md` |
| 任务领域不在技能范围内（小程序 / App / Unity） | 本文件「未知领域自进化（DOMAIN-GAP）」 | `FAQ.md` 二十二、未知领域自进化 |
| 想先知道哪些不能做 / 红线 | `FAQ.md`「能力边界速览」/ 二、执行禁区 / 六、边界外 | `references/execution-safety.md` 安全闸门 / 澄清策略分级 |

### 组合与进阶

- **组合是自动的**：说清完整目标（如"实现导出功能并出接口文档"）即自动串联（代码生成 + 文档生成），不必手动点名先后。
- **想精确控制时才显式表达**：① 顺带式点名；② 多个 `@`（"`@code-review` 先审，`@refactoring` 再重构"）——只跳过路由匹配，不影响协同加载。
- **典型顺序**：审查类（代码审查 / Bug诊断）只读，先出报告、你确认后再走重构 / 生成；性能类先跑基线再重构，禁止无基线声称提升。
- **完整协同顺序（20 条）与优先级矩阵**：见 `references/routing.md`「协同顺序规则」（本文件不再重复清单）。

## 未知领域自进化（DOMAIN-GAP）

技能不假装什么都会：任务落在没有专项判据的领域（小程序、移动 App、Unity、嵌入式…）时，**先判缺口，再决定要不要长出能力**。

**识别（Step 1.2 自动跑）**：`python scripts/domain_evolve.py --detect "<任务描述>"` → `VERDICT=COVERED | GAP | UNSURE`

- 三路信号：既有 reference 的「不适用 / 不覆盖」声明（硬信号）／领域路由表触发词命中／任务里的技术词在全部 reference 未出现
- `GAP` ⇒ 打 `[DOMAIN-GAP: <domain>]` 并列出缺哪些判据；`UNSURE` ⇒ 先语义裁决，不猜
- **不以固定词表为门槛**：词表未收录的领域（如 Unity）同样会被判出来

**两种处置**：

| | A 仅声明 | B 同一会话内进化 |
|---|---|---|
| 做什么 | 明确告知「本领域无专项判据，以下用通用判据替代，可能与领域规范不符」，任务照常推进 | 生成草稿 → 取证填充 → 校验 → 注册，长出专项 reference |
| 命令 | 无 | `--scaffold <domain> --title <中文名>` → 填判据 → `--validate` → `--register`（dry-run）→ `--register --apply` → `--check` |
| 适合 | 一次性问题 | 反复出现的领域 |

**硬约束（防伪判据）**：

- 每条判据必须带**证据锚**（官方文档 `URL#章节` 或项目 `文件:行号`），**无锚不收**
- ≥5 条判据 + 七节骨架（输入要求 / 核心判据 / 执行流程 / 输出格式 / 失败回退机制 / 关联 reference / 验证清单），`--validate` 不过不得注册
- 首版标 `v0.1-provisional`，满 3 个真实任务前不得用于否决你的方案
- 注册默认 dry-run，`--apply` 才写盘；写前 `.bak`，写后回读，`--check` 校验孤儿/悬空/计数
- 当前只到「专项 reference」档（关键词触发）；要 `@` 子技能需另行升级，不自动扩大调用面
- 不改 `hooks/`、断言与评分基线

**边界**：判据只来自公开规范与真实项目实码；没有取证来源时只声明缺口，不编造领域规范。

## 如何扩展子技能

三种扩展方式，按成本从低到高选：

| 方式 | 适用 | 产物 | 注册点 | 触发方式 |
|---|---|---|---|---|
| ① 补既有 reference | 领域已有文件、只是缺判据 | 改 `references/<name>.md` | 无（已在册） | 不变 |
| ② 新增专项 reference | 新领域、关键词触发足够 | `references/<domain>.md` | 领域路由表 +1、专项映射 +1、计数同步 | 关键词 |
| ③ 新增正式子技能 | 需要 `@<domain>` 点名 | 同 ② | ② 全部 + 子技能索引 +1 + README 子技能表 +1 + 子技能计数 19→20 | `@` + 关键词 |

### 自动生成（推荐先用，只到 ② 档）

```bash
python scripts/domain_evolve.py --scaffold <domain> --title <中文名>   # 生成骨架
# 取证填充：每条判据带锚（官方文档 URL#章节 / 项目 文件:行号）
python scripts/domain_evolve.py --validate <domain>                  # 不过则回填
python scripts/domain_evolve.py --register <domain>                  # dry-run 预览
python scripts/domain_evolve.py --register <domain> --apply          # 落盘（写前 .bak）
python scripts/domain_evolve.py --check                               # 孤儿/悬空/计数
```

**升级到 ③ 档须手工补两处注册**（子技能索引 + README 子技能表）——不自动化，因为它扩大调用面，会影响优先级矩阵与协同顺序。

### 手工新增清单（逐项打勾，缺一即孤儿或悬空）

1. **命名**：英文标识 `^[a-z][a-z0-9-]{2,30}$`（与脚本白名单一致）；文件 `references/<标识>.md`；中文名 3-5 字
2. **七节骨架**：输入要求 / 核心判据（≥5，每条带证据锚）/ 执行流程（须出现 `Step 2/3/4`）/ 输出格式 / 失败回退机制 / 关联 reference / 验证清单
3. **首版标记**：文首 `> 版本: 0.1-provisional ｜ 证据源: … ｜ 已验证任务: 0`
4. `references/routing.md`「子技能索引」加 1 行（仅 ③ 档）
5. `references/routing.md`「领域路由表」加 1 行（触发信号 / 首选 / 协同 / 路由边界）
6. `references/routing.md`「专项 reference 映射」加 1 行
7. `README.md`「子技能列表」加 1 行（仅 ③ 档）+ **全量同步计数**：搜索旧值并替换**所有出现处**（`19 个子技能`、`共 46 个 md`），不要只改表头那一行
8. `routing.md`「专项 reference 映射」表末注「专项计 N 个」与 README「N 个专项 reference」同口径同步

各档计数变化（以当前 19 子技能 / 25 专项 / 46 md 为基线）：

| 档 | 子技能数 | 专项数 | md 总数 |
|---|---|---|---|
| ② 新增专项 reference | 19（不变） | 25 → 26 | 46 → 47 |
| ③ 新增正式子技能 | 19 → 20 | 25（不变） | 46 → 47 |

> 计数是 `--check` 的硬判据：声明与磁盘不符会直接 FAIL，所以第 7、8 步不要留到"以后补"。

### 验收（必须全绿才算扩展完成）

| 命令 | 期望 |
|---|---|
| `python scripts/domain_evolve.py --check` | `CHECK=PASS`，无孤儿 / 悬空，计数一致 |
| `python hooks/step_ref_check.py` | `✅ 全部匹配`，EXIT=0 |
| `python scripts/domain_evolve.py --validate <domain>` | `VALIDATE=PASS`（② / ③ 档） |
| 真实任务 E2E | 用该领域一个真实任务跑通，附证据（命令输出 / 截图 / 体积数值） |

### 反模式（会被门禁拒绝或留下隐患）

- 只写介绍不写判据 → `--validate` 判「<5 条」拒收
- 判据无证据锚 → 拒收（防模型记忆入库）
- 抄邻近领域规范不标差异 → 至少落 A 档声明「以通用判据替代，可能不符领域规范」
- 加了 `@` 却没进子技能索引 → 调用不到，等同不存在
- 计数漏改 → `--check` 报「声明 N / 实际 M」并 FAIL
- 把草稿直接放 `references/` → 计入 md 总数、被当孤儿；草稿只放 `references/.drafts/`

## Hooks 自动守卫（可选，高级进阶；须按自身运行时适配）

> **非开箱即用**：须按自身运行时部署 / 接入后才生效。共 28 个可选护栏钩子（PreToolUse 9 + PostToolUse 18 + PreCompact 1），跨 IDE 用**工具名并集匹配（matcher）**，接入后自动匹配。

覆盖机械兜底项：备份、lint、PHP8 兼容、安全 / 脱敏、UTF-8、调试残留、`SELECT *`、压缩快照、规划拦截、受保护目录写前拦截、写入前综合检查、数据外发拦截、踩坑召回 / 查重、图谱影响面、日迹归档、步骤号引用一致性。

### 设计要点（每条可在 `hooks/*.py` 中检索到依据）

| # | 设计要点 | 依据 |
| - | - | - |
| 1 | **写前阻断是最强的送达通道**——PostToolUse 裸 stdout 不回传 Agent（其 `hookSpecificOutput.additionalContext` JSON 可送达），只有 PreToolUse `exit 2` 能回传**拒绝理由**；故「必须拒绝」的检查走写前 | `hooks/precheck_on_write.py:3-7`、`step_ref_guard.py:56-62` |
| 2 | **组合模式压误报**——安全项要求「危险函数 **且** 用户输入源」同现才命中；`replace_in_file` 只审 `new_str` 片段 | `precheck_on_write.py:47-50`、`:19-23` |
| 3 | **失败一律放行**——任何异常 / 依赖缺失 / 解释器不可用 → 静默 `exit 0`，绝不误拦 | 各脚本 `except → return 0` 早退 |
| 4 | **依赖探测链，不写死路径**——PHP 按 `PHP_BIN` → 多版本环境变量 → 三平台候选目录 × 版本降序解析；Java 走 `javac` 且只认白名单语法错 | `lint_on_write.py:20-39`、`:6-9` |
| 5 | **防杀软自伤**——危险函数名 / 敏感词一律字符串拼接构造，并防「钩子被再次写入时自己拦自己」 | `precheck_on_write.py:31-32`、`secret_scan.py:13-15` |
| 6 | **一套配置跨 IDE**——matcher 工具名并集（`write_to_file\|replace_in_file\|Write\|Edit`）；五路证据探测在用工具；幂等只追加不删除；对「技能安装目录 / 模板自身」两重拒写 | `scripts/hooks.json:2`、`scripts/init_deploy.py` |

### 能力矩阵

| 维度 | 覆盖规模 | 钩子 |
| - | - | - |
| 写前阻断 | 4 类内容级检查（PHP 语法 / 调试残留 / 安全组合 / 语言规范），命中 `exit 2` 拒写并回传理由 | `precheck_on_write` |
| 回滚网 | 改写前自动 `.bak`，保留最近 10 版（`.bak` + `.bak.1`…`.bak.9`）；内容一致跳过、新文件不备份、8 类目录豁免、25 种扩展名生效（22 类扩展名 + 3 个点文件名） | `backup_on_write` |
| 边界守卫 | 4 个受保护目录（`uploads` / `backup` / `vendor` / `node_modules`）拒写；核心目录改动前要求存在进行中的 `*_plan.md`（默认 7 核心目录 / 15 排除目录 / 9 扩展名，可 env 覆盖） | `guard_dirs`、`plan_guard` |
| 语法自检 | 3 语言：PHP `php -l` / Java `javac`（白名单过滤）/ Python `compile()`（零产物） | `lint_on_write` |
| 兼容扫描 | PHP 8.x 3 类（短标签 / 裸数组键 / `each`·`create_function`·`get_magic_quotes_gpc`，跳过全大写常量）；Java 10 个版本特性按目标版本判定，探测不到即静默 | `php8_compat`、`java_compat` |
| 安全扫描 | PHP 5 规则 + Java 6 规则（原生反序列化 / 命令执行 / SQL 拼接 / XXE / 弱哈希加密 / 堆栈外泄） | `security_scan` |
| 数据外发拦截 | 写前检测「外发调用 **且** 敏感来源」组合，覆盖 PHP / Python / JS·TS / Java / Go / Shell | `egress_scan` |
| SQL 注入 | 7 风险模式 × 13 种扩展名 × 5 语言；含 MySQL 高危关键字（`LOAD DATA` / `INTO OUTFILE` / `GRANT`）；4 类安全模式跳过 | `sql_injection_check` |
| CMS / 框架 | 37 条规则 = 18 条 CMS/框架 SQL 注入 + 7 条框架特有 + 12 条通用风险，覆盖 17 个生态（帝国 / 织梦 / Discuz / WordPress / PHPCMS / Drupal / Joomla / ThinkPHP / CI / Laravel / Yii / Symfony / Typecho / ZBlog / Emlog / PDO / mysqli） | `cms_risk_check` |
| 脱敏 | 硬编码明文凭证（12 类凭证名变体）+ 日志 / 文件写入含敏感变量 | `secret_scan` |
| 调试残留 | 4 语言族（PHP `var_dump`·`print_r`·`die`；JS·TS `console.log`；Java·Kotlin `System.out.print*`·`printStackTrace`；Laravel·Symfony `dd`·`dump`），17 种扩展名，跳过 `tests/` | `debug_residue` |
| 依赖漏洞 | 7 生态（npm / yarn / pnpm · pip · composer · Go · Maven / Gradle · Ruby）依赖文件变更即提示对应 `audit` 命令 | `dep_scan` |
| 学习闭环 | 双册召回（反册 `[ERR-RECALL]` / 正册 `[SUC-RECALL]`，每册预算 3）；反册按复发（RC≥3 + Tasks≥2 + 30 天）、正册按复用（hit_count≥3）给升格建议；非阻塞、不自动写文件（升格裁定归 Agent 自评） | `capture_learning`、`errors_recall_guard`（双册）、`errors_dup_guard`；`recurrence_promote`（手动 CLI，不接自动提醒） |
| 图谱兜底 | 写代码后附上游 2 跳依赖摘要（≤5 文件 / 15s 超时）；三件套齐全才查、`--no-rebuild` 绝不重建、无上游则静默 | `graph_impact` |
| 上下文与卫生 | 压缩前落检查点快照；超期日迹归档（只移不删）；技能文档改动后自动跑步骤号一致性校验；`select_star`、`utf8_check` | `handoff_snapshot`、`memory_prune`、`step_ref_guard` |

### 三个 hooks 文件的关系（源 / 增量草案 / 安装产物）

三者都在 **`scripts/`**（与唯一消费者 `scripts/init_deploy.py` 同目录）；`hooks/` 只放被注册的运行时钩子脚本。

| 文件 | 类别 | 作用 |
| -------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------ |
| `hooks.json` | 主模板（源，手写） | 28 个守卫钩子完整定义；占位符 `{{PYTHON_BIN}}` / `{{HOOKS_DIR}}` 由运行时或部署器替换；**不含** `UserPromptSubmit` 段 |
| `hooks.capture-draft.json` | 增量草案（源，可选） | 同一条 `capture_learning.py` + 额外一条 `UserPromptSubmit`（`--mode correction`，抓你的纠错句式）。因非所有 IDE 支持该事件名，**单列 opt-in** |
| `hooks.installed.json` | 安装产物（自动生成，勿手改） | 占位符已替换为真实路径的可加载配置；每次 `--apply` 重写；`.gitignore` 已排除 |

### 一键初始化部署

**前置：Python ≥3.8**（本步骤与 hooks、图谱、步骤号校验的唯一运行时依赖）：

- Agent 先**实际执行**探测 `py -3` → `python` → `python3`（用 `-c "import sys;print(sys.executable)"`，以识别 Windows Store 假别名），命中即作为 `PYTHON_BIN`。
- 未检测到 → **先告知、经你同意后自动安装**（不静默）：Windows `winget install -e --id Python.Python.3.12 --scope user` / macOS `brew install python@3.12` / Debian·Ubuntu `sudo apt-get install -y python3` / RHEL·Fedora `sudo dnf install -y python3` / Alpine `sudo apk add python3`；装完自动复检。
- 安装失败或你不装 → 跳过 hooks 部署与图谱，**技能核心不受影响**（对应检查回退正文手动执行）。

```bash
python scripts/init_deploy.py                          # 第一步：只探测出计划（默认 dry-run，不写文件）
python scripts/init_deploy.py --apply                  # 第二步：落地（写前 .bak；只追加不删除；同名冲突默认跳过）
python scripts/init_deploy.py --scope both --apply     # 作用域 project（默认）/ user（⚠️ 影响所有项目）/ both
python scripts/init_deploy.py --tools codebuddy,trae --apply
python scripts/init_deploy.py --root D:/proj --apply --copy-to-project
python scripts/init_deploy.py --root D:/proj --apply --copy-to-project --copy-rel .myide/hooks
python scripts/init_deploy.py --json                   # 机器可读
```

**探测依据（五路证据任一命中即视为"在用"）**：`exe`（常见安装位置可执行文件）｜`cmd`（PATH 命令名）｜`data`（应用数据目录）｜`user_cfg`（用户级配置落点存在）｜`proj_cfg`（项目级配置落点存在）。内置工具：CodeBuddy CN、Trae（Trae CN）、Cursor、Claude Code、Windsurf；跨平台、不写死任何机器路径（全部经 `%VAR%` / `~` 展开）；工具未探测到 → 不写。

**它会做什么**：① 探测在用工具 + 配置落点 + 按 `hooks.json` 引用逐个校验 `*.py`（缺项直接报错且不写盘）；② 按 `--scope` 生成「工具 × 作用域」落点清单并幂等合并写入（单目标失败不影响其他）；③ 逐目标回读校验 JSON 合法 + 每个 command 指向的脚本存在。

**安全保证**：默认 dry-run；`--apply` 才写；写前 `.bak`；只追加不删除；同名冲突默认跳过（`--allow-overwrite` 才替换）；`--scope user|both` 会提示「影响该用户所有项目」；项目根疑似技能安装目录、或目标配置与技能模板同文件时自动拒绝写入。未探测到任何工具时仍生成 `hooks.installed.json`，按方式 B 手动接入即可。

**启用方式（任选其一）**：

- **方式 A（占位符替换，适用于支持变量替换的 IDE）**：把 `hooks.json` 接入运行时，设环境变量 `PYTHON_BIN`（解释器路径）与 `HOOKS_DIR`（hook 脚本目录，可指技能自带 `hooks/` 或你项目 `.codebuddy/hooks/`），加载时替换占位符。
- **方式 B（安装器预处理，推荐跨平台）**：`python hooks/install_hooks.py`（可加 `--python-bin` / `--hooks-dir`，或设同名环境变量）生成 `hooks.installed.json`，直接接入；`--in-place` 原地覆盖（自动备份 `.bak`）。换机 / 换项目重跑即可。

> 平台落点声明集中在 `scripts/platforms.json`（探测器唯一数据源，缺失或非法时**拒绝启动**，退出码 2，不静默降级为空表）：记录各工具的探测路径 / hooks 配置落点 / skill 加载目录与命名约定 / 平台注册表，逐字段标可信度（`measured` / `documented` / `candidate` / `unknown`）。**它仅作声明，不自动安装 skill、不写任何平台注册表**。可用 `--platforms <路径>` 指定外部声明。

> hooks 是护栏不是验证替代：动态 / 业务正确性（真实运行、端到端）仍须 Agent 显式产出证据；被拦即视为该防线未过，禁止绕过；运行时无 hooks 集成时回退正文手动执行。故障排查见 `FAQ.md` 十五。

### 适配平台（多 IDE）

这是**匹配层**能力，不等于开箱即用：须先按自身运行时完成接入与环境适配，之后只要工具名落在下表某个家族里即被自动匹配。工具名不同时在 matcher 用 `|` 追加一行即可，无需改脚本。

| 平台 | 工具名家族 | matcher | 落点 / 说明 |
| ----------------------- | ---------------------------------------------- | --------- | ---------------------------------------------------------------------- |
| **CodeBuddy CN** | `write_to_file` / `replace_in_file` | ✅ 已覆盖 | `~/.codebuddy/settings.json` 或 `~/.codebuddycn/settings.json`（实测均含 hooks 键） |
| **Trae / Trae CN** | `Write` / `Edit` | ✅ 已覆盖 | 实测 `~/.trae-cn/hooks.json`；`~/.trae/hooks.json` 作候选 |
| **Cursor** | `Write` / `Edit` | ✅ 已覆盖 | 代码 / 历史已确认 |
| **Qoder CN** | `write_to_file` / `replace_in_file` | ✅ 已覆盖 | 实测 `~/.qoder-cn/settings.json`；官方文档 `~/.lingma/settings.json` 作候选 |
| **WorkBuddy** | `write_to_file` / `replace_in_file` | ✅ 已覆盖 | 实测 `~/.workbuddy/settings.json`（含 hooks 键） |
| **Claude Code** | `Write` / `Edit` / `Bash` / `UserPromptSubmit` | ✅ 已覆盖 | 事件最全；`UserPromptSubmit` 可选 |
| **Codex / Gemini CLI / OpenClaw** | `Bash` / 命令类 | ✅ 已覆盖 | 命令类家族 |
| **Cline / Roo Code** | `write_to_file` / `replace_in_file` | ⚠️ 仅工具名同族 | 寄生 VS Code；实测无文件式 hooks 落点（配置在扩展 `globalState.json`），需手工接入或不适用 |
| **Windsurf** | `write_file` / `edit_file` | ⚠️ 需追加 | 在 matcher 补 `write_file \| edit_file` |
| **Zed / Continue** | 视配置 / 扩展 | ⚠️ 待确认 | 确认工具名后追加 |
| **Aider** | CLI 自有机制 | ❌ 不适用 | 走自带 hook / 包装层，不在 matcher 范围 |

**追加未列出的平台**：编辑 `hooks.json` 每个 matcher 字符串，用 `|` 并入新工具名（例如加上 `MultiEdit`、`save_file`）。**额外名称不匹配时无害**，可放心并集；改完重跑安装器即可。

**事件键裁剪**：若运行时因未知事件名导致整份配置加载失败，用 `python scripts/init_deploy.py --events PreToolUse,PostToolUse --apply` 只保留受支持事件；**默认全量不裁剪**（本技能模板只注册 `PreToolUse` / `PostToolUse` / `PreCompact`；其余平台事件清单未逐一查证）。

> ⚠️ **长任务 / 捕获 hook 要"自动执行 + 自动测试"须开放运行时权限**：`capture_learning.py` 与长任务闭环要自主跑通「执行命令 → 跑测试（`php -l` / `phpunit` / `node --check`）→ 落记录」，依赖运行时授予 `Bash` / `execute_command` 的**免确认执行权限**。两层开放：① 技能侧 `SKILL.md` 的 `allowed-tools` 已声明；② 运行侧须允许这些工具 auto-approve。未开放时须退化为「每步请求确认」模式，不得假设可无人值守自动执行。

## 协同技能

19 个子技能通过各自文末的 `## 关联 reference` 章节相互引用（专项 reference 的协同由 `references/routing.md`「专项 reference 映射」收口）。常见链路的形状（非穷举，**完整 20 条以 `references/routing.md`「协同顺序规则」为唯一真源**）：

- 交付型：Spec驱动开发 → 任务拆解与执行 → 代码生成 → 代码审查 → 测试用例生成 → 文档生成 → 项目记忆管理
- 治理型：Bug诊断 / 重构建议 → 代码审查 → 项目记忆管理
- 专项型：CMS二次开发 / MySQL / Laravel / Java / 性能基准测试 → 按需协同代码生成、代码审查、测试用例生成
- 本技能包为独立套件，暂无可联动的其他职业技能包；需外部数据或服务时用主 Agent 可用的检索工具。

## 文件结构

- `SKILL.md` - 技能运行时指令（**薄入口**：七步骨架 Step 0–6 + 门禁索引 + 强制加载表；细则在 `references/`，按步强制加载）
- `README.md` - 本文件，用户入口文档
- `FAQ.md` - 常见问题、执行禁区、验证失败与边界外请求答疑
- `hooks/` - 钩子脚本目录（高级功能，须按自身 IDE 适配）：28 个守卫钩子（备份/lint/计划质量守卫/命令卫生/测量口径提示/PHP8 与 Java 版本兼容/安全/数据外发拦截/脱敏/UTF-8/调试残留/`SELECT *`/依赖扫描/SQL注入/CMS风险/学习捕获/压缩快照/规划拦截/受保护目录拦截/写入前综合检查/踩坑召回（含命中自动记账）/踩坑查重/图谱影响面/日迹归档/步骤号引用一致性/**反样本册写侧硬拦**/**正样本册写侧硬拦**）+ `install_hooks.py` 安装器 + `ledger_common.py` 共享判据模块（记忆根/编号/索引解析/触发词/日期/引用验真/值域解析——值域真源＝`references/error-ledger.md` 表格，技能树内直接解析、部署态经 `ERR_CATEGORY_RULES` 覆写或降级留痕，**禁另放部署件**）+ `step_ref_check.py`（**钩子运行时依赖**：`step_ref_guard` 按同目录路径调用它做步骤号核对，故必须常驻 hooks/；亦可手动跑）。**hooks/ 只放运行时钩子脚本及其依赖**（手动工具一律在 scripts/）
- `scripts/ledger_judge.py` - 治理判据**单一实现**（升格/归档/退役/反哺/计划状态阈值与候选判据＋四类处置出口识别）：原语全走 `hooks/ledger_common.py`，被 `recurrence_promote.py` 与 `metrics_report.py` 共用（禁在消费方另写判据——ERR-226 族）
- `scripts/metrics_report.py` - 结果指标只读聚合（手动跑）：M1 计划收敛率 / M2 ERR 复发率 / M3·M5 字段完整率 / M4 消费覆盖率 / M6 兜底类占比 / M7 最大桶占比 / M9 归档可迁 / M9-SUC 退役候选 / M10 跨册反哺 / R1·R1-SUC 升格候选；每项同报分母样本，候选型指标全带处置出口（消音计数可见）；**仅用于定位瓶颈，禁用于个人绩效**；裁定归 Agent 自评
- `scripts/err_slim_eval.py` - 索引摘要截断定档评估（手动跑）：跑 `err_index_gen.py --summary-limit` 多档对比「压缩率 vs 召回损失」（观测词默认从基线关键词列自动派生），定档前必跑、结论由人下
- `scripts/recurrence_promote.py` - 升格建议扫描（手动 CLI，非钩子）：反册按复发（RC≥3 + Tasks≥2 + 30 天窗口）、正册按复用（hit_count≥3 + Tasks≥2）输出升格**建议**；只手动执行、**禁**接自动提醒通道（自动提醒型升格属已淘汰形态，噪音成本高于收益）；裁定归 Agent 自评＋处置出口
- `scripts/err_next_id.py` / `err_index_gen.py` / `success_index_gen.py` / `err_id_dup_check.py` / `err_fields_check.py` / `success_fields_check.py` - 正反手册机械化工具（手动跑）：双册取号（索引∪磁盘）、双册索引生成（3 列＋活跃/归档区）、编号唯一与内容判重、双册存量字段校验（退出码同 verdict）；判据均经 `hooks/ledger_common.py` 单源
- `scripts/init_deploy.py` - 初始化部署器（工具，非钩子；默认 dry-run）
- `scripts/domain_evolve.py` / `scripts/domain_keywords.json` - 领域自进化（手动 CLI）：`--detect` 判定未覆盖领域（DOMAIN-GAP）→ `--scaffold` 生成 v0.1 草稿 → `--validate` 校验判据数与证据锚 → `--register --apply` 四件套注册（默认 dry-run，写前 `.bak`）→ `--check` 孤儿/悬空/计数一致性 → `--selftest` 端到端自测
- `scripts/build_graph.py` - 知识图谱构建/查询（纯正则、零 LLM token）：`--root` 全量 / `--query <file|symbol> [--direction up|down|both] [--depth N]` / `--rebuild` / `--selftest`；产物 `{PROJECT_ROOT}/.ai-memory/knowledge-graph/{graph,meta,symbols}.json`
- `scripts/hooks.json` - hooks 主模板（源，手写维护）
- `scripts/hooks.installed.json` - hooks 安装产物（自动生成，勿手改；首次部署前不存在，不入版本库与发布包）
- `scripts/platforms.json` - 平台落点声明（单一事实源；缺失即 fail-closed）
- `scripts/hooks.capture-draft.json` - 捕获 hook 增量草案（可选 opt-in）
- `references/` - **共 46 个 md**：19 个子技能详细模板 + 25 个专项 reference + 1 个路由层 reference（`routing.md`）+ 1 个推理与工具行为协议（`agent-reasoning-patterns.md`）（不计入子技能，其中 11 个为工程纪律层专项）
- `references/task-decomposition-and-execution.md` - 任务拆解与执行（五要素结构 / Wave 链式执行 / Task Summary / checkpoint / 证据归档 / 子 Agent 委派纪律 / 无断点执行协议 / 大项目分级 P0-P1-P2 与 Wave 划分 / TDD 前置判定 / 子代数据三标签与抽验作废制）
- `references/routing.md` - 路由层：子技能索引 / 领域路由表 / 优先级矩阵 / 互斥 / 协同顺序（20 条）/ 专项映射 / 意图三分法 / Wayfinder / 加载经济与执行集（**档位 → 最小执行集**单一定义源 / 单轮 ≤3 上限 / **兜底路由**）
- `references/agent-reasoning-patterns.md` - 推理与工具行为协议（按需加载）：16 条模式 + 思维链五段式骨架 + Method 四步硬序 + 推理侧重校准 + 思维链强度分档（档位名：轻量 / 常规 / 复杂 / 大项目，判据见 `routing.md`）+ 高阶思维模式（含防套路化 / 链内纠偏留痕 / 二阶效应枚举 / 失败模式分档 / 歧义清单 / 未知清单）+ 验证自检（元验证，9 条）
- `references/delivery-assurance.md` - 交付保障：执行率自检（27 条，含覆盖完整性收口 / 真人功能验证 / 迁移完整性 / 防作弊 / 信心门控 / 推理外化 / 报告口径 / 产物与探针卫生 / 完成权双状态 / 任务分类 / 状态四态）/ 信心门控 / 抗合理化 / 收尾报告（5 字段模板＋量化强制）/ 任务分类（主线/支线/元任务）/ 状态四态 / 未验证项披露 / 确认超时 / Graceful Abort
- `references/execution-safety.md` - 执行安全：规划门禁（三池 10+13＋规划自审＋方案成形自检）/ 审计修复分离 / 阶段3出口 GATE-CHECK / 失败计数与升级（失败签名口径 / 归因先行 / 换框三轴）/ 解题方法论（14 类打法）/ 外部检索六律 / 批量修改 7 防线（脚本落点判据）/ 质量与安全清单（技术债禁令 / 性能禁则 / 注释极简）/ 防 AI 通病五戒 / 架构一致性铁律（含 DDL 自愈表登记）/ 覆盖完整性枚举 / 配对契约核验 / 移除停用存在性锁 / 审查三问 / 回归基线 / 回滚决策 / 真人功能验证硬约束 / 门禁资产只读 / 保护型守卫作用范围 / 动作决策轴 / 边界判定正反例
- `references/mysql-database.md` - MySQL 专项（含「SQL 动态构建验证铁律」）
- `references/error-ledger.md` - 正反手册（反样本册 errors/ ＋ 正样本册 success/：索引与单条模板、形态正反对照、确定性检索、新坑即录（成果门槛一票否决）、命中即复核、归档评审、升格裁定（Agent 自评 + 处置出口）、跨册反哺）
- `references/style-alignment.md` - 风格对齐（二开前强制取样原项目、产出风格基线逐行对齐）
- `references/architecture-decision.md` - 架构决策（候选 + trade-off + 反选论证 + 撤销条件）
- `references/cms-development.md` - CMS 二次开发专项
- `references/frontend-design.md` - 前端设计专项
- `references/design-audit.md` - UI 改造场景审计专项
- `references/design-critique.md` - 设计评审与认知负荷专项
- `references/api-design.md` - API 设计专项
- `references/software-project.md` - 软件项目总控专项
- `references/website-project.md` - 网站项目总控专项
- `references/spec-driven-development.md` - Spec 驱动开发专项
- `references/code-generation.md` / `code-review.md` / `refactoring.md` / `test-generation.md` / `bug-diagnosis.md` / `doc-generation.md` / `tech-selection.md` / `performance-benchmark.md` / `karpathy-coding-guidelines.md` / `project-memory-management.md` / `project-knowledge-graph.md` - 各子技能主模板
- `references/laravel-development.md` / `laravel-testing.md` / `java-development.md` / `java-testing.md` / `javascript-development.md` - 框架专项（不计入子技能）
- `references/domain-driven-design.md` / `distributed-systems.md` - 领域建模与分布式专项
- `references/root-cause-debugging.md` / `dev-navigation.md` / `incident-review.md` / `threat-modeling.md` / `production-readiness.md` / `ai-coding-governance.md` / `code-readability-for-agents.md` / `llm-application-security.md` / `technical-strategy.md` / `tech-influence.md` / `engineering-metrics.md` - 工程纪律层专项
## 维护

- **体量**：按需 reference 不设行数 / 字符硬上限（按需加载、单次 ≤3、分节取用）；400 行仅为提示性参考，不作拆分或判缺陷的触发条件。`SKILL.md` ≤8000 字符（平台硬线，超出即静默截断）。
- **自检命令**：`python hooks/step_ref_check.py`（步骤号引用一致性，退出码 0=匹配 / 1=发现不匹配 / 3=校验器自身错误）；`python scripts/init_deploy.py`（脚本完整性，dry-run）。
- **质量自评基线（9 维，本包自定判据）**：当前 93/100；扣分项＝部分 reference 未声明异常路径、`allowed-tools` 字段有效性待对照规范、`version` / `author` 未收进 `metadata`。分数仅用于本包纵向对比（单变量迭代：涨分保留、平/跌回滚），不可与其他项目横向比较。

## 附录 A：知识图谱 token 消耗对比

估算量级（非精确计费）；基准：332 文件 / ~5 万行 CMS 项目，图含 2890 有效依赖边，节点硬上限 `MAX_NODES=80`。

| 维度 | 常规 LLM 理解（无图谱） | 知识图谱方式 |
| --------------- | -------------------------------------------------- | ---------------------------------------------- |
| 构建 / 索引成本 | 无（每次现读源码） | 0 token（纯正则本地抽取，不进 LLM 上下文） |
| 单次依赖查询 | 6k–60k token（把 5–50 个源文件喂进上下文） | 1k–3k token（返回子图 JSON，≤80 节点） |
| 10 次任务累积 | 60k–600k token | 10k–30k token |
| 跨会话复用 | 每次重读，不留存 | 图谱缓存复用，query 恒定 ~2k |
| 上下文污染 | 大（源码占满窗口） | 小（仅依赖拓扑，不含实现细节） |

**为何能省**：把「代码 → 依赖」的抽取放在 LLM 之外（纯正则静态抽取，LSP 仅探测可用性、不参与抽取），LLM 只消费精简后的依赖拓扑 JSON。构建阶段 token≈0、查询阶段不重读源码；单次节省约 70%–95%，跨会话累积更显著。详见 `references/project-knowledge-graph.md`。
## 授权协议与义务（GPL-3.0-or-later）

本技能整体以 **GNU GPL v3 或更高版本**（SPDX: `GPL-3.0-or-later`）授权，版权归 **智慧&半岛-www.52yuer.cn** 所有。完整许可证文本：<https://www.gnu.org/licenses/gpl-3.0.txt>（本包未附全文，正式分发时宜附带）。

**复制 / 分发 / 修改本技能（SKILL.md / references / hooks / scripts 全部内容）时的义务**：

| # | 义务 | 依据 |
|---|---|---|
| 1 | **保留版权与署名**——不得删除或改写 `SKILL.md` frontmatter 的 `author` 行、版权声明及本节；改动过的文件须带显著声明说明已修改与日期 | GPL §5 |
| 2 | **同许可传染**——再分发本技能或其修改版，整体须以 GPL-3.0-or-later 授权，**禁附加额外限制**（收费 / 禁商用等均属额外限制） | GPL §7/§10 |
| 3 | **提供对应源码**——以打包 / 目标形式分发时，须同批提供完整对应源码或书面获取途径 | GPL §6 |
| 4 | **保留许可文本指引**——本节与许可证 URL 须随包保留 | GPL §5/§6 |
| 5 | **无担保**——本技能不提供任何担保 | GPL §15/§16 |

> ⚠️ 义务声明无法技术强制——它的作用是把义务**随包传播**（抄走全包即抄走义务）并构成授权依据。**删除版权 / 署名 = 违反 GPL §5 = 失去授权**，此后的分发构成侵权。本节为工程合规摘要，**非法律意见**。
