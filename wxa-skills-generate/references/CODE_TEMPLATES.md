# 代码生成模板

> 第五阶段使用。包含 `utils/util.js` / 原子接口 / `index.js` / `mcp.json` / `SKILL.md` 的代码模板，以及 `app.json` / `project.config.json` 配置片段。

> ⚠️ **独立运行原则**：所有代码运行在独立分包 `skills/` 中，与主包 JS 环境完全隔离。不得出现 `getApp()`、跨包 `require/import`。工具函数、配置、初始化逻辑必须自包含在技能目录内。
>
> ⚠️ **目录分层原则**：工具函数统一放在 `utils/` 目录下，与 `apis/` **同级**；`apis/` 目录只存放**在 `mcp.json` 中注册的原子接口**，不要混入工具函数，以保持接口与工具层的清晰边界。
>
> ⚠️ **日志必写原则**：原子接口和原子组件在关键节点（入口/入参/请求前后/出口/catch；组件的 created/setData/attached）打 `[ai-mode]` 前缀的 `console.info` 日志，这是真机验证失败时唯一的排查依据。

## 目录

- [一、utils/util.js 工具函数](#一utilsutiljs-工具函数)
  - [1.1 必选：返回值工厂](#11-必选返回值工厂每个-skill-都需要)
  - [1.2 按需：云开发初始化](#12-按需云开发初始化使用-wxcloud-时才需要)
  - [1.3 按需：主包 storage 初始化迁移](#13-按需主包-storage-初始化迁移仅当主包-appjs-有写-storage-默认值时才需要)
  - [1.4 按需：HTTP 请求（含登录鉴权）](#14-按需http-请求使用-wxrequest-时才需要)
  - [1.5 按需：JSAPI 封装](#15-按需jsapi-封装仅白名单内)
  - [1.6 按需：接口间数据传递](#16-按需接口间数据传递)
- [二、原子接口模板](#二原子接口模板)
- [三、index.js 注册模板](#三indexjs-注册模板)
- [四、mcp.json 模板](#四mcpjson-模板)
- [五、SKILL.md 模板](#五skillmd-模板)
- [六、app.json + project.config.json 配置](#六appjson--projectconfigjson-配置)

---

## 一、utils/util.js 工具函数

`utils/util.js` 是分包的工具层，位于 `utils/` 目录下，与 `apis/` 同级。按实际需要**按需组合**以下能力块，只保留真正用到的部分。**不要把所有块都写进来**。

> 若工具函数较多，可以在 `utils/` 下再拆分文件（如 `utils/request.js`、`utils/login.js`），但**禁止把这些工具函数放到 `apis/` 下**——`apis/` 只能放 `mcp.json` 注册的原子接口。

### 1.1 必选：返回值工厂（每个 skill 都需要）

```javascript
// utils/util.js — 始终包含
function errorResult(msg) {
  return { isError: true, content: [{ type: 'text', text: msg }] }
}

function successResult(msg, structuredContent) {
  const result = { isError: false, content: [{ type: 'text', text: msg }] }
  if (structuredContent !== undefined) result.structuredContent = structuredContent
  return result
}

module.exports = { errorResult, successResult /* 按需追加其它导出 */ }
```

### 1.2 按需：云开发初始化（使用 `wx.cloud.*` 时才需要）

```javascript
let _cloudInited = false
function ensureCloudInit() {
  if (_cloudInited) return
  wx.cloud.init({ env: '{从 app.js 提取的实际 env ID}', traceUser: true })
  _cloudInited = true
}
```

### 1.3 按需：主包 storage 初始化迁移（仅当主包 app.js 有写 storage 默认值时才需要）

若主包 `app.js` 中存在 `wx.setStorageSync('key', defaultValue)` 初始化语句，需在分包内迁移，否则跳过此块：

```javascript
let _storageInited = false
function ensureStorageInit() {
  if (_storageInited) return
  // 从主包 app.js 扫描到的 setStorageSync 语句，按原样迁移到此处
  _storageInited = true
}
```

### 1.4 按需：HTTP 请求（使用 `wx.request` 时才需要）

鉴权方式**完全以主包 request 封装为准**——有些项目用 header token、有些用 cookie、有些用签名、有些无鉴权——生成时读主包 `utils/request.js` 确认后再写，不要套固定模式。

token 由 `ensureLogin()` 获取后保存在**模块级变量**中，`request` 函数从该变量读取附加到 header，不从 storage 读取。

```javascript
const BASE_URL = '{从主包提取的 baseUrl}'
let _token = ''  // 模块级变量，由 ensureLogin() 写入

function request(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      ...options,
      url: options.url.startsWith('http') ? options.url : BASE_URL + options.url,
      header: Object.assign(
        { '{鉴权 header 字段名}': _token },  // 按主包实际方式替换
        options.header
      ),
      success(res) {
        res.statusCode >= 200 && res.statusCode < 300
          ? resolve(res.data)
          : reject(new Error(`HTTP ${res.statusCode}`))
      },
      fail: reject
    })
  })
}
```

#### 登录鉴权（按需，接口需要登录态时）

> **何时需要**：若主包中该业务接口的 `wx.request` 携带了 token / session / cookie 等鉴权信息，则分包必须实现 `ensureLogin()`，并在每个需要鉴权的原子接口入口处 `await ensureLogin()`。

**实现规则**（完全以主包登录逻辑为准，不要套固定写法）：

- 分包**不依赖 storage 中的登录态**，每次冷启动都重新走一遍登录流程
- 登录流程与主包完全相同（`wx.login` 换 token）：**打开主包中的真实登录函数本体，逐字复刻**接口完整 URL（含 host 取自哪个 baseUrl 变量）、每个请求字段名、method、响应取值路径——禁止凭函数名/字符串/通用模式推断
- 登录成功后将 token 保存到**模块级变量**（如 `let _token = ''`），供同一进程内的后续请求复用；不写 storage
- 需防并发重复登录（多个接口同时调用 `ensureLogin` 时只发起一次登录请求）
- 关键节点打 `[ai-mode]` 前缀日志

> **使用方式**：在需要鉴权的原子接口文件入口处 `await ensureLogin()` 后再发起业务请求。

### 1.5 按需：接口侧 JSAPI 封装（仅接口侧白名单内）

按实际接口自行封装，参考主包实现。常见接口侧示例：`wx.getLocation` / `wx.getFuzzyLocation` / `wx.login` / `wx.checkSession` / `wx.authorize` / `wx.getPhoneNumber` / `wx.getRealtimePhoneNumber` / `wx.startFacialRecognitionVerify` / `wx.requestSubscribeMessage` / `wx.cloud.database`。支付、选择器、媒体采集和扫码等组件侧能力按 `references/JSAPI_WHITELIST.md §2` 生成。不要模板化复制——形式由主包实现决定。

### 1.6 按需：接口间数据传递

接口间数据传递有两种方式，**由业务逻辑决定用哪种，不要默认引入 storage 传递**：

- **直接通过 `inputSchema` 参数传递**：下游接口在 `mcp.json` 的 `inputSchema` 中声明所需字段，由小程序 AI 从上游 `structuredContent` 里提取后传入，分包内无需写任何 storage 代码——这是优先选项。
- **通过 `wx.setStorageSync` 传递**：仅当下游接口无法在 `inputSchema` 中描述依赖（例如需要静默传递大量中间态）时使用。key 命名格式 `skills_{skillName}_{dataName}`。

```javascript
// 仅在确认需要 storage 传递时才加入 utils/util.js
function setStepContext(key, value) { wx.setStorageSync(key, value) }
function getStepContext(key, defaultValue) { return wx.getStorageSync(key) || defaultValue }
function removeStepContext(key) { wx.removeStorageSync(key) }
```

---

## 二、原子接口模板

每个原子接口文件遵循以下骨架，内部逻辑完全由主包对应业务决定，不要套固定范式。

> ⚠️ **封装层强制复用**：网络请求**必须**通过 `require('../utils/request')` 的 `request()` 发起，禁止 API 文件中直接 `wx.request` 或自行拼 URL/header/query。API 文件只负责业务参数整理 + 响应归一化。
>
> ⚠️ **响应字段类型安全**：API 响应的数组字段调数组方法前加 `(x || [])` 或 `Array.isArray(x) ?` 保护，防 `TypeError` 崩溃。
>
> ⚠️ **响应状态码类型保护**：主包后端常返回字符串型状态码（如 PHP 接口的 `"ret_code":"1"`），不要写 `res.ret_code !== 1` 这种严格类型比较。生成代码时应显式归一化：`Number(res.ret_code) !== 1` 或 `String(res.ret_code) !== '1'`。

```javascript
// apis/{apiName}.js
const { errorResult, successResult } = require('../utils/util')
// 按需追加其它 utils 导入，如 require('../utils/request')

async function {apiName}(params = {}) {
  console.info('[ai-mode] {apiName} 入口, params=', JSON.stringify(params))
  try {
    // 1. 参数校验（仅校验真正必须的字段）
    // 2. 执行业务逻辑（网络请求 / JSAPI / storage 读写，完全对照主包）
    // 3. 整理返回值，返回 successResult
    return successResult('描述结果的一句话', { /* structuredContent */ })
  } catch (err) {
    console.error('[ai-mode] {apiName} 出错:', err.message)
    return errorResult(`操作失败: ${err.message}`)
  }
}

module.exports = {apiName}
```

> **生成原则**：
> - 业务逻辑完全以主包为准，不要根据模板臆造字段名、接口路径或 storage key。
> - 只校验真正影响业务的必填参数，不要过度防御。
> - 有需要传递数据给下游的，先考虑 `outputSchema` + 小程序 AI 传参；确实需要 storage 传递时再用。

### 2.1 按需：`apiCalls` 显式指定下一步接口

源业务流程本来就固定衔接（如"未登录 → 先登录"）时，在返回值顶层加 `apiCalls`，省掉模型推理这一跳。`name` 必须是当前 skill `mcp.json.apis[]` 里已声明的接口，`arguments` 与其 `inputSchema` 对齐。开放式场景不要用，交给模型判断。

```javascript
async function placeOrder({ skuId, count }) {
  const loggedIn = await checkUserLogin()
  if (!loggedIn) {
    return {
      isError: false,
      content: [{ type: 'text', text: '用户未登录' }],
      apiCalls: [{ name: 'login', arguments: {} }],   // 指示下一步调 login
    }
  }
  const order = await createOrder({ skuId, count })
  return {
    isError: false,
    content: [{ type: 'text', text: `订单已创建，订单号 ${order.id}` }],
    structuredContent: order,
  }
}
```

### 2.2 按需：隐私授权卡片

服务需要用户先同意协议才能用时，在原子接口内调 `wx.requestAgentPrivacyAuthorization` 弹平台授权卡片，同意后与小程序原有隐私授权链路对齐（之后 `wx.getPrivacySetting` 返回 `needAuthorization: false`）。

```javascript
async function loginByPhone() {
  const { authorized } = await wx.requestAgentPrivacyAuthorization({
    privacyAgreements: [
      { name: '用户服务协议', path: 'pages/protocol/user-service' },
      { name: '隐私政策', path: 'pages/protocol/privacy' },
    ],
  })
  if (!authorized) {
    return errorResult('隐私授权未通过')
  }
  // 授权通过后再走 wx.getPhoneNumber 等取号流程
}
```

> 数组顺序即协议展示顺序；`path` 为协议详情页路径（可带 query / hash），在小微中以半屏形式打开。
>
> **注意时机**：用户没有触发需要该权限的功能时，不得提前申请授权或收集个人信息。优先让用户先看到内容，真正要操作时再要授权。

---

## 三、index.js 注册模板

### 3.1 基础模式（无中间件）

```javascript
// skills/{skillName}/index.js

// 按 mcp.json 中 apis[].name 一一注册，三者必须完全一致：
// require 导入名 = registerAPI 第一参数 = mcp.json name
const {apiName1} = require('./apis/apiName1')
const {apiName2} = require('./apis/apiName2')

wx.modelContext.registerAPI('apiName1', apiName1)
wx.modelContext.registerAPI('apiName2', apiName2)
```

### 3.2 中间件模式（推荐用于需要统一登录态 / 上报 / 错误监听的场景）

Koa 式洋葱模型的中间件，每个原子接口都会执行一遍，可用于统一登录态、统一上报和错误监听等场景。

```javascript
// skills/{skillName}/index.js
const {apiName1} = require('./apis/{apiName1}')
const {apiName2} = require('./apis/{apiName2}')

const skill = wx.modelContext.createSkill('skills/{skillName}')

// 注册中间件（按需组合，执行顺序 = 注册顺序）
skill.use(async (ctx, next) => { // ← 中间件 1：鉴权
  console.info('[ai-mode] middleware: ensureLogin')
  await next()
})
skill.use(async (ctx, next) => { // ← 中间件 2：上报
  try {
    await next()
  } finally {
    console.info('[ai-mode] middleware: report', { name: ctx.name })
  }
})

// 注册原子接口（等同于 wx.modelContext.registerAPI；第二参数必须是 handler 函数）
skill.registerAPI('apiName1', apiName1)
skill.registerAPI('apiName2', apiName2)
```

**中间件 context 属性**：
- `ctx.name` — 原子接口名称
- `ctx.skillPath` — 中间件执行时的 skillPath
- `ctx.arguments` — 传递给原子接口的参数的**副本**，修改后不影响传递给原子接口的真实参数值

> **使用原则**：
> - `use` 注册的是公共逻辑函数，`registerAPI` 注册的是原子接口，两者职责不同：用了 `createSkill` 也必须 `registerAPI` 每个接口，否则接口注册不上。
> - 禁止使用 skill.use(require('./apis/...js')); **use 方法不能用来注册接口**
> - 中间件与「各接口内 `ensureLogin()`」**二选一，不要混用**。

---

## 四、mcp.json 模板

```json
{
  "apis": [
    {
      "name": "{apiName}",
      "description": "{完整描述接口行为，含内部操作与前置依赖}",
      "_meta": { "ui": { "pagePath": "/pages/{page}/detail" } },
      "inputSchema": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
          "{param}": { "type": "string", "description": "{参数含义}" }
        },
        "required": ["{param}"]
      },
      "outputSchema": {
        "type": "object",
        "properties": {}
      }
    }
  ]
}
```

> `outputSchema` **建议填写**：接口返回有明确字段结构的 `structuredContent`，或使用 `format: "page-link"` 时应声明；只返回文本且不需要结构化契约时可省略。声明后须与实际 `structuredContent` 一致。

**多模态入参（接收用户上传图片）**：当接口需要图片时，对应字段类型为 `string` 并加 `"format": "image"`，运行时填本地图片路径；小程序 AI 输入框据此识别为多模态字段并引导用户上传。

```json
{
  "name": "editPhoto",
  "description": "帮用户 P 图",
  "inputSchema": {
    "type": "object",
    "properties": {
      "imagePath": { "type": "string", "format": "image", "description": "本地图片路径" },
      "query":     { "type": "string", "description": "用户的 P 图需求" }
    },
    "required": ["imagePath", "query"]
  }
}
```

> `components[]` 仅生成原子组件时才有（规则见 `SKILL.md` D.3）；`components[].path` 必须与对应接口的 `_meta.ui.componentPath` 字符串完全相等，同基路径 `.js` / `.json` / `.wxml` / `.wxss` 文件齐全。**`relatedPage` 为必填**（卡片右上角"进入小程序"入口，缺失会被平台强校验拦下）；`permissions["scope.dynamic"]`（实时动态能力）与 `expirable` + `expiredText`（卡片过期）按需，规则见 `SKILL.md` D.3 / D.4、`references/JSAPI_WHITELIST.md` §2.1 与 `references/COMPONENT_TEMPLATES.md` "卡片过期"节。进小程序见下方 "handoff 接力页"（`_meta.ui.pagePath` + 返回值 `handoff`）。

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
      "permissions": { "scope.dynamic": { "desc": "卡片需按分钟刷新实时天气" } },
      "expirable": true,
      "expiredText": "该时段已结束"
    }
  ]
}
```

> 运行时给关联页附加 query（`setRelatedPage`）的组件代码见 `references/COMPONENT_TEMPLATES.md` "关联小程序页面"节。

### 文本混排链接（`format: "page-link"`，按需）

接口返回的数据里带小程序页面路径、且希望模型在**回复正文中间**给出可点蓝链时用。只改两处：`outputSchema` 标记字段 + `structuredContent` 返回真实路径，**不要在 `content` 里手写 Markdown 超链接**。

**① `outputSchema` 标记**（叶子字段必须是 `string`；`x-link-text-field` 指向**同级**的描述字段）：

```json
{
  "name": "searchGoods",
  "description": "按关键词搜索可购买的商品，返回名称、价格和详情页路径",
  "inputSchema": {
    "type": "object",
    "properties": { "keyword": { "type": "string", "description": "搜索关键词，如美式、拿铁" } },
    "required": ["keyword"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "goodsId": { "type": "number" },
            "name": { "type": "string" },
            "price": { "type": "number" },
            "pagePath": {
              "type": "string",
              "format": "page-link",
              "x-link-text-field": "name"
            }
          }
        }
      },
      "total": { "type": "number" }
    }
  }
}
```

**② 接口返回真实路径**：

```js
return {
  isError: false,
  content: [{ type: 'text', text: '已为您找到两款咖啡' }],
  structuredContent: {
    items: [
      { goodsId: 1, name: '冰美式', price: 18, pagePath: 'pages/goods/detail?id=1' },
      { goodsId: 2, name: '拿铁', price: 22, pagePath: '/packageDetail/pages/sku-picker?drinkId=289' },
    ],
    total: 2,
  },
}
```

约束：只认 `type: object` + `properties` 与 `type: array` + `items` 这两种结构（`oneOf` / `anyOf` / `$ref` 不展开）；字段名任意，**以 `format` 为准**；`format` 必须精确写成 `page-link`（不是 `pagelink` / `pageLink`）；填页面路径（可带 query / hash），不要填 HTTPS 链接；空字符串 / 缺字段会跳过，相同 path 去重，单次结果最多抽 20 条；`isError: true` 时整个 `structuredContent` 被忽略、不抽链接。单对象场景也可以直接标在根对象上（如订单详情的 `detailPath`）。

> 计算 `mcp.json` 长度时会去掉所有 `outputSchema`，所以加 page-link 标记一般不额外占用字节限额（见 6.3）。

### handoff 接力页（进小程序的主要方式，见 `SKILL.md` D.6）

默认只返回文本 + 小程序卡片，用户点卡片后由平台 handoff 进接力页。给"执行完停下等用户确认"类接口配 `pagePath` 并在返回值加 `handoff`。

**① `mcp.json`**：接口 `_meta.ui` 加 `pagePath`（接力页 path，不含 query）：

```json
{
  "apis": [
    {
      "name": "queryDrugUsage",
      "_meta": {
        "ui": {
          "pagePath": "/pages/drug/detail"
        }
      }
    }
  ]
}
```

**② 原子接口返回值**：顶层（与 `content` / `structuredContent` 同级）加 `handoff`，**兼容对象（立即模式）与函数（延迟模式）两种形态**：

```js
async function queryDrugUsage({ name }) {
  const drug = await fetchDrug(name)
  return {
    isError: false,
    content: [{ type: 'text', text: `已查询到${drug.name}用法用量` }],
    structuredContent: drug,
    // 函数模式（延迟）：入参为对象，data.result = 模型按用户意图过滤后的完整 result
    handoff: ({ result }) => ({
      query: `drugId=${encodeURIComponent(result.structuredContent.drugId)}`,  // string，宜短
      payload: result.structuredContent,                                       // 可选：接力页首屏加速
    }),
    // —— 或者无需模型筛选时，直接用对象（立即模式，链路更短、更快）：
    // handoff: { query: `drugId=${drug.drugId}`, payload: drug },
  }
}
```

> 形态选择：无需模型改动 result → 用**对象**（立即模式，更快）；需要用模型修改后的 result 拼 query/payload → 用**函数**（延迟模式，入参 `{ result }`，`result` 为模型修改后的完整 result）。
>
> **字段只有三个**：`query`（string，页面 query 字符串，如 `'drugId=xxx'`、`'orderId=1&spec=large'`，原样注入 `onLoad(query)` 与 `wx.onAgentHandoff` 回调；含特殊字符时自行 `encodeURIComponent`，页面侧对应 `decodeURIComponent`）、`payload`（接力页首屏加速数据）、`path`（可选，动态指定页面路径，覆盖 `mcp.json` 里固定的 `pagePath`）

**③ 主包 `app.js`**：`onLaunch` 内注册（须早于 handoff 触发的 `onBeforeAppRoute`）：

```js
App({
  onLaunch() {
    wx.onAgentHandoff(({ pageId, path, query, payload }) => {
      this.globalData.agentHandoffs = this.globalData.agentHandoffs || {}
      this.globalData.agentHandoffs[pageId] = { path, query, payload }
    })
  },
})
```

> 回调参数：`pageId`（目标页实例 ID，用于按页投递 payload）/ `path`（平台实际打开的 path，不含 query）/ `query`（**string**，页面 query 字符串，同 `handoff.query`）/ `payload?`。仅 handoff 场景触发，普通打开小程序不触发；`wx.offAgentHandoff()` 取消监听。

**④ 接力业务页**：`onLoad(query)` 消费——`query` 为 **string**（与 `handoff.query` 一致），按页面原有方式解析 query 字符串；`payload` 有则先 `setData` 加速首屏：

```js
Page({
  onLoad(query) {
    const handoffs = getApp().globalData.agentHandoffs || {}
    const handoff = handoffs[this.getPageId()]
    delete handoffs[this.getPageId()]

    if (handoff && handoff.payload) this.setData({ drug: handoff.payload })

    const params = parseQuery(query) // 如 { drugId: 'xxx' }
    if (params.drugId) this.loadDrugDetail(params.drugId).then(drug => this.setData({ drug }))
  },
})
```

> `wx.openAgent` / `wx.navigateBackAgent` 当前会失败，接力页勿依赖"打开/返回 Agent 对话"。

---

## 五、SKILL.md 模板

> **定位**：SKILL.md 是技能的业务编排与路由说明，目标 = 让调度方判断需求是否属于本技能、了解跨接口的流程与前置条件，并在多 skill 共存时不抢别人的活。

**写入内容清单**（按下表 5 节顺序排列）：

| # | 章节 | 写什么 | 不写什么 | 何时省略 |
|---|------|--------|----------|---------|
| 1 | 能力域定位 | 一句话锚点，位于 `# 标题` 下首行 | 多段落叙事、emoji、口号 | 不可省略 |
| 2 | 触发场景 | 3~6 条**用户原话 few-shot**，每条是一句真实用户口吻的自然语言（口语、片段、含俚语都行），覆盖不同表达方式 | 关键词清单；技术术语；照抄 `mcp.json.apis[].description` | 不可省略 |
| 3 | 不适用范围 | 反例短句（"xx 诉求 → 不在本技能范围 / 由 yy 技能处理"） | 自我否定式废话 | 项目内无易混淆兄弟 skill 时整节省略 |
| 4 | 前置条件 | 影响是否可路由的硬约束（已登录 / 授权 / 区域 / 账号资质） | 实现细节、token 来源、storage 初始化等技术内容 | 无前置条件时整节省略，**不要写"无"占行** |
| 5 | 使用顺序 | 业务流程、已注册方法名、方法前置条件、上下游依赖和跨接口规则 | 参数 schema、返回字段、storage key、实现细节 | 各能力相互独立时整节省略 |

**硬性约束**（通篇生效，命中即重写）：

- 使用顺序中出现的方法名必须与 `mcp.json.apis[].name` 逐字一致（含大小写）
- 不出现 `inputSchema` / `outputSchema` / 参数表 / 返回值表 / `_meta.ui.componentPath` / 组件路径 / JSON Schema 片段（接口契约只在 `mcp.json` 单一来源维护）
- 不出现 storage key 清单、字段映射或实现细节
- 不写安装 / CLI / 部署 / 如何使用本技能 等运维文档

```markdown
# {技能业务名，中文，例：商品检索与下单}

{一句话能力域定位。例：基于商品库进行关键词检索、查看详情、加入购物车并完成下单的能力集合。}

## 触发场景
用户原话举例（路由命中本技能）：
- "帮我搜下有没有那种轻便的{品类}"
- "我想买{品牌}的，有什么推荐"
- "把刚才那个加到购物车"
- "结一下账吧"
- ...（3~6 条；用真实用户口吻，覆盖不同表达方式；不要写关键词清单或技术术语）

## 不适用范围
- {反例 1，例：售后退款相关诉求 → 不在本技能范围}
- {反例 2，例：会员积分查询 → 由会员技能处理}
- ...（项目内无易混淆兄弟 skill 时整节省略）

## 前置条件
- {影响是否可路由的硬约束，例：需用户已登录 / 需定位授权 / 仅 xx 城市可用}
- ...（无前置条件时整节省略；不要写"无"占行）

## 使用顺序
- `searchProducts`：用户给出商品关键词时调用。
- 用户选定商品后调用 `getProductDetail`；取得具体商品后才能调用 `addToCart`。
- `addToCart` 成功后才可调用 `createOrder`；未成功时不得向用户宣称已加入购物车。
- ...（方法名必须与 mcp.json 完全一致；各能力相互独立时整节省略）
```

---

## 六、app.json + project.config.json 配置

```json
{
  "lazyCodeLoading": "requiredComponents",
  "agent": {
    "skills": [{ "name": "...", "description": "...", "path": "skills/..." }],
    "instruction": "AGENTS.md",
    "pageMetadata": "page-meta.json"
  },
  "subPackages": [{
    "root": "skills",
    "independent": true,
    "pages": []
  }]
}
```

> ⚠️ **`lazyCodeLoading` 由开发者在使用 skill 前自行添加，generate 不要写入此字段**（只用于展示完整目标形态）。阶段 1 扫描时若 `app.json` 顶层缺该字段，按阻断规则 B 终止流程并提示用户去补；不要"代为补全"或"忽略继续"。本次 generate 的写入范围只有 `agent` 和 `subPackages` 两块。

> **多 skill 共用一个独立分包**：`subPackages` 里 `root: "skills"` 指**外层目录**，多个 skill（`skills/foo/`、`skills/bar/`）整体作为**同一个**独立分包。新增 skill 时只在 `agent.skills[]` 数组里追加一项 `{ name, description, path: "skills/<新>" }`，**不要**为每个 skill 再加一条 `subPackages` 条目。反过来不成立：**一个 SKILL 不能拆到多个分包**；单包 2M 不够时用异步分包机制从另一个分包引入代码。

> `agent.skills[]` 每项 `name` / `description` / `path` 三个字段都必填，数量上限见 6.3。`instruction` 与 `pageMetadata` 均为可选，不用时整个字段不要写。

### 6.1 全局提示词 `AGENTS.md`（可选，上限见 6.3）

`agent.instruction` 指向一个 Markdown 文件（相对项目根的路径），用来交代**跨 skill 的全局信息**：整体服务范围、背景知识、行为逻辑、回答风格，以及多个 skill 之间的关系与选择依据（帮模型选对 skill）。单个 skill 内部的路由说明写在各自的 `SKILL.md`，不要在这里重复。

```markdown
<!-- AGENTS.md -->
# {小程序名} 智能助手

{一句话说明这个小程序提供什么服务、覆盖哪些场景、不做什么。}

## 技能选择

- 用户想{检索/下单/查看商品} → {shoppingSkill}
- 用户想{查订单/退换货} → {orderSkill}
- 两者都不匹配的知识类提问 → 走知识库兜底

## 回答风格

- {例：价格一律带单位，时间用"今天 15:30"这类口语表述}
```

### 6.2 服务直达 `page-meta.json`（可选，上限见 6.3）

`agent.pageMetadata` 指向页面元数据文件。当用户意图**没有对应的原子接口**时，平台据此回复"账号卡片"引导进页面（场景值 1435 / 1436）。`query` 是标准 object 型 JSON Schema。

```json
{
  "pages": [
    {
      "path": "pages/home/home",
      "name": "首页",
      "description": "展示最新的内容和推荐"
    },
    {
      "path": "pages/detail/detail",
      "name": "商品详情",
      "description": "展示特定商品的信息",
      "query": {
        "type": "object",
        "properties": {
          "id": { "type": "string", "description": "商品的唯一标识符" }
        },
        "required": ["id"]
      }
    }
  ]
}
```

> 接口已能返回具体页面路径、只想在回复正文里给入口时，用 `outputSchema` 的 `format: "page-link"`（见第四节），不要为同一结果再配 `pageMetadata`。

### 6.3 体积与数量上限

| 对象 | 上限 |
|------|------|
| `mcp.json` | 24000 字节（去掉所有 `outputSchema` 及空格换行后计算） |
| 每个 skill 的 `SKILL.md` | 16000 字节（单文件，不支持引用其它 md） |
| `AGENTS.md` | 10000 字节 |
| `page-meta.json` | 8000 字节 |
| `agent.skills[]` 条目数 | 30 |
| 单接口 `content` / `structuredContent` / `_meta` | 各 200 KB |

`project.config.json` 确保 `packOptions.include` 含 `{ "type": "folder", "value": "skills" }`。
