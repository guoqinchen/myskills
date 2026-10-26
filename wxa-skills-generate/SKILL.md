---
name: wxa-skills-generate
description: 分析小程序项目源代码（含压缩/混淆），识别核心业务步骤，提取网络接口与 JSAPI 调用，生成符合 wx.modelContext 规范的技能分包（含原子接口 + 原子组件），并完成 app.json / project.config.json 配置集成。在以下场景触发：把小程序页面能力改造为小程序 AI 原子接口、生成 skills/ 分包代码、从源项目派生 MCP 工具、小程序 AI 的开发模式代码生成。仅负责静态生成，生成完成后必须交棒 wxa-skills-validate 做校验。
metadata:
  author: Tencent
  version: '0.3.0'
---

# wxa-skill-generate

从小程序源码生成符合 `wx.modelContext` 规范的技能分包（skills/）：**分析源码 → 识别业务 → 提取接口与 JSAPI → 设计原子接口 → 生成代码 → 集成配置 → 交棒校验**。

## 职责边界

- ✅ 本 skill 做：源码分析、原子接口设计、按需使用 automator 获取真实响应、代码生成、`app.json` / `project.config.json` 集成
  - 生成过程内的自检：字段来源自检（§5.8）、`AUTH_MIGRATION.md §6` 鉴权自检、硬性约束 C 代码一致性自检
- ❌ 本 skill 不做：对生成产物的独立校验（静态规则校验 V001~V021、真机 execute 跑通、组件渲染核对）——全部由 `wxa-skills-validate` 负责。生成阶段的自检是本 skill 的组成部分，不因"校验交给 validate"而跳过
- 📦 交付：`skills/{skill-name}/`（含 `mcp.json`、`SKILL.md`、`index.js`、原子接口实现文件、工具模块；组件目录仅生成组件时才有，见 D.3）+ 配置文件更新 + `.ai-mode-skills/` 分析产物两份

## 分析产物（`<源项目>/.ai-mode-skills/`）

分析结果落盘两份，按读取频率拆分，避免单文件全量读入：

| 文件 | 产出时机 | 内容 | 用法 |
|------|---------|------|------|
| `analysis-auth.md` | 阶段 1.2 | 鉴权事实 + 逐字代码片段 | 写一次、读多次；阶段 3 / 5.6 引用 |
| `analysis-apis.md` | 阶段 3 | 逐接口规格 + probe 结果摘要 | 逐接口追加；阶段 4 / 5 引用 |

`probe/plan.json`（probe.mjs 的输入）与 `probe/<run-id>.json`（脚本写盘）由subagent脚本管理，不属于分析产物。

## 依赖

- **可读的源码目录**（仅给 appid / URL / 截图 → 触发阻断）
- **开发者工具**：微信开发者工具 + `scripts/probe.mjs`（`miniprogram-automator` 装 skill 的 `scripts/`，不装源项目）。只在阶段 3.7 的两种触发条件命中时才用，见 3.7 与 `references/RUNTIME_PROBE.md`

## 术语约定

- **原子接口**：对外暴露给小程序 AI 的可调用能力。约定路径 `skills/{skill}/apis/{name}.js`（validator 也兼容 `tools/services/` / `tools/`）
- **原子组件**：用于渲染原子接口返回数据的 GUI 卡片（是否生成、`componentPath` 规则见 D.3）。
- **压缩代码**：单行超 500 字符、变量名单字符的产物（含混淆）
- **probe**：本 skill 阶段 3.7 的运行时探测。用 automator（`miniprogram-automator` npm 包）连接开发者工具 WS 端口（9420），在**源项目**上触发请求、捕获真实响应，产物落盘 `.ai-mode-skills/probe/`。

## 参考资料索引

| 文件 | 用途 | 加载时机 | 不加载条件 |
|------|------|---------|------------|
| `references/ANALYSIS_PATTERNS.md` | 业务流程识别、接口/JSAPI 搜索模式 | 阶段 2 / 3 扫描源码时 | 用户已明确全部能力且无需再扫页面结构时 |
| `references/JSAPI_WHITELIST.md` | wx API 白名单完整清单（接口侧 / 组件侧 / 不可迁移）；D 节只列高频项 | 阶段 1 / 3 / 5（D 节未覆盖目标 API 时必查） | 无（建议每次对照，不要凭印象） |
| `references/CODE_TEMPLATES.md` | 代码与配置模板（`index.js` / utils / apis / `mcp.json` / skill `SKILL.md` / `app.json`） | 阶段 5 / 6 | 纯改已有单行逻辑、不涉及模板结构时 |
| `references/COMPONENT_TEMPLATES.md` | 原子组件模板 | 阶段 5（生成组件时） | 不生成组件（默认，见 D.3） |
| `references/ATOMIC_COMPONENT_DESIGN.md` | 组件设计规范（尺寸 / 主题 / 边距 / 字体 / 布局） | 同上（强制前置，优先级最高） | 同上 |
| `references/ATOMIC_COMPONENT_CSS.md` | 组件 WXSS 实现规范 | 同上（写样式时） | 同上 |
| `references/STYLE_MIGRATION.md` | 源样式提取 + 字段映射工作流 | 同上（写 WXML/WXSS 前强制前置） | 同上 |
| `references/HALF_SCREEN.md` | 半屏页 API 与禁用清单 | 按需（源业务确有详情/补充信息语义） | 默认不生成半屏时 |
| `references/RUNTIME_PROBE.md` | probe 触发场景、plan/result 格式、执行命令 | 阶段 3.7 命中触发条件时 | 分析源码之后决定不跑 probe 时 |
| `references/AUTH_MIGRATION.md` | analysis-auth.md 填写指引、鉴权复刻、ensureXxx、§6 自检 | 阶段 1.2 / 3（鉴权引用）/ 5.6 | 无（「无登录」≠「无鉴权」，通用 header/query 仍要读） |
| `references/SUBAGENT_PROTOCOL.md` | 大项目 subagent 派发协议（能力索引 → ①鉴权 ②api ③probe；读取预算与回传纪律） | 阶段 1 判定为大项目时 | 小项目（页面 ≤ ~30 且无多分包）直读时 |

---

## 硬性约束

### A. 独立分包禁止项（必须改写）

| 禁止项 | 正确做法 |
|--------|---------|
| `getApp()` | 分包内自行管理状态（模块变量 / `wx.storage`） |
| `require('../../xxx')` 引用主包/兄弟分包 / `import ... from '@/'` | 把依赖**完整拷贝**到当前分包：单 skill 私有放 `{skill}/utils/`，多 skill 复用放 `skills/_shared/` |
| 依赖主包 `wx.cloud.init()` | `utils/util.js` 中 `ensureCloudInit()` 自行初始化 |
| 依赖主包 `app.js` 初始化 storage | `utils/util.js` 中 `ensureStorageInit()` 自行初始化 |
| 从 `getApp().globalData` 读配置 | `baseUrl` / `env` 硬编码在分包 `utils/util.js` |
| 依赖主包登录态 | 每次执行接口前 `ensureLogin()` 主动走一遍登录流程 |
| 使用主包注册的全局组件 | 在分包 JSON 中重新声明 `usingComponents` |

### B. 直接终止生成的阻断规则

出现以下任一情况，立即终止生成并告知用户：

