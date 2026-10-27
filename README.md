# QQ 账号管理

为 MaiBot 的 SnowLuma 适配器提供**仅主人可调用**的机器人自身 QQ 账号工具：昵称/个人说明、个性签名、头像、在线状态与 QQ 空间黑名单。

## 功能

- 修改机器人自己的昵称、个人说明和性别；
- 修改个性签名、HTTPS 头像与在线状态；
- 管理机器人自身 QQ 空间黑名单；
- 自动拒绝无法验证为主人的调用。

## 安装与配置

从 MaiBot 插件市场安装，或将仓库目录复制至 MaiBot 的 `plugins/`。通过 MaiBot 运行时配置或 WebUI 设置：

```toml
[account]
owner_qq = "你的 QQ 号"
```

重启 Core 后生效。未配置 `owner_qq` 时，所有账号修改都会拒绝。

- `config.toml` 已在 `.gitignore` 中忽略，配置由 MaiBot 运行时管理。
- 插件不使用、请求或记录审批口令。

## 使用

主人在与机器人 QQ 私聊时明确提出修改要求后，模型会按需调用对应工具；例如“把你的在线状态改成忙碌”或“把 QQ 空间拉黑 12345678”。所有群聊请求一律拒绝。

## 安全边界

- 只调用 SnowLuma 适配器公开的 `adapter.snowluma.action.call`；不建立第二条 QQ 连接。
- 授权仅以 Core 强制注入的当前聊天流为准：插件通过宿主 `chat.get_stream_by_user_id(owner_qq)` 反查主人私聊流，并要求该流与当前流完全匹配；不信任模型可提供的 `user_id`、`message` 或其他身份参数。
- 头像仅接受 HTTPS URL，拒绝服务器本地文件路径。
- 不提供导入 QQ 收藏表情功能：当前适配器没有可安全验证的等价收藏 API。
