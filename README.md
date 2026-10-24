# Agent ID Hunter

**为所有关注币安 Agent ID（.ai）活动的用户准备的开源 Skill。**

用法很简单：先找官方活动，再核对是否真的要求持有 .ai，最后生成报名、绑定、有效任务、证明和领奖清单。**不需要事先填写任何人的 Agent ID**，也不会自动签名、转账、Mint 或交易。

> 社区项目，非 Binance、SPACE ID、BNB Chain、Four.meme 官方产品。活动未官宣时，不预测资格或奖励。

## 现在能做什么

- **官方线索扫描**：读取白名单网站的公开页面，发现新增的 Agent ID/Agentic Wallet 相关链接，保存本地结果，标记抓取失败。
- **持有人任务检查**：只在官方活动卡明确要求 .ai 时，提示核对 .ai 所有权；仅填写名称绝不代表持有权已确认。
- **报名防漏**：对照活动规则检查报名、绑定钱包、截图/链接、有效计数、截止与领奖步骤。
- **可选 GitHub 定时提醒**：Actions 每 6 小时运行，但必须自行开启仓库变量。发现新的直接 Agent ID 线索，可选择自动创建待核验 Issue。GitHub Issue 不是手机推送。

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

### 活动资格核对

编辑一份活动卡（参见 `examples/activity.example.json`），**必须人工确认并填写官方规则**，然后运行：

```bash
python scripts/checklist.py --activity examples/activity.example.json
```

可选个人资料 `data/profile.json`，例如 `{"agent_id":"yourname.ai"}`。不填也可运行；填写了也必须核验真正持有者/活动绑定地址。

```bash
python scripts/checklist.py --activity examples/activity.example.json --profile data/profile.json
```

## 定时扫描（可选）

仓库 Actions > **Agent ID Hunter scout** > Run workflow 可手动运行。要定时运行，在 Settings > Secrets and variables > Actions > Variables 添加：

- `ENABLE_AGENT_ID_WATCH=true`：每 6 小时扫描一次。
- `ENABLE_AGENT_ID_ALERTS=true`：发现新的 *Agent ID 强相关线索* 时创建待核验 GitHub Issue。需要 Issues 功能启用、Actions 具备 issues: write 权限。

首次扫描建立基线，**不直接把历史页面当成新消息提醒**。用 Actions cache 保存扫描状态；缓存可能过期或被清除，所以不能保证绝不重复提醒。

## 能力边界

扫描发现的是“待核验线索”，不是正式活动认定；官方页面可能反爬、需要登录、动态加载或移动到其他网址。对交易和合约只给检查清单，所有签名、转账由用户自己在官方界面完成。不要把助记词、私钥、Binance UID 或敏感凭证写进配置。

代码使用 Python 3.10+ 标准库。执行 `python -m unittest discover -s tests -v` 可运行测试。

作者：[@0xMulight](https://github.com/0xMulight) · MIT