| 阻断情况 | 检测时机 | 告知文案 |
|---------|---------|---------|
| 依赖小程序插件（`plugin://` / `requirePlugin` / `app.json` 的 `plugins`） | 阶段 1/3 | "该功能依赖小程序插件，当前暂不支持自动生成，需手动接入" |
| 用户声明的能力在源码中找不到任何对应接口或页面 | 阶段 3 | "未能在源码中定位到 `<能力名>`，无法生成，请确认能力名称或补充源码" |
| 未提供可读的源码目录（只给 appid / URL / 截图） | 阶段 1 前 | "请提供小程序完整源码目录，当前无法基于非源码资产生成" |
| 所有候选实现都依赖非白名单 JSAPI 且无替代方案 | 阶段 3 | "该能力依赖非白名单 JSAPI（如 `<api>`），无法自动生成" |
| `app.json` 缺 `"lazyCodeLoading": "requiredComponents"` 配置 | 阶段 1 | "项目 `app.json` 顶层缺少 `\"lazyCodeLoading\": \"requiredComponents\"`，否则独立分包内的原子接口被小程序 AI 路由调用时无法正确加载执行。请在 `app.json` 顶层添加该字段后重新触发生成" |
| 响应结构无法从源码消费点确定，且 probe 不可用 | 阶段 3 | "接口 `<api>` 的响应结构无法静态确定且运行时探测不可用，请协助提供接口文档或排查 probe 环境" |

### C. 代码一致性（不增不减 + 封装层强制复用）

本 skill 的唯一目标：将参考源码迁移/转换为目标格式，保持逻辑、结构、行为与参考源码**完全一致**。

迁移 = 忠实搬移，不是重写。源码中存在的每一项逻辑都必须保留到产物中，源码中不存在的不得添加。

**封装层强制复用**：`utils/request.js` 是网络请求唯一入口，所有 `apis/*.js` **必须通过它发请求**，禁止 API 文件中直接调 `wx.request` 或自行拼 URL/header/query——否则鉴权参数全部丢失导致 403/空数据。

#### C.1 禁止添加（源码中不存在的逻辑）

- 添加参考源码中不存在的错误处理（try/catch、if 判断等）
- 添加参考源码中不存在的默认值或兜底逻辑
- 添加参考源码中不存在的输入校验
- 「优化」、「修正」、「补全」参考源码中看起来不完整的逻辑
- 任何形式的「我觉得这里应该加上...」

如果参考源码本身没有处理某种情况，输出也不处理。参考源码某处看起来像是 bug 或缺失，原样保留。


#### C.2 禁止丢弃（源码中存在的逻辑）

> **核心原则：你无权判断"这个参数是否必要"。** 后端校验规则对你是黑盒，源码 request 封装中每一个 header/query 都必须保留。

- **鉴权参数完整保留**：见 `references/AUTH_MIGRATION.md`；生成后按 AUTH_MIGRATION §6 自检
- **依赖完整内联**：阶段 3.2 追踪到的依赖，阶段 5 完整拷贝到分包
- **响应字段类型安全**：对 API 响应中的数组字段进行处理前，加空保护（`(x || []).method()` 或 `Array.isArray(x) ? x.method() : []`）。

### D. wx API 白名单（每次生成必须对照）

> 阶段 1 鉴权扫描、阶段 3 JSAPI 提取、阶段 5 代码生成时**必须对照白名单**。源码用到清单之外的 JSAPI → 按"不可迁移 JSAPI"处理。
>
> **完整清单**（接口侧 / 组件侧 / 不可迁移）见 **`references/JSAPI_WHITELIST.md`**。下文 D.1 / D.2 / D.6 仅列高频条目，覆盖业务时必查 reference 完整列表，不要凭印象。

#### D.1 接口侧白名单

> "接口侧"指通过 `wx.modelContext.registerAPI()` 注册的处理函数及其依赖的纯 JS 模块——常规放在 `<skill>/apis/`（也可放 `tools/services/` / `tools/`，validator 会按这三个候选目录解析），引用的工具模块目录名（如 `utils/` / `services/` / `helpers/` / 自定义名）不限。**作用域以"是否在原子接口处理函数链路上"判定，不以目录名判定**。

| 分类 | 高频接口 |
|------|---------|
| 小程序 AI | `wx.modelContext.registerAPI`、`wx.modelContext.createSkill`（返回 `{ use, registerAPI }`）、`wx.modelContext.expireAllCards`、`wx.modelContext.getSessionId`（获取会话 ID） |
| 登录 | `wx.login`、`wx.checkSession` |
| 网络 | `wx.request`、网络状态 `getNetworkType` / `on*NetworkStatusChange` |
| 云开发 | `wx.cloud.init` / `callFunction` / `database` |
| 位置 | `wx.getLocation` / `getFuzzyLocation`（**不含** `chooseLocation` / `openLocation`） |
| 系统 | `wx.getDeviceInfo`、`wx.getAppBaseInfo`、`wx.getWindowInfo` |
| 数据缓存 | `wx.{get,set,remove,clear,batchGet,batchSet}Storage`（含 `Sync`）、`wx.getStorageInfo` |
| 上传下载 | `wx.uploadFile`、`wx.downloadFile` |
| 订阅消息 | `wx.requestSubscribeMessage` |
| 授权设置 | `wx.authorize`、`wx.getSetting`（**不含** `openSetting`） |
| 图片 | `wx.getImageInfo` |
| 手机号 | `wx.getPhoneNumber`、`wx.getRealtimePhoneNumber` |
| 账号 | `wx.getAccountInfoSync`（接口与组件均可调） |
| 隐私授权 | `wx.requestAgentPrivacyAuthorization({ privacyAgreements })`（弹平台隐私授权卡片，返回 `{ authorized }`；用法见 `references/CODE_TEMPLATES.md` 第二节） |

> 支付类、系统选择器/采集（`choose*` / `scanCode` / `saveImageToPhotosAlbum`）、主动打开原生页/面板（`openLocation` / `makePhoneCall` / `openDocument` / `shareAppMessage` / `openSetting` / `openPrivacyContract`）、界面反馈（`showToast` / `hideToast`）**不在接口侧**——见 D.2 / `references/JSAPI_WHITELIST.md §2`（组件侧）。其他场景（人脸核身、微信运动、加密、WiFi、蓝牙/BLE、WebSocket、TCP/UDP、mDNS、传感器等）查 **`references/JSAPI_WHITELIST.md §1`** 完整表。

源码用到清单之外的 JSAPI → 按 D.9 判定规则处理。阶段 1/3/5 每次对照白名单，不要凭印象。

#### D.2 组件侧白名单

> "组件侧"指原子组件 `Component({})` 内的代码及其引用的纯 JS 模块。`_meta.ui.componentPath` 是相对 skill 目录的组件基路径，对应 `<componentPath>.{js,json,wxml,wxss}`；默认模板使用 `components/<name>/index`。

**完整清单见 `references/JSAPI_WHITELIST.md §2`**（含小程序 AI getContext/getViewContext/setRelatedPage/updateModelContext/expireAllCards/expirePreviousCards、界面 previewMedia/showToast/hideToast、系统、缓存、文件、账号、位置 openLocation、设备、设置、分享、振动、隐私、地图 MapContext 全方法等）。组件侧禁用规则（`wx.cloud.*` 及白名单外 JSAPI 不可用、组件与接口全局变量不共享、上下文按使用点获取或 `this._viewCtx` 缓存）同见该文 §2 末段。

