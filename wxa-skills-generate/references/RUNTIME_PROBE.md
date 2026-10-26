# 运行时探测（Automator Probe）

> 通过 [`miniprogram-automator`](https://developers.weixin.qq.com/miniprogram/dev/devtools/auto/automator.html) 启动开发者工具，在**源项目**上触发请求、捕获真实 URL 与响应。定位是**验证 / 补齐静态分析**（而非替代）。只操作源项目，与 `skills/` 分包和 agent 模式无关。

## 何时使用

简单项目默认不跑 probe，静态分析能定的直接定稿。仅两种情况触发：

1. **值是运行时动态下发**：URL / header / 签名参数在源码里是运行时拼接（如 `baseUrl` 由 `getApp().globalData` 动态返回、签名由运行时函数计算），静态读不出真实值。此时用 `kind: "evaluate"` trigger 在运行时直接取值，或 `kind: "request"` trigger 直接发请求捕获真实 URL + 参数——run 中的 `request.url` / `request.header` / `request.data` 即为真实运行时值
2. **响应结构无法从源码消费点确定**：接口返回大量字段但页面只用一部分，且消费点看不出字段层级 / 嵌套结构

> **敏感接口（注销/删除/解绑/解散/踢出等不可逆操作）一律不探测**——probe 在源项目真实环境触发交互，误触发即产生不可逆后果。`probe-lib.mjs` 内置拦截：plan 项标 `"destructive": true` 或 api_name 命中关键词时跳过（`status=skipped_destructive`，不导航、不触发交互）。确需探测某个敏感接口，由用户明确要求并在该 plan 项写 `"confirmDestructive": true` 单独解锁，不批量放行。

## 技术原理

通过 `miniProgram.evaluate` 在运行时覆写 `wx.request`，在 `success`/`fail` 回调中记录请求参数 + 响应数据到全局变量。原始请求正常发出，业务不受影响。覆写跨页面持久（逻辑层单一 JS Realm、`wx` 全局共享），因此三类请求都能捕获：

1. **点击/输入触发**：`trigger` 用 `tap`/`input`/`longpress`/`callMethod`
2. **进页面自动发**（`onLoad`/`onShow`）：`trigger` 留空，仅靠跳转捕获
3. **非 UI 直发 / 串联中间请求**：`trigger` 用 `request`（直接以已知 url/参数调 `wx.request`）或 `evaluate`（执行任意取数函数体）

> 例外：`app.js` `onLaunch` 阶段在 automator 接管前已执行，其请求需用 `request`/`evaluate` 重放。

## 环境要求

| 项 | 要求 |
|---|------|
| 微信开发者工具 | 已安装、已登录、「设置 → 安全设置 → 服务端口」已开启（服务端口是 IDE HTTP 服务） |
| `miniprogram-automator` | 安装到 skill 的 `scripts/` 目录（禁止装到源项目） |
| CLI 路径 | 环境变量 `WX_CLI_PATH` 或平台默认路径；不存在则通过 `--cli-path` 指定 |
| automator 端口 | `cli auto --auto-port` 拉起的 WebSocket 端口（默认 `9420`），与服务端口不同。`probe.mjs --mode auto` 自动拉起并检查端口 |

## 执行

plan 由 probe subagent 写（从 `analysis-apis.md` 取请求构造，每个触发条件的 api 一条；同 URL 多 api 时 trigger 要可区分；指令与读取边界见 `SUBAGENT_PROTOCOL.md` §3.3）。只探需要的 api，不探源项目其余无关请求；一次把要探的都列进 plan 批量跑，不反复启动开发者工具。

```bash
node scripts/probe.mjs --project <源项目> --plan <plan.json>
```

- 脚本自动完成 `cli open` → `cli auto --auto-port 9420 --project` → 端口检查 → `probe --mode connect`，失败自动重试 3 轮
- `cli auto` 带 `--project <源项目>`；只跑 `cli auto --auto-port 9420` 常报 websocket 错误且 9420 不会开
- 每次执行落盘 `<project>/.ai-mode-skills/probe/<run-id>.json`（runId 为 UTC 时间戳，写在 JSON 根字段）；多轮重试积累多个 run 文件，不覆盖、不手写
- **trigger 偏好**：优先 `tap`/`input`/`callMethod` 走真实 UI；进页自动发的留空。`evaluate` 里调 `getApp().request()` 常因 `getApp()` 未就绪报错——非 UI 直发优先 `kind: request`

## plan.json 格式

```json
[
  {
    "api_name": "searchMovies",
    "target_page": "/pages/movie/list",
    "matchUrlIncludes": "/api/movie/search",
    "captureWaitMs": 6000,
    "trigger": [
      { "kind": "input", "selector": "#search-input", "value": "阿凡达" },
      { "kind": "tap", "selector": "#search-btn", "delayAfterMs": 200 }
    ],
    "preSteps": [
      { "target_page": "/pages/login/index", "trigger": [{ "kind": "tap", "selector": "#login-btn" }], "waitMs": 3000 }
    ]
  },
  {
    "api_name": "submitOrder",
    "target_page": "/pages/cart/index",
    "matchUrlIncludes": ["/api/stock/check", "/api/order/create", "/api/pay/prepay"],
    "trigger": [
      { "kind": "request", "options": { "url": "https://shop.example.com/api/stock/check", "method": "POST", "data": { "skuId": 1 } } },
      { "kind": "evaluate", "code": "getCurrentPages().pop().submit()" }
    ]
  },
  {
    "api_name": "deleteAccount",
    "target_page": "/pages/settings/index",
    "matchUrlIncludes": "/api/account/delete",
    "trigger": [],
    "destructive": true,
    "destructiveReason": "注销账号不可逆，probe 跳过不触发",
    "confirmDestructive": false
  }
]
```

| 字段 | 说明 |
|------|------|
| `api_name` | 接口标识（与 `analysis-apis.md` / `mcp.json` 的接口 name 一致） |
| `target_page` | 目标页面路径 |
| `matchUrlIncludes` | URL 匹配关键词。**string**=单请求；**数组**=「一个能力 = 多请求」，按序逐个匹配 |
| `captureWaitMs` | 等待超时，默认 10000ms |
| `trigger` | 触发操作（可为空数组=纯靠进页面自动发请求）：`tap` / `longpress` / `input` / `callMethod` / `wait` / **`request`**（`options` 为 wx.request 参数，非 UI 直发） / **`evaluate`**（`code` 为运行时函数体字符串） |
| `preSteps` | 前置步骤（如登录），含 `target_page` / `trigger` / `waitMs` |
| `destructive` | 可选，`true`=敏感接口（probe 跳过）/ `false`=判定非敏感（即使 api_name 命中关键词也放行）/ 缺省=脚本按 `api_name` 关键词初筛兜底 |
| `destructiveReason` | 可选，`destructive: true` 时附一句话原因 |
| `confirmDestructive` | 可选，`true`=用户明确要求 probe 该敏感接口（单独解锁，禁止批量放行） |

## result 关键字段

| 字段 | 说明 |
|------|------|
| `status` | `ok` / `partial`（多请求部分命中） / `no_request` / `url_unmatched` / `error` / `skipped_destructive` |
| `request` / `response` | 单请求结果（`matchUrlIncludes` 为 string 时） |
| `requests` | 多请求有序结果数组 `[{ matchUrlIncludes, request, response, matched }]`（`matchUrlIncludes` 为数组时） |
| `extras` | 未匹配关键词的其余捕获请求 |

常见失败：CLI 找不到 → 用 `--cli-path` 指定；端口被占但协议不响应 → `cli auto --project <源项目> --auto-port 9420` 重新拉起；登录失效 → `preSteps` 等待扫码，超时标 `auth_required`；接口无响应 → `no_request`；URL 不匹配 → `url_unmatched`（run 里列出所有捕获的请求，据此修 plan 再跑）。

## 结果怎么用

读成功 run（用 `jq` 按 `api_name` 抽取，不整文件 read；大数组只保留 `[0]` 看 item 形状），回填到 `analysis-apis.md` 对应接口的响应节：真实 URL / header / data 回填请求构造，响应字段结构回填响应节并标 `sampleSource: probe:<run-id>`。写入的仅为字段路径 / 类型摘要，不拷贝全量 `response.data`。

```bash
jq '.results[] | select(.api_name=="<api>") | .response.data | walk(if type=="array" then .[:1] else . end)' probe/<run-id>.json
```

probe 跑不了的（环境不可用 / 多轮重试仍失败）：静态结果照常使用，响应节标 `sampleSource: static-source`，生成的 `apis/<name>.js` 顶部注释 `[ai-mode:static]`，交棒时向用户声明响应未经真机验证。probe run 文件由 `probe.mjs` 写，agent 不手写、不伪造。
