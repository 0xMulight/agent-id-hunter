# 存储与兼容性

核对日期：2026-11-04。社区多钱包管理扩展，需另行安装币安官方 CLI；不包含官方 CLI 代码。

## 已核对的来源

- [币安官方 Skill](https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/SKILL.md)
- [官方认证流程与 verify 参数](https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/references/authentication.md)
- [官方 wallet status / address 返回结构](https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/references/wallet-view.md)
- [官方 CLI 预检与安装](https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/references/preflight.md)
- [官方 npm 1.12.0 元数据](https://registry.npmjs.org/@binance/agentic-wallet/1.12.0)

从 npm 官方发布包核对 dist/index.js，验证了发布包 sha512 integrity。没有从社区改版推断官方支持的环境变量。已审核文件 SHA-256：

    e63e2dff4a6d267d2375a0bbcdf518f10ddd04b0ffaff378c265a26f0961fe4f

## baw 1.12.0 的实际行为

| 项目 | 文件存储 | 可用系统钥匙串 |
| --- | --- | --- |
| BINANCE_BAW_DIR | 改变 session.json 所在目录 | 改变本地 clientId 文件目录 |
| BINANCE_INSTANCE_ID | 参与 clientId/sessionId 加密密钥派生；必须保持原值 | 参与本地 clientId 加密；不会隔离钥匙串条目 |
| sessionId 保存位置 | 目标目录中的加密 session.json | 全局 service=baw、account=agentSessionId |
| 仅靠目录和实例 ID 实现隔离 | 可作为配置基础，仍需核对状态和地址 | 不足；第二次配对可能影响第一个会话 |

脚本只允许已审核 CLI、且无法加载系统 keytar 模块的环境继续登录。能加载 keytar 时，无论服务探测成功与否都停止，避免把探测失败误判为可靠隔离。doctor 不读取现有 baw 凭证、不调用 auth、不导入 baw 主程序。

BINANCE_KEYTAR_SERVICE 未出现在所审核官方构建中；不能把设置该变量当作隔离方案。不要给已登录的 1 号钱包补设新的 INSTANCE_ID。不同实例 ID 不会解除平台会话期限、App 权限或活动资格限制。

## 版本与异常处理

当前脚本有意限制于已审核构建。若 CLI 版本或文件指纹不同，读取当前官方包的目录选择、加密密钥来源和钥匙串命名，再在隔离测试中确认行为；完成审核后才更新版本与指纹。不要删除检查以让 doctor 通过，也不要自动降级用户环境。

钥匙串能够加载时，当前 helper 不实施同一 OS 用户下的多会话登录。可选独立 OS 用户或彼此独立的运行环境；仅新建聊天 Bot 或只隔离文件夹不够。不得复制会话到其他机器，移动环境需重新合法配对。

私有 profiles.json 中的新实例 ID 是随机固定值；POSIX 下配置文件权限为 600，新钱包目录为 700。Windows 需核对 ACL，chmod 不是等价保障。离线测试验证环境分配、数据保护、命令限制与地址核对，不代表通过了用户实际钱包的双会话测试。