> **同步交互状态给模型**：用户在卡片上改了选择（选规格、选时段等）时，在 tap handler 内调 `wx.modelContext.getViewContext(this).updateModelContext({ content: [{ type: 'text', text: '用户选择了大杯' }] })`，让模型感知最新状态。必须在用户的 tap 点击事件回调中调用，不可在异步逻辑或定时器中调用，短时间重复调用会被节流拒绝，`content` 须为非空数组且 `text` 非空。

#### D.3 组件配置（原子组件按需生成 + 关联页 + 实时动态能力）

**默认不生成原子组件**。原子接口只返回文本 + `structuredContent` + `handoff`（进接力页，见 D.6）。**仅当用户明确要求生成原子组件（GUI 卡片）时**才生成：对应接口声明相对 skill 目录的 `_meta.ui.componentPath`，并在 `mcp.json` 顶层 `components[]` 声明一条记录，**`path` 必须与该接口 `_meta.ui.componentPath` 字符串完全相等**。

**`relatedPage` 必填**：卡片标题栏右上角的"进入小程序"入口靠它配置，缺失会导致 `cli preview` / 上传时被平台强校验拦下。取值必须以 `/` 开头（绝对路径），去掉前导 `/` 后是项目 `app.json` 中真实存在的页面（主包 `pages[]` 或分包 `root + page`）；业务上没有对应页面时兜底填首页 `/<app.json.pages[0]>`。通过该入口进小程序的场景值为 1442 / 1443。

`permissions.scope.dynamic` 仅在组件需要 `wx.login` / `wx.checkSession` / `wx.request` / 定时器时按需声明（规则见 `references/JSAPI_WHITELIST.md` §2.1）。

```json
{
  "components": [
    {
      "path": "components/order-list/index",
      "relatedPage": "/pages/order/list"
    },
    {
      "path": "components/weather-card/index",
      "relatedPage": "/pages/weather/index",
      "permissions": { "scope.dynamic": { "desc": "声明使用场景" } }
    }
  ]
}
```

运行时给关联页附加 query 参数：可在组件 `created` 中保存 `this._viewCtx = wx.modelContext.getViewContext(this)`，收到 `NotificationType.Result` 或状态变化后调 `this._viewCtx.setRelatedPage({ query })`；组件可能关联多个页面时再额外传 `path`。也可按使用点获取 `viewCtx` 后调用。示例代码见 `references/COMPONENT_TEMPLATES.md` "关联小程序页面"节。该约束由静态规则校验（V015）。

#### D.4 组件过期态声明（按需，非强制）

默认不生成。**仅当**源业务上存在"卡片到某时刻作废、不应再被点"语义（成交、关店、活动结束、超时）时，在 `components[]` 记录上加 `expirable: true` + 业务化 `expiredText`。声明与调用必须配对。

触发 API 二选一（不要同时调）、精细过滤（`componentPaths` / `match: 'latest'`）、代码示例详见 **`references/COMPONENT_TEMPLATES.md` "卡片过期"节**。

#### D.5 半屏页面（按需，**默认不生成**）

> 本节说的半屏页面是**另开一个小程序页面**（`openDetailPage`），运行环境等同普通小程序页面；与原子组件自身展开成半屏的 `collapsible-view` 不是一回事，选用辨析见 `references/HALF_SCREEN.md` §4。

仅当源业务确有"详情 / 用户补充信息"语义时挂上。入口仅在原子组件 `methods` 内（`getViewContext(this).openDetailPage`，**原子接口无 `this` 不可调**）。半屏内上行 `sendFollowUpMessage`、禁用清单（跳出类 / 页面路由 / 聊天工具 / 广告 / 导航组件等）、场景值、关闭按钮适配详见 **`references/HALF_SCREEN.md`**。

#### D.6 handoff 接力页（进小程序的主要方式）

进小程序统一走 **handoff**。默认流程：原子接口返回**文本 + 小程序卡片**，用户点卡片后由平台 handoff 进入小程序内的**接力业务页**继续操作。

**何时必须配**：若某原子接口执行完会**停下等用户确认**（展示小程序卡片、等用户点击进小程序），必须为它配置 `pagePath`，否则用户无法进入业务页。纯数据、无停顿接续的接口可不配。

四项适配（`mcp.json` 配 `_meta.ui.pagePath` → 返回值顶层 `handoff`（对象立即 / 函数延迟两形态，字段 `query` / `payload` / `path`）→ 主包 `app.js` 注册 `wx.onAgentHandoff` → 接力页 `onLoad(query)` 消费）的字段规格与完整代码，见 `references/CODE_TEMPLATES.md` "handoff 接力页"节。

> **与文本混排链接的分工**：handoff 是把**当前对话流程整段接力进页面**；只想在回复文字中间给一个可点的详情入口时用 `outputSchema` 的 `format: "page-link"`（见阶段 4.2），**不要返回 handoff**。两者可同时存在，互不替代。

> **禁用**：`wx.openAgent` / `wx.navigateBackAgent` 当前基础库侧未打通，调用会失败——接力页内不要依赖"打开 Agent / 返回 Agent 对话"，后续流程由业务页自行完成。

#### D.7 不可迁移 JSAPI（接口与组件均禁用）

完整清单与替代策略见 **`references/JSAPI_WHITELIST.md` §3**（含 Taro 特有不可迁移项）。高频项：`wx.showModal` / `showLoading` 系、`wx.navigateTo` 系路由、`chooseImage` / `chooseVideo` / `previewImage` 老接口、`setClipboardData` / `getClipboardData`、`getUserInfo` / `getUserProfile`、`createSelectorQuery` / `createCanvasContext`、`pageScrollTo` / `createAnimation`、普通原子组件内 `setTimeout` / `setInterval`。

> **注意区分"两侧都不可用"与"只是换了一侧"**：`showToast` / `chooseMedia` / `scanCode` / `makePhoneCall` 这类**不是全禁**，只是从接口侧移到了组件侧；一侧可用的查 D.1 / D.2 与 `references/JSAPI_WHITELIST.md`。

#### D.8 `button` 的 `open-type` 改写

组件内 `button` 禁用 `open-type`（`share` / `getPhoneNumber` / `getRealtimePhoneNumber`）→ 去掉 `open-type`，改 `bindtap`，在 tap handler 内调对应白名单 JSAPI（`wx.shareAppMessage`；手机号相关须放在原子接口侧完成，见 D.1 / D.2）。

#### D.9 判定规则

按 `references/JSAPI_WHITELIST.md` §4 三条执行（仅能不可迁移 JSAPI 实现且无替代 → 阻断 B；核心逻辑可用网络请求实现 → 纯网络请求版本；老接口有白名单内替代 → 自动替换）。自动替换时**同时确认替代接口所在的一侧**（多数只在组件侧可用）。

### E. 原子组件约束

事件 / 内置组件白名单 / 渲染容器 / 实时动态能力 / 动画限制等完整约束，见 `references/COMPONENT_TEMPLATES.md` "重要限制"节；CSS 属性支持范围见 `references/ATOMIC_COMPONENT_CSS.md`。另有两条限制：

- **数据通道禁止 `properties` / `observer` / `dataSource`**：必须通过 `NotificationType.Result` 取 `structuredContent`（详见 `references/COMPONENT_TEMPLATES.md` 与阶段 5.4）
- **WXML 表达式限制**：`{{ }}` 中不支持数组下标（如 `[0]`）、函数调用（如 `.slice()`）、模板字符串等复杂 JS。需要计算的字段一律在 `index.js` 归一化阶段预处理好再 `setData`

---

## 执行清单（复制后勾选）

