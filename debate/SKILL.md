---
name: debate
description: >
  GAN-style adversarial analysis skill that iteratively refines technical proposals,
  code reviews, and product requirements through two fully independent agents:
  Agent A (proposer) and Agent B (critic). Use when the user wants deep multi-angle
  analysis of a technical solution, code change, or product requirement. Triggers on:
  "/debate [content]", "用对抗分析", "帮我做对抗评审", "从正反两面分析", or any request
  for adversarial review, debate-style analysis, or GAN-style critique.
  Supports flags: --verbose (show full debate rounds), --rounds N where N is max rounds (default 5).
---

# Debate Skill

Two fully independent agents debate a proposal through iterative rounds until convergence,
then a neutral Synthesizer produces the final output.

## Architecture

```
User Input → Auto-detect domain → Agent A (propose) → Agent B (critique)
→ Orchestrator (score + converge?) → [loop] → Synthesizer → Final Output
```

- **Agent A** (Proposer): Knows only the original input + previous version + B's last criticism
- **Agent B** (Critic): Knows only the original input + current version + its own last criticism
- **Agents are fully context-isolated** — neither knows the other exists
- **Synthesizer**: Sees the full debate history, produces neutral final output

## Step 1 — Parse Arguments

Extract from user input:
- `--verbose` → show all round details (default: false)
- `--rounds N` → max rounds (default: 5)
- remaining text → `{subject}`

## Step 2 — Auto-Detect Domain

Analyze `{subject}` and select one domain. See [references/domains.md](references/domains.md) for role definitions and focus areas per domain.

| Domain | Detect when |
|--------|-------------|
| `tech` | architecture, system design, API, database, algorithm, infra |
| `cr` | code snippet, diff, PR description, function/class review |
| `product` | requirements, user story, feature spec, PRD |

## Step 3 — Iterative Debate Loop

Run rounds 1 → max_rounds. Each round:

1. **Agent A** (independent context) — see [references/prompts.md § Agent A](references/prompts.md)
   - Round 1: Generate initial proposal from `{subject}`
   - Round N: Respond to B's criticism + output improved full version

2. **Agent B** (independent context) — see [references/prompts.md § Agent B](references/prompts.md)
   - Critique current version; reference own last criticism to avoid repetition

3. **Orchestrator scoring** (inline logic, not a separate agent):
   - Parse B's output for 🔴/🟡/🟢 counts
   - **Converge early** if: 🔴 == 0 AND 🟡 ≤ 1
   - **Force converge** if: round == max_rounds
   - Otherwise: pass context to next round

4. **Print round status panel** (always visible, even without --verbose):
   ```
   ━━━ Round N/max ━━━  🔴×N  🟡×N  🟢×N  →  [继续迭代 | 收敛 ✓]
   ```

## Step 4 — Synthesizer

After convergence, run Synthesizer with full debate history.
See [references/prompts.md § Synthesizer](references/prompts.md).

## Step 5 — Output

**Default (精简) mode:**
```
━━━ 对抗分析完成：共 N 轮 ━━━

## 最终方案
[complete, ready-to-use content]

## 关键决策
| 议题 | 决策 | 依据 |
|------|------|------|

## 遗留风险
- ...
```

**--verbose mode** (prepend before final output):
```
## 对抗过程

### Round N
**Agent A 方案：**
[full proposal]

**Agent B 批评：**
[full criticism with 🔴🟡🟢 breakdown]
```
