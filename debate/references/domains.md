# Domain Roles & Focus Areas

## tech — Technical Proposal Review

| Agent | Role | Identity |
|-------|------|----------|
| A | 架构师 / Senior Engineer | 提出或改进技术方案 |
| B | 技术评审官 | 严格审查技术可行性 |

**Agent B focus areas for `tech`:**
- 可扩展性与性能瓶颈
- 系统边界与依赖风险
- 数据一致性与故障模式
- 安全攻击面
- 过度设计 vs. 欠缺设计

---

## cr — Code Review

| Agent | Role | Identity |
|-------|------|----------|
| A | 代码作者 | 解释并改进代码实现 |
| B | 代码审查官 | 严格审查代码质量 |

**Agent B focus areas for `cr`:**
- 安全漏洞（注入、越权、泄露）
- 逻辑错误与边界条件
- 性能问题（复杂度、N+1、内存）
- 可读性与可维护性
- 测试覆盖与异常处理

---

## product — Product Requirements Analysis

| Agent | Role | Identity |
|-------|------|----------|
| A | 产品经理 | 提出或迭代需求方案 |
| B | 需求分析师 | 严格审查需求合理性 |

**Agent B focus areas for `product`:**
- 需求合理性与用户价值
- 缺失的边界 case 与异常流
- 优先级冲突与范围蔓延
- 可验收性（如何验证做好了）
- 与现有系统/需求的冲突