```
阶段 0 — 业务需求澄清（前置）
- [ ] 判定用户场景是否明确（两项判定）
- [ ] 不明确 → 最小扫描 + 引导澄清 + 等待确认
- [ ] 确认是否生成原子组件（默认不生成，见 D.3）
- [ ] 产出"目标业务场景 + 期望原子能力"清单

阶段 1 — 项目扫描
- [ ] 首检 `lazyCodeLoading`（缺则阻断 B）
- [ ] 提取 app.json / app.js / project.config.json 关键字段
- [ ] 产出云开发 / 插件 / storage 初始化清单
- [ ] 落盘 `analysis-auth.md`（鉴权事实 + 逐字代码片段，见 `AUTH_MIGRATION.md` §2/§3；大项目派 subagent ① 鉴权分析，三类中最先）
- [ ] 大项目：先产能力索引坐标（见 1.0）

阶段 2 — 业务功能识别（用户已明确时跳过）
- [ ] 产出结构化功能清单 JSON
- [ ] 用户二次确认

阶段 3 — 接口与 JSAPI 提取 + 可行性校验
- [ ] 逐接口分析（小项目直读 / 大项目派 **subagent ② api 分析**，须在 ① 完成后，见 3.2），追加到 `analysis-apis.md`
- [ ] 按需 probe（两个触发条件，见 3.7）：派 **subagent ③**（须在 ①② 完成后），跑了的回填真实响应到 `analysis-apis.md`

阶段 4 — 原子接口设计
- [ ] 原子接口清单（含 name / description / inputSchema；按需声明 outputSchema。进小程序的接口配 _meta.ui.pagePath + 返回 handoff；_meta.ui.componentPath 仅生成组件时才有）
- [ ] API 依赖图
- [ ] storage key 清单

阶段 5 — 代码生成
- [ ] 进小程序的接口已配 _meta.ui.pagePath + 返回值顶层 handoff（见 D.6）
- [ ] `utils/request.js` 按 `AUTH_MIGRATION.md` §5 生成，§6 自检清单逐条过
- [ ] 每写完一个 `apis/<name>.js` 做字段来源自检（见 5.8）
- [ ] （生成组件时）组件走 5.1–5.4 前置与模板；`components[]` 每条都填了 `relatedPage`
- [ ] `skills/{skill-name}/` 目录完整（mcp.json / SKILL.md / index.js / apis/* / utils/*；仅生成组件时含 components/*）；SKILL.md 按 `CODE_TEMPLATES.md` 第五节 5 节结构写完

阶段 6 — 配置集成
- [ ] app.json 加 agent.skills（每项含 `{ name, description, path }`）+ subPackages
- [ ] project.config.json 的 packOptions.include 加 skills
- [ ] （按需）AGENTS.md + `agent.instruction`；page-meta.json + `agent.pageMetadata`（见 6.1 / 6.2）
- [ ] 体积与数量上限自查（上限表见 `CODE_TEMPLATES.md` 6.3）

收尾 — 交棒给 wxa-skills-validate
- [ ] 明确告知用户："请使用 wxa-skills-validate 做校验"
- [ ] 提示 skills 路径与 project-path
```

---

## 跨阶段跳转规则

| 场景 | 流向 |
|------|------|
| 正常主干 | 0 → 1 → (2) → 3 → 4 → 5 → 6 → 交棒 `wxa-skills-validate` |
| 用户已明确能力 | 跳过 2，0 → 1 → 3 |
| 阶段 3 | 3.6 → 3.7（命中触发条件才 probe）→ 4 |
| probe 环境不可用 | 静态结果照常使用，代码标 `[ai-mode:static]`，交棒时声明未真机验证 |
| validator 反馈 T1~T6 / A/B/C/D 类错误 | 回本 skill 阶段 5 改代码 |
| validator 反馈 T7/T8（接口划分 / 依赖链路） | 回本 skill 阶段 4 重设计 |
| 任一阶段触发阻断规则 B | 立即终止，输出阻断原因 |

**核心原则**：

1. 业务场景不明确时，**必须先澄清后生成**
2. 每个阶段完整产出"产出物清单"中的全部项后再跳转到下一阶段

### 增量与重入

工作区已存在 `skills/` 产物时：

| 用户意图 | 入口阶段 | 说明 |
|---------|---------|------|
| 新增一个原子能力 | 阶段 0（轻量）→ 阶段 3 | 先澄清新能力，扫描接口并入增量清单 |
| 修改已有原子接口的行为 | 阶段 4 | 更新接口清单 → 5 → 6 → 交棒 |
| 修改组件样式/模板 | 阶段 5 | 仅改 `components/{x}/`，重新走 5 → 6 → 交棒 |
| validator T1~T6 / A/B/C/D 反馈 | 阶段 5 | 按报告定位文件，改完交棒 |
| validator T7/T8 反馈 | 阶段 4 | 重设计后 5 → 6 → 交棒 |
| 仅做验证 | **不进入本 skill**，直接给 `wxa-skills-validate` | — |

> 重入时已生成且未触及的文件保持不变，只更新受影响的文件。

---

## 阶段 0 — 业务需求澄清（强制前置）

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 用户发起生成请求（任何请求都必须从本阶段开始） |
| 产出物 | 判定结果 + 必要时的澄清清单 |
| 下一步 | "明确"或澄清确认完毕 → 阶段 1 |

**判定规则**（必须同时满足 2 项才算"明确"）：

| # | 判定项 | 示例 |
|---|--------|------|
| ① | 指明**具体业务名词** | "商品检索""订单管理""地址管理""签到"；而不是"核心功能""主要能力" |
| ② | 可推断**至少 2-3 个原子能力的粒度** | "检索商品 + 展示列表 + 查看详情"；而不是"业务相关" |

任一不满足 → 进入下方澄清流程。

### 不明确时的引导流程

1. **最小扫描**：只读 `app.json` 的 `tabBar.list`、`pages`（一级路径）、`subPackages.root`。**禁止**读 JS/WXML/WXSS，禁止做依赖分析。
2. **归纳候选**：基于路径关键词（见 `references/ANALYSIS_PATTERNS.md` 页面功能识别表）归纳 3~6 个候选场景。
3. **向用户提问**（一次问完，别反复打断）：
   - 希望把哪些业务场景做成小程序 AI 的 SKILL？
   - 每个场景希望暴露给小程序 AI 的原子能力大致是什么？
   - 是否涉及登录态、支付、位置、云开发等敏感能力？
   - 是否需要生成**原子组件（GUI 卡片）**？**默认不生成**——只做原子接口 + handoff（点小程序卡片进接力页）；仅当你明确需要对话内卡片式 GUI 时才生成。
4. **等用户回复后**才能进入阶段 1。严禁在用户确认前扫描源码或生成代码。

**澄清输出清单模板**：

```
目标业务场景：
  - 场景 A：<名称> → 期望原子能力：<能力 1>、<能力 2>
  - 场景 B：<名称> → 期望原子能力：<能力 3>

技术约束：
  - 是否涉及支付/登录/位置：是/否
  - 是否使用云开发：待阶段 1 扫描确认
  - 是否生成原子组件（GUI 卡片）：是/否
```

---

## 阶段 1 — 项目扫描

### 项目结构速览 + 读取策略分流

读 `app.json` 映射阶段 0 目标到页面/分包。按规模分流：

