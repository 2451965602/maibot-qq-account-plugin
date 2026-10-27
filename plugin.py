"""Owner-scoped QQ account controls for MaiBot's SnowLuma adapter."""

from __future__ import annotations

from typing import Any, ClassVar

from maibot_sdk import MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType
from pydantic import Field


class PluginSectionConfig(PluginConfigBase):
    """MaiBot's mandatory versioned plugin section."""

    enabled: bool = Field(default=True, description="是否启用 QQ 账号工具")
    config_version: str = Field(default="1.0.5", description="插件配置版本")


class AccountSettings(PluginConfigBase):
    """Runtime settings for self-account mutations."""

    owner_qq: str = Field(
        default="",
        description="主人 QQ 号；仅该 QQ 发起的私聊可修改机器人账号。",
    )


class QQAccountConfig(PluginConfigBase):
    """Plugin settings shown in MaiBot WebUI."""

    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    account: AccountSettings = Field(default_factory=AccountSettings)


class QQAccountPlugin(MaiBotPlugin):
    """Expose a deliberately small allowlist of self-account OneBot actions."""

    config_model: ClassVar[type[PluginConfigBase] | None] = QQAccountConfig

    async def on_load(self) -> None:
        """Required MaiBot lifecycle hook; tools are registered by decorators."""
        self.ctx.logger.info("QQ 账号工具已加载")

    async def on_unload(self) -> None:
        """Required MaiBot lifecycle hook; this plugin has no background tasks."""
        self.ctx.logger.info("QQ 账号工具已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        """Apply WebUI changes to this plugin's own configuration."""
        if scope == "self":
            self.set_plugin_config(config_data)

    async def _call_action(self, action_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call SnowLuma through its public adapter API, never via a raw socket."""

        response = await self.ctx.api.call(
            "adapter.snowluma.action.call", action_name=action_name, params=params
        )
        if not isinstance(response, dict):
            return {"success": False, "error": "适配器没有返回有效结果"}
        if response.get("success") is False:
            return {"success": False, "error": str(response.get("error") or "适配器调用失败")}
        if str(response.get("status") or "ok").lower() != "ok":
            return {"success": False, "error": str(response.get("message") or "OneBot 动作失败")}
        if response.get("retcode") not in (None, 0, 1):
            return {"success": False, "error": str(response.get("message") or "OneBot 动作失败")}
        return {"success": True, "response": response}

    async def _owner_error(self, stream_id: str) -> dict[str, Any] | None:
        """Only allow the configured owner's trusted private-chat stream.

        ``stream_id`` is overwritten by the Core after model arguments are parsed.
        Sender-related kwargs are deliberately never read because a model can supply
        them itself.
        """
        owner_qq = str(self.config.account.owner_qq or "").strip()
        current_stream_id = str(stream_id or "").strip()
        if not owner_qq or not current_stream_id:
            return {"success": False, "error": "此操作仅限已配置主人发起的 QQ 私聊"}
        try:
            result = await self.ctx.chat.get_stream_by_user_id(owner_qq, platform="qq")
        except Exception:
            return {"success": False, "error": "此操作仅限已配置主人发起的 QQ 私聊"}
        if not isinstance(result, dict) or result.get("success") is not True:
            return {"success": False, "error": "此操作仅限已配置主人发起的 QQ 私聊"}
        stream = result.get("stream")
        if not isinstance(stream, dict):
            return {"success": False, "error": "此操作仅限已配置主人发起的 QQ 私聊"}
        if (
            str(stream.get("user_id") or "").strip() != owner_qq
            or str(stream.get("stream_id") or stream.get("session_id") or "").strip() != current_stream_id
            or stream.get("chat_type") != "private"
            or stream.get("is_group_session") is not False
        ):
            return {"success": False, "error": "此操作仅限已配置主人发起的 QQ 私聊"}
        return None

    @Tool(
        name="qq_set_profile",
        platforms="qq",
        description="仅允许已配置主人从 QQ 私聊修改机器人自己的昵称、个人说明或性别。只能改当前登录账号。",
        parameters=[
            ToolParameterInfo(name="nickname", param_type=ToolParamType.STRING, description="新昵称；未填写则保持原值", required=False),
            ToolParameterInfo(name="personal_note", param_type=ToolParamType.STRING, description="新的个人说明；未填写则保持原值", required=False),
            ToolParameterInfo(name="sex", param_type=ToolParamType.INTEGER, description="0 未知、1 男、2 女；未填写则保持原值", required=False),
        ],
    )
    async def set_profile(
        self, nickname: str = "", personal_note: str | None = None, sex: int | None = None, stream_id: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        if not self.config.plugin.enabled:
            return {"success": False, "error": "QQ 账号工具已禁用"}
        if error := await self._owner_error(stream_id):
            return error
        params: dict[str, Any] = {}
        if nickname.strip():
            params["nickname"] = nickname.strip()[:64]
        if personal_note is not None:
            params["personal_note"] = str(personal_note)[:256]
        if sex is not None:
            if sex not in (0, 1, 2):
                return {"success": False, "error": "sex 只能是 0、1 或 2"}
            params["sex"] = sex
        if not params:
            return {"success": False, "error": "至少提供一项要修改的资料"}
        result = await self._call_action("set_qq_profile", params)
        return {"success": result["success"], "changed": list(params), **({"error": result["error"]} if not result["success"] else {})}

    @Tool(
        name="qq_set_signature",
        platforms="qq",
        description="仅允许已配置主人从 QQ 私聊修改机器人自己的 QQ 个性签名。传空字符串会清空签名。",
        parameters=[
            ToolParameterInfo(name="long_nick", param_type=ToolParamType.STRING, description="新的个性签名", required=True),
        ],
    )
    async def set_signature(self, long_nick: str = "", stream_id: str = "", **kwargs: Any) -> dict[str, Any]:
        if not self.config.plugin.enabled:
            return {"success": False, "error": "QQ 账号工具已禁用"}
        if error := await self._owner_error(stream_id):
            return error
        if not isinstance(long_nick, str) or len(long_nick) > 256:
            return {"success": False, "error": "个性签名必须是最多 256 个字符的字符串"}
        result = await self._call_action("set_self_longnick", {"long_nick": long_nick})
        return {"success": result["success"], **({"error": result["error"]} if not result["success"] else {})}

    @Tool(
        name="qq_set_avatar",
        platforms="qq",
        description="仅允许已配置主人从 QQ 私聊通过 HTTPS 图片直链修改机器人自己的 QQ 头像。不接受服务器本地路径。",
        parameters=[
            ToolParameterInfo(name="url", param_type=ToolParamType.STRING, description="HTTPS 图片直链", required=True),
        ],
    )
    async def set_avatar(self, url: str = "", stream_id: str = "", **kwargs: Any) -> dict[str, Any]:
        if not self.config.plugin.enabled:
            return {"success": False, "error": "QQ 账号工具已禁用"}
        if error := await self._owner_error(stream_id):
            return error
        normalized = str(url or "").strip()
        if not normalized.startswith("https://") or len(normalized) > 2048:
            return {"success": False, "error": "头像必须是 HTTPS 图片直链"}
        result = await self._call_action("set_qq_avatar", {"file": normalized})
        return {"success": result["success"], **({"error": result["error"]} if not result["success"] else {})}

    @Tool(
        name="qq_set_online_status",
        platforms="qq",
        description="仅允许已配置主人从 QQ 私聊设置机器人自己的 QQ 在线状态：10 在线、30 离开、50 忙碌、70 隐身。",
        parameters=[
            ToolParameterInfo(name="status", param_type=ToolParamType.INTEGER, description="在线状态 ID", required=True),
        ],
    )
    async def set_online_status(self, status: int = 0, stream_id: str = "", **kwargs: Any) -> dict[str, Any]:
        if not self.config.plugin.enabled:
            return {"success": False, "error": "QQ 账号工具已禁用"}
        if error := await self._owner_error(stream_id):
            return error
        if status not in (10, 30, 50, 70):
            return {"success": False, "error": "status 只能是 10、30、50 或 70"}
        result = await self._call_action("set_online_status", {"status": status, "ext_status": 0, "battery_status": 100})
        return {"success": result["success"], "status": status, **({"error": result["error"]} if not result["success"] else {})}

    @Tool(
        name="qq_set_qzone_block",
        platforms="qq",
        description="仅允许已配置主人从 QQ 私聊管理机器人自己 QQ 空间的黑名单；enable=true 拉黑，false 解除。",
        parameters=[
            ToolParameterInfo(name="target_qq", param_type=ToolParamType.STRING, description="目标 QQ 号", required=True),
            ToolParameterInfo(name="enable", param_type=ToolParamType.BOOLEAN, description="是否拉黑", required=False),
        ],
    )
    async def set_qzone_block(self, target_qq: str = "", enable: bool = True, stream_id: str = "", **kwargs: Any) -> dict[str, Any]:
        if not self.config.plugin.enabled:
            return {"success": False, "error": "QQ 账号工具已禁用"}
        if error := await self._owner_error(stream_id):
            return error
        target = str(target_qq or "").strip()
        if not target.isdecimal() or not 5 <= len(target) <= 12:
            return {"success": False, "error": "target_qq 必须是 5–12 位数字 QQ 号"}
        result = await self._call_action("set_qzone_ban", {"user_id": int(target), "enable": bool(enable)})
        return {"success": result["success"], "user_id": target, "blocked": bool(enable), **({"error": result["error"]} if not result["success"] else {})}


def create_plugin() -> QQAccountPlugin:
    return QQAccountPlugin()
