# Subagent 分级派发协议（大项目适用）

> 项目页面 > ~30 / 多分包 / 源码展开后单文件巨大时按本协议执行（三类 subagent 全派）；小项目（页面 ≤ ~30 且无多分包）跳过本文件，主 agent 直接 `read` / `grep`。`SKILL.md` 阶段 1 分流表与阶段 3.2 是本协议的入口摘要。

## 一、能力索引（先定位再读，只产坐标）

先产"能力索引"再开始读源码，避免把全项目源码拉进上下文：

- **数据源仅限**：`app.json`（pages/subPackages）+ 目标页面 `.json` 标题 + `.wxml` 按钮/输入框文案与 `bind*` 名 + 页面 `.js` 的**函数名与行号**（用 `grep` 取行号，**不读函数体**）
- **分包级裁剪**：能力清单已知时，先用 `app.json` + `.wxml` 文案把每个能力锁定到 1~2 个分包/页面，其余分包不进视野
- **优先 `grep`**（按能力关键词 / 文案 / handler 名搜命中行号），而非 `read` 整文件
- 索引存上下文或落盘均可（含：能力名 / 分包 / 页面 path / handler 名 + 行号 / uiHints）；已存在时直接用，不重产
- 后续所有读取**凭坐标直达**（按行号 offset/limit 读那一段），不从 `app.json` 重新满项目找入口

## 二、分流：小项目直读 / 大项目全派


| 规模 | 策略 |
|---|---|
| 小项目 | 不经过本协议，主 agent 全程直读（1.2 鉴权 + 阶段 3 接口提取） |
| 大项目 | 三类 subagent 全派：① 鉴权分析（§3.1）→ ② 每能力 api 分析（§3.2）→ ③ probe（§3.3，3.7 命中时） |

> ② 只探测业务层逻辑：含签名 / 多级登录是 ① 的探测对象（§3.1），鉴权已由 ① 落盘 `analysis-auth.md`，② 只引用结论、**不重复探测鉴权链路**。

## 三、三类 subagent（同等重要，按序执行）

简化后共三类 subagent，各自独立派生、职责互不重叠、**同等重要**，按先后关系执行：

| # | subagent | 数量 | 时机 | 依赖 |
|---|---------|------|------|------|
| ① | 探测通用鉴权 / utils | 1 个 | 最先 | 能力索引（§一） |
| ② | 探测业务 api | 每能力 1 个，可并行 | ① 之后 | 能力索引 + ① 的产物 |
| ③ | 设置计划并执行 probe | 整批 1 个 | 最后（3.7 命中触发条件时） | ① ② 的产物 |

> **顺序是硬约束**：① 鉴权分析未完成前 ② 不得启动（② 引用 ① 的 `analysis-auth.md`）；①② 未完成前 ③ 不得启动（③ 引用 `analysis-apis.md` 的请求构造 + `analysis-auth.md` 拼 preSteps）。

### 3.1 探测通用鉴权 / utils（1 个，最先）

subagent 深读 `app.js` / request 封装 / 登录文件 / 签名模块 / 通用 utils（多级登录 / 签名 / 指纹模块全在此层探测），按 `references/AUTH_MIGRATION.md` §2/§3 填写 `analysis-auth.md`（鉴权事实结构化 + 逐字代码片段），回传结论摘要。

已记录进 `analysis-auth.md` 的鉴权封装，其他 subagent 不再重复深追。

### 3.2 探测业务 api（1 个，可根据需要并行）

深读该能力的**业务层逻辑**（入参来源 / 返回结构 / 跳转链），把接口语义回填 `analysis-apis.md` 对应接口节：

- 从 §一 索引的入口坐标起步，读真实事件 handler → 实际调用处 → 请求构造；接口由真实入口唯一确定，禁止凭接口名"语义相近"挑选
- 每个入参追到真实赋值来源（页面 data ← onLoad/onShow/事件回调 ← JSAPI/storage/globalData/用户输入）；来源未追清时不用 `|| 0` / `|| ''` 兜底；正常路径 + 失败/缺省分支与主包一致
- 鉴权只引用 `analysis-auth.md`（requiresLogin / signing / dynamicValues / 通用参数 inherit），不重新定义鉴权事实，避免漂移

### 3.3 设置计划并执行 probe（1 个）

阶段 3.7 命中触发条件（请求值运行时动态下发 / 响应结构无法从源码消费点确定，见 `RUNTIME_PROBE.md`）时派 subagent 完成「写 plan → 跑 probe → 回填」整段闭环，主 agent 不亲自跑（probe 日志与多轮重试会挤占主上下文）。

**指令**：输入 `analysis-apis.md`（请求构造与入口坐标）+ `analysis-auth.md`（拼 `preSteps` 时引用）。按 `references/RUNTIME_PROBE.md` 的 plan 格式落盘 `<源项目>/.ai-mode-skills/probe/plan.json`，随后执行：

```bash
node scripts/probe.mjs --project <源项目> --plan <plan.json>
```

并把成功 run 的真实响应回填 `analysis-apis.md` 对应接口的响应节：

- plan 条目的 `target_page` / `matchUrlIncludes` / `trigger` 必须与 `analysis-apis.md` 记录的**同一真实入口**对齐，不得为「更好触发」换页或换接口
- `trigger`：UI 触发用 `tap` / `input` / `callMethod`；进页自动发则留空；非 UI 或 hook 捕不到时用 `request` / `evaluate`
- 同 URL 多 api（不同 tab / stype / 模式标志）时，`trigger` 必须可区分，禁止复制粘贴同一条
- 敏感接口（不可逆副作用）一律不进 plan（`probe-lib.mjs` 内置拦截）

**读取边界**：

- ✅ 允许：`analysis-apis.md`、`analysis-auth.md`、能力索引（补页面路径）
- ✅ selector 缺失时：仅对 `target_page` 对应 `.wxml` **grep** class/id/`bind*`（不读 `.js` 函数体）
- ❌ 禁止：为改 plan 重读业务 `.js` 做接口分析（那是 ② 的事）；手写 probe run 文件

回传主 agent：「plan 已落盘 + probe 结果摘要（成功 N / 失败 M / 跳过原因）+ 已回填的 api 列表」，≤20 行，**不回传源码**。probe 结果 `url_unmatched` 需改 plan 时仍派本 subagent 重产（可附最新 `probe/<run-id>.json` 作为输入）。

## 四、读取预算与回传纪律（三类通用）

- **凭索引坐标直达**：从 §一 索引给的坐标文件起步，`read` 那个 handler 那一段（行号 offset/limit），不得从 `app.json` 重新满项目找入口
- **只读 1 跳依赖**：只允许打开「坐标文件 + 它直接 `import`/`require` 的那 1 层依赖」；不得跨分包递归追第 2、3 跳；鉴权公共封装走 `analysis-auth.md` 结论
- **单 subagent 读取硬上限**：累计打开文件 ≤ ~5 个（或字节超阈值即停）；逼近上限仍未定位 → 停下回传 `{status:"need_confirm", reason, 已读文件列表}`，交主 agent 决策
- **回传纯结论**：产物落盘 + ≤20 行事实摘要，**零源码原文**