| 规模 | 判定 | 策略 |
|------|------|------|
| **小项目** | 页面 ≤ ~30、无多分包 | 主 agent 直接 `read`/`grep` |
| **大项目** | 页面 > ~30 / 多分包 / 单文件巨大 | 按 `references/SUBAGENT_PROTOCOL.md` 执行（能力索引 → 三类 subagent 全派） |

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 阶段 0 产出明确 |
| 产出物 | 配置字段、云开发/插件、`analysis-auth.md`、storage 清单；大项目附能力索引 |
| 下一步 | 已明确能力 → 阶段 3；否则 → 阶段 2 |
| 阻断条件 | 缺 `lazyCodeLoading` / 无源码 / 依赖插件 |

### 1.1 配置扫描

读 `app.json` / `app.js` / `project.config.json`，提取 `pages` / `subPackages` / `tabBar` / 已有 `agent` / `appid` / `packOptions`；扫云开发（`wx.cloud` 调用 / `cloudfunctions/` 目录）与云环境 ID（`wx.cloud.init({ env })`）。**`lazyCodeLoading` 必检**：缺 `"lazyCodeLoading": "requiredComponents"` → 阻断规则 B（不要"代为补全"）。云开发项目同时扫 `cloudfunctionRoot/<fn>/index.js` 的入参/返回结构。

### 1.2 鉴权逻辑扫描

按 `references/AUTH_MIGRATION.md` §2/§3 落盘 `<源项目>/.ai-mode-skills/analysis-auth.md`（鉴权事实结构化 + 逐字代码片段，签名函数体不写成步骤数组）。

- **小项目**：主 agent 读 `app.js`/request 封装/登录文件，自行填写
- **大项目**：派 **subagent ①（鉴权分析）** 深读 `app.js` / request 封装 / 登录文件 / 签名模块，回传结论摘要（见 `references/SUBAGENT_PROTOCOL.md` §3.1）

> analysis-auth.md 落盘后即为"可信事实"，后续阶段 3 / 5.6 直接引用，不重读同一鉴权函数。

### 1.3 主包 storage 初始化扫描（必做）

扫 `app.js` 与主包 `.js` 中的 `wx.{set,get,clear}Storage*`，提取 `key` / `defaultValue` / `initCondition` / `sourceFile`。迁移：① `setStorageSync` 初始化值 → 分包 `ensureStorageInit()` 重建；② `getApp().globalData` 运行时缓存 → 模块级变量或按需写 storage；③ `onLaunch` 异步获取后写 storage → 分包首次调用时自行重发请求并缓存。形成 **storage 初始化清单**（与阶段 4 内部"接口间数据传递的 storage key 清单"不是同一张表）。

### 1.4 压缩代码处理

识别：单行 >500 字符 / 单双字符变量名 / 缺注释空行。处理顺序：① 优先问用户要未压缩源码；② 否则尝试 prettier 格式化后再提取；③ 格式化后关键字段仍全是 `a.b.c.d` → 阻断规则 B。**禁止盲目猜变量名**——猜出来的代码会在 validator 大量失败。

### 1.5 插件检测

扫 `app.json` 的 `plugins` 字段、页面/组件 JSON 的 `usingComponents` 中的 `plugin://` 引用。目标能力依赖插件 → 阻断规则 B。

---

## 阶段 2 — 业务功能识别（用户已明确时跳过）

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 阶段 1 完成 **且** 用户仅给源码未明确原子能力 |
| 产出物 | 结构化功能清单（JSON）**且已获得用户二次确认** |
| 下一步 | 用户确认 → 阶段 3 |
| 阻断条件 | 用户始终无法确认 → 停留本阶段 |

**动作**：

1. 针对阶段 0 选定的候选场景对应页面，按 `references/ANALYSIS_PATTERNS.md` 的模式分析页面用途、交互事件、数据流向
2. 从用户视角识别功能点（每个功能 = 一个原子接口）
3. 分析数据依赖（A 的返回值被 B 使用）

**mcp.json 只注册用户直接使用的原子能力（硬约束）**：

以下接口**不收集为原子能力**、不写 mcp.json、不生成 `apis/*.js`：

1. **鉴权/登录类**：`wx.login` / `wx.checkSession` / `ensureLogin()` / token 刷新 / 获取 sessionId 等——这些是**基础设施**，由 `utils/` 内 `ensureLogin()` 等函数在每次接口调用前自动执行，不是用户直接使用的能力
2. **系统级/生命周期接口**：app 初始化（`onLaunch` / `onShow`）、storage 初始化、配置获取、全局状态读取等——这些是框架/运行时行为，不是用户主动触发的业务功能
3. **内部辅助接口**：被其他原子接口调用但不直接面向用户的 API（如"获取子列表"被"搜索"内部调用但用户不直接用）——只收集用户视角的功能入口
4. **工具函数**：`utils/` 中的纯函数（格式化、计算、URL 拼接等）——这些是代码组织，不是独立能力
5. **敏感接口**（不可逆副作用）：注销/删除/解绑等——见下方专门规则
6. **管理端接口**：管理端操作（如"导出数据"、"管理成员"、"删除商品"、"发布公告"等）——这些是管理端操作，不是用户直接使用的能力

**判定标准**：问自己"用户会对小程序 AI 说'帮我做 X'吗？"——会 → X 是原子能力；"系统自动做的"或"另一个接口内部调的" → 不是。

**敏感接口默认不收集为原子能力（硬约束）**：

会产生**不可逆副作用**的接口，**默认不收集为原子能力**、不写 mcp.json、不生成 `apis/*.js`。理由：这类接口风险高（误触发不可恢复）、低频、应由用户在原生页面主动操作，不适合 AI agent 自动调用。

**判定原则**：
- **不可逆的状态变更**：注销账号、删除数据、清空记录等执行后无法撤销的操作，解绑、退订、解散团队、踢出成员、退出等无法恢复的操作

**关键词提示清单**（命中≠一定敏感，仍需结合语义判断；用于辅助筛选，非穷尽）：
`log_off / 注销 / 销户 / cancel / delete / 删除 / remove / 移除 / unbind / 解绑 / dissolve / 解散 / kick / 踢出`

**处理方式**：识别到敏感接口时，**跳过不选**，并在功能清单 JSON 里标注 `"skipped": "destructive"`（附原因）。这些功能由用户在小程序原生页面自己实现，不暴露给 AI agent。若用户**明确要求**把某个敏感接口做成原子能力，才收集，并在 `probe/plan.json` 对应 api 项标 `"destructive": true` + `"destructiveReason"`

**产出物 JSON**（字段统一 camelCase）：

```json
[
  {
    "functionName": "检索商品",
    "pages": ["pages/items/list", "pages/search/index"],
    "sourceApis": ["GET /api/items/search"],
    "suggestedAtomicInterfaces": ["searchItems"],
    "needsComponent": true
  }
]
```

**将清单发给用户二次确认**后才能进入阶段 3。

---

## 阶段 3 — 接口与 JSAPI 提取 + 可行性校验

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 已有用户确认的目标原子能力清单 + 已落盘的 `analysis-auth.md` |
| 产出物 | `analysis-apis.md`（每接口：真实入口 + 请求构造 + 每入参赋值来源 + 鉴权引用 + 响应字段与来源标记）+ 可行性校验结果 |
| 下一步 | 所有能力均找到对应实现 → 阶段 4 |
| 阻断条件 | 任一能力找不到对应实现 / 依赖链路含插件 → 阻断规则 B |

详细匹配模式见 `references/ANALYSIS_PATTERNS.md`。

