# MaiBot QQ Account Plugin

为 MaiBot 的 SnowLuma 适配器提供**仅主人可调用**的机器人自身 QQ 资料工具：昵称/个人说明、个性签名、头像、在线状态与 QQ 空间黑名单。

## 安装

复制仓库目录至 MaiBot 的 `plugins/`，在 `config.toml` 设置：

```toml
owner_qq = "你的 QQ 号"
```

重启 Core 后生效。未配置 `owner_qq` 时，所有改动都会拒绝。

## 安全边界

- 只调用 SnowLuma 适配器公开的 `adapter.snowluma.action.call`；不建立第二条 QQ 连接。
- 头像仅接受 HTTPS URL，拒绝服务器本地文件路径。
- 不提供导入 QQ 收藏表情功能：当前适配器没有可安全验证的等价收藏 API。
