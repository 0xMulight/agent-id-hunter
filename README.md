# Agent ID Hunter

**Binance Agent ID 活动追踪 + AI Agent Mint/打新助手（社区开源 Skill）。**

先发现官方活动和新项目，再检查是否真的要求持有 .ai、是否仍开放 Mint、合约和钱包资格、交易资金和 Gas。安装币安官方 Agentic Wallet Skill 后，可进一步由 AI 发起交易预览，并在你看过风险、明确确认后通过官方钱包执行。**Hunter 自己的 Python 脚本只读，不会偷偷签名、转账或交易；不需要预设任何人的 Agent ID。**

> 社区项目，非 Binance、SPACE ID、BNB Chain、Four.meme 官方产品。活动未官宣时，不预测资格或奖励。

## 现在能做什么

- **官方线索扫描**：读取白名单网站的公开页面，发现新增的 Agent ID/Agentic Wallet 相关链接，保存本地结果，标记抓取失败。
- **持有人任务检查**：只在官方活动卡明确要求 .ai 时，提示核对 .ai 所有权；仅填写名称绝不代表持有权已确认。
- **报名防漏**：对照活动规则检查报名、绑定钱包、截图/链接、有效计数、截止与领奖步骤。
- **已开启 GitHub 定时提醒**：本仓库每 6 小时扫描一次官方线索；发现新的强相关 Agent ID 链接，自动尝试建立待核验 Issue。
- **AI Mint 预检**：检查开放状态、合约地址/调用数据、.ai 门槛、费用与预算，生成 BLOCKED / NEEDS_REVIEW / READY_FOR_PREVIEW 结论。
- **Agentic Wallet 结合**：可运行只读状态查询；需要真实操作时使用币安官方 Wallet Skill 的合约预览，必须由用户确认该笔具体交易才执行。

## 快速使用

在支持 Agent Skills 的工具中安装：

```bash
npx skills add 0xMulight/agent-id-hunter
```

让 AI 读取 SKILL.md，然后说：

> 查一下币安最近有哪些正式公布的 Agent ID 活动。请先确认是否真的需要持有 .ai，给我官方链接、报名/钱包/计数/截止/领奖条件。没有依据的地方写“待核验”，别替我交易。

无需填写钱包也能扫描：

```bash
python scripts/scout.py scan
```

输出保存在忽略提交的 `data/` 目录中。扫码只读，不等于全网实时搜索；动态站点和 X 首发内容可能漏掉。

### 用 AI 帮你打新 / Mint

不要把截图里的旧项目当成还在开放的 Mint。把新项目官网链接交给 AI，先让它核实官方规则、合约和成本，再考虑是否使用钱包。

**先看操作手册：[AI Mint 全流程](references/mint-playbook.md)** · **[直接复制给 Agent 的指令](examples/ASK_AGENT.md)**。

币安官方钱包 Skill（Hunter 不会替你安装或配对钱包）：

```bash
npx skills add binance/binance-skills-hub/skills/binance-web3/binance-agentic-wallet
```

检查钱包，只执行只读请求：

```bash
python scripts/wallet_probe.py status
python scripts/wallet_probe.py settings
python scripts/wallet_probe.py address
```

Mint 参数预检（先复制示例活动卡，再补入真实官方数据）：

```bash
python scripts/mint_preflight.py --plan examples/mint-plan.example.json
```

示例中的合约地址和活动信息故意留空，脚本应返回 NEEDS_REVIEW。**这是防止用户把演示参数拿去付款。** 真正钱包 execute 的命令不在 Hunter 的 Python 脚本里，而由官方 Wallet Skill 在逐笔核对并获得明确确认后执行。


### 活动资格核对

编辑一份活动卡（参见 `examples/activity.example.json`），**必须人工确认并填写官方规则**，然后运行：

```bash
python scripts/checklist.py --activity examples/activity.example.json
```

可选个人资料 `data/profile.json`，例如 `{"agent_id":"yourname.ai"}`。不填也可运行；填写了也必须核验真正持有者/活动绑定地址。

```bash
python scripts/checklist.py --activity examples/activity.example.json --profile data/profile.json
```

## GitHub 定时监控（已在此仓库启用）

本仓库已启用 Actions，每 6 小时从白名单公开网页获取 Agent ID 相关候选链接；发现新直接线索时自动尝试建立待核验 Issue。可前往 [Actions](https://github.com/0xMulight/agent-id-hunter/actions/workflows/scout.yml) 查看运行日志或手动运行。

已完成首次扫描基线；用 Actions cache 保存本次状态。首次基线不把既有历史链接当新活动提醒。**定时任务只抓公开网页，不搜索 X/币安 App 内全部活动，不会连接钱包，不会自动交易，也不是秒级监控。** Issue 是仓库记录，是否收到通知取决于你的 GitHub 通知设置。


## 能力边界

扫描发现的是“待核验线索”，不是正式活动认定；官方页面可能反爬、需要登录、动态加载或移动到其他网址。本仓库的 Python 脚本永远只做查询和预检；结合已安装且配对的 Binance 官方 Agentic Wallet Skill 时，AI 可以发起外部合约预览，并在用户明确确认后按官方两步流程执行。不保证任何项目能被 Agentic Wallet 调用。不要把助记词、私钥、Binance UID 或敏感凭证写进配置。

代码使用 Python 3.10+ 标准库。执行 `python -m unittest discover -s tests -v` 可运行测试。

作者：[@0xMulight](https://github.com/0xMulight) · MIT