**3.1 提取范围**：仅扫用户已确认能力对应的页面/模块，搜索网络调用（`wx.request` / `wx.cloud.{callFunction,database,callContainer}`）+ 白名单内 JSAPI（高频列表见"硬性约束 D"，完整清单见 `references/JSAPI_WHITELIST.md`）。

**3.2 依赖追踪（读真实源码，逐字复刻）**：

逐能力先定位**承载它的真实交互入口**——源码中触发该能力的那段代码（页面生命周期 `onLoad`/`onShow`、按钮 / 输入框等事件 handler，或对应业务函数）。**该入口实际调用的接口，就是这个能力的唯一标准接口**；连同它传入的分支参数（类型 / 模式标志位等）一起逐字复刻。能力与接口一一对应，不在多个名字相近的接口间"挑一个更好实现的"——一切以源码真实入口为准。

**每个入参追到真实赋值来源**：不止复刻 `wx.request` 那一行——每个请求字段继续向上追：`页面 data` ← `onLoad`/`onShow`/事件回调 ← JSAPI / `wx.getStorageSync` / `globalData` / 用户输入。动态值（定位、设备、登录态等）标注到 analysis-apis.md，阶段 5 生成 `ensureXxx()`（见 `AUTH_MIGRATION.md` §4）。**来源未追清时禁止用固定值兜底**；正常路径 + 失败/缺省分支与主包一致。

> **定位迁移与鉴权同级**：接口入参含坐标/定位时，与鉴权一样不可跳过——追到真实来源、阶段 5 生成 `ensureLocation()` 实调 `wx.getLocation` 取真值，禁止硬编码或只读缓存兜底（细则见 `AUTH_MIGRATION.md` §4）。

**按规模分流**（防爆上下文）——主 agent **不预先读源码判断接口复杂度**

- **小项目**：主 agent 逐接口直读（真实入口 handler → 调用处 → 请求构造）
- **大项目**：每能力派 1 个 **subagent ②（api 分析）** 深读**业务层逻辑**（入参来源 / 返回结构 / 跳转链），回传结论摘要。须在 ①（鉴权分析）完成后启动；鉴权事实已由 ① 落盘 `analysis-auth.md`，② 只引用结论（标行号）、不重复探测鉴权链路

读取预算（坐标直达 / 只读 1 跳依赖 / 单次 ≤ ~5 文件 / 逼近上限回传待确认）与回传纪律（只回 ≤20 行结论摘要、零源码原文）见 `references/SUBAGENT_PROTOCOL.md` §四。

**3.3 鉴权依赖确认**：结合 analysis-auth.md，对每个目标接口确认 ① 是否需要登录态 ② token 来源（storage 直读 / 需先登录）③ 登录方式（`wx.login` + 换 token / 其他）。analysis-apis.md 只填鉴权引用（`requiresLogin` / `signing` / `dynamicValues` / 通用参数 inherit），**不重新定义鉴权事实**，避免与 analysis-auth.md 漂移。详见 `AUTH_MIGRATION.md` §2/§5。

**3.4 签名 / 可请求性**：若接口请求含签名 / 反爬字段（sign / timestamp+nonce / 指纹等），记入 analysis-auth.md 签名清单（`id` / `scope` / 触发 / 密钥来源 / 输出字段 / 依赖模块 / 原文片段指针），函数体 verbatim 入逐字代码片段节。**不因「更好实现」换接口或简化签名**——签名一错全废。可请求性判定：依赖验证码/短信等运行时人机交互 → `replicable: false` + `blockers` → 阻断或人工接入。

**3.5 插件依赖**：依赖链路含 `requirePlugin` / `require('../plugin/')` / `plugin://` → 阻断规则 B。

**3.6 可行性三级校验**：

| 级别 | 识别特征 | 处理 |
|------|---------|------|
| ✅ 高置信 | 真实入口唯一确定接口，参数/返回路径清晰 | 直接进阶段 4 |
| ⚠️ 中置信 | 参数/返回模糊，或多个并列真实入口 | 补读或问用户 |
| ❌ 无置信 | 找不到任何实现 | 阻断 B |

**中置信询问模板**：

```
以下原子能力在源码中存在多个并列的真实入口，请确认对应哪一个：

能力：<能力名>
入口 1：<页面/事件> 调用 <接口/云函数> — 参数 <x>、返回 <y>（来自 pages/xxx.js 第 N 行）
入口 2：<页面/事件> 调用 <接口/云函数> — 参数 <x>、返回 <y>（来自 pages/yyy.js 第 M 行）

请按你实际想暴露的小程序功能确认对应哪个入口（接口由能力入口唯一确定，不以实现难易为取舍）。
```

**3.7 运行时探测（probe，按需）**

默认不跑 probe，静态分析能定的直接定稿。仅两种情况触发：

1. **值是运行时动态下发**：请求中的 URL / header / 签名参数在源码里是运行时拼接（如 `baseUrl` 由 `getApp().globalData` 动态返回），静态读不出真实值
2. **响应结构无法从源码消费点确定**：接口返回大量字段但页面只用一部分，且消费点看不出字段层级 / 嵌套结构

命中任一 → 派 subagent ③（probe） 执行整段闭环（写 `probe/plan.json` → 跑 probe → 回填 `analysis-apis.md`；须在 ①② 完成后启动。指令与读取边界见 `references/SUBAGENT_PROTOCOL.md` §3.3；plan 格式、环境要求、result 字段见 `references/RUNTIME_PROBE.md`）：

```bash
node scripts/probe.mjs --project <源项目> --plan <plan.json>
```

每次执行落盘 `probe/<run-id>.json`，读成功 run 的真实响应回填 `analysis-apis.md` 对应接口的响应节（probe run 文件由脚本写，不手写）。

- **probe 成功**：该 api 的响应节标 `sampleSource: probe:<run-id>`，`apis/<name>.js` 顶部注释 `[ai-mode:probe] <run-id> 实际响应字段：…`
- **probe 没跑或环境不可用**：响应节用源码消费点字段，标 `sampleSource: static-source`，代码顶部注释 `[ai-mode:static]`，交棒时向用户声明未经真机验证
- **敏感接口不进 plan**：注销/删除/解绑等不可逆接口一律不探测（probe-lib.mjs 内置拦截）；确需探测时在该 plan 项显式写 `"destructive": true` + `"confirmDestructive": true`，且由用户明确要求

---

## 阶段 4 — 原子接口设计

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 阶段 3 完成：`analysis-apis.md` 已有每个原子接口的请求构造与响应字段（probe 跑过用真实响应，没跑用源码消费点），鉴权引用 analysis-auth.md |
| 产出物 | ① 原子接口清单；② API 依赖图；③ storage key 清单 |
| 下一步 | 三份产出物齐全 → 阶段 5 |

**4.1 技能划分**：同业务域（商品/订单/地址）原子接口聚合到同一 skill；共享 storage 上下文的接口在同一 skill 内；每 skill 推荐 3-8 个原子接口（更多则按子业务拆分）。

**4.2 接口字段**：每条接口必含 `name`（驼峰、全局唯一）/ `description`（含内部串联操作，帮助小程序 AI 决策）/ `inputSchema`（仅小程序 AI 需从用户获取的参数；无参用 `{"type":"object","properties":{}}`）；按需加 `outputSchema`（建议填写；接口返回有明确字段结构的 `structuredContent` 或使用 `page-link` 时声明，依据 analysis-apis.md 的响应字段）/ `_meta.ui.pagePath`（**按需**，接力页 path、不含 query；"执行完停下等用户确认"类接口需配，配合返回值 `handoff`，详见 D.6）/ `_meta.ui.componentPath`（仅生成组件时声明，规则见 D.3；声明则同基路径 `.js` / `.json` / `.wxml` / `.wxss` 文件齐全）。

