---
name: binance-wallet-multi
description: Configure and verify separate Binance Agentic Wallet (baw) sessions, preserve wallet 1, select wallets by number, and prepare a persistent wallet Bot handoff. Use for Grok Bot multi-wallet login, 多钱包/Agent ID 会话管理, adding wallet 2 or 3, and diagnosing cross-wallet session interference. Requires a local command runtime; defaults to authentication and read-only queries.
---

# 币安多钱包管家

实际建立配置并逐个验证登录。先保留原有钱包，再增加其他钱包。不要仅回传教程，也不要把配置文件存在当作登录成功。

## 先确认运行条件

1. 确认宿主能够运行 Python 3.10+、Node.js 和官方 baw CLI，并能持久保存本地私有文件。纯聊天环境无法操作本地钱包；缺少什么就明确报告什么。
2. 在 1 号钱包最初登录的同一用户、同一机器/容器和相同环境变量下工作。识别已有 BINANCE_BAW_DIR / BINANCE_INSTANCE_ID 与自定义启动器；来源不明时先查清，不要猜测、改值或试登录。
3. 将下方命令中的 <skill-dir> 换成本 Skill 实际安装目录，所有调用使用绝对脚本路径。运行：

    python3 <skill-dir>/scripts/wallet_profiles.py doctor

4. 阅读 [存储与兼容性](references/storage.md)。当前脚本检查官方 baw 1.12.0 的代码指纹，并检测系统钥匙串。发现可用钥匙串、探测不确定或未审核的新版本时停止新增登录。不要改源码、注入 preload、伪造设备身份、关闭钥匙串或自动降级以绕过检查。

doctor 不登录钱包。baw 1.12.0 的钥匙串条目是全局共享的；BINANCE_INSTANCE_ID 不会隔离该条目。仅在确定使用文件存储的环境中继续本流程。独立 OS 用户或真正隔离的运行环境需要分别安装和配对，不能承诺复用这里的同环境方案。

## 建立本地编号

确认原钱包环境正确后运行：

    python3 <skill-dir>/scripts/wallet_profiles.py init
    python3 <skill-dir>/scripts/wallet_profiles.py add --wallet 2
    python3 <skill-dir>/scripts/wallet_profiles.py list

- init 只登记原目录和原 INSTANCE_ID，不读取、覆盖、复制或清理 ~/.baw/session.json。重复运行保留现有配置。
- 新钱包默认使用 ~/.baw-wallet2、~/.baw-wallet3 等目录，自动生成各自固定的随机 INSTANCE_ID。不要把所有钱包都设成公开示例 wallet-2，也不要在登录后更换值。
- 私有配置默认存于 ~/.config/baw-multi/profiles.json，包含实例密钥材料。留在运行机器上，不读取给用户、贴进聊天、提交 GitHub、复制进 Skill 或放到跨设备同步文件夹。
- home 不持久时，先选择一个私有且持久的运行目录，通过 BAW_MULTI_CONFIG 指定其中的 profiles.json，并在 add 时用 --directory 指定其他钱包的持久目录。1 号钱包原目录不持久时先报告限制，不自行搬迁或重新加密。
- 每次只向当前子进程传入该钱包环境；不要全局 export 一个钱包的变量，不要修改其他 Bot 的启动环境。

Windows 使用 python 替换 python3；保持使用同一 Windows 用户，确认目录 ACL 仅向该用户开放。WSL、Windows 本机和远程 Grok 运行容器属于不同环境，不能假定共享会话。

## 逐个登录与验收

1. 先只读检查 1 号钱包，不重新 signin 已连接的钱包：

    python3 <skill-dir>/scripts/wallet_profiles.py run --wallet 1 status
    python3 <skill-dir>/scripts/wallet_profiles.py run --wallet 1 address

2. 连接 2 号钱包：

    python3 <skill-dir>/scripts/wallet_profiles.py run --wallet 2 signin

将实际返回的 pairingCode 和 urlForWeb 原样交给当前用户，标注这是 2 号钱包。链接使用可点击格式，不缩短、不重建；仅让用户在币安 App 核对配对码并确认。不索取密码、私钥、助记词或 API Key。返回 ALREADY_CONNECTED 时直接核对状态和地址。

