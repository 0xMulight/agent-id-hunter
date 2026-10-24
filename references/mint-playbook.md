# AI Mint / 打新：Binance Agentic Wallet 操作指南

Agent ID Hunter 的作用是把 **发现活动 → 核实规则 → 钱包预检 → 合约预览 → 人工确认 → 交易核验** 连起来。只装 Hunter 不会获取钱包签名能力；要使用 Binance 官方 Agentic Wallet Skill 并在自己的 Binance App 配对。

官方参考：
- https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/SKILL.md
- https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/references/external-sign.md
- https://developers.binance.com/en/docs/products/agentic-wallet/welcome

## 一条项目链接开始（推荐）

不用先填一大堆 JSON。用户把项目官网链接交给 AI，AI 可以用本地纯只读命令初始化待核验草稿：

    python scripts/quickstart.py --url https://example.com/mint --budget-bnb 0.02

然后根据真实官网与合约信息补全 `data/mint-my-plan.json`，再执行：

    python scripts/mint_preflight.py --plan data/mint-my-plan.json

**请勿把 0 wei 当成免费 Mint 的默认值。** 缺少真实价格、付款币种、合约函数或 Gas 报价时只能等待补充。用户自己输入的 Gas 预算不是钱包的实际报价；需要通过官方 preview 获取链上模拟和安全结果。

## 1. 三种使用模式

| 模式 | 任务 | 需要钱包 |
| --- | --- | --- |
| SCOUT | 找活动、新 Mint、官方消息、有效时间 | 否 |
| PREPARE | 查真实 Mint 合约、资金需求、.ai 资格，模拟前检查 | 有钱包更好，但可以无钱包研究 |
| EXECUTE | 在真实钱包 preview 之后，由用户明确批准具体交易才执行 | 必须是已配对的 Binance Agentic Wallet |

GitHub Actions **只能扫描公开活动**。它不会连接任何个人交易钱包、签名或自动抢 Mint。

## 2. Mint 前先问清楚

1. 核对网站是否真正为项目官网，是否仍开放 Mint；截图、KOL 转发不能代替原始官方规则。
2. 核对身份：需要 Binance/SPACE ID 的 .ai 吗？是否只需要其他 AI Agent 身份？是否需要报名/白名单/快照/指定钱包？
3. 核对真实合约地址、链、ABI、data、付款币种、合约函数、数量、最大成本和手续费；**不要把转 BNB、USDT approve、DEX swap 当成通用 Mint**。
4. 运行下面的纯本地预检脚本，用官方数据填写样例，不得凭空补数字：

    python scripts/mint_preflight.py --plan examples/mint-plan.example.json

返回 BLOCKED 或 NEEDS_REVIEW 则继续研究，不签名；READY_FOR_PREVIEW 也**不是**“安全”或“允许执行”。
5. 安装官方 Binance Wallet Skill：

    npx skills add binance/binance-skills-hub/skills/binance-web3/binance-agentic-wallet

配对钱包只能在真实 Binance App 内走官方认证流程。**不需要将私钥、助记词复制给 AI。**
6. 检查钱包状态（本工具已加只读探测器）：

    python scripts/wallet_probe.py status

    python scripts/wallet_probe.py settings

    python scripts/wallet_probe.py address

需要开发者模式时，必须在 Binance App 内明确自行启用。高级外部交易权限会扩大风险。

## 3. Binance 官方交易两步法

仔细阅读官方钱包 Skill 的 external-sign.md 与 preflight.md；语法可能升级，应以当前版本为准。

1. 从 Binance 官方钱包读取真实钱包地址，以及官方核验的目标合约和调用 data；如果某个字段拿不到就停。
2. 由 Agent 调用 **预览**（下面的字段必须从真实查询获得）：

    baw contract-call preview --binanceChainId 56 --from <真实钱包地址> --to <核实合约地址> --value <整数wei> --inputData <核实的合约calldata> --json

3. AI 必须展示 parsedTx、simulationResult、risks、authorityChanges、requireConfirmation 以及 requestId；解释可能产生的资产和授权变化。
4. 用户必须在**这次预览之后**确认这笔具体交易（合约、金额、数量、最大成本、钱包、授权范围）。不要以之前一句“以后自动打新”当作永久授权。
5. 用户明确确认后，由官方钱包 Skill 执行：

    baw contract-call execute --requestId <上一步成功预览的requestId> --json

   **注意：** 币安的自动签名权限开启后，execute 可能直接广播到链上，不一定再次弹手机确认，所以 AI 必须在 execute 前征得明确同意。
6. 查看 BROADCASTED / PENDING_CONFIRMATION / REJECTED 等结果，并以 txHash 的区块浏览器确认交易状态。调用完成不能算 Mint 成功。
7. Mint 后检查是否产生代币授权，必要时在用户确认后撤销或关闭开发者模式。

## 4. Four.meme

Four.meme 社区发布的工具提供新币、报价、事件信息和部分链上交易。但其写入操作可能通过本地 PRIVATE_KEY 签名，**不是**币安 Agentic Wallet 的同一套无私钥权限体系。

可结合 Four.meme 的只读行情工具进行研究，但不要将任何私钥发进聊天、网页、GitHub Secret 或这个仓库。钱包执行应以使用者实际配对的官方钱包支持范围为准。

Four.meme 参考： https://github.com/four-meme-community/four-meme-ai/blob/main/skills/four-meme-integration/SKILL.md

## 5. Fast / Medium 怎么用

日常查活动、整理 Mint 规则：快模型 + 中档推理一般足够；合约解析和风险评估再使用更深入的推理。但模型速度不能代替合约预览，GitHub 定时扫描也不是秒级抢 Mint 系统。