> **多模态入参**：当接口需要用户上传图片或文件（如 P 图、图像识别、文件解析）时，对应 `inputSchema.properties.<field>` 加 `"format": "image"` 或 `"format": "file"`，类型为 `string`（运行时填本地路径）。小程序 AI 输入框会据此识别为多模态字段、引导用户上传。

> **文本混排链接（`page-link`）**：若某接口返回的数据天然对应小程序页面（商品、订单、门店等），且希望模型在**回复正文里内联可点蓝链**，在 `outputSchema` 中把页面路径字段标成 `{ "type": "string", "format": "page-link", "x-link-text-field": "<同级描述字段名>" }`，接口 `structuredContent` 按 schema 返回真实页面路径即可，平台会渲染成 `#小程序：名称/描述`。字段约束与完整示例见 `references/CODE_TEMPLATES.md` 第四节。**与 handoff 的区别**：`page-link` 只给一个详情入口，handoff 是把整段流程接力进页面——只想要前者时不要返回 `handoff`。

> **敏感接口标记**：阶段 2 已规定敏感接口默认不收集为原子能力。若因用户明确要求或疏漏导致敏感接口进入阶段 4，必须在 `probe/plan.json` 对应 api 项写 `"destructive": true` 和 `"destructiveReason": "<一句话原因>"`（probe 据此跳过）。判定原则与关键词清单见阶段 2

**4.3 进小程序方式（默认 handoff）**：需接续操作/查看详情的接口，配 `_meta.ui.pagePath` + 返回 `handoff`（见 D.6），用户点小程序卡片进接力页。生成原子组件时（规则见 D.3），按返回值类型对照组件模板（详见 `references/COMPONENT_TEMPLATES.md`）：列表/卡片项 → 通用列表；详情/单对象 → 详情卡片；购物车/带数量总价 → 购物车；下单成功/支付结果/操作确认 → 状态结果。

**4.4 产出物示例**（默认形态：无组件，配 handoff）：

```json
[{
  "skill": "business",
  "name": "searchItems",
  "title": "检索商品",
  "description": "根据关键词检索商品，返回商品列表",
  "inputSchema": { "type": "object", "properties": {} },
  "outputSchema": { "type": "object", "properties": { "items": { "type": "array" } } },
  "_meta": { "ui": { "pagePath": "/pages/goods/list" } }
}]
```

API 依赖图（仅在通过 storage 传上下文时必备）：

```
searchProducts ──(storage: skills_shopping_lastSearchResult)──▶ addToCart
              └─(storage: skills_shopping_lastSearchResult)──▶ getProductDetail
```

storage key 命名统一 `skills_{skillName}_{dataName}`，列表含 `key` / 写入方 / 读取方 / 数据结构。

---

## 阶段 5 — 代码生成

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 阶段 4 三份产出物齐全；`.ai-mode-skills/analysis-auth.md` + `analysis-apis.md` 已落盘——缺则回对应阶段补（analysis-auth→1.2、analysis-apis→3.2） |
| 产出物 | 完整的 `skills/{skill-name}/`（`mcp.json` / `SKILL.md` / `index.js` / `apis/*` / `utils/*` / `components/*`）；每个 `apis/<name>.js` 经 5.8 字段来源自检 |
| 下一步 | 代码生成完成 → 阶段 6 |
| 阻断条件 | 产出物缺失 → 停留本阶段补齐 |

代码模板见 `references/CODE_TEMPLATES.md`、组件模板见 `references/COMPONENT_TEMPLATES.md`、**设计规范见 `references/ATOMIC_COMPONENT_DESIGN.md`（最高优先级）**、CSS 实现规范见 `references/ATOMIC_COMPONENT_CSS.md`。

### 5.1–5.4 组件四个前置（仅生成组件时适用，见 D.3；写任何组件 WXML/WXSS/JS 前按序走完）

> 生成组件前**完整阅读** `references/COMPONENT_TEMPLATES.md` 和 `references/ATOMIC_COMPONENT_DESIGN.md`。跳过阅读是导致"接口请求成功但组件不渲染"的常见根因。

| 编号 | 主题 | 关键要点 | 详见 |
|------|------|---------|------|
| **5.1** 设计规范（最高优先级） | 尺寸/主题/边距/字体/布局/操作区 | ① 5 档宽高比 + 圆角 4px；② 主题色按 §2.1 流程从主包 `app.json`/`app.wxss` 抽（浅 + 暗都抽，wxss 顶部注释"色源=…"链路；主包 6 步都查不到才走 §2.3 兜底）；③ 边距 屏幕 16 / 卡片 12 / 元素 8·16；④ 字号 17/15/12 三档 + 同一基色 0.9/0.45/0.3 透明度分层；⑤ 主轴上下/左右布局；横向超长可用 `<scroll-view scroll-x>`，禁纵向滚动、禁 >2 列网格；⑥ ≤3 控件、主动作 ≤1、动宾文案、主按钮居右 | `references/ATOMIC_COMPONENT_DESIGN.md` |
| **5.2** 源样式提取 + 字段映射 | 7 步工作流 | 与设计规范冲突时以**设计规范为准**，仅迁移源项目品牌色与字段映射结果。**自检**：wxss 主色是 `#07c160` / `#ff4d4f` 且源页面未用，或 wxml 出现 `item.imageUrl` 但源 API 字段是 `cover`/`pic`/`thumb` — 视为"照抄模板"，回炉重做 | `references/STYLE_MIGRATION.md` |
| **5.3** 组件交互行为 | 组件是小程序 AI 的"回合出口"，不是"页面入口" | 每个组件都要同时考虑"展示什么"+"用户下一步做什么"——按 `mcp.json.apis[].description` + API 依赖图列出下一步，映射到 `mcp.json.apis[].name` **已存在**的接口；不存在则去掉按钮，**不上行不存在的 name**。每个可交互元素绑 `bindtap` + `hover-class`，关键实体用 `data-*` 携带 | `references/COMPONENT_TEMPLATES.md` "上行消息"节 |
| **5.4** 组件 JS 骨架（数据接入） | 数据只能经 `NotificationType.Result` 下发 | 禁止 `properties` / `dataSource` / `observers`；按 `COMPONENT_TEMPLATES.md` 骨架在 `created` 里绑定 Result 与 Overflow，并打印 `[ai-mode] {componentName} overflow monitor=on` | `references/COMPONENT_TEMPLATES.md` "组件 JS 骨架"节 + "溢出处理模板"节 |

tap handler 的 `content` 形态（优先形态 2：`text` + `api/call` 组合）、`name` / `arguments` 对齐规则、日志要求与禁用项，见 `references/COMPONENT_TEMPLATES.md` "上行消息"节。

### 5.5 目录结构

```
{项目根目录}/
├── app.json                              # 含 agent.skills 注册
└── skills/                               # 独立分包（多 skill 共用）
    ├── _shared/                          # 可选：≥2 个 skill 共用的工具函数才放这里
    └── {skill-name}/
        ├── mcp.json                      # 原子接口 Schema 定义
        ├── SKILL.md                      # skill 路由说明
        ├── index.js                      # 接口注册入口
        ├── apis/                         # 原子接口实现（推荐目录；validator 兼容 tools/services/、tools/）
        ├── utils/                        # 工具模块（目录名不限，常见 utils/services/helpers）
        └── components/{component-name}/  # 默认组件目录；实际组件文件由 mcp.json 的相对 componentPath 决定
```