3. 使用本次 2 号 signin 实际返回的 qrCodeId：

    python3 <skill-dir>/scripts/wallet_profiles.py run --wallet 2 verify --qr-code-id <actual-qrCodeId>

保持 verify 进程运行至成功、拒绝或约五分钟超时；通过短间隔工具轮询保持用户可见的进度，不要杀掉进程后宣称完成。配对码过期就重新 signin，不反复使用旧 qrCodeId。一次只配对一个钱包，避免混用二维码。

4. 再检查所有钱包：

    python3 <skill-dir>/scripts/wallet_profiles.py check

检查 wallet status 均为 CONNECTED；展示每个钱包的完整地址。脚本检测同一链地址重复、与已确认地址不符以及未连接的钱包。不同 EVM 链出现同一个钱包地址属于正常情况；检测比较不同编号在同一链上的地址。发现重复就停止，不能把两个编号当作两个独立钱包。

5. 请用户在 App 中核对编号与地址，再登记该用户确认的真实地址：

    python3 <skill-dir>/scripts/wallet_profiles.py pin --wallet 1 --chain 56 --address <user-confirmed-address>
    python3 <skill-dir>/scripts/wallet_profiles.py pin --wallet 2 --chain 56 --address <user-confirmed-address>

脚本再次读取地址，匹配后才保存绑定。按实际使用的链绑定地址，不要把 Solana 地址填成 EVM 地址。再按编号查询 agent-id 和 settings，核对 .ai 名称和会话到期时间。不从“登录成功”推断已领取 Agent ID。

6. 再开一个全新命令进程运行 check。只有状态、不同钱包地址及用户确认的对应关系全部验证后才报告完成。3 号钱包按 add --wallet 3 扩展，同样逐个验证。

输出简洁表格：编号、连接状态、链、完整地址、Agent ID、地址确认情况。标明失败或待确认项；没有真实钱包环境时写“尚未实测登录”，不能把离线脚本测试说成配对成功。

## 以后按编号调用

例如用户说“查 2 号余额”：

    python3 <skill-dir>/scripts/wallet_profiles.py run --wallet 2 balance

可用只读 operation：status、address、balance、agent-id、settings、chains、tx-history。每次显示编号；具体活动前核对对应地址和 Agent ID。编号有歧义时让用户选定，不默认使用最近操作的钱包。

脚本的命令入口不提供转账、兑换、Mint、授权、签名、登出或任意命令透传。需要这些操作时：

1. 读取币安官方 Agentic Wallet Skill 对应的当前命令文档，重新核对指定编号的状态、已绑定地址、链及必要的 Developer Mode。
2. 仅在内存中通过本脚本的 load / select / environment 取得目标钱包环境；不打印或生成带 INSTANCE_ID 的命令文件。每次 preview 与 execute 使用同一编号的环境，通过 runtime.lock 串行调用。
3. 展示编号、完整地址、操作、目标合约/收款方、数量、费用与官方 preview 风险。即使免费 Mint 也须获得该笔操作的明确确认，不由配置多钱包推断交易授权。
4. preview 返回错误就停止。获得确认后才按官方流程执行；参数、钱包或 requestId 对应关系发生变化时重新预览并确认。交易哈希仅表示提交，确认链上状态后再报告完成。

保留每个钱包原有的期限和平台会话限制，不承诺永久在线、不承诺多钱包奖励可以叠加。遇到会话到期只重新配对对应编号，不自动 signout 所有钱包。

## 主 Bot 与子 Bot

按 [Bot 交接规则](references/sub-bot.md) 生成不含凭证的交接。用户要求建立专门的钱包 Bot，且宿主支持持久创建时，再建立一个负责所有编号的专门 Bot；不要每个钱包建一个 Bot。没有该能力就给出可复制的交接内容，不能将一次性子代理声称为已经安装的长期 Bot。

主 Bot 和钱包 Bot 只共享必要的调用方式与地址映射，不假定自动共享聊天历史、文件系统或登录会话。