> **目录分层**：跨 skill **禁止** `require('../../{otherSkill}/...')`；多 skill 复用走 `skills/_shared/`（不在 `mcp.json` 注册、不调 `registerAPI`）。

### 5.6 鉴权代码生成

按 `AUTH_MIGRATION.md` §5/§6 生成 `utils/request.js` + `index.js`；模板见 `CODE_TEMPLATES.md`。生成后过 AUTH_MIGRATION §6 自检清单（逐条）。

### 5.7 mcp.json + 技能自身 SKILL.md + 返回值 + 日志

- **`mcp.json`**：顶层 `{ "apis": [...] }`，每项必含 `name` / `description` / `inputSchema`；`outputSchema` 可选，建议填写，接口返回有明确字段结构的 `structuredContent` 或使用 `page-link` 时应声明。进小程序的接口按需加 `_meta.ui.pagePath`（配合返回值 `handoff`）；`_meta.ui.componentPath` 与 `components[]` 仅生成组件时才有（`components[]` 的 `relatedPage` 必填、实时动态能力按需，详见 D.3）。体积上限见 `references/CODE_TEMPLATES.md` 6.3（计算时会去掉所有 `outputSchema`）。完整字段示例见 `references/CODE_TEMPLATES.md` 第四节
- **技能自身 `SKILL.md`**（**文件名严格全大写**）是业务编排与路由说明，**按 5 节顺序**：能力域定位 → 触发场景（用户原话 few-shot）→ 不适用范围 → 前置条件 → 使用顺序。使用顺序可写业务流程、已注册方法名、前置条件、上下游依赖和跨接口规则；方法名必须与 `mcp.json.apis[].name` 逐字一致。**通篇不写**：`inputSchema` / `outputSchema` / 参数表 / 返回值表 / `componentPath` / storage key / 实现细节 / 安装 CLI 运维。体积上限见 `references/CODE_TEMPLATES.md` 6.3，且只支持单文件、不能引用其它 md。完整模板见 `references/CODE_TEMPLATES.md` 第五节
- **返回值格式**：`{ isError?, content: [{type:'text', text}], structuredContent?, _meta?, handoff?, apiCalls? }`——`content` 给 LLM 文本，`structuredContent` 有 `outputSchema` 时须与之对齐，`_meta` 对 LLM 不可见可传 UI 组件；`handoff`（**进小程序按需**）为 `{ query?, payload?, path? }`，承接卡片点击进接力页，详见 D.6。`content` / `structuredContent` / `_meta` 体积上限见 `references/CODE_TEMPLATES.md` 6.3
- **`apiCalls`（按需，流程固定时用）**：返回值顶层加 `apiCalls: [{ name, arguments }]` 可**显式指定下一步要调的原子接口**，省掉模型推理这一跳、链路更快。典型场景：接口内发现未登录 → 返回 `apiCalls: [{ name: 'login', arguments: {} }]`。`name` 必须是当前 skill `mcp.json.apis[]` 中已声明的接口，`arguments` 与其 `inputSchema` 对齐。**只在源业务流程本来就固定衔接时才写**，开放式场景仍交给模型判断
- **日志规范**：原子接口打 入口 / 入参 / 请求前后 / 出口 / catch；原子组件打 `created`/`attached` / 收到 Result / `setData` / `NotificationType.Overflow`（用于校验裁剪）。统一前缀 `[ai-mode]`。真机失败时靠这些节点定位问题，日志要打全

### 5.8 字段忠实自检

> 每写完一个 `apis/<name>.js`，就地核对其 `structuredContent` 字段集：该 api 在 `analysis-apis.md` 有 probe 真实响应的，与真实响应字段比对；没有的，与源码页面实际消费的字段比对。生成一个查一个，不攒到收尾。

- 字段一致 → 通过，继续下一个
- 缺少/多出字段 → 代码臆造，以记录为准修正 `structuredContent`；已声明 `outputSchema` 时同步修正该 schema

## 阶段 6 — 配置集成

**契约**：

| 项 | 内容 |
|---|------|
| 入口条件 | 阶段 5 生成完整 `skills/{skill-name}/` |
| 产出物 | `app.json` 含 `agent.skills` + `subPackages`；`project.config.json` 的 `packOptions.include` 含 `skills` |
| 下一步 | 两份配置均已更新 → 交棒 `wxa-skills-validate` |
| 阻断条件 | 未更新配置直接交棒 → 必定失败，停留本阶段 |
| 产物校验 | 交棒前**必须确认以下文件存在**：`skills/{skill-name}/mcp.json` + `skills/{skill-name}/index.js` + 每个 `apis/*.js` + `utils/request.js`（或 `utils/util.js`）；`app.json` 的 `agent.skills[]` 含本 skill 条目且 `subPackages` 含 `skills` 独立分包；`project.config.json` 的 `packOptions.include` 含 `skills`。缺任一 → 回阶段 5 补 |

配置格式见 `references/CODE_TEMPLATES.md` 第六节。关键要点：

- **多 skill 共用同一个 `skills` 独立分包**——新增 skill 只在 `agent.skills[]` 里追加 `{ name, description, path }`，不为每个 skill 加一条 `subPackages` 条目。注意反过来不成立：**一个 SKILL 不能跨分包**
- **handoff（按需）**：若有接口配了 `_meta.ui.pagePath` 并返回 `handoff`，在主包 `app.js` 的 `onLaunch` 内注册 `wx.onAgentHandoff`（详见 D.6 与 `references/CODE_TEMPLATES.md` "handoff 接力页" 节）

### 6.1 全局提示词 `AGENTS.md`（按需）

多个 skill 共存、或需要交代整体服务范围 / 背景知识 / 回答风格时，写一个 `AGENTS.md` 并在 `app.json` 用 `agent.instruction` 指向它（相对项目根的路径）。内容定位是"跨 skill 的全局说明"——服务边界、各 skill 之间的关系与选择依据；单个 skill 内部的路由说明仍写在该 skill 自己的 `SKILL.md` 里，不要重复。模板与上限见 `references/CODE_TEMPLATES.md` 6.1 节。

### 6.2 小程序服务直达 `page-meta.json`（按需）

当用户意图**没有对应的原子接口**、只能引导进小程序页面时，配 `agent.pageMetadata` 指向 `page-meta.json`，平台会据此回复"账号卡片"（场景值 1435 / 1436）。条目字段、上限与模板见 `references/CODE_TEMPLATES.md` 6.2 节。

### 6.3 体积与数量上限（生成完自查）

上限表见 `references/CODE_TEMPLATES.md` 6.3 节。超限会在预览 / 上传时被平台拒绝。

---

## 收尾 — 交棒给 wxa-skills-validate

阶段 6 完成后，在回复中明确告知用户：

```
代码生成与配置集成已完成。下一步请使用 `wxa-skills-validate` skill 对产物进行校验与真机验证：

- skills 路径：<abs-path>/skills
- project-path：<abs-path>（含 project.config.json 的 appid 为 <appid>）

wxa-skills-validate 会依次执行：静态校验 → cli agent tool execute → cli agent render → 交付文档。
```

仅输出代码不算完成——在对话中显式提示用户切换到校验 skill 后本 skill 才算结束。

> **建议**：复杂项目上，交棒后的 `wxa-skills-validate` 全流程可派 subagent 执行（独立上下文窗口，避免校验过程挤占主上下文）。
